(function waitForDjangoJQuery() {
    if (typeof window.django === "undefined" || typeof django.jQuery === "undefined") {
        setTimeout(waitForDjangoJQuery, 50);
        return;
    }
    var $ = django.jQuery;
    $(function() {
        // Use ends-with selector in case of inlines or different prefixes
        var $contentType = $('[id$="content_type"]');
        var $objectId = $('[id$="object_id"]');

        function updateObjectIdChoices() {
            var contentType = $contentType.val();
            if (!contentType) {
                $objectId.empty();
                return;
            }
            // Use admin root for AJAX endpoint
            var baseUrl = window.location.pathname.replace(/(add|\d+|change)\/?$/, '');
            if (!baseUrl.endsWith('/')) baseUrl += '/';
            var ajaxUrl = baseUrl + 'get-objects/';
            console.log('Fetching objects for content_type:', contentType, 'via', ajaxUrl);
            $.ajax({
                url: ajaxUrl,
                data: { content_type: contentType },
                success: function(data) {
                    $objectId.empty();
                    if (data.results && data.results.length) {
                        $.each(data.results, function(i, obj) {
                            $objectId.append($('<option>', {
                                value: obj.id,
                                text: obj.text
                            }));
                        });
                    } else {
                        $objectId.append($('<option>', {
                            value: '',
                            text: 'No objects found'
                        }));
                    }
                },
                error: function(xhr, status, error) {
                    console.error('AJAX error:', status, error);
                }
            });
        }

        $contentType.change(updateObjectIdChoices);
        updateObjectIdChoices();

        // Ensure Select2 uses the correct jQuery instance
        if (typeof window.jQuery === "undefined") {
            window.jQuery = django.jQuery;
        }
        var initialObjectId = $objectId.val();
        if (initialObjectId) {
            // Fetch the display text for the initial value
            var contentType = $contentType.val();
            var baseUrl = window.location.pathname.replace(/(add|\d+|change)\/?$/, '');
            if (!baseUrl.endsWith('/')) baseUrl += '/';
            var ajaxUrl = baseUrl + 'get-objects/';
            $.ajax({
                url: ajaxUrl,
                data: { content_type: contentType, object_id: initialObjectId },
                dataType: 'json',
                success: function(data) {
                    if (data.results && data.results.length) {
                        var obj = data.results[0];
                        var option = new Option(obj.text, obj.id, true, true);
                        $objectId.append(option).trigger('change');
                    }
                }
            });
        }
        // Wait for Select2 to be available before initializing
        function initSelect2() {
            if (typeof $objectId.select2 !== "function") {
                setTimeout(initSelect2, 50);
                return;
            }
            $objectId.select2({
                width: '100%',
                placeholder: 'Select an object',
                allowClear: true,
                ajax: {
                    url: function() {
                        var baseUrl = window.location.pathname.replace(/(add|\d+|change)\/?$/, '');
                        if (!baseUrl.endsWith('/')) baseUrl += '/';
                        return baseUrl + 'get-objects/';
                    },
                    dataType: 'json',
                    delay: 250,
                    data: function(params) {
                        return {
                            content_type: $contentType.val(),
                            q: params.term, // search term
                            page: params.page || 1
                        };
                    },
                    processResults: function(data, params) {
                        params.page = params.page || 1;
                        return {
                            results: data.results,
                            pagination: {
                                more: data.more
                            }
                        };
                    },
                    cache: true
                },
                minimumInputLength: 2
            });
            $objectId.next('.select2').css('width', '100%');
        }
        initSelect2();
    });
})();
