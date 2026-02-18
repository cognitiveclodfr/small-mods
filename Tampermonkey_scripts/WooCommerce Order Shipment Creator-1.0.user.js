// ==UserScript==
// @name         WooCommerce Order Shipment Creator
// @namespace    http://tampermonkey.net/
// @version      1.0
// @description  Opens orders from a list and auto-clicks Create Shipment on each order page
// @match        https://lidagreen.com/wp-admin/edit.php*
// @match        https://lidagreen.com/wp-admin/post.php*
// @grant        none
// ==/UserScript==

(function () {
    'use strict';

    const QUEUE_KEY = 'wc_shipment_queue';

    // ─── ORDERS LIST PAGE ────────────────────────────────────────────────────
    function isOrdersListPage() {
        const params = new URLSearchParams(window.location.search);
        return (
            window.location.pathname.includes('edit.php') &&
            params.get('post_type') === 'shop_order'
        );
    }

    function initListPage() {
        waitForElement('#the-list', function () {
            addProcessButton();
        });
    }

    function addProcessButton() {
        const button = document.createElement('button');
        button.textContent = 'Process Orders';
        button.style.cssText = `
            position: fixed;
            top: 70px;
            right: 20px;
            z-index: 99999;
            padding: 12px 20px;
            background: #28a745;
            color: white;
            border: none;
            border-radius: 6px;
            cursor: pointer;
            font-weight: bold;
            font-size: 13px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.25);
        `;
        button.addEventListener('mouseover', function () { button.style.background = '#218838'; });
        button.addEventListener('mouseout', function () { button.style.background = '#28a745'; });
        button.addEventListener('click', onProcessClick);
        document.body.appendChild(button);
    }

    function onProcessClick() {
        const input = prompt(
            'Enter order numbers to process (one per line):\n\nExample:\n#36576\n#36574\n#36573'
        );
        if (!input) return;

        // Parse order numbers — strip #, whitespace, empty lines
        const requested = input
            .split('\n')
            .map(function (n) { return n.trim().replace(/^#/, ''); })
            .filter(Boolean);

        if (requested.length === 0) {
            alert('No order numbers entered.');
            return;
        }

        // Build map of orderNumber → editURL from current page rows
        const orderMap = {};
        document.querySelectorAll('a.order-view').forEach(function (link) {
            const strong = link.querySelector('strong');
            if (!strong) return;
            const match = strong.textContent.match(/^#?(\d+)/);
            if (match) {
                orderMap[match[1]] = link.href;
            }
        });

        const found = [];
        const notFound = [];

        requested.forEach(function (num) {
            if (orderMap[num]) {
                found.push({ num: num, url: orderMap[num] });
            } else {
                notFound.push(num);
            }
        });

        if (found.length === 0) {
            let msg = 'None of the entered orders were found on this page.';
            if (notFound.length > 0) {
                msg += '\n\nNot found:\n' + notFound.map(function (n) { return '#' + n; }).join('\n');
            }
            alert(msg);
            return;
        }

        // Save queue of found order IDs to localStorage for order pages to pick up
        const existingQueue = safeParseQueue();
        const combined = Array.from(new Set(existingQueue.concat(found.map(function (f) { return f.num; }))));
        localStorage.setItem(QUEUE_KEY, JSON.stringify(combined));

        // Open each found order in a new tab with a 600ms stagger
        found.forEach(function (order, index) {
            setTimeout(function () {
                window.open(order.url, '_blank');
            }, index * 600);
        });

        // Show report
        setTimeout(function () {
            let msg = 'Opening ' + found.length + ' order(s) for shipment creation.';
            if (notFound.length > 0) {
                msg += '\n\n\u26a0\ufe0f Not found on this page (' + notFound.length + '):\n';
                msg += notFound.map(function (n) { return '#' + n; }).join('\n');
                msg += '\n\nMake sure these orders are visible on the current page/filter.';
            }
            alert(msg);
        }, found.length * 600 + 200);
    }

    // ─── SINGLE ORDER PAGE ───────────────────────────────────────────────────
    function isOrderEditPage() {
        const params = new URLSearchParams(window.location.search);
        return (
            window.location.pathname.includes('post.php') &&
            params.get('action') === 'edit'
        );
    }

    function initOrderPage() {
        const params = new URLSearchParams(window.location.search);
        const postId = params.get('post');
        if (!postId) return;

        const queue = safeParseQueue();
        if (!queue.includes(postId)) return;

        // Order is in queue — wait for Create Shipment button and click it
        waitForElement(
            'button[data-toggle="sksoftware-postone-for-woocommerce-shipment-create"]',
            function (btn) {
                btn.click();

                // Remove this order from queue
                const updatedQueue = safeParseQueue().filter(function (id) { return id !== postId; });
                localStorage.setItem(QUEUE_KEY, JSON.stringify(updatedQueue));
            },
            10000 // wait up to 10 seconds
        );
    }

    // ─── UTILITIES ───────────────────────────────────────────────────────────
    function safeParseQueue() {
        try {
            const raw = localStorage.getItem(QUEUE_KEY);
            const parsed = JSON.parse(raw);
            return Array.isArray(parsed) ? parsed : [];
        } catch (e) {
            return [];
        }
    }

    /**
     * Polls for a CSS selector until found or timeout reached.
     * @param {string} selector
     * @param {function} callback  Called with the found element
     * @param {number}  [timeout]  Max wait in ms (default 5000)
     */
    function waitForElement(selector, callback, timeout) {
        var maxWait = timeout || 5000;
        var waited = 0;
        var interval = 500;

        var el = document.querySelector(selector);
        if (el) {
            callback(el);
            return;
        }

        var timer = setInterval(function () {
            waited += interval;
            var el = document.querySelector(selector);
            if (el) {
                clearInterval(timer);
                callback(el);
            } else if (waited >= maxWait) {
                clearInterval(timer);
            }
        }, interval);
    }

    // ─── ENTRY POINT ─────────────────────────────────────────────────────────
    if (isOrdersListPage()) {
        initListPage();
    } else if (isOrderEditPage()) {
        initOrderPage();
    }

})();
