#!/usr/bin/env python2.7
'''Check if metric is valid against datasources.

'''
import requests
import simplejson as json
import triconf
from urllib3.exceptions import LocationParseError

CONFIGS = ''
KNOWN_METRICS = {}


class ValidateMetricsError(Exception):
    def __init__(self, msg=''):
        super(ValidateMetricsError, self).__init__(msg)


def metric_children(metric, all_datasources=False):
    '''Display potential sub values for a given metric. Note that if the
    metric ends with a name, the actual children will be returned. If
    the metric ends with a *, the values that are valid replacements
    for the * will be returned. These are ultimately the same results
    for metric and metric.*, but in order to get the children of
    metric.*, metric.*.* needs to be used since a specific value under
    metric.<value> wasn't supplied.

    This assumes that every other object on the path is a specific
    context name with no contenders in the name space.

    '''
    ret = []
    if metric.endswith('.*'):
        # Complete the *, take the first value it completes to, then pass it on
        machine, resp = metric_exists(metric, query={'query': metric, 'format': 'completer'})
        if resp:
            metric = resp['metrics'][0]['path']+'.*'
    else:
        metric += '.*'
    if all_datasources:
        resp = metric_exists_all(metric,
                                 fetch_response=True,
                                 query={'query': metric, 'format': 'completer'})
        for machine, res in resp:
            ret_tup = (machine, [])
            if res:
                [ret_tup[1].append(x['name'])
                 for x in res['metrics'] if not x['name'] in ret_tup[1]]
            ret.append(ret_tup)
    else:
        machine, resp = metric_exists(metric, query={'query': metric, 'format': 'completer'})
        if resp:
            [ret.append(x['name']) for x in resp['metrics'] if not x['name'] in ret]
    return ret


def metric_exists(metric, query=None):
    '''Check if metric exists at all in any datasource, if true, returns
    machine the response was collected from and the json object
    returned from the datasource

    '''
    if metric in KNOWN_METRICS:
        return reduce(lambda x, y: ['', x[1] or y[1]], KNOWN_METRICS[metric])[1]
    query = query or {'query': metric}
    for datasource in CONFIGS.datasources:
        try:
            resp = requests.post(datasource.url+CONFIGS.graphite_find_endpoint,
                                 data=query, timeout=10)
        except (LocationParseError, requests.exceptions.InvalidSchema):
            print('Unable to connect to datasource: %s. Must be a complete url.'
                  % CONFIGS.graphite_server+CONFIGS.graphite_find_endpoint)
        except requests.exceptions.Timeout:
            continue
        if resp.status_code == 400:
            print("Got bad status code from find call: %s." % resp.text)
            raise ValidateMetricsError
        if resp.text == '[]' or resp.text == '{"metrics": []}':
            continue
        else:
            return (datasource.url, json.loads(resp.text))
    return (None, False)


def metric_exists_all(metric, fetch_response=False, query=None):
    '''Returns list structure indicating whether a metric exists for each
    datasource.

    '''
    ret = []
    if metric in KNOWN_METRICS:
        return KNOWN_METRICS[metric]
    query = query or {'query': metric}
    for datasource in CONFIGS.datasources:
        try:
            resp = requests.post(datasource.url+CONFIGS.graphite_find_endpoint, data=query)
        except (LocationParseError, requests.exceptions.InvalidSchema):
            print('Unable to connect to datasource: %s. Must be a complete url.'
                  % CONFIGS.graphite_server+CONFIGS.graphite_find_endpoint)
        if resp.status_code == 400:
            print("Got bad status code from find call: %s." % resp.text)
            raise ValidateMetricsError
        if resp.text == '[]' or resp.text == '{"metrics": []}':
            ret.append((datasource.name, False))
        else:
            ret.append((datasource.name, json.loads(resp.text) if fetch_response else True))
    KNOWN_METRICS[metric] = ret
    return ret


def initialize(**kargs):
    global CONFIGS
    CONFIGS = triconf.conf.initialize('validate_metrics',
                                      conf_file_names=['conf.ini', 'datasources.ini'],
                                      **kargs)
    return CONFIGS


if __name__ == '__main__':
    from pprint import pprint
    CONFIGS = initialize()
    PARSER = triconf.conf.ArgumentParser(CONFIGS)
    RESPONSE = None
    PARSER.add_argument('metric')
    PARSER.add_argument('--all-datasources', action='store_true',
                        help='Check metric against all datasources.')
    PARSER.add_argument('--children', action='store_true',
                        help='Return child values for given metric.')
    PARSER.add_argument('--specific-datasource',
                        help=('Only check metric against specific datasource '
                              '(provide url or name of datasource in datasources.ini.'))
    CONFIGS(PARSER.parse_args())  # CONFIGS({'cli': parser.parse_args()})
    if CONFIGS.specific_datasource:
        if hasattr(CONFIGS.datasources, CONFIGS.specific_datasource):
            CONFIGS.datasources = [getattr(CONFIGS.datasources, CONFIGS.specific_datasource)]
        else:
            CONFIGS.datasources = [triconf.conf.Namespace(url=CONFIGS.specific_datasource,
                                                          name='User specified datasource')]
    try:
        if CONFIGS.all_datasources and CONFIGS.children:
            RESPONSE = metric_children(CONFIGS.metric, all_datasources=True)
            RESPONSE.sort(key=lambda x: x[1])  # Put most relevant results at the bottom
            pprint(RESPONSE)
        elif CONFIGS.all_datasources:
            RESPONSE = metric_exists_all(CONFIGS.metric)
            RESPONSE.sort(key=lambda x: x[1])  # Put most relevant results at the bottom
            pprint(RESPONSE)
        elif CONFIGS.children:
            pprint(metric_children(CONFIGS.metric))
        else:
            print(metric_exists(CONFIGS.metric))
    except KeyboardInterrupt:
        print('\naborted\n')
