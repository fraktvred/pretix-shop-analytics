# pretix-shop-analytics

A pretix plugin that forwards shop, cart and checkout events to a configurable
analytics endpoint. Defaults to [Umami](https://umami.is/) but the dispatcher
body is editable so it works with Plausible, GA4 or anything else that exposes
a JS `track(name, props)` shape.

The plugin is designed to close the funnel between a marketing website and a
pretix ticket shop:

1. The website generates an anonymous visitor UUID (e.g. in `localStorage`).
2. When linking to the ticket shop the website appends `?uid=<UUID>`.
3. This plugin reads that `uid` on arrival, calls `umami.identify(uid)`, and
   fires further events on cart and checkout interactions.
4. Server-side events (`order_paid`, `order_canceled`) are sent **anonymously**
   via Celery → analytics HTTP API. No order code, no email, no `uid` ever
   reaches the order record.

## Events emitted

| Event | Source | Carries `uid`? | Payload |
|---|---|---|---|
| `shop_pageview` | browser | yes (via `umami.identify`) | path |
| `add_to_cart` | browser | yes | — |
| `remove_from_cart` | browser | yes | — |
| `checkout_started` | browser | yes | step |
| `order_placed` | browser (confirmation page) | yes | total, currency |
| `order_paid` | server (Celery) | no | total, currency |
| `order_canceled` | server (Celery) | no | total, currency |

## Installation (dev)

```bash
pip install -e .
```

Then enable **Shop Analytics** on the organizer in the pretix control panel
and configure script URL, site id and the server endpoint.

## Brittle surface

The browser-side cart/remove listeners depend on pretix's stock cart markup
selectors (`form[action*="cart/add"]`, `button[name="remove"]`). If pretix
ships a major frontend rewrite these need to be updated. They are isolated in
`static/pretix_shop_analytics/bootstrap.js`.
