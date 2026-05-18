def test_form_valid_with_empty_fields(organizer):
    from pretix_shop_analytics.forms import ShopAnalyticsForm
    form = ShopAnalyticsForm(data={
        'shop_analytics_enabled': '',
        'shop_analytics_script_url': '',
        'shop_analytics_site_id': '',
        'shop_analytics_server_endpoint': '',
        'shop_analytics_dispatcher_body': '',
    }, obj=organizer)
    assert form.is_valid(), form.errors


def test_form_valid_fully_configured(organizer):
    from pretix_shop_analytics.forms import ShopAnalyticsForm
    form = ShopAnalyticsForm(data={
        'shop_analytics_enabled': 'on',
        'shop_analytics_script_url': 'https://analytics.example.com/s.js',
        'shop_analytics_site_id': 'site-1',
        'shop_analytics_server_endpoint': 'https://analytics.example.com/api/send',
        'shop_analytics_dispatcher_body': 'umami.track(name, props);',
    }, obj=organizer)
    assert form.is_valid(), form.errors
    assert form.cleaned_data['shop_analytics_enabled'] is True
    assert form.cleaned_data['shop_analytics_site_id'] == 'site-1'


def test_form_rejects_invalid_url(organizer):
    from pretix_shop_analytics.forms import ShopAnalyticsForm
    form = ShopAnalyticsForm(data={
        'shop_analytics_script_url': 'not-a-url',
    }, obj=organizer)
    assert not form.is_valid()
    assert 'shop_analytics_script_url' in form.errors
