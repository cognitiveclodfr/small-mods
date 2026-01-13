// ==UserScript==
// @name         DHL Order Selector
// @namespace    http://tampermonkey.net/
// @version      1.0
// @description  AutoSelect for DHL
// @match        https://app2.dhlexpresscommerce.com/orders/
// @grant        none
// ==/UserScript==

(function() {
    'use strict';

    function waitForGrid() {
        const grid = document.querySelector('.ssit-order-grid');
        if (grid) {
            addButton();
        } else {
            setTimeout(waitForGrid, 500);
        }
    }

    function addButton() {
        const button = document.createElement('button');
        button.textContent = 'Select DHL orders';
        button.style.cssText = `
            position: fixed;
            top: 15px;
            right: 20px;
            z-index: 9999;
            padding: 12px 20px;
            background: #d40511;
            color: white;
            border: none;
            border-radius: 6px;
            cursor: pointer;
            font-weight: bold;
            box-shadow: 0 2px 8px rgba(0,0,0,0.2);
        `;

        button.addEventListener('mouseover', function() {
            button.style.background = '#b00410';
        });

        button.addEventListener('mouseout', function() {
            button.style.background = '#d40511';
        });

        document.body.appendChild(button);

        button.addEventListener('click', function() {
            const input = prompt('Enter your DHL order numbers (each on a new line):\n\nFor example:\n134386\n134385\n134384');
            if (!input) return;

            const orderNumbers = input.split('\n')
                .map(function(n) { return n.trim().replace('#', ''); })
                .filter(Boolean);

            const rows = document.querySelectorAll('.k-table-row.k-master-row');
            let selected = 0;
            const notFound = [];

            rows.forEach(function(row) {
                // Шукаємо номер замовлення
                const orderLink = row.querySelector('a.order-number');
                if (orderLink) {
                    const orderNumber = orderLink.textContent.trim().replace('#', '');

                    if (orderNumbers.includes(orderNumber)) {
                        // Шукаємо чекбокс в цьому рядку
                        const checkbox = row.querySelector('input[type="checkbox"].k-grid-checkbox');

                        if (checkbox && !checkbox.checked) {
                            checkbox.click();
                            selected++;
                        }
                    }
                }
            });

            // Перевіряємо які не знайшли
            orderNumbers.forEach(function(num) {
                const found = Array.from(rows).some(function(row) {
                    const link = row.querySelector('a.order-number');
                    return link && link.textContent.includes(num);
                });
                if (!found) {
                    notFound.push(num);
                }
            });

            let message = 'Selected: ' + selected + ' orders';
            if (notFound.length > 0) {
                message += '\n\n⚠️ Not found on page:\n' + notFound.join(', ');
            }

            alert(message);
        });
    }

    waitForGrid();
})();