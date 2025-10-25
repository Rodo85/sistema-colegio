(function($) {
    'use strict';

    // Esperar a que el DOM esté listo
    $(document).ready(function() {
        console.log('Script buscar-estudiante-existente.js cargado');

        // Solo ejecutar en la página de agregar estudiante (no en edición)
        var identificacionField = $('#id_identificacion');
        if (identificacionField.length === 0) {
            console.log('Campo identificacion no encontrado');
            return;
        }

        // Verificar si es un nuevo estudiante (no tiene parámetro 'change' en la URL)
        var urlPath = window.location.pathname;
        var isEdit = urlPath.indexOf('/change/') !== -1;
        
        if (isEdit) {
            console.log('Modo edición detectado, no mostrar botón de búsqueda');
            return;
        }

        // Agregar botón de búsqueda al lado del campo identificación
        var botonBuscar = $('<button>')
            .attr('type', 'button')
            .attr('id', 'btn-buscar-estudiante')
            .attr('class', 'button')
            .css({
                'margin-left': '10px',
                'padding': '8px 15px',
                'background': '#417690',
                'color': 'white',
                'border': 'none',
                'border-radius': '4px',
                'cursor': 'pointer',
                'display': 'inline-block'
            })
            .html('🔍 Buscar')
            .on('click', buscarEstudiante);

        // Insertar el botón después del campo identificación
        identificacionField.after(botonBuscar);

        // Agregar área para mostrar resultados
        var areaResultados = $('<div>')
            .attr('id', 'resultados-busqueda')
            .css({
                'margin-top': '15px',
                'padding': '15px',
                'border-radius': '5px',
                'display': 'none'
            });
        
        identificacionField.parent().after(areaResultados);

        console.log('Botón de búsqueda agregado');

        function buscarEstudiante() {
            var identificacion = identificacionField.val().trim();
            
            if (!identificacion) {
                alert('Por favor ingrese una identificación');
                return;
            }

            console.log('Buscando estudiante con identificación:', identificacion);
            var boton = $('#btn-buscar-estudiante');
            boton.prop('disabled', true).html('⏳ Buscando...');

            $.ajax({
                url: '/matricula/api/buscar-estudiante/',
                method: 'GET',
                data: { identificacion: identificacion },
                success: function(response) {
                    console.log('Respuesta recibida:', response);
                    mostrarResultados(response);
                },
                error: function(xhr, status, error) {
                    console.error('Error en la búsqueda:', error);
                    alert('Error al buscar el estudiante: ' + error);
                },
                complete: function() {
                    boton.prop('disabled', false).html('🔍 Buscar');
                }
            });
        }

        function mostrarResultados(data) {
            var resultados = $('#resultados-busqueda');
            
            if (!data.existe) {
                resultados
                    .css('background-color', '#d4edda')
                    .css('border', '1px solid #c3e6cb')
                    .html('<strong style="color: #155724;">✓ Identificación disponible</strong><br>No existe ningún estudiante con esta identificación. Puede continuar con el registro.')
                    .fadeIn();
                return;
            }

            // El estudiante existe
            var estudiante = data.estudiante;
            var institucion = data.institucion_activa;

            if (data.ya_esta_en_institucion) {
                // Ya está en esta institución
                resultados
                    .css('background-color', '#fff3cd')
                    .css('border', '1px solid #ffeaa7')
                    .html(
                        '<strong style="color: #856404;">⚠ Estudiante ya registrado en su institución</strong><br>' +
                        'Nombre: <strong>' + estudiante.nombre_completo + '</strong><br>' +
                        'Institución actual: ' + institucion.nombre
                    )
                    .fadeIn();
            } else {
                // Existe en otra institución
                var html = 
                    '<div style="background-color: #d1ecf1; border: 1px solid #bee5eb; padding: 15px; border-radius: 5px;">' +
                    '<strong style="color: #0c5460;">ℹ Estudiante encontrado en el sistema</strong><br>' +
                    '<strong>Nombre:</strong> ' + estudiante.nombre_completo + '<br>' +
                    '<strong>Fecha de nacimiento:</strong> ' + estudiante.fecha_nacimiento + '<br>' +
                    '<strong>Institución actual:</strong> ' + institucion.nombre + '<br><br>' +
                    '<button type="button" id="btn-copiar-datos" class="button" style="background: #28a745; color: white; padding: 10px 20px; border: none; border-radius: 4px; cursor: pointer;">' +
                    '✓ Copiar datos y agregar a mi institución' +
                    '</button>' +
                    '</div>';
                
                resultados
                    .html(html)
                    .fadeIn();

                // Agregar evento al botón de copiar datos
                $('#btn-copiar-datos').on('click', function() {
                    copiarDatosEstudiante(estudiante);
                });
            }
        }

        function copiarDatosEstudiante(estudiante) {
            console.log('Copiando datos del estudiante:', estudiante);

            // Llenar los campos del formulario con los datos del estudiante
            $('#id_identificacion').val(estudiante.identificacion);
            $('#id_primer_apellido').val(estudiante.primer_apellido);
            $('#id_segundo_apellido').val(estudiante.segundo_apellido);
            $('#id_nombres').val(estudiante.nombres);
            $('#id_correo').val(estudiante.correo);
            
            if (estudiante.celular) $('#id_celular').val(estudiante.celular);
            if (estudiante.telefono_casa) $('#id_telefono_casa').val(estudiante.telefono_casa);
            if (estudiante.direccion_exacta) $('#id_direccion_exacta').val(estudiante.direccion_exacta);
            
            // Campos de selección (select)
            if (estudiante.sexo) $('#id_sexo').val(estudiante.sexo).trigger('change');
            if (estudiante.nacionalidad) $('#id_nacionalidad').val(estudiante.nacionalidad).trigger('change');
            if (estudiante.provincia) $('#id_provincia').val(estudiante.provincia).trigger('change');
            if (estudiante.canton) $('#id_canton').val(estudiante.canton).trigger('change');
            if (estudiante.distrito) $('#id_distrito').val(estudiante.distrito).trigger('change');
            if (estudiante.fecha_nacimiento) $('#id_fecha_nacimiento').val(estudiante.fecha_nacimiento);

            // Ocultar resultados
            $('#resultados-busqueda').fadeOut();

            // Mostrar mensaje de éxito
            alert('✓ Datos copiados exitosamente.\n\nRevise la información y complete los campos faltantes antes de guardar.');

            // Scroll al inicio del formulario
            $('html, body').animate({ scrollTop: 0 }, 'slow');
        }
    });

})(django.jQuery);

