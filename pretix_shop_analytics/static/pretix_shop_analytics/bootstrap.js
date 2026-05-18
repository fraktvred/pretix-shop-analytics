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

    function identify(uid) {
        if (!uid) return;
        whenUmamiReady(function () {
            try { window.umami.identify(uid); } catch (e) {}
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

    function init() {
        var uid = resolveUid();
        identify(uid);
        pageview();
        wireCart();
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
