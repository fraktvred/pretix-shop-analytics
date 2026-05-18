/* pretix-shop-analytics bootstrap
 *
 * 1. Picks up `?uid=...` from the URL on first arrival, persists it in
 *    sessionStorage, and calls `umami.identify(uid)` so the shop visitor
 *    is linked to the referring website's anonymous visitor record.
 * 2. Wires delegated DOM listeners for cart add/remove and checkout-start.
 * 3. All tracking goes through window.shopAnalytics.track(name, props), which
 *    is defined by the dispatcher.js served by this plugin.
 *
 * Selectors here are coupled to pretix's stock cart/checkout markup. If pretix
 * ships a major frontend rewrite, update the SELECTORS block below.
 */
(function () {
    'use strict';

    // Strip identifying tokens (order codes, ticket secrets, uid, …) from any
    // URL/path before it reaches Umami. Wired up via the umami script's
    // `data-before-send` attribute and exposed as a global so umami can find
    // it by name. Defined at script-load time (not in init()) so it is in
    // place before umami fires its autotrack pageview.
    var SENSITIVE_QUERY_KEYS = ['uid', 'cart_id', 'voucher', 'token', 'code', 'secret', 'hash'];

    function sanitizePath(path) {
        if (!path || typeof path !== 'string') return path;
        // /order/<code>/<secret>/...
        path = path.replace(/\/order\/[^/]+\/[^/]+/g, '/order/:code/:secret');
        // /ticket/<code>/<position>/<secret>/...
        path = path.replace(/\/ticket\/[^/]+\/[^/]+\/[^/]+/g, '/ticket/:code/:position/:secret');
        return path;
    }

    function sanitizeUrl(value) {
        if (!value || typeof value !== 'string') return value;
        var hashIdx = value.indexOf('#');
        var hash = hashIdx >= 0 ? value.slice(hashIdx) : '';
        var rest = hashIdx >= 0 ? value.slice(0, hashIdx) : value;
        var qIdx = rest.indexOf('?');
        var path = qIdx >= 0 ? rest.slice(0, qIdx) : rest;
        var search = qIdx >= 0 ? rest.slice(qIdx + 1) : '';
        path = sanitizePath(path);
        if (search) {
            try {
                var params = new URLSearchParams(search);
                for (var i = 0; i < SENSITIVE_QUERY_KEYS.length; i++) {
                    if (params.has(SENSITIVE_QUERY_KEYS[i])) {
                        params.delete(SENSITIVE_QUERY_KEYS[i]);
                    }
                }
                search = params.toString();
            } catch (e) {}
        }
        return path + (search ? '?' + search : '') + hash;
    }

    window.pretixShopAnalyticsBeforeSend = function (type, payload) {
        try {
            if (payload && typeof payload === 'object') {
                if (payload.url) payload.url = sanitizeUrl(payload.url);
                if (payload.referrer) payload.referrer = sanitizeUrl(payload.referrer);
                if (payload.data && typeof payload.data === 'object') {
                    if (payload.data.path) payload.data.path = sanitizeUrl(payload.data.path);
                }
            }
        } catch (e) {}
        return payload;
    };

    // Form-action selectors against pretix's stock cart/checkout endpoints.
    // These are the URLs the markup actually POSTs to (verified against pretix
    // 2024.x). If pretix renames them, update here.
    var SELECTORS = {
        cartAddForm: 'form[action*="/cart/add"]',
        cartRemoveForm: 'form[action$="/cart/remove"]',
        cartClearForm: 'form[action$="/cart/clear"]',
        checkoutStartForm: 'form[action$="/checkout/start"]',
    };

    function getUidFromUrl() {
        try {
            var p = new URLSearchParams(window.location.search);
            return p.get('uid');
        } catch (e) {
            return null;
        }
    }

    function resolveUid() {
        var fromUrl = getUidFromUrl();
        if (fromUrl) {
            try { sessionStorage.setItem('pretix_shop_analytics_uid', fromUrl); } catch (e) {}
            return fromUrl;
        }
        try { return sessionStorage.getItem('pretix_shop_analytics_uid'); } catch (e) { return null; }
    }

    function whenUmamiReady(cb, tries) {
        tries = tries == null ? 50 : tries;
        if (window.umami && typeof window.umami.identify === 'function') {
            cb();
        } else if (tries > 0) {
            setTimeout(function () { whenUmamiReady(cb, tries - 1); }, 100);
        }
    }

    var UTM_KEYS = ['utm_source', 'utm_medium', 'utm_campaign', 'utm_term', 'utm_content'];

    function getDeviceClass() {
        var w = window.innerWidth;
        if (w < 640) return 'mobile';
        if (w < 1024) return 'tablet';
        return 'desktop';
    }

    function buildSessionData() {
        var data = {
            device: getDeviceClass(),
            viewport: window.innerWidth + 'x' + window.innerHeight,
        };
        if (navigator.language) data.language = navigator.language;
        if (document.referrer) {
            try {
                var ref = new URL(document.referrer);
                if (ref.host !== window.location.host) data.referrer_host = ref.host;
            } catch (e) {}
        }
        try {
            var params = new URLSearchParams(window.location.search);
            for (var i = 0; i < UTM_KEYS.length; i++) {
                var key = UTM_KEYS[i];
                var value = params.get(key);
                if (value) data[key] = value.slice(0, 500);
            }
        } catch (e) {}
        return data;
    }

    function identify(uid) {
        if (!uid) return;
        var sessionData = buildSessionData();
        whenUmamiReady(function () {
            try { window.umami.identify(uid, sessionData); } catch (e) {}
        });
    }

    function track(name, props) {
        try {
            if (window.shopAnalytics && typeof window.shopAnalytics.track === 'function') {
                window.shopAnalytics.track(name, props || {});
            }
        } catch (e) {}
    }

    function pageview() {
        track('shop_pageview', { path: window.location.pathname });
    }

    function wireCart() {
        document.addEventListener('submit', function (ev) {
            var t = ev.target;
            if (!t || !t.matches) return;
            if (t.matches(SELECTORS.cartAddForm)) {
                track('add_to_cart', {});
            } else if (t.matches(SELECTORS.cartRemoveForm)) {
                track('remove_from_cart', {});
            } else if (t.matches(SELECTORS.cartClearForm)) {
                track('cart_cleared', {});
            } else if (t.matches(SELECTORS.checkoutStartForm)) {
                track('checkout_started', { path: window.location.pathname });
            }
        }, true);
    }

    function fireOrderPlaced() {
        var el = document.getElementById('pretix-shop-analytics-order');
        if (!el) return;
        var data;
        try { data = JSON.parse(el.textContent || ''); } catch (e) { return; }
        if (!data || !data.key) return;
        try {
            if (sessionStorage.getItem(data.key)) return;
            sessionStorage.setItem(data.key, '1');
        } catch (e) {}
        track('order_placed', { total: data.total, currency: data.currency });
    }

    function init() {
        var uid = resolveUid();
        identify(uid);
        pageview();
        wireCart();
        fireOrderPlaced();
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
