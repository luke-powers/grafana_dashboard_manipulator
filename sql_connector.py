#!/usr/bin/env python
'''Connect to sql

'''
#TODO: should really be using an orm like sqlalchemy

from collections import namedtuple
import MySQLdb
from getpass import getpass
from random import randint
import simplejson as json
import triconf

CONFIGS = None
DASHBOARD_RECORD = None
DATASOURCE_RECORD = None

class SQLConnectionException(Exception):
    def __init__(self, msg=''):
        super(SQLConnectionException, self).__init__(msg)

def close():
    CONFIGS.sql_connection.close()

def delete_dashboards():
    '''Remove all dashboards from database.

    Development function only, will only work on grafana_test.
    '''
    if CONFIGS.database != 'grafana_test':
        raise SQLConnectionException('Not running any deletes in production; do it manually')
    delete_dashboards_sql \
        = "delete from dashboard where id in (select dashboard_id from dashboard_tag where term = 'quorra-conv')"
    delete_quorra_tags_sql \
        = "delete from dashboard_tag where term = 'quorra-conv'"
    sql_cursor = _get_sql_cursor()
    try:
        for sql_cmd in [delete_dashboards_sql, delete_quorra_tags_sql]:
            sql_cursor.execute(sql_cmd)
        CONFIGS.sql_connection.commit()
    except:
        CONFIGS.sql_connection.rollback()
        raise

def initialize(**kargs):
    '''Setup sql connections, Dashboard and Record tuples.

    '''
    global CONFIGS
    global DASHBOARD_RECORD
    global DATASOURCE_RECORD
    CONFIGS = triconf.conf.initialize('sql_connector', conf_file_names=['database.ini'],
                                      log_file='sql_connector', **kargs)
    CONFIGS.sql_connection = MySQLdb.connect(host=CONFIGS.host,
                                             user=CONFIGS.user,
                                             passwd=getpass(),
                                             db=CONFIGS.database)
    sql_cursor = CONFIGS.sql_connection.cursor()
    sql_cursor.execute('desc dashboard')
    DASHBOARD_RECORD = namedtuple('DashboardRecord',
                                         ' '.join([x[0] for x in sql_cursor.fetchall()]))
    sql_cursor.execute('desc data_source')
    DATASOURCE_RECORD = namedtuple('DatasourceRecord',
                                   ' '.join([x[0] for x in sql_cursor.fetchall()]))

def _get_sql_cursor():
    '''Return a properly initialized sql cursor.

    '''
    initialize()
    sql_cursor = CONFIGS.sql_connection.cursor()
    return sql_cursor

def get_dashboard(dashboard_slug):
    '''Find the dashboard with dashboard_slug in the database and return
    it.

    '''
    sql_cursor = _get_sql_cursor()
    ret = []
    dashboard_sql = ('SELECT * '
                     'FROM dashboard where slug = "%s"' % dashboard_slug)
    sql_cursor.execute(dashboard_sql)
    dashboards = sql_cursor.fetchall()
    if dashboards:
        ret = DASHBOARD_RECORD(*dashboards[0])
    return ret

def get_dashboards():
    '''Return all dashboards.

    '''
    sql_cursor = _get_sql_cursor()
    dashboard_sql = ('SELECT * '
                     'FROM dashboard ')
    sql_cursor.execute(dashboard_sql)
    return sql_cursor.fetchall()

def get_datasources():
    '''Gather all datasources.

    '''
    sql_cursor = _get_sql_cursor()
    ret = []
    datasource_sql = ('select * from data_source')
    sql_cursor.execute(datasource_sql)
    datasources = sql_cursor.fetchall()
    if datasources:
        for datasource in datasources:
            ret.append(DATASOURCE_RECORD(*datasource))
    return ret

def set_dashboard(dashboard_obj):
    '''Given dashboard dict object, insert the dashboard into the
    dashboard in the grafana database.

    '''
    sql_cursor = _get_sql_cursor()

    try:
        title = dashboard_obj['title']
        original_title = dashboard_obj['originalTitle']
    except json.JSONDecodeError:
        raise SQLConnectionException('Invalid json')
    except KeyError:
        raise SQLConnectionException('Json is not a conversion from a xaap file (missing title).')
    json_string = json.dumps(dashboard_obj)
    try:
        # version and org_id are hard coded in grafana to be 2 and 1 respectively.
        insert_dashboard_sql = ('INSERT INTO dashboard '
                                '(version, slug, title, data, org_id, created, updated) '
                                'VALUES (2, %s, %s, %s, 1, NOW(), NOW())')
        dashboard_params = (original_title.replace(' ', '-'), title, json_string)
        try:
            affected = sql_cursor.execute(insert_dashboard_sql, dashboard_params)
        except MySQLdb.IntegrityError:
            try:
                dashboard_params = (original_title.replace(' ', '-')+'-Dup-%s' % randint(0, 1000),
                                    title, json_string)
                affected = sql_cursor.execute(insert_dashboard_sql, dashboard_params)
            except MySQLdb.IntegrityError as exc:
                raise SQLConnectionException('SQL Error: %s.' % exc)
        if affected > 0:
            new_id = CONFIGS.sql_connection.insert_id()
        else:
            raise SQLConnectionException('No row affected for given json.')
        CONFIGS.sql_connection.commit()
        sql_cursor.execute('INSERT INTO dashboard_tag (dashboard_id, term) VALUES (%s, %s)',
                           (new_id, 'quorra-conv'))
        CONFIGS.sql_connection.commit()
    except:
        CONFIGS.sql_connection.rollback()
        raise
    return True

def update_dashboard_data(data_string, dashboard_id):
    '''Update dashboard data at dashboard_id with given
    data_string. Return data_string if successful.

    '''
    update_sql = ('UPDATE dashboard '
                  'SET data=%s '
                  'WHERE id=%s')
    sql_cursor = _get_sql_cursor()
    affected = 0
    try:
        affected = sql_cursor.execute(update_sql,
                                      (json.dumps(json.loads(data_string, encoding="latin-1")),
                                       dashboard_id))
    except MySQLdb.OperationalError:
        raise MySQLdb.OperationalError
    if affected == 0:
        raise SQLConnectionException('No row affected for dashboard %s' % dashboard_id)
    else:
        CONFIGS.sql_connection.commit()
    return data_string

