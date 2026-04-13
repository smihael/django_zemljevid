(function () {
    function moveChildren(sourceEl, targetEl) {
        while (sourceEl.firstChild) {
            targetEl.appendChild(sourceEl.firstChild);
        }
    }

    function rowForField(input) {
        if (!input) return null;
        return input.closest('.form-row') || input.closest('.fieldBox') || input.closest('td') || input.parentElement;
    }

    function setRequired(input, required) {
        if (!input) return;
        input.required = !!required;
        input.setAttribute('aria-required', required ? 'true' : 'false');
    }

    function setVisible(input, visible) {
        const row = rowForField(input);
        if (!row) return;

        const isTableCell = row.tagName === 'TD' || row.classList.contains('fieldBox');
        if (isTableCell) {
            row.classList.toggle('memorialimage-empty-cell', !visible);
            row.setAttribute('aria-hidden', visible ? 'false' : 'true');
            row.style.display = '';
            return;
        }

        row.style.display = visible ? '' : 'none';
    }

    function ensureInlineDateComplexCell(container) {
        const row = container && container.tagName === 'TR' ? container : container.closest && container.closest('tr');
        if (!row || row.dataset.memorialImageDateComplexReady === '1') return;

        const takenCell = row.querySelector('td.field-date_taken');
        const approxCell = row.querySelector('td.field-date_approx_text');
        if (!takenCell || !approxCell) return;

        const takenInput = takenCell.querySelector('[name$="-date_taken"]');
        const approxInput = approxCell.querySelector('[name$="-date_approx_text"]');
        if (!takenInput || !approxInput) return;

        const exactSlot = document.createElement('div');
        exactSlot.className = 'memorialimage-date-slot memorialimage-date-slot-exact';

        const approxSlot = document.createElement('div');
        approxSlot.className = 'memorialimage-date-slot memorialimage-date-slot-approx';

        moveChildren(takenCell, exactSlot);
        moveChildren(approxCell, approxSlot);

        takenCell.appendChild(exactSlot);
        takenCell.appendChild(approxSlot);

        approxCell.classList.add('memorialimage-date-padding-cell');
        approxCell.innerHTML = '&nbsp;';

        row.dataset.memorialImageDateComplexReady = '1';
    }

    function syncInlineDateComplexCell(container, mode) {
        const row = container && container.tagName === 'TR' ? container : container.closest && container.closest('tr');
        if (!row) return false;

        const takenCell = row.querySelector('td.field-date_taken');
        const approxCell = row.querySelector('td.field-date_approx_text');
        const exactSlot = row.querySelector('.memorialimage-date-slot-exact');
        const approxSlot = row.querySelector('.memorialimage-date-slot-approx');
        if (!takenCell || !approxCell || !exactSlot || !approxSlot) return false;

        const showTaken = mode === 'exact';
        const showApprox = mode === 'approximate';

        exactSlot.classList.toggle('is-visible', showTaken);
        approxSlot.classList.toggle('is-visible', showApprox);
        takenCell.classList.toggle('memorialimage-date-empty', !showTaken && !showApprox);

        approxCell.classList.add('memorialimage-date-padding-cell');
        if (!approxCell.innerHTML.trim()) {
            approxCell.innerHTML = '&nbsp;';
        }

        return true;
    }

    function syncOne(container) {
        const modeInput = container.querySelector('[name$="-date_mode"], #id_date_mode');
        if (!modeInput) return;

        const takenInput = container.querySelector('[name$="-date_taken"], #id_date_taken');
        const approxInput = container.querySelector('[name$="-date_approx_text"], #id_date_approx_text');

        ensureInlineDateComplexCell(container);

        const mode = modeInput.value || 'exact';
        const showTaken = mode === 'exact';
        const showApprox = mode === 'approximate';

        const usedComplexCell = syncInlineDateComplexCell(container, mode);
        if (!usedComplexCell) {
            setVisible(takenInput, showTaken);
            setVisible(approxInput, showApprox);
        }

        setRequired(takenInput, showTaken);
        setRequired(approxInput, showApprox);

        if (!showTaken && takenInput) {
            takenInput.value = '';
        }
        if (!showApprox && approxInput) {
            approxInput.value = '';
        }
    }

    function bindModeListeners(root) {
        const modeInputs = root.querySelectorAll('[name$="-date_mode"], #id_date_mode');
        modeInputs.forEach((modeInput) => {
            modeInput.addEventListener('change', function () {
                const container = modeInput.closest('tr') || modeInput.closest('.inline-related') || document;
                syncOne(container);
            });

            const container = modeInput.closest('tr') || modeInput.closest('.inline-related') || document;
            syncOne(container);
        });

    }

    function init() {
        bindModeListeners(document);

        document.addEventListener('formset:added', function (event) {
            bindModeListeners(event.target || document);
            syncOne(event.target || document);
        });
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
