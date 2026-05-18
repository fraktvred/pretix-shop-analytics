from unittest.mock import MagicMock, patch


def make_request(organizer=None):
    request = MagicMock()
    if organizer is not None:
        request.organizer = organizer
    else:
        del request.organizer
    return request


# --- inject_head -------------------------------------------------------------

def test_inject_head_no_organizer_returns_empty():
    from pretix_shop_analytics.signals import inject_head
    assert inject_head(sender=None, request=make_request(organizer=None)) == ''


def test_inject_head_disabled_returns_empty(organizer):
    from pretix_shop_analytics.signals import inject_head
    assert inject_head(sender=None, request=make_request(organizer)) == ''


def test_inject_head_missing_script_url_returns_empty(organizer):
    from pretix_shop_analytics.signals import inject_head
    organizer.settings.set('shop_analytics_enabled', True)
    organizer.settings.set('shop_analytics_site_id', 'site-1')
    assert inject_head(sender=None, request=make_request(organizer)) == ''


def test_inject_head_missing_site_id_returns_empty(organizer):
    from pretix_shop_analytics.signals import inject_head
    organizer.settings.set('shop_analytics_enabled', True)
    organizer.settings.set('shop_analytics_script_url', 'https://x/y.js')
    assert inject_head(sender=None, request=make_request(organizer)) == ''


def test_inject_head_enabled_emits_three_scripts(configured_organizer):
    from pretix_shop_analytics.signals import inject_head
    result = inject_head(sender=None, request=make_request(configured_organizer))
    assert 'https://analytics.example.com/script.js' in result
    assert 'data-website-id="site-123"' in result
    assert '/shop-analytics/dispatcher.js' in result
    assert '/shop-analytics/bootstrap.js' in result
    assert 'data-performance' not in result


def test_inject_head_performance_enabled_sets_attribute(configured_organizer):
    from pretix_shop_analytics.signals import inject_head
    configured_organizer.settings.set('shop_analytics_performance_enabled', True)
    result = inject_head(sender=None, request=make_request(configured_organizer))
    assert 'data-performance="true"' in result


# --- inject_footer -----------------------------------------------------------

def test_inject_footer_is_noop(configured_organizer):
    from pretix_shop_analytics.signals import inject_footer
    assert inject_footer(sender=None, request=make_request(configured_organizer)) == ''


# --- inject_order_placed -----------------------------------------------------

def test_inject_order_placed_disabled(organizer, order):
    from pretix_shop_analytics.signals import inject_order_placed
    result = inject_order_placed(sender=order.event, order=order, request=make_request(organizer))
    assert result == ''


def test_inject_order_placed_enabled_emits_json_payload(configured_organizer, order):
    import json
    import re
    from pretix_shop_analytics.signals import inject_order_placed
    result = inject_order_placed(sender=order.event, order=order, request=make_request(configured_organizer))
    # Inert JSON, not executable JS — CSP-safe without `unsafe-inline`.
    assert 'type="application/json"' in result
    assert 'id="pretix-shop-analytics-order"' in result
    m = re.search(r'>(.*?)</script>', result, re.S)
    assert m, result
    # HTML-escaped JSON: unescape the quotes before parsing.
    payload = json.loads(m.group(1).replace('&quot;', '"').replace('&#x27;', "'"))
    assert payload == {
        'key': 'pretix_shop_analytics_op_ABC12',
        'total': 42.0,
        'currency': 'EUR',
    }


def test_inject_order_placed_no_request(configured_organizer, order):
    from pretix_shop_analytics.signals import inject_order_placed
    assert inject_order_placed(sender=order.event, order=order, request=None) == ''


# --- server-side events ------------------------------------------------------

def test_on_order_paid_enqueues_task(configured_organizer, order):
    from pretix_shop_analytics.signals import on_order_paid
    with patch('pretix_shop_analytics.signals.send_analytics_event.apply_async') as m:
        on_order_paid(sender=order.event, order=order)
    m.assert_called_once()
    args = m.call_args.kwargs['args']
    assert args[0] == 'https://analytics.example.com/api/send'
    assert args[1] == 'site-123'
    assert args[2] == 'order_paid'
    assert args[3] == {'total': 42.0, 'currency': 'EUR'}


def test_on_order_paid_disabled_does_nothing(organizer, order):
    from pretix_shop_analytics.signals import on_order_paid
    with patch('pretix_shop_analytics.signals.send_analytics_event.apply_async') as m:
        on_order_paid(sender=order.event, order=order)
    m.assert_not_called()


def test_on_order_paid_missing_endpoint_does_nothing(organizer, order):
    from pretix_shop_analytics.signals import on_order_paid
    organizer.settings.set('shop_analytics_enabled', True)
    organizer.settings.set('shop_analytics_site_id', 'site-1')
    with patch('pretix_shop_analytics.signals.send_analytics_event.apply_async') as m:
        on_order_paid(sender=order.event, order=order)
    m.assert_not_called()


def test_on_order_canceled_enqueues_task(configured_organizer, order):
    from pretix_shop_analytics.signals import on_order_canceled
    with patch('pretix_shop_analytics.signals.send_analytics_event.apply_async') as m:
        on_order_canceled(sender=order.event, order=order)
    m.assert_called_once()
    assert m.call_args.kwargs['args'][2] == 'order_canceled'
