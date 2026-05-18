import datetime

import pytest
from django.utils.timezone import now
from django_scopes import scopes_disabled


@pytest.fixture
def organizer(db):
    from pretix.base.models import Organizer
    return Organizer.objects.create(name='Test Org', slug='testorg')


@pytest.fixture(autouse=True)
def _scope_disabled():
    """Run every test with django-scopes' organizer scope check disabled — tests
    construct Order/Event objects directly which would otherwise trip the scope
    guard. Production code paths run inside an organizer-scoped request so this
    only affects test fixtures."""
    with scopes_disabled():
        yield


@pytest.fixture
def configured_organizer(organizer):
    organizer.settings.set('shop_analytics_enabled', True)
    organizer.settings.set('shop_analytics_script_url', 'https://analytics.example.com/script.js')
    organizer.settings.set('shop_analytics_site_id', 'site-123')
    organizer.settings.set('shop_analytics_server_endpoint', 'https://analytics.example.com/api/send')
    return organizer


@pytest.fixture
def event(organizer):
    from pretix.base.models import Event
    return Event.objects.create(
        organizer=organizer,
        name='Test Event',
        slug='testevent',
        date_from=now() + datetime.timedelta(days=10),
        currency='EUR',
        plugins='pretix_shop_analytics',
    )


@pytest.fixture
def order(event):
    from pretix.base.models import Order
    sales_channel = event.organizer.sales_channels.get(identifier='web')
    return Order.objects.create(
        event=event,
        status='n',
        email='test@example.com',
        datetime=now(),
        expires=now() + datetime.timedelta(days=10),
        total=42,
        code='ABC12',
        sales_channel=sales_channel,
    )
