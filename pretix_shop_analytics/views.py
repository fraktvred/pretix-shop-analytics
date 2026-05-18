import hashlib

from django.http import Http404, HttpResponse
from django.urls import reverse
from django.views import View

from pretix.base.models import Organizer
from pretix.control.views.organizer import OrganizerSettingsFormView

from .forms import DEFAULT_DISPATCHER_BODY, ShopAnalyticsForm


class ShopAnalyticsSettingsView(OrganizerSettingsFormView):
    form_class = ShopAnalyticsForm
    template_name = 'pretix_shop_analytics/settings.html'

    def get_success_url(self):
        return reverse('plugins:pretix_shop_analytics:settings', kwargs={
            'organizer': self.request.organizer.slug,
        })


def _hash(s: str) -> str:
    return hashlib.md5((s or '').encode()).hexdigest()[:8]


class DispatcherJSView(View):
    def get(self, request, organizer, **kwargs):
        try:
            org = Organizer.objects.get(slug=organizer)
        except Organizer.DoesNotExist:
            raise Http404
        if not org.settings.get('shop_analytics_enabled'):
            raise Http404
        body = org.settings.get('shop_analytics_dispatcher_body') or DEFAULT_DISPATCHER_BODY
        js = (
            'window.shopAnalytics = window.shopAnalytics || {};'
            'window.shopAnalytics.track = function(name, props) {'
            f'{body}'
            '};'
        )
        response = HttpResponse(js, content_type='application/javascript; charset=utf-8')
        response['Cache-Control'] = 'public, max-age=31536000, immutable'
        response['ETag'] = f'"{_hash(body)}"'
        return response


class BootstrapJSView(View):
    """Serves the static bootstrap.js. Routed through the plugin URL so it works
    even when pretix's static-file handling is restricted to specific apps.
    """
    def get(self, request, organizer, **kwargs):
        try:
            org = Organizer.objects.get(slug=organizer)
        except Organizer.DoesNotExist:
            raise Http404
        if not org.settings.get('shop_analytics_enabled'):
            raise Http404
        from django.contrib.staticfiles import finders
        path = finders.find('pretix_shop_analytics/bootstrap.js')
        if not path:
            raise Http404
        with open(path, 'rb') as f:
            content = f.read()
        response = HttpResponse(content, content_type='application/javascript; charset=utf-8')
        # Hash the contents so a deploy invalidates the URL-level cache.
        response['ETag'] = f'"{_hash(content.decode("utf-8", errors="replace"))}"'
        response['Cache-Control'] = 'public, max-age=3600, must-revalidate'
        return response
