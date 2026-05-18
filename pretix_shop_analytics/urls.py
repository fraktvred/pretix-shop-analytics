from django.urls import re_path

from .views import BootstrapJSView, DispatcherJSView, ShopAnalyticsSettingsView

urlpatterns = [
    re_path(
        r'^control/organizer/(?P<organizer>[^/]+)/shop-analytics/$',
        ShopAnalyticsSettingsView.as_view(),
        name='settings',
    ),
    re_path(
        r'^(?P<organizer>[^/]+)/shop-analytics/dispatcher\.js$',
        DispatcherJSView.as_view(),
        name='dispatcher',
    ),
    re_path(
        r'^(?P<organizer>[^/]+)/shop-analytics/bootstrap\.js$',
        BootstrapJSView.as_view(),
        name='bootstrap',
    ),
]
