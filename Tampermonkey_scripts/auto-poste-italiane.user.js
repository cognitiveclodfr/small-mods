// ==UserScript==
// @name         Auto Courier Provider
// @namespace    http://tampermonkey.net/
// @version      1.1
// @description  Автоматично визначає кур'єра по тракінг-номеру і зберігає
// @match        */wp-admin/post.php?post=*&action=edit*
// @match        */wp-admin/admin.php?page=wc-orders&action=edit*
// @grant        none
// ==/UserScript==

/* globals jQuery */

(function() {
    'use strict';

    // Чекаємо завантаження сторінки
    function init() {
        const trackingWidget = document.getElementById('woocommerce-advanced-shipment-tracking');
        if (!trackingWidget) return;

        // Створюємо кнопку
        const btn = document.createElement('button');
        btn.type = 'button';
        btn.className = 'button button-primary btn_ast2';
        btn.textContent = '📦 Quick Save';
        btn.style.cssText = 'margin-top: 10px; margin-left: 10px; background: #28a745; border-color: #28a745;';

        // Знаходимо кнопку Add Tracking Info і додаємо поруч
        const addBtn = trackingWidget.querySelector('.button-show-tracking-form');
        if (addBtn) {
            addBtn.parentNode.insertBefore(btn, addBtn.nextSibling);
        }

        // Обробник кліку
        btn.addEventListener('click', function() {
            const addTrackingBtn = trackingWidget.querySelector('.button-show-tracking-form');
            const form = document.getElementById('advanced-shipment-tracking-form');

            // Перевіряємо чи форма прихована (будь-яким способом)
            const isHidden = !form || form.offsetParent === null ||
                             getComputedStyle(form).display === 'none';

            if (isHidden && addTrackingBtn) {
                // Відкриваємо форму
                addTrackingBtn.click();
                // Чекаємо поки форма відкриється
                setTimeout(() => {
                    processTracking();
                }, 300);
            } else {
                // Форма вже відкрита - обробляємо одразу
                processTracking();
            }
        });

        function processTracking() {
            const trackingInput = document.getElementById('tracking_number');
            const providerSelect = document.getElementById('tracking_provider');
            const saveButton = trackingWidget.querySelector('.button-save-form');

            // Перевірка: є тракінг номер?
            if (!trackingInput || !trackingInput.value.trim()) {
                alert('Tracking number порожній!');
                return;
            }

            const trackingNumber = trackingInput.value.trim();

            // Визначаємо провайдера по префіксу/паттерну тракінгу
            let provider = '';
            if (trackingNumber.startsWith('3UW')) {
                provider = 'poste-italiane';
            } else if (trackingNumber.startsWith('H00TCA')) {
                provider = 'evri';
            } else if (trackingNumber.startsWith('3SBPB')) {
                provider = 'bpost';                                         // DHL via B-POST
            } else if (/^LY\d{9}[A-Z]{2}$/.test(trackingNumber)) {
                provider = 'deutsche-post';
            } else if (/^LM\d{9}[A-Z]{2}$/.test(trackingNumber)) {
                provider = 'postnord';
            } else if (/^LS\d{9}[A-Z]{2}$/.test(trackingNumber)) {
                provider = 'asendia';
            } else if (trackingNumber.startsWith('1042') && trackingNumber.length === 22) {
                provider = 'austria-post';
            } else if (trackingNumber.startsWith('633') && trackingNumber.length === 23) {
                provider = 'correos-express';
            } else if (trackingNumber.startsWith('323') && trackingNumber.length === 23) {
                provider = 'correos';
            } else if (trackingNumber.startsWith('7000') && trackingNumber.length === 13) {
                provider = 'fan-courier';
            }

            // Якщо provider не вибраний і ми знаємо який ставити
            if (providerSelect && providerSelect.value === '' && provider) {
                if (typeof jQuery !== 'undefined') {
                    jQuery(providerSelect).val(provider).trigger('change');
                } else {
                    providerSelect.value = provider;
                    providerSelect.dispatchEvent(new Event('change', { bubbles: true }));
                }
            }

            // Якщо provider досі порожній і ми не знаємо що ставити
            if (providerSelect && providerSelect.value === '') {
                alert('Невідомий формат тракінгу. Виберіть провайдера вручну.');
                return;
            }

            // Зберігаємо
            setTimeout(() => {
                if (saveButton) {
                    saveButton.click();
                }
            }, 100);
        }
    }

    // Запускаємо після завантаження DOM
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
