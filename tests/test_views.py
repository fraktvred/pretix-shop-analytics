import pytest
from django.test import Client
from django.urls import reverse


@pytest.fixture
def admin_user(db):
    from pretix.base.models import User
    return User.objects.create_superuser('admin@example.com', 'adminpassword')


@pytest.fixture
def logged_in_client(admin_user):
    client = Client()
    client.login(email='admin@example.com', password='adminpassword')
    return client


@pytest.fixture
def organizer_with_team(organizer, admin_user):
    from pretix.base.models import Team
    team = Team.objects.create(
        organizer=organizer, name='Admins',
        all_organizer_permissions=True, all_events=True,
    )
    team.members.add(admin_user)
    return organizer


def test_settings_page_get(logged_in_client, organizer_with_team):
    url = reverse('plugins:pretix_shop_analytics:settings', kwargs={'organizer': organizer_with_team.slug})
    response = logged_in_client.get(url)
    assert response.status_code == 200


def test_settings_page_saves_values(logged_in_client, organizer_with_team):
    from pretix.base.models import Organizer
    url = reverse('plugins:pretix_shop_analytics:settings', kwargs={'organizer': organizer_with_team.slug})
    response = logged_in_client.post(url, {
        'shop_analytics_enabled': 'on',
        'shop_analytics_script_url': 'https://analytics.example.com/script.js',
        'shop_analytics_site_id': 'site-xyz',
        'shop_analytics_server_endpoint': 'https://analytics.example.com/api/send',
        'shop_analytics_dispatcher_body': 'umami.track(name, props);',
    })
    assert response.status_code in (200, 302)
    fresh = Organizer.objects.get(pk=organizer_with_team.pk)
    assert fresh.settings.get('shop_analytics_enabled') is True
    assert fresh.settings.get('shop_analytics_script_url') == 'https://analytics.example.com/script.js'
    assert fresh.settings.get('shop_analytics_site_id') == 'site-xyz'
    assert fresh.settings.get('shop_analytics_server_endpoint') == 'https://analytics.example.com/api/send'
    assert fresh.settings.get('shop_analytics_dispatcher_body') == 'umami.track(name, props);'


def test_dispatcher_404_when_disabled(client, organizer):
    url = reverse('plugins:pretix_shop_analytics:dispatcher', kwargs={'organizer': organizer.slug})
    assert client.get(url).status_code == 404


def test_dispatcher_returns_js_when_enabled(client, configured_organizer):
    configured_organizer.settings.set('shop_analytics_dispatcher_body', 'console.log(name);')
    url = reverse('plugins:pretix_shop_analytics:dispatcher', kwargs={'organizer': configured_organizer.slug})
    response = client.get(url)
    assert response.status_code == 200
    assert 'javascript' in response['Content-Type']
    assert b'window.shopAnalytics' in response.content
    assert b'console.log(name);' in response.content


def test_dispatcher_uses_default_when_body_unset(client, configured_organizer):
    url = reverse('plugins:pretix_shop_analytics:dispatcher', kwargs={'organizer': configured_organizer.slug})
    response = client.get(url)
    assert response.status_code == 200
    assert b'umami.track' in response.content


def test_bootstrap_404_when_disabled(client, organizer):
    url = reverse('plugins:pretix_shop_analytics:bootstrap', kwargs={'organizer': organizer.slug})
    assert client.get(url).status_code == 404


def test_bootstrap_returns_js_when_enabled(client, configured_organizer):
    url = reverse('plugins:pretix_shop_analytics:bootstrap', kwargs={'organizer': configured_organizer.slug})
    response = client.get(url)
    assert response.status_code == 200
    assert 'javascript' in response['Content-Type']
    assert b'shopAnalytics' in response.content
    assert b'umami' in response.content
