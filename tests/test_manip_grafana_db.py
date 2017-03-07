from .. import manip_grafana_db
from nose import tools

def test_insert_dashboard_into_grafana_db():
    import mock
    import StringIO
    test_cursor = mock.Mock(execute=mock.Mock())
    test_conn = mock.Mock(cursor=mock.Mock(return_value=test_cursor))
    test_conn.insert_id = mock.Mock(return_value=42)
    test_obj = {"Good Json": "Bad content"}
    manip_grafana_db.initialize()
    manip_grafana_db.SQL_CONNECTION = test_cursor
    tools.assert_raises(manip_grafana_db.GrafanaDataManipulationException,
                        manip_grafana_db.insert_dashboard_into_grafana_db, test_obj)


# Test values
# loadbalancers.vsvrClientConnOpenRate.vsvrName_u_net_dsr.*.*.*.*
# loadbalancers.svcGrpMemberRequestRate.collection_ip_10_16_253_2.*.*.service_group_overlords_xa_1012.*.*.value should return loadbalancers.md.svcGrpMemberRequestRate.collection_ip.10_16_253_2.group_member_ip.*.group_member_name.*.service_group.overlords_xa_1012.host.*.gauge.value
# loadbalancers.svcGrpMemberRequestRate.collection_ip_10_16_253_2.*.*.service_group_overlords_xa_1012.*.gauge.value should return loadbalancers.md.svcGrpMemberRequestRate.collection_ip.10_16_253_2.group_member_ip.*.group_member_name.*.service_group.overlords_xa_1012.host.*.gauge.value
# loadbalancers.vsvrCurServicesUp.collection_ip_10_33_253_2.vsvrName_prod_ox3_bid_dsr.shared.gauge.value should return loadbalancers.md.vsvrCurServicesUp.collection_ip.10_33_253_2.vsvrName.prod_ox3_bid_dsr.host.shared.gauge.value
#vertpoolquery.*.caac-k12.gauge.value

get_path:
#"aliasByNode(sortByMaxima(highestCurrent(scale(routers.*_in_Uplink_ae*.xva{[h-j]*,g[d-g]}-rs-01.counter.value, 8), 5)), 2)" should return routers.*_in_Uplink_ae*.xva{[h-j]*,g[d-g]}-rs-01.counter.value

# "alias(offset(scale(sumSeries(ox_broker_delivery.impression_mkt_adv_spend.*.counter.value), 0.001), 60), 'Advertiser Spend')" should return ox_broker_delivery.impression_mkt_adv_spend.*.counter.value


#hadoop.hdfs2_log_fatal_datanode_avg_rate.cluster_storage_grid_Storage_Cluster___CDH4.storage-grid-cdh-monitor-ca-01.gauge.value

#routers.ge_0_0_36_in.$rack_switch.counter.value
# hadoop.mapreduce1_reduces_running.cluster_qa_storage_grid_Cluster_1___CDH4.qa-cdh-grid-monitor-xv-01.gauge.value


# Strange
#hadoop.hdfs2_log_fatal_datanode_avg_rate.cluster_storage_grid_Storage_Cluster___CDH4.storage-grid-cdh-monitor-ca-01.gauge.value -- hadoop.md.hdfs2_log_fatal_datanode_avg_rate

# role.vertica_edw_prod.host.*.interface-eth0.if_octets.rx -- role.md.vertica_edw_prod
