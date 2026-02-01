var utils = (function () {
    'use strict';
    var rateInterval;

    return {
        showNoCredits: showNoCredits,
        showRateLimitModal: showRateLimitModal,
        showSizeExceededModal: showSizeExceededModal,
        setInputFilter: setInputFilter,
        formDataToJSON: formDataToJSON,
        promiseRequest: promiseRequest
    };

    function showNoCredits(totalSeconds) {
        $('#nocredits').modal('show');

        if (rateInterval) {
            clearInterval(rateInterval);
        }

        if (totalSeconds === '-') {
            $('.exceeded-wrapper').hide();
        } else {
            $('.exceeded-wrapper').show();
            $('.timer').text(secondsToTime(totalSeconds));
            rateInterval = setInterval(
                function () {
                    totalSeconds--;
                    $('.timer').text(secondsToTime(totalSeconds));

                    if (totalSeconds < 0) {
                        clearInterval(rateInterval);
                        window.location.reload();
                    }
                }, 1000
            );
        }
    }

    function showRateLimitModal(totalSeconds) {
        $('#ratelimit').modal('show');

        if (rateInterval) {
            clearInterval(rateInterval);
        }

        if (totalSeconds === '-') {
            $('.exceeded-wrapper').hide();
        } else {
            $('.exceeded-wrapper').show();
            $('.timer').text(secondsToTime(totalSeconds));
            rateInterval = setInterval(
                function () {
                    totalSeconds--;
                    $('.timer').text(secondsToTime(totalSeconds));

                    if (totalSeconds < 0) {
                        clearInterval(rateInterval);
                        window.location.reload();
                    }
                }, 1000
            );
        }
    }

    function showSizeExceededModal() {
        $('#sizelimit').modal('show');
    }

    function secondsToTime(totalSeconds) {
        var sec_num = parseInt(totalSeconds, 10);
        var hours = Math.floor(sec_num / 3600);
        var minutes = Math.floor((sec_num - (hours * 3600)) / 60);
        var seconds = sec_num - (hours * 3600) - (minutes * 60);

        if (hours < 10) {
            hours = "0" + hours;
        }
        if (minutes < 10) {
            minutes = "0" + minutes;
        }
        if (seconds < 10) {
            seconds = "0" + seconds;
        }
        return hours + ':' + minutes + ':' + seconds;
    }

    function setInputFilter(textbox, inputFilter) {
        ["input", "keydown", "keyup", "mousedown", "mouseup", "select", "contextmenu", "drop"].forEach(function (event) {
            textbox.addEventListener(event, function () {
                if (inputFilter(this.value)) {
                    this.oldValue = this.value;
                    this.oldSelectionStart = this.selectionStart;
                    this.oldSelectionEnd = this.selectionEnd;
                } else if (this.hasOwnProperty("oldValue")) {
                    this.value = this.oldValue;
                    this.setSelectionRange(this.oldSelectionStart, this.oldSelectionEnd);
                } else {
                    this.value = "";
                }
            });
        });
    }

    function formDataToJSON(form) {
        var data = form.serializeArray();
        var dataParsed = {};

        for (var i = 0; i < data.length; i++) {
            var found = data.filter(
                function (item) {
                    return item.name === data[i].name;
                }
            );

            if (found.length > 1) {
                if (dataParsed[data[i].name]) {
                    dataParsed[data[i].name].push(data[i].value);
                } else {
                    dataParsed[data[i].name] = [];
                    dataParsed[data[i].name].push(data[i].value);
                }
            } else {
                dataParsed[data[i].name] = data[i].value;
            }
        }

        return dataParsed;
    }

    function getCookie(name) {
        var cookieValue = null;

        if (document.cookie && document.cookie !== '') {
            var cookies = document.cookie.split(';');

            for (let i = 0; i < cookies.length; i++) {
                var cookie = cookies[i].trim();

                if (cookie.substring(0, name.length + 1) === (name + '=')) {
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }
        return cookieValue;
    }

    /**
     * DELETE: should pass params as object
     */
    function promiseRequest(form, method, endpoint, params, files, xhr, contentType) {
        var requestParams = {
            url: endpoint,
            method: method,
            contentType: files ? false : 'application/json',
            dataType: files ? false : 'json',
            cache: false,
        };
        var p;

        if (xhr) {
            requestParams.xhr = xhr;
        }

        if (params) {
            if (params.csrfmiddlewaretoken) {
                requestParams.headers = {
                    "X-CSRFToken": params.csrfmiddlewaretoken
                };
                delete params.csrfmiddlewaretoken;
            } else {
                requestParams.headers = {
                    "X-CSRFToken": getCookie('csrftoken')
                };
            }
        }

        if (form) {
            form.find('button').addClass('m-progress').attr('disabled', 'disabled');
            form.find('.alert').remove();
            form.find('.error-message').remove();
            form.find('.error').removeClass('error');
        }

        if (params) {
            if (method.toLowerCase() === 'get') {
                requestParams.data = params;
            } else {
                if (files !== null && files !== undefined) {
                    var formData = new FormData();

                    $.each(files, function (e, item) {
                        formData.append('files', item);
                    });

                    formData.append('data', JSON.stringify(params));
                    requestParams.processData = false;
                    requestParams.data = formData;
                } else {
                    requestParams.data = JSON.stringify(params);
                }
            }
        }

        if (method.toLowerCase() === 'delete' && params) {
            requestParams.url += '?' + $.param(params);
        }

        p = $.ajax(requestParams);
        p = p.then(
            function (response) {
                return response
            },
            function (error) {
                return $.Deferred().reject(error.responseJSON);
            }
        ).always(
            function () {
                if (form) {
                    form.find('button').removeClass('m-progress').removeAttr('disabled');
                }
            }
        );

        return p;
    }
}());