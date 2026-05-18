from django.utils.translation import gettext_lazy as _
from pretix.base.plugins import PluginConfig, PLUGIN_LEVEL_ORGANIZER
from . import __version__


class PluginApp(PluginConfig):
    default = True
    name = 'pretix_shop_analytics'
    verbose_name = _('Shop Analytics')

    class PretixPluginMeta:
        name = _('Shop Analytics')
        author = 'fraktvred'
        description = _(
            'Forward shop, cart and checkout events to a configurable analytics endpoint '
            '(Umami by default). Preserves an anonymous visitor UUID from the referring website.'
        )
        visible = True
        version = __version__
        category = 'CUSTOMIZATION'
        compatibility = 'pretix>=4.0.0'
        level = PLUGIN_LEVEL_ORGANIZER

    def ready(self):
        from . import signals  # NOQA
