from django import forms
from django.utils.translation import gettext_lazy as _
from pretix.base.forms import SettingsForm


DEFAULT_DISPATCHER_BODY = """// Default dispatcher: forwards to Umami. Replace to use Plausible, GA4, etc.
if (window.umami && typeof window.umami.track === 'function') {
    window.umami.track(name, props || {});
}"""


class ShopAnalyticsForm(SettingsForm):
    shop_analytics_enabled = forms.BooleanField(
        label=_('Enabled'),
        required=False,
        help_text=_('Master switch for this organizer. When off, no scripts are injected and no server-side events are sent.'),
    )
    shop_analytics_script_url = forms.URLField(
        label=_('Analytics script URL'),
        required=False,
        help_text=_('URL of the analytics JS library to inject, e.g. https://analytics.example.com/script.js'),
    )
    shop_analytics_site_id = forms.CharField(
        label=_('Site ID'),
        required=False,
        help_text=_('Website ID passed to the script as data-website-id (Umami) or equivalent.'),
    )
    shop_analytics_server_endpoint = forms.URLField(
        label=_('Server-side event endpoint'),
        required=False,
        help_text=_('HTTP endpoint that receives anonymous server-side events, e.g. https://analytics.example.com/api/send'),
    )
    shop_analytics_dispatcher_body = forms.CharField(
        label=_('Browser dispatcher body'),
        required=False,
        widget=forms.Textarea(attrs={'rows': 10, 'class': 'form-control', 'style': 'font-family: monospace;'}),
        help_text=_(
            'JavaScript body for window.shopAnalytics.track(name, props). The name and props variables are in scope. '
            'Default forwards to Umami.'
        ),
        initial=DEFAULT_DISPATCHER_BODY,
    )
