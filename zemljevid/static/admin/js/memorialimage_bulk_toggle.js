(function () {
    const BULK_FIELD_NAMES = [
        'bulk_images',
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

    function moveBulkUploadSectionAfterInlines() {
        const firstBulkRow = getFieldRow('bulk_images');
        if (!firstBulkRow) return;

        const rows = BULK_FIELD_NAMES
            .map((name) => getFieldRow(name))
            .filter((row) => !!row);

        if (!rows.length) return;

        const existingContainer = document.getElementById('bulk-image-upload-module');
        const container = existingContainer || document.createElement('fieldset');
        container.id = 'bulk-image-upload-module';
        container.className = 'module aligned';

        if (!existingContainer) {
            const title = document.createElement('h2');
            const label = firstBulkRow.querySelector('label');
            title.textContent = (label && label.textContent && label.textContent.trim()) || 'Bulk upload';
            container.appendChild(title);
        }

        rows.forEach((row) => container.appendChild(row));

        const inlineGroups = document.querySelectorAll('.inline-group');
        const submitRow = document.querySelector('.submit-row');

        if (inlineGroups.length) {
            const lastInline = inlineGroups[inlineGroups.length - 1];
            if (lastInline.nextSibling) {
                lastInline.parentNode.insertBefore(container, lastInline.nextSibling);
            } else {
                lastInline.parentNode.appendChild(container);
            }
            return;
        }

        if (submitRow && submitRow.parentNode) {
            submitRow.parentNode.insertBefore(container, submitRow);
        }
    }

    function hasSelectedFiles() {
        const fileInput = getInput('bulk_images');
        if (!fileInput || !fileInput.files) return false;
        return fileInput.files.length > 0;
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

    function syncDateFields(hasFiles) {
        const modeInput = getInput('bulk_date_mode');
        const mode = modeInput ? modeInput.value : 'exact';
        const selectedFiles = typeof hasFiles === 'boolean' ? hasFiles : hasSelectedFiles();

        const showTaken = mode === 'exact';
        const showApprox = mode === 'approximate';

        setRowVisibility('bulk_date_taken', showTaken);
        setRowVisibility('bulk_date_approx_text', showApprox);

        setRequired('bulk_date_taken', selectedFiles && showTaken);
        setRequired('bulk_date_approx_text', selectedFiles && showApprox);

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

        moveBulkUploadSectionAfterInlines();

        syncDateFields(hasSelectedFiles());
        fileInput.addEventListener('change', () => syncDateFields(hasSelectedFiles()));
        if (modeInput) {
            modeInput.addEventListener('change', () => syncDateFields(hasSelectedFiles()));
        }
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
