// ==UserScript==
// @name         Order Selector Posone
// @namespace    http://tampermonkey.net/
// @version      1.0
// @description  Autoselect Orders for Postone
// @match        https://postone.eu/orders*
// @grant        none
// ==/UserScript==

(function() {
    'use strict';

    // Чекаємо поки таблиця завантажиться
    function waitForTable() {
        const table = document.querySelector('#orders');
        if (table) {
            addButton();
        } else {
            setTimeout(waitForTable, 500);
        }
    }

    function addButton() {
        // Додаємо кнопку
        const button = document.createElement('button');
        button.textContent = 'Select the orders';
        button.style.cssText = `
            position: fixed;
            top: 70px;
            right: 500px;
            z-index: 9999;
            padding: 12px 20px;
            background: #28a745;
            color: white;
            border: none;
            border-radius: 6px;
            cursor: pointer;
            font-weight: bold;
            box-shadow: 0 2px 8px rgba(0,0,0,0.2);
        `;

        // Виправлені обробники подій
        button.addEventListener('mouseover', function() {
            button.style.background = '#218838';
        });

        button.addEventListener('mouseout', function() {
            button.style.background = '#28a745';
        });

        document.body.appendChild(button);

        button.addEventListener('click', function() {
            const input = prompt('Enter order numbers (each on a new line):\n\nFor example:\n12962\n12963\n12964');
            if (!input) return;

            const orderNumbers = input.split('\n')
                .map(function(n) { return n.trim().replace('#', ''); })
                .filter(Boolean);

            const rows = document.querySelectorAll('#orders tbody tr');
            let selected = 0;
            const notFound = [];

            rows.forEach(function(row) {
                const orderCell = row.querySelector('td:nth-child(2)');
                if (orderCell) {
                    const orderNumber = orderCell.textContent.trim().replace('#', '');
                    if (orderNumbers.includes(orderNumber)) {
                        const checkbox = row.querySelector('td.select-checkbox');
                        if (checkbox && !row.classList.contains('selected')) {
                            checkbox.click();
                            selected++;
                        }
                    }
                }
            });

            // Перевіряємо які не знайшли
            orderNumbers.forEach(function(num) {
                const found = Array.from(rows).some(function(row) {
                    const cell = row.querySelector('td:nth-child(2)');
                    return cell && cell.textContent.includes(num);
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

    waitForTable();
})();