(function($) {
    'use strict';

    function actualizarBotones() {
        $('div.submit-row input[name="_save"]').each(function() {
            $(this).val('Finalizar Matrícula');
        });
    }

    $(document).ready(function() {
        actualizarBotones();

        // Reaplicar si Django agrega botones dinámicamente
        $(document).on('formset:added', actualizarBotones);
        $(document).on('formset:removed', actualizarBotones);
    });
})(django.jQuery);

