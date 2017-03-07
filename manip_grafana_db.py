#!/usr/bin/env python
'''Manipulate the grafana database.

'''

import dashboard_processors
import os
from pipes import quote
import shlex
import simplejson as json
import sql_connector
from subprocess import Popen, PIPE
import sys
from time import gmtime, sleep, strftime, time
import triconf
from simple_logger import configure_file_and_console

CONFIGS = None
LOGGER = None


class GrafanaDataManipulationException(Exception):
    def __init__(self, msg=''):
        super(GrafanaDataManipulationException, self).__init__(msg)


def initialize(**kargs):
    '''Module level CONFIGS initializer. Returns configurations object.

    '''
    global CONFIGS
    CONFIGS = triconf.conf.initialize('manip_grafana_db', conf_file_names=['conf.ini'],
                                      log_file='manip_grafana_db.log', **kargs)
    dashboard_processors.initialize(**kargs)
    return CONFIGS


def initialize_logger():
    '''Setup the logger with config values.
    '''
    global LOGGER
    LOGGER = configure_file_and_console(module_name='manip_grafana_db',
                                        log_path='manip_grafana_db.log',
                                        level=CONFIGS.log_level)
    LOGGER.debug('Initialized @ %s', strftime('%Y-%m-%dT%H:%M:%S', gmtime()))
    dashboard_processors.LOGGER = LOGGER


def iterate_grafana_dashboards(fun):
    '''Iterate through grafana dashboards and run the given callable fun on
    the results. Object passed to fun is a named_tuple with the field
    names corresponding to the row names.

    '''
    global CONFIGS
    if not hasattr(fun, '__call__'):
        raise GrafanaDataManipulationException('"fun" is not callable.')
    g_start = time()
    LOGGER.info('gathering dashboards')
    dashboards = sql_connector.get_dashboards()
    LOGGER.info('gathering done in %ss', time()-g_start)
    LOGGER.info('iterating')
    iter_start = time()
    count = 0
    proc_pool = []
    proc_pool_output = ''
    for dash in dashboards:
        slug = sql_connector.DASHBOARD_RECORD(*dash).slug
        sys.stdout.write('%s\r' % {0: '|', 1: '/', 2: '-', 3: '\\'}[count % 4])
        sys.stdout.flush()
        count += 1
        while len(proc_pool) >= int(CONFIGS.process_count_limit):
            for proc in proc_pool:
                if not proc[1].poll() is None:
                    proc_pool_output += proc[1].communicate()[1]
                    proc_pool.remove(proc)
                else:
                    sleep(0.05)
        cmd_string = 'python manip_grafana_db.py --processor %s --dashboard %s' \
                     % (quote(CONFIGS.db_iterator), quote(slug))
        if CONFIGS.processor_argument:
            cmd_string += ' --processor-arg %s ' % quote(CONFIGS.processor_argument)
        proc_pool.append((slug, Popen(shlex.split(cmd_string), stdout=PIPE, stderr=PIPE)))
    for _, proc in proc_pool:
        _, stderr = proc.communicate()
        if stderr:
            proc_pool_output += stderr
    LOGGER.info("%s\nIterating done in %ss." % (''.join(proc_pool_output), time()-iter_start))


def main():
    '''Returns True if completed successfuly, False if encountered an
    error.

    '''
    if CONFIGS.dry_run:
        print('dry run')
        print(CONFIGS)
        exit(0)
    if CONFIGS.list_processors:
        print(dashboard_processors.list_processors())
        exit(0)
    if CONFIGS.db_iterator:
        iterate_grafana_dashboards(getattr(dashboard_processors, CONFIGS.db_iterator))
        exit(0)
    if CONFIGS.db_processor:
        if not CONFIGS.dashboard:
            print('processor needs a specified --dashboard, otherwise use --iterator.')
            exit(1)
        if ' ' in CONFIGS.dashboard:
            print('db_processor needs dashboard slug, not title as there may be duplicates.')
            exit(1)
        processor_arg = None if not hasattr(CONFIGS, 'processor_argument') \
            else CONFIGS.processor_argument
        try:
            getattr(dashboard_processors,
                    CONFIGS.db_processor)(sql_connector.get_dashboard(CONFIGS.dashboard),
                                          processor_arg)
        except KeyError:
            print('Unknown processor "%s"' % CONFIGS.db_processor)
            exit(1)
        exit(0)
    if CONFIGS.delete:
        sql_connector.delete_dashboards()
        exit(0)
    dashboards = []
    if os.path.isdir(CONFIGS.dashboards):
        dashboards = [os.path.join(CONFIGS.dashboards, x) for x in os.listdir(CONFIGS.dashboards)]
    elif os.path.isfile(CONFIGS.dashboards):
        dashboards.append(CONFIGS.dashboards)
    else:
        LOGGER.error('Unknown file %s.', CONFIGS.dashboards)
        exit(0)

    for dashboard in dashboards:
        if sql_connector.set_dashboard(json.load(open(dashboard))):
            LOGGER.info('Saved dashboard %s to database.', dashboard.slug)

    sql_connector.close()


if __name__ == '__main__':
    START_TIME = time()
    initialize()
    # Keep arg_parser operations in the area dedicated to dealing with
    # being called from the cli.
    ARG_PARSER = triconf.conf.ArgumentParser(CONFIGS,
                                             description='Used to manipulate grafana databases.')
    ARG_PARSER.add_argument('-d', dest='dashboards',
                            help='Grafana json dashboard (file or directory) to push into database.')
    ARG_PARSER.add_argument('--dry-run', action='store_true',
                            help='Don\'t actually do anything.')
    ARG_PARSER.add_argument('--delete', action='store_true',
                            help='Delete quorra graphs explicitly from grafana_test database.')
    ARG_PARSER.add_argument('--iterator', dest='db_iterator',
                            help='Specify processor function to iterate over per dashboard in db.')
    ARG_PARSER.add_argument('--processor', dest='db_processor',
                            help='Specify processor function to operate on a specified dashboard.')
    ARG_PARSER.add_argument('--processor-argument', default=None,
                            help='Specify argument (or comma separated list of arguments) for processor.')
    ARG_PARSER.add_argument('--dashboard', help='Specific Grafana dashboard to use with --processor.')
    ARG_PARSER.add_argument('--list-processors', action='store_true', dest='list_processors',
                            help='List possible database iterators to use with --iterator or --processor.')
    CONFIGS(ARG_PARSER.parse_args())
    initialize_logger()
    try:
        main()
    except KeyboardInterrupt:
        LOGGER.error('User exited.')
        exit(0)
    except Exception as exc:
        import traceback
        print(traceback.format_exc())
        LOGGER.error('Finished ABNORMALLY: %s after %s seconds: %s.', exc, (time()-START_TIME),
                     CONFIGS.processor_argument)
        exit(0)
    LOGGER.debug('Finished normally after %s seconds.', (time()-START_TIME))
