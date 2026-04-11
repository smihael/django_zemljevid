(function () {
    const BULK_META_FIELD_NAMES = [
        'bulk_caption',
        'bulk_author',
        'bulk_date_taken',
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
        setMetaVisibility(hasSelectedFiles());
    }

    function init() {
        const fileInput = getInput('bulk_images');
        if (!fileInput) return;

        syncVisibility();
        fileInput.addEventListener('change', syncVisibility);
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
