// ==UserScript==
// @name         DHL Nigeria Price Calculator
// @namespace    http://tampermonkey.net/
// @version      3.0
// @description  Smart price distribution for Nigeria with iterative logic
// @match        https://app2.dhlexpresscommerce.com/orders/*
// @grant        none
// ==/UserScript==

(function() {
    'use strict';

    function waitForGrid() {
        // ПЕРЕВІРКА 1: URL повинен містити /orders/
        if (!window.location.pathname.includes('/orders/')) {
            return;
        }

        // ПЕРЕВІРКА 2: Таблиця артикулів повинна існувати
        const grid = document.querySelector('.ssit-order-detail-grid.order-items');
        if (grid) {
            addButton();
        } else {
            setTimeout(waitForGrid, 500);
        }
    }

    function addButton() {
        // Перевіряємо чи кнопка вже існує
        if (document.getElementById('nigeria-calc-button')) {
            return;
        }

        const button = document.createElement('button');
        button.id = 'nigeria-calc-button';
        button.textContent = '🇳🇬 Calculate Nigeria Prices';
        button.style.cssText = `
            position: fixed;
            top: 15px;
            left: 100px;
            z-index: 9999;
            padding: 12px 20px;
            background: #008751;
            color: white;
            border: none;
            border-radius: 6px;
            cursor: pointer;
            font-weight: bold;
            box-shadow: 0 2px 8px rgba(0,0,0,0.2);
        `;

        button.addEventListener('mouseover', function() {
            button.style.background = '#006d40';
        });

        button.addEventListener('mouseout', function() {
            button.style.background = '#008751';
        });

        document.body.appendChild(button);
        button.addEventListener('click', redistributePrices);
    }

    function redistributePrices() {
        const MAX_TOTAL = 200; // Nigeria customs limit
        const MAX_PER_ITEM = 50; // Max price per item
        const MIN_PRICE = 1; // Minimum price for zero items

        // Find all item rows
        const rows = document.querySelectorAll('.ssit-order-detail-grid.order-items tbody tr[data-index]');

        if (rows.length === 0) {
            alert('❌ No items found!');
            return;
        }

        const items = [];
        let totalOriginal = 0;

        // Збираємо дані з кожного рядка
        rows.forEach(function(row, index) {
            const skuInput = row.querySelector('td[data-col-index="1"] input.k-input-inner');
            const sku = skuInput ? skuInput.value.trim() : '';

            const itemInput = row.querySelector('td[data-col-index="0"] input.k-input-inner');
            const itemName = itemInput ? itemInput.value.trim() : '';

            const priceInput = row.querySelector('td[data-col-index="3"] input.ssit-input-text');
            const currentPrice = priceInput && priceInput.value ? parseFloat(priceInput.value) : 0;

            const qtyInput = row.querySelector('td[data-col-index="2"] input.ssit-input-numeric');
            const qty = qtyInput && qtyInput.value ? parseInt(qtyInput.value) : 1;

            totalOriginal += currentPrice * qty;

            items.push({
                index: index,
                sku: sku,
                name: itemName,
                qty: qty,
                originalPrice: currentPrice,
                priceInput: priceInput
            });
        });

        console.log('Items found:', items.length);
        console.log('Original total:', totalOriginal.toFixed(2), '€');

        // КРОК 1: Фіксуємо нульові ціни
        let zeroFixed = 0;
        items.forEach(function(item) {
            if (item.originalPrice === 0) {
                item.originalPrice = MIN_PRICE;
                zeroFixed++;
            }
        });

        // Пересчитуємо загальну суму після фіксації нулів
        let totalAfterZeroFix = 0;
        items.forEach(function(item) {
            totalAfterZeroFix += item.originalPrice * item.qty;
        });

        console.log('Total after zero fix:', totalAfterZeroFix.toFixed(2), '€');

        // КРОК 2: Спробуємо просто обмежити артикули >50€ до 50€
        let totalAfterCapping = 0;
        items.forEach(function(item) {
            const cappedPrice = item.originalPrice > MAX_PER_ITEM ? MAX_PER_ITEM : item.originalPrice;
            totalAfterCapping += cappedPrice * item.qty;
        });

        console.log('Total after capping to 50€:', totalAfterCapping.toFixed(2), '€');

        // Якщо після обмеження сума ≤ 200€ - просто застосовуємо це!
        if (totalAfterCapping <= MAX_TOTAL) {
            let newTotal = 0;
            const changes = [];

            items.forEach(function(item) {
                let newPrice = item.originalPrice;

                if (item.originalPrice > MAX_PER_ITEM) {
                    newPrice = MAX_PER_ITEM;
                }

                if (item.priceInput) {
                    item.priceInput.value = newPrice.toFixed(2);

                    const event = new Event('change', { bubbles: true });
                    item.priceInput.dispatchEvent(event);
                    const event2 = new Event('input', { bubbles: true });
                    item.priceInput.dispatchEvent(event2);
                }

                newTotal += newPrice * item.qty;

                if (newPrice !== item.originalPrice) {
                    changes.push({
                        name: item.name || 'Item ' + (item.index + 1),
                        sku: item.sku,
                        qty: item.qty,
                        oldPrice: item.originalPrice,
                        newPrice: newPrice
                    });
                }
            });

            // Звіт для випадку ≤ 200€ після обмеження
            let report = '✅ DONE! Simple cap to 50€ applied\n\n';
            report += '📊 Summary:\n';
            report += '━━━━━━━━━━━━━━━━\n';
            report += 'Original: ' + totalOriginal.toFixed(2) + '€\n';
            report += 'After zero fix: ' + totalAfterZeroFix.toFixed(2) + '€\n';
            report += 'Final: ' + newTotal.toFixed(2) + '€\n';
            report += 'Items capped at 50€: ' + changes.length + '\n';

            if (zeroFixed > 0) {
                report += 'Zero prices fixed: ' + zeroFixed + '\n';
            }

            if (changes.length > 0) {
                report += '\n✏️ Changes:\n';
                changes.forEach(function(ch) {
                    report += '  • ' + (ch.name || ch.sku) + ' (x' + ch.qty + '):\n';
                    report += '    ' + ch.oldPrice.toFixed(2) + '€ → ' + ch.newPrice.toFixed(2) + '€\n';
                });
            }

            alert(report);
            return;
        }

        // КРОК 3: Після обмеження все ще > 200€ - потрібен розумний розподіл
        const THRESHOLD = MAX_PER_ITEM; // Поріг для "дешевих" артикулів

        // Ітеративний алгоритм розподілу
        let iteration = 0;
        let maxIterations = items.length; // Захист від нескінченного циклу
        let distributed = false;
        let finalPricePerUnit = 0;

        while (!distributed && iteration < maxIterations) {
            iteration++;

            // Ділимо артикули на дешеві та дорогі
            const cheapItems = [];
            const expensiveItems = [];

            items.forEach(function(item) {
                if (item.originalPrice <= THRESHOLD) {
                    cheapItems.push(item);
                } else {
                    expensiveItems.push(item);
                }
            });

            // Якщо немає дорогих - всі отримують однакову ціну
            if (expensiveItems.length === 0) {
                let totalQty = 0;
                items.forEach(function(item) {
                    totalQty += item.qty;
                });
                finalPricePerUnit = MAX_TOTAL / totalQty;
                distributed = true;
                break;
            }

            // Рахуємо суму дешевих
            let cheapTotal = 0;
            cheapItems.forEach(function(item) {
                cheapTotal += item.originalPrice * item.qty;
            });

            // Доступний бюджет для розподілу
            const availableBudget = MAX_TOTAL - cheapTotal;

            // Рахуємо кількість одиниць дорогих артикулів
            let expensiveQty = 0;
            expensiveItems.forEach(function(item) {
                expensiveQty += item.qty;
            });

            // Нова ціна для дорогих артикулів
            const pricePerUnit = availableBudget / expensiveQty;

            // Перевіряємо чи не перевищує максимум
            if (pricePerUnit > MAX_PER_ITEM) {
                alert('⚠️ ERROR: Cannot distribute!\n\n' +
                      'Price per unit would be: ' + pricePerUnit.toFixed(2) + '€\n' +
                      'Maximum allowed: ' + MAX_PER_ITEM + '€\n\n' +
                      'Please remove items or reduce quantities.');
                return;
            }

            // Знаходимо найдорожчий "дешевий" артикул
            let maxCheapPrice = 0;
            cheapItems.forEach(function(item) {
                if (item.originalPrice > maxCheapPrice) {
                    maxCheapPrice = item.originalPrice;
                }
            });

            // Перевірка: чи нова ціна менша за найдорожчий дешевий?
            if (pricePerUnit < maxCheapPrice) {
                // Знаходимо найдорожчий дешевий артикул і переміщуємо його в дорогі
                let mostExpensiveCheap = null;
                items.forEach(function(item) {
                    if (item.originalPrice === maxCheapPrice) {
                        if (!mostExpensiveCheap) {
                            mostExpensiveCheap = item;
                        }
                    }
                });

                if (mostExpensiveCheap) {
                    // Переміщуємо його в категорію "дорогих"
                    mostExpensiveCheap.originalPrice = THRESHOLD + 0.01; // Трохи більше порогу
                    console.log('Iteration ' + iteration + ': Moving item to expensive category');
                }
            } else {
                // Розподіл успішний!
                finalPricePerUnit = pricePerUnit;
                distributed = true;
            }
        }

        if (!distributed) {
            alert('⚠️ ERROR: Distribution algorithm failed after ' + maxIterations + ' iterations.\n\nPlease contact support.');
            return;
        }

        // ЗАСТОСОВУЄМО НОВІ ЦІНИ
        let newTotal = 0;
        const changes = [];

        items.forEach(function(item) {
            let newPrice;

            if (item.originalPrice <= THRESHOLD) {
                // Дешевий артикул - залишаємо як є
                newPrice = item.originalPrice;
            } else {
                // Дорогий артикул - застосовуємо розподілену ціну
                newPrice = finalPricePerUnit;
            }

            if (item.priceInput) {
                item.priceInput.value = newPrice.toFixed(2);

                const event = new Event('change', { bubbles: true });
                item.priceInput.dispatchEvent(event);
                const event2 = new Event('input', { bubbles: true });
                item.priceInput.dispatchEvent(event2);
            }

            newTotal += newPrice * item.qty;

            // Зберігаємо оригінальну ціну для звіту (до фіксації нулів)
            const originalForReport = items[item.index].originalPrice === MIN_PRICE && totalOriginal < totalAfterZeroFix
                ? 0
                : item.originalPrice;

            if (Math.abs(newPrice - originalForReport) > 0.01) {
                changes.push({
                    name: item.name || 'Item ' + (item.index + 1),
                    sku: item.sku,
                    qty: item.qty,
                    oldPrice: originalForReport,
                    newPrice: newPrice
                });
            }
        });

        // ГЕНЕРУЄМО ЗВІТ
        let report = '✅ DONE! Smart distribution applied\n\n';
        report += '📊 Summary:\n';
        report += '━━━━━━━━━━━━━━━━\n';
        report += 'Original: ' + totalOriginal.toFixed(2) + '€\n';
        report += 'Final: ' + newTotal.toFixed(2) + '€\n';
        report += 'Items changed: ' + changes.length + '/' + items.length + '\n';
        report += 'Iterations: ' + iteration + '\n';

        if (zeroFixed > 0) {
            report += 'Zero prices fixed: ' + zeroFixed + '\n';
        }

        report += '\n✏️ Changes:\n';
        changes.forEach(function(ch) {
            report += '  • ' + (ch.name || ch.sku) + ' (x' + ch.qty + '):\n';
            report += '    ' + ch.oldPrice.toFixed(2) + '€ → ' + ch.newPrice.toFixed(2) + '€\n';
        });

        alert(report);
    }

    waitForGrid();
})();