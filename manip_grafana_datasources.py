#!/usr/bin/env python
'''Manipulate the grafana datasources.

'''
# TODO: should really be using an orm like sqlalchemy

import manip_grafana_db
import triconf

CONFIGS = None
SQL_CONNECTION = None


def initialize(**kargs):
    '''Module level configs.

    '''
    global CONFIGS
    CONFIGS = triconf.conf.initialize('manip_grafana_datasources',
                                      conf_file_names='datasources.ini')
    manip_grafana_db.initialize()
    return CONFIGS


def insert_grafana_datasource(datasource):
    '''Add datasource to grafana db.

    '''
    sql_cursor = SQL_CONNECTION.cursor()
    insert_sql = ('INSERT INTO data_source '
                  '(org_id, version, type, name, access, url, password, user, `database`, '
                  'basic_auth, basic_auth_user, basic_auth_password, is_default, created, updated) '
                  'VALUES (%(org_id)s, 0, %(type)s, %(name)s, %(access)s, %(url)s, '
                  '%(password)s, %(user)s, %(database)s, %(basic_auth)s, %(basic_auth_user)s, '
                  '%(basic_auth_password)s, %(is_default)s, NOW(), NOW())')
    try:
        affected = sql_cursor.execute(insert_sql, datasource.__dict__)
        print('Pushed datasource %s to grafana db.' % datasource.name)
    except Exception as exc:
        SQL_CONNECTION.rollback()
        print('Failed to put datasource %s into grafana: %s.' % (datasource, exc))
        exit(0)
    if affected > 0:
        SQL_CONNECTION.commit()


def remove_grafana_datasources():
    '''Remove all grafana datasources from the grafana db.

    '''
    sql_cursor = SQL_CONNECTION.cursor()
    delete_sql = ('TRUNCATE data_source')
    try:
        sql_cursor.execute(delete_sql)
    except Exception as exc:
        SQL_CONNECTION.rollback()
        print('Failed to remove datasources: %s' % exc)


if __name__ == '__main__':
    CONFIGS = initialize()
    parser = triconf.conf.ArgumentParser(CONFIGS)
    parser.add_argument('--dry-run', action='store_true', help='Don\'t actually do anything.')
    parser.add_argument('--dump_and_reload', '--dr', action='store_true',
                        help='Delete current datasources and reload with given datasources.')
    CONFIGS(parser.parse_args())
    if CONFIGS.dry_run:
        print 'dry run'
        print CONFIGS
        print manip_grafana_db.CONFIGS
        exit(0)
    SQL_CONNECTION = manip_grafana_db.initialize_db_connection()
    # Remove any non config datasources as those in the config are
    # considered production.
    if CONFIGS.dump_and_reload:
        remove_grafana_datasources()
    for datasource in CONFIGS.datasources:
        insert_grafana_datasource(datasource)
