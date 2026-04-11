(function () {
    function setupSortableInline(groupEl) {
        if (!groupEl || groupEl.dataset.memorialImageSortReady === '1') {
            return;
        }

        const tbody = groupEl.querySelector('table tbody');
        if (!tbody) {
            return;
        }

        groupEl.dataset.memorialImageSortReady = '1';

        function isRealRow(row) {
            if (!row) return false;
            if (row.classList.contains('empty-form')) return false;
            if (row.classList.contains('add-row')) return false;
            const orderInput = row.querySelector('input[name$="-order"]');
            return !!orderInput;
        }

        function visibleRows() {
            return Array.from(tbody.querySelectorAll('tr')).filter((row) => {
                if (!isRealRow(row)) return false;
                const deleteCheckbox = row.querySelector('input[name$="-DELETE"]');
                if (deleteCheckbox && deleteCheckbox.checked) return false;
                return true;
            });
        }

        function renumberOrder() {
            const rows = visibleRows();
            rows.forEach((row, index) => {
                const orderInput = row.querySelector('input[name$="-order"]');
                if (!orderInput) return;
                orderInput.value = String(index + 1);
                orderInput.dispatchEvent(new Event('change', { bubbles: true }));
            });
        }

        function makeDraggable(row) {
            if (!isRealRow(row)) return;

            row.setAttribute('draggable', 'true');

            row.addEventListener('dragstart', (e) => {
                row.classList.add('memorialimage-row-dragging');
                if (e.dataTransfer) {
                    e.dataTransfer.effectAllowed = 'move';
                    e.dataTransfer.setData('text/plain', 'memorial-image-row');
                }
            });

            row.addEventListener('dragend', () => {
                row.classList.remove('memorialimage-row-dragging');
            });
        }

        function getDragAfterElement(container, y) {
            const draggableElements = Array.from(container.querySelectorAll('tr[draggable="true"]:not(.memorialimage-row-dragging)'))
                .filter(isRealRow);

            return draggableElements.reduce(
                (closest, child) => {
                    const box = child.getBoundingClientRect();
                    const offset = y - box.top - box.height / 2;
                    if (offset < 0 && offset > closest.offset) {
                        return { offset: offset, element: child };
                    }
                    return closest;
                },
                { offset: Number.NEGATIVE_INFINITY, element: null }
            ).element;
        }

        tbody.addEventListener('dragover', (e) => {
            e.preventDefault();
            const dragging = tbody.querySelector('.memorialimage-row-dragging');
            if (!dragging) return;

            const afterElement = getDragAfterElement(tbody, e.clientY);
            if (afterElement == null) {
                tbody.appendChild(dragging);
            } else {
                tbody.insertBefore(dragging, afterElement);
            }
        });

        tbody.addEventListener('drop', (e) => {
            e.preventDefault();
            renumberOrder();
        });

        Array.from(tbody.querySelectorAll('tr')).forEach(makeDraggable);

        const observer = new MutationObserver((mutations) => {
            let changed = false;
            mutations.forEach((mutation) => {
                mutation.addedNodes.forEach((node) => {
                    if (node.nodeType === 1 && node.matches && node.matches('tr')) {
                        makeDraggable(node);
                        changed = true;
                    }
                });
            });
            if (changed) {
                renumberOrder();
            }
        });

        observer.observe(tbody, { childList: true });

        tbody.addEventListener('change', (e) => {
            const target = e.target;
            if (target && target.name && target.name.endsWith('-DELETE')) {
                renumberOrder();
            }
        });

        renumberOrder();
    }

    function init() {
        const groups = document.querySelectorAll('.inline-group');
        groups.forEach((group) => {
            if (group.querySelector('input[name$="-order"]')) {
                setupSortableInline(group);
            }
        });
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
