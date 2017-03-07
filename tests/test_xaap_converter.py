from .. import xaap_converter
from nose import tools
import mock

@tools.with_setup(lambda: xaap_converter.initialize())
def test_generate_metric_path():
    xaap_converter.validate_metrics.metric_exists = mock.Mock(return_value = {'test':'obj'})
    expected = ('total_req',
                'scaleToSeconds(ssrtb.agg.total_req.acctid.537073295.cluster.$colo.host.all.sum.value, 1)')
    ret = xaap_converter._generate_metric_path("total_req = SUM(ssrtb, total_req,counter,acctid=537073295)")
    tools.assert_equal(ret, expected, 'test failed expected %s got %s' % (expected, ret))

    expected = ('mops_success', 'ox_broker_delivery.agg.market_opportunity_service_successesCount.cluster.$colo.host.all.sum.value')
    ret = xaap_converter._generate_metric_path("mops_success = SUM(ox_broker_delivery,market_opportunity_service.successesCount,gauge)")
    tools.assert_equal(ret, expected, 'test failed expected %s got %s' % (expected, ret))

