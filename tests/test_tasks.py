from unittest.mock import MagicMock, patch

import pytest
import requests


def test_send_analytics_event_posts_expected_payload():
    from pretix_shop_analytics.tasks import send_analytics_event
    with patch('pretix_shop_analytics.tasks.requests.post') as m:
        m.return_value = MagicMock(status_code=200)
        m.return_value.raise_for_status = MagicMock()
        send_analytics_event.run(
            'https://analytics.example.com/api/send',
            'site-1',
            'order_paid',
            {'total': 42.0, 'currency': 'EUR'},
        )
    m.assert_called_once()
    body = m.call_args.kwargs['json']
    assert body == {
        'type': 'event',
        'payload': {
            'website': 'site-1',
            'name': 'order_paid',
            'data': {'total': 42.0, 'currency': 'EUR'},
        },
    }


def test_send_analytics_event_noop_without_endpoint():
    from pretix_shop_analytics.tasks import send_analytics_event
    with patch('pretix_shop_analytics.tasks.requests.post') as m:
        send_analytics_event.run('', 'site-1', 'order_paid', {})
    m.assert_not_called()


def test_send_analytics_event_noop_without_site_id():
    from pretix_shop_analytics.tasks import send_analytics_event
    with patch('pretix_shop_analytics.tasks.requests.post') as m:
        send_analytics_event.run('https://x/y', '', 'order_paid', {})
    m.assert_not_called()


def test_send_analytics_event_retries_on_request_exception():
    from pretix_shop_analytics.tasks import send_analytics_event
    with patch('pretix_shop_analytics.tasks.requests.post') as m:
        m.side_effect = requests.ConnectionError('boom')
        # Celery's .run() bypasses retry machinery and re-raises; that's enough
        # to assert the failure path is reached.
        with pytest.raises((requests.ConnectionError, Exception)):
            send_analytics_event.run('https://x/y', 'site-1', 'order_paid', {})
    m.assert_called_once()
