'''Processors to be used by manip_grafana_db

'''
import simplejson as json
import re
import rpn
import sql_connector
import validate_metrics

LOGGER = None
METRIC_CATEGORIES = ('md', 'agg', 'collectd')
PROCESSORS = {}


class ProcessorException(Exception):
    def __init__(self, msg=''):
        super(ProcessorException, self).__init__(msg)


def initialize(**kargs):
    validate_metrics.initialize(**kargs)


def list_processors():
    return '\n\n'.join(['%s - %s'
                        % (i, PROCESSORS[i].__doc__.strip())
                        for i in PROCESSORS])


def _get_path(grafana_metric_path):
    '''Remove formulas and aliases etc to return just the metric path.

    Path always has '.' in it to join metric attributes, join based on
    those in case there is a regex in the path.

    '''
    path = grafana_metric_path.split('(')[-1].split(')')[0].split(', ')[0]
    return path

def _get_target_panel_title(data, search_target):
    '''Search the json blob data for the search_target and return the
    'title' field of the json block that encapsulates the
    search_target block.

    '''
    graph_matches = []
    for panel in _yield_panels(data):
        if 'targets' not in panel:
            continue
        for target in panel['targets']:
            target_path = _get_path(target['target'])
            if search_target in target_path:
                panel_title = panel['title'] if panel['title'] \
                              else 'panelId=%s' % panel['id']
                graph_matches.append(panel_title)
    return graph_matches


def _get_template_variable_value(data, variable_name):
    '''Search the json blob data for the value to replace the given
    variable_name.

    '''
    try:
        json_data = json.loads(data)
    except Exception:
        json_data = json.loads(data, encoding="latin-1")
    variable_name = variable_name.strip('$')
    for template in json_data['templating']['list']:
        if template['name'] == variable_name:
            for option in template['options']:
                if option['selected']:
                    return option['value']


def _yield_panels(data):
    try:
        json_data = json.loads(data)
    except Exception:
        json_data = json.loads(data, encoding="latin-1")
    for rows in json_data['rows']:
        for panel in rows['panels']:
            if'targets' not in panel:
                continue
            yield panel


def make_db_processor(fun):
    def wrapper(dashboard, *args, **kargs):
        if hasattr(dashboard, 'slug'):
            return fun(dashboard, *args, **kargs)
        else:
            raise ProcessorException('Not %s is not a dashboard.' % dashboard)
    PROCESSORS[fun.__name__] = wrapper
    PROCESSORS[fun.__name__].__doc__ = fun.__doc__
    return wrapper


@make_db_processor
def find_dashboard_with_metric(dashboard, search_metric=None):
    '''Find the given metric in the dashboard.

    '''
    if not dashboard:
        return None
    if not search_metric:
        LOGGER.error(('find_dashboard_with_metric requires a search metric, '
                      'use --processor-argument from the cli.'))
        exit(0)
    target_regex = re.compile('target":\s*"([^"]*)"')
    matches_in_dashboard = []
    for match in target_regex.findall(dashboard.data):
        path = _get_path(match)
        program_id, _, working = path.partition('.')
        metric_name, _, working = working.partition('.')
        if path == search_metric:
            graph_matches = _get_target_panel_title(dashboard.data, path)
            matches_in_dashboard.append((dashboard.slug,
                                         ', '.join(graph_matches),
                                         'MATCH', search_metric))
        else:
            program_id_search_metric, _, working = search_metric.partition('.')
            metric_name_search_metric, _, working = working.partition('.')
            if program_id_search_metric == program_id \
               and metric_name_search_metric == metric_name:
                partial_path = '.'.join([program_id_search_metric,
                                         metric_name_search_metric])
                graph_matches = _get_target_panel_title(dashboard.data,
                                                        partial_path)
                matches_in_dashboard.append((dashboard.slug,
                                             ', '.join(graph_matches),
                                             'SIMILAR', path))
    if matches_in_dashboard:
        [LOGGER.info('"%s" graph "%s" contains %s: %s', *x)
         for x in matches_in_dashboard]
    else:
        LOGGER.debug('No matches for "%s" found.' % search_metric)


@make_db_processor
def find_dashboards_with_datasource(dashboard, processor_arg=None):
    '''Find dashboards with the specified datasource.

    '''
    regex = re.compile('datasource":\s*"%s"' % processor_arg)
    if regex.search(dashboard.data):
        LOGGER.info('Dashboard %s uses %s' % (dashboard.slug, processor_arg))


@make_db_processor
def find_dashboard_with_regex(dashboard, search_regex=None):
    '''Find the given metric in the dashboard.

    '''
    if not search_regex:
        LOGGER.error(('find_dashboard_with_metric requires a search metric, '
                      'use --search-metric from the cli.'))
        exit(0)
    target_regex = re.compile(search_regex)
    matches = []
    search = target_regex.search(dashboard.data)
    if search:
        matches.append([dashboard.slug, search.start(), search.end()])
    if matches:
        [LOGGER.info('"%s" graph matches: %s', x[0], search.string[x[1]:x[2]])
         for x in matches]
    else:
        LOGGER.debug('No matches for "%s" found.' % search_regex)


@make_db_processor
def update_datasource(dashboard, processor_arg=None):
    '''Updates current datasource in dashboards to the specified
datasource. processor_arg is expected to be a two element tuple as
"old_datasource, new_datasource".

    '''
    new_data = dashboard.data
    old, new = processor_arg.split(',')
    old = old.strip()
    new = new.strip()
    datasources = sql_connector.get_datasources()
    if not [x for x in datasources if x.name == new]:
        raise ProcessorException('%s is an unknown datasource.' % new)
    regex = re.compile('datasource":\s*"%s"' % old)
    new_data = regex.sub('datasource": "%s"' % new, new_data)
    # Don't update if there's no change
    if new_data != dashboard.data:
        LOGGER.info('updating %s', dashboard.slug)
        sql_connector.update_dashboard_data(new_data, dashboard.id)
    else:
        LOGGER.info('skipping %s, no change.', dashboard.slug)


@make_db_processor
def update_old_paths(dashboard, processor_arg=None):
    '''Try to modify the target path to the updated path.

    '''
    childless_params = ['avg', 'count', 'max', 'min', 'sum', 'value']
    new_data = dashboard.data
    for panel in _yield_panels(new_data):
        if panel['datasource'] in ['null', 'Aggregate All Global']:
            LOGGER.warn('In %s, skipping %s, global metric.', dashboard.slug,
                        ' and skipping '.join([x['target']
                                               for x in panel['targets']]))
            continue
        if 'targets' not in panel:
            continue
        ref_id = 'A'
        for target in panel['targets']:
            if 'datasource' in target:
                if target['datasource'] in ['null', 'Aggregate All Global']:
                    LOGGER.warn('In %s, skipping %s, global metric.',
                                dashboard.slug, target['target'])
                    continue
            path = _get_path(target['target'])
            new_path = None
            program_id, _, working = path.partition('.')
            update_able = False
            if '_rt' in program_id or 'collectd' in program_id:
                continue
            metric_name, _, working = working.partition('.')
            # Check if * has been used to indicate 'md'
            if metric_name == '*' and working[0] != '*':
                if validate_metrics.metric_exists('%s.md.%s'
                                                  % (program_id,
                                                     working.split('.')[0]))[-1]\
                   and validate_metrics.metric_exists('%s.md.%s'
                                                      % (program_id, working)):
                    LOGGER.warn('In %s, original metric good %s, just using * instead of md.',
                                dashboard.slug, path)
                    continue
            if len(path.split('.')) == 1:
                LOGGER.info('not update-able metric %s, unusual metric.', path)
                continue
            program_id_changed = False
            if program_id.startswith('$'):
                program_id_changed = program_id
                if 'Riak Multiview' in dashboard.slug:
                    program_id = 'riak_adquality_prod'
                else:
                    program_id = _get_template_variable_value(new_data,
                                                              program_id)
            metric_name_changed = False
            if metric_name not in METRIC_CATEGORIES:
                metric_type = 'md'
                if metric_name == 'quorra-conv':
                    metric_type = 'agg'
                    metric_name, _, working = working.partition('.')
                if metric_name.startswith('$'):
                    metric_name_changed = metric_name
                    metric_name = '*'
                # Old metric path was
                #   program_id.metric_name.<context_name_context_value>.<host>.<type>.value
                # New metric path is
                #   program_id.md.metric_name.<context_name>.<context_value>.host.<host>.<type>.value
                rest_of_path = working.split('.')
                if len(rest_of_path) == 3:  # If only three, just host, type value are being used
                    if rest_of_path[0].startswith('$') or rest_of_path[0].startswith('{'):
                        host_value = '*'
                    else:
                        host_value = rest_of_path[0]
                    new_path = '%s.%s.%s.host.%s.%s.%s' % (program_id, metric_type,
                                                           metric_name, host_value,
                                                           rest_of_path[1], rest_of_path[2])
                    if validate_metrics.metric_exists(new_path)[-1]:
                        update_able = True
                    # Have to put the templating back in after we test
                    # that the metric exists and is correct.
                    if rest_of_path[0].startswith('$') or rest_of_path[0].startswith('{'):
                        new_path = '%s.%s.%s.host.%s.%s.%s' % (program_id, metric_type, metric_name,
                                                               rest_of_path[0],
                                                               rest_of_path[1],
                                                               rest_of_path[2])
                else:  # If more than 3 left, contexts are being used
                    new_path = '%s.%s.%s' % (program_id, metric_type, metric_name)
                    children = validate_metrics.metric_children(new_path)
                    try:
                        # Go through children and attempt to match
                        # children to values in the path.
                        while children:
                            if len(children) == 1:  # context name
                                if children[0] in working:
                                    for context in rest_of_path:
                                        if children[0] in context:
                                            # If not a childless_param and '_' in param, it is
                                            # possibly a joined context_name_context_value
                                            if children[0] not in childless_params \
                                               and '_' in context:
                                                new_path += '.%s.%s' \
                                                            % (children[0],
                                                               context.split(children[0]+'_')[-1])
                                                rest_of_path.remove(context)
                                            else:
                                                rest_of_path.remove(context)
                                                new_path += '.%s' % children[0]
                                            break
                                elif '*' in rest_of_path:
                                    context_name = children[0]
                                    if context_name in rest_of_path:
                                        context_value \
                                            = rest_of_path.pop(rest_of_path.index(context_name)+1)
                                    elif '*' == rest_of_path[0]:
                                        rest_of_path.pop(0)  # Remove * for context name
                                    if rest_of_path:
                                        if rest_of_path[0] != context_name:  # Context out of place
                                            if '*' in rest_of_path:
                                                # Remove another *,
                                                # hoping context_value
                                                # is also represented
                                                # as *
                                                rest_of_path.remove('*')
                                                context_value = '*'
                                            else:
                                                context_value = '*'
                                    else:  # Out of rest of path options.. assume * mismatch
                                        context_value = '*'
                                    if context_name not in childless_params:
                                        new_path += '.%s.%s' % (context_name, context_value)
                                    else:
                                        new_path += '.%s' % context_name
                                        # remove whatever is being
                                        # used to represent the
                                        # childless param
                                        rest_of_path.pop()
                                elif children[0] == 'host':
                                    new_path += '.host.%s' % rest_of_path.pop(0)
                                else:
                                    # Mismatched placeholders
                                    if len(children) == 1:
                                        new_path = '%s.%s' % (new_path, children[0])
                                    if len(children) > 1:  # If we're dealing with a context
                                        new_path += '.*'
                                    else:
                                        machine, resp = validate_metrics.metric_exists(new_path)
                            else:
                                new_path += '.*'
                            children = validate_metrics.metric_children(new_path)
                    except Exception:
                        import pdb; pdb.set_trace()
                    if rest_of_path:
                        update_able = False
                    else:
                        update_able = True
                if metric_name_changed:
                    # Metric was a variable and was changed to *, so
                    # need to replace the * with the original variable.
                    metric_name = metric_name_changed
                    new_path = new_path.replace('%s.*' % metric_type,
                                                '%s.%s' % (metric_type, metric_name_changed))
                if program_id_changed:
                    # Program id was a variable and changed to a
                    # particular value, need to replace it with the
                    # original variable.
                    new_path = new_path.replace(program_id, program_id_changed, 1)
                if not update_able:
                    if not validate_metrics.metric_exists(path)[-1]:
                        LOGGER.warn('In %s: not update-able: orginal metric %s does not exist.',
                                    dashboard.slug, path)
                    else:
                        LOGGER.info('In %s: not update-able: %s -- %s', dashboard.title, path,
                                    new_path)
                else:
                    LOGGER.info('update-able metric: %s for %s', new_path, path)
                    new_target = _process_target(target, path, new_path)
                    new_target['refId'] = ref_id
                    new_data = new_data.replace(target['target'], new_target)
                    ref_id = chr(ord(ref_id) + 1)
            else:
                LOGGER.info('Already good %s', path)

    if new_data != dashboard.data:
        sql_connector.update_dashboard_data(new_data, dashboard.id)


def _update_node_alias(grafana_target):
    '''Given a new_pth, check if the grafana_target references aliases, if so,
    update the values for those node aliases.

    '''
    ret_target = grafana_target
    if 'aliasByNode' in ret_target:
        json_obj = rpn.grafana_target_to_json_obj(grafana_target)
        for func in json_obj:
            if func == 'aliasByNode':
                args = [str(int(i)*2) for i in json_obj[func][1:]]
                json_obj[func][1:] = args
        ret_target = rpn.json_obj_to_grafana_target(json_obj)
    return ret_target


def _process_target(target, path, new_path):
    '''Groom the target with the new_path and return a string
    representation of the new target.

    '''
    new_grafana_target = target['target']
    new_grafana_target = new_grafana_target.replace(path, new_path)
    new_grafana_target = _update_node_alias(new_grafana_target)
    return new_grafana_target


@make_db_processor
def list_dashboards_with_old_metric_paths(dashboard, processor_arg=None):
    '''Search the whole dashboard for potential old metrics (metrics that
do not have the md or agg namespace).

    '''
    target_regex = re.compile('target":\s*"([^"]*)"')
    for match in target_regex.findall(dashboard.data):
        working = _get_path(match)
        working = working.split('.')
        if 'collectd' in working[0]:
            continue
        if len(working) > 1 and working[1] not in METRIC_CATEGORIES:
            LOGGER.info('Old metric %s in %s' % (_get_path(match), dashboard.slug))
