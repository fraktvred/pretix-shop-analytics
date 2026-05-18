import logging
import requests
from pretix.celery_app import app

logger = logging.getLogger(__name__)


@app.task(bind=True, max_retries=5, default_retry_delay=60, ignore_result=True)
def send_analytics_event(self, endpoint: str, site_id: str, event_name: str, payload: dict):
    """Send an anonymous server-side event to a Umami-compatible /api/send endpoint.

    No identifiers are passed — server-side events are intentionally aggregate-only.
    """
    if not endpoint or not site_id:
        return
    body = {
        'type': 'event',
        'payload': {
            'website': site_id,
            'name': event_name,
            'data': payload or {},
        },
    }
    try:
        resp = requests.post(
            endpoint,
            json=body,
            timeout=10,
            headers={
                'Content-Type': 'application/json',
                'User-Agent': 'pretix-shop-analytics/0.1 (server)',
            },
        )
        resp.raise_for_status()
    except requests.RequestException as exc:
        logger.warning('shop-analytics: failed to send %s to %s: %s', event_name, endpoint, exc)
        raise self.retry(exc=exc)
