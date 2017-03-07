import validate_metrics
from nose import tools
import mock

def test_metric_exists():
    mock_resp = mock.Mock(status_code=200, text='{"json":"obj"}')
    validate_metrics.initialize()
    validate_metrics.requests = mock.Mock()
    validate_metrics.requests.post.return_value = mock_resp
    validate_metrics.CONFIGS.datasources = [mock.Mock(url='example', name='test')]
    validate_metrics.CONFIGS.graphite_find_endpoint = '/endpoint'
    known_metric = "market_opportunity_svc"
    tools.assert_equal({'json':'obj'}, validate_metrics.metric_exists(known_metric))
    known_metric = 'bad_metric'
    mock_resp.text = '[]'
    tools.assert_equal(False, validate_metrics.metric_exists(known_metric))

def test_metric_children():
    search_metric = 'metric_name.gauge'
    mock_metric_exists = mock.Mock(return_value=(
        "{u'metrics': [{u'is_leaf': u'1', u'path': u'metric_name.gauge.value', u'name': u'value'}, "
        "{u'is_leaf': u'1', u'path': u'metric_name.gauge.value', u'name': u'value'}, "
        "{u'is_leaf': u'1', u'path': u'metric_name.gauge.value', u'name': u'value'}]}"))
    validate_metrics.metric_exists = mock_metric_exists
    expected = ['value']
    ret = validate_metrics.metric_children(search_metric)
    assert ret == expected
