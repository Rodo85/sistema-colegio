// static/matricula/js/dependent-dropdowns.js
(function($) {
    $(document).ready(function() {
        // Función para cargar cantones
        function loadCantons(provinceId) {
            if (!provinceId) {
                $('#id_canton').empty().append('<option value="">----</option>');
                $('#id_distrito').empty().append('<option value="">----</option>');
                return;
            }
            
            $.getJSON('/catalogos/api/cantones/' + provinceId + '/', function(data) {
                var $canton = $('#id_canton').empty();
                $canton.append('<option value="">----</option>');
                $('#id_distrito').empty().append('<option value="">----</option>');
                
                $.each(data, function(index, item) {
                    $canton.append($('<option>', {
                        value: item.id,
                        text: item.nombre
                    }));
                });
            }).fail(function(jqXHR, textStatus, errorThrown) {
                console.error("Error loading cantones:", textStatus, errorThrown);
            });
        }

        // Función para cargar distritos
        function loadDistricts(cantonId) {
            if (!cantonId) {
                $('#id_distrito').empty().append('<option value="">----</option>');
                return;
            }
            
            $.getJSON('/catalogos/api/distritos/' + cantonId + '/', function(data) {
                var $distrito = $('#id_distrito').empty();
                $distrito.append('<option value="">----</option>');
                
                $.each(data, function(index, item) {
                    $distrito.append($('<option>', {
                        value: item.id,
                        text: item.nombre
                    }));
                });
            }).fail(function(jqXHR, textStatus, errorThrown) {
                console.error("Error loading distritos:", textStatus, errorThrown);
            });
        }

        // Eventos
        $('#id_provincia').on('change', function() {
            loadCantons($(this).val());
        });

        $('#id_canton').on('change', function() {
            loadDistricts($(this).val());
        });

        // Carga inicial si hay valores seleccionados
        if ($('#id_provincia').val()) {
            loadCantons($('#id_provincia').val());
            
            if ($('#id_canton').val()) {
                loadDistricts($('#id_canton').val());
            }
        }
    });
})(django.jQuery);