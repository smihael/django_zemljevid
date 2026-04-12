(function () {
    const BULK_META_FIELD_NAMES = [
        'bulk_caption',
        'bulk_author',
        'bulk_date_mode',
        'bulk_date_taken',
        'bulk_date_approx_text',
        'bulk_license',
        'bulk_source',
    ];

    function getInput(name) {
        return document.getElementById(`id_${name}`);
    }

    function getFieldRow(name) {
        const input = getInput(name);
        if (!input) return null;
        return input.closest('.form-row') || input.closest('.fieldBox') || input.parentElement;
    }

    function setMetaVisibility(show) {
        BULK_META_FIELD_NAMES.forEach((name) => {
            const row = getFieldRow(name);
            if (!row) return;
            row.style.display = show ? '' : 'none';
        });
    }

    function hasSelectedFiles() {
        const fileInput = getInput('bulk_images');
        if (!fileInput || !fileInput.files) return false;
        return fileInput.files.length > 0;
    }

    function syncVisibility() {
        const showMeta = hasSelectedFiles();
        setMetaVisibility(showMeta);
        if (showMeta) {
            syncDateFields();
        }
    }

    function setRequired(name, required) {
        const input = getInput(name);
        if (!input) return;
        input.required = !!required;
        input.setAttribute('aria-required', required ? 'true' : 'false');
    }

    function setRowVisibility(name, show) {
        const row = getFieldRow(name);
        if (!row) return;
        row.style.display = show ? '' : 'none';
    }

    function syncDateFields() {
        const modeInput = getInput('bulk_date_mode');
        const mode = modeInput ? modeInput.value : 'exact';

        const showTaken = mode === 'exact';
        const showApprox = mode === 'approximate';

        setRowVisibility('bulk_date_taken', showTaken);
        setRowVisibility('bulk_date_approx_text', showApprox);

        setRequired('bulk_date_taken', showTaken);
        setRequired('bulk_date_approx_text', showApprox);

        if (!showTaken) {
            const taken = getInput('bulk_date_taken');
            if (taken) taken.value = '';
        }
        if (!showApprox) {
            const approx = getInput('bulk_date_approx_text');
            if (approx) approx.value = '';
        }
    }

    function init() {
        const fileInput = getInput('bulk_images');
        if (!fileInput) return;

        const modeInput = getInput('bulk_date_mode');

        syncVisibility();
        fileInput.addEventListener('change', syncVisibility);
        if (modeInput) {
            modeInput.addEventListener('change', syncDateFields);
        }
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
