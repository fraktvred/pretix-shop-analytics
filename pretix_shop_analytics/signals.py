import hashlib
from decimal import Decimal
from urllib.parse import urlparse

from django.dispatch import receiver
from django.urls import reverse
from django.utils.html import escape
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _

from pretix.base.signals import order_canceled, order_paid
from pretix.control.signals import nav_organizer
from pretix.presale.signals import (
    global_html_footer,
    global_html_head,
    order_info_top,
    process_response,
)

from .tasks import send_analytics_event


def _settings(organizer):
    s = organizer.settings
    if not s.get('shop_analytics_enabled'):
        return None
    return s


def _hash(s: str) -> str:
    return hashlib.md5((s or '').encode()).hexdigest()[:8]


# --- Browser injection -------------------------------------------------------

@receiver(global_html_head, dispatch_uid='pretix_shop_analytics_head')
def inject_head(sender, request=None, **kwargs):
    if not request or not hasattr(request, 'organizer'):
        return ''
    s = _settings(request.organizer)
    if not s:
        return ''
    script_url = s.get('shop_analytics_script_url') or ''
    site_id = s.get('shop_analytics_site_id') or ''
    if not script_url or not site_id:
        return ''
    dispatcher_url = reverse(
        'plugins:pretix_shop_analytics:dispatcher',
        kwargs={'organizer': request.organizer.slug},
    )
    bootstrap_url = reverse(
        'plugins:pretix_shop_analytics:bootstrap',
        kwargs={'organizer': request.organizer.slug},
    )
    body = s.get('shop_analytics_dispatcher_body') or ''
    # Hash the bootstrap.js bytes so a plugin upgrade busts the browser cache.
    bootstrap_hash = _bootstrap_hash()
    return mark_safe(
        f'<script async defer src="{escape(script_url)}" data-website-id="{escape(site_id)}"></script>'
        f'<script src="{dispatcher_url}?v={_hash(body)}"></script>'
        f'<script defer src="{bootstrap_url}?v={bootstrap_hash}"></script>'
    )


_bootstrap_hash_cache = None


def _bootstrap_hash() -> str:
    """Hash of the bundled bootstrap.js. Cached at import time."""
    global _bootstrap_hash_cache
    if _bootstrap_hash_cache is None:
        from django.contrib.staticfiles import finders
        path = finders.find('pretix_shop_analytics/bootstrap.js')
        if path:
            with open(path, 'rb') as f:
                _bootstrap_hash_cache = hashlib.md5(f.read()).hexdigest()[:8]
        else:
            _bootstrap_hash_cache = 'dev'
    return _bootstrap_hash_cache


@receiver(global_html_footer, dispatch_uid='pretix_shop_analytics_footer')
def inject_footer(sender, request=None, **kwargs):
    # All wiring lives in bootstrap.js (loaded from head). Footer hook is a no-op
    # placeholder so future ad-hoc per-page snippets have a place to live.
    return ''


@receiver(order_info_top, dispatch_uid='pretix_shop_analytics_order_info_top')
def inject_order_placed(sender, order, request=None, **kwargs):
    """Fire `order_placed` exactly once per order, browser-side.

    Uses sessionStorage to dedupe so the event only fires on the *first* visit
    to the order page in a given browser session — typically the post-checkout
    redirect. No order code or PII is sent to analytics; only total and currency.
    """
    if not request or not _settings(order.event.organizer):
        return ''
    total = order.total
    if isinstance(total, Decimal):
        total = float(total)
    # The order code is used purely as a sessionStorage dedup key and never
    # leaves the browser.
    key = f'pretix_shop_analytics_op_{escape(order.code)}'
    return mark_safe(
        '<script>(function(){'
        'try{'
        f'if(sessionStorage.getItem("{key}"))return;'
        f'sessionStorage.setItem("{key}","1");'
        'if(window.shopAnalytics&&window.shopAnalytics.track){'
        f'window.shopAnalytics.track("order_placed",{{total:{total},currency:"{escape(order.event.currency)}"}});'
        '}'
        '}catch(e){}'
        '})();</script>'
    )


# --- Server-side anonymous events --------------------------------------------

def _enqueue(organizer, event_name: str, payload: dict):
    s = _settings(organizer)
    if not s:
        return
    endpoint = s.get('shop_analytics_server_endpoint') or ''
    site_id = s.get('shop_analytics_site_id') or ''
    if not endpoint or not site_id:
        return
    send_analytics_event.apply_async(args=[endpoint, site_id, event_name, payload])


def _order_payload(order) -> dict:
    total = order.total
    if isinstance(total, Decimal):
        total = float(total)
    return {
        'total': total,
        'currency': order.event.currency,
    }


@receiver(order_paid, dispatch_uid='pretix_shop_analytics_order_paid')
def on_order_paid(sender, order, **kwargs):
    _enqueue(order.event.organizer, 'order_paid', _order_payload(order))


@receiver(order_canceled, dispatch_uid='pretix_shop_analytics_order_canceled')
def on_order_canceled(sender, order, **kwargs):
    _enqueue(order.event.organizer, 'order_canceled', _order_payload(order))


# --- Control panel nav -------------------------------------------------------

@receiver(nav_organizer, dispatch_uid='pretix_shop_analytics_nav')
def nav_organizer_link(sender, request=None, **kwargs):
    from django.urls import resolve
    url = resolve(request.path_info)
    return [{
        'label': _('Shop Analytics'),
        'url': reverse('plugins:pretix_shop_analytics:settings', kwargs={
            'organizer': request.organizer.slug,
        }),
        'active': url.namespace == 'plugins:pretix_shop_analytics',
        'icon': 'line-chart',
        'parent': reverse('control:organizer.edit', kwargs={
            'organizer': request.organizer.slug,
        }),
    }]

# --- Adjust CSP headers -----------------------------------------------------

@receiver(process_response, dispatch_uid="pretix_umami_process_response")
def extend_csp(sender, request, response, **kwargs):

    if not request or not hasattr(request, "organizer"):
        return response
    s = _settings(request.organizer)

    script_url = s.get("shop_analytics_script_url")
    if not script_url:
        return response

    parsed = urlparse(script_url)
    origin = f"{parsed.scheme}://{parsed.netloc}"

    csp = response.get("Content-Security-Policy", "")
    for directive in ("script-src", "connect-src"):
        if directive in csp:
            csp = csp.replace(directive, f"{directive} {origin}", 1)
        else:
            csp = f"{csp}; {directive} {origin}" if csp else f"{directive} {origin}"
    response["Content-Security-Policy"] = csp

    return response
