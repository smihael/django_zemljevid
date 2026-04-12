(function () {
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
        row.style.display = visible ? '' : 'none';
    }

    function syncOne(container) {
        const modeInput = container.querySelector('[name$="-date_mode"], #id_date_mode');
        if (!modeInput) return;

        const takenInput = container.querySelector('[name$="-date_taken"], #id_date_taken');
        const approxInput = container.querySelector('[name$="-date_approx_text"], #id_date_approx_text');

        const mode = modeInput.value || 'exact';
        const showTaken = mode === 'exact';
        const showApprox = mode === 'approximate';

        setVisible(takenInput, showTaken);
        setVisible(approxInput, showApprox);

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
