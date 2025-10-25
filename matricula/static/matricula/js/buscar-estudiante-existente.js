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

        function getCookie(name) {
            var cookieValue = null;
            if (document.cookie && document.cookie !== '') {
                var cookies = document.cookie.split(';');
                for (var i = 0; i < cookies.length; i++) {
                    var cookie = cookies[i].trim();
                    if (cookie.substring(0, name.length + 1) === (name + '=')) {
                        cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                        break;
                    }
                }
            }
            return cookieValue;
        }

        function copiarDatosEstudiante(estudiante) {
            console.log('Agregando estudiante a la institución:', estudiante);

            // Deshabilitar el botón para evitar clics múltiples
            var botonCopiar = $('#btn-copiar-datos');
            botonCopiar.prop('disabled', true).html('⏳ Agregando...');

            // Obtener CSRF token
            var csrftoken = getCookie('csrftoken');

            // Hacer llamada AJAX para agregar el estudiante a la institución
            $.ajax({
                url: '/matricula/api/agregar-estudiante-institucion/',
                method: 'POST',
                headers: {
                    'X-CSRFToken': csrftoken,
                    'Content-Type': 'application/json'
                },
                data: JSON.stringify({
                    estudiante_id: estudiante.id
                }),
                success: function(response) {
                    console.log('Respuesta del servidor:', response);
                    
                    if (response.success) {
                        alert('✓ ' + response.message + '\n\nSerás redirigido al listado de estudiantes donde podrás ver al estudiante agregado.');
                        // Redirigir al listado de estudiantes
                        window.location.href = '/admin/matricula/estudiante/';
                    } else {
                        alert('Error: ' + response.error);
                        botonCopiar.prop('disabled', false).html('✓ Copiar datos y agregar a mi institución');
                    }
                },
                error: function(xhr, status, error) {
                    console.error('Error al agregar estudiante:', error);
                    var mensajeError = 'Ocurrió un error al agregar el estudiante a tu institución.';
                    
                    try {
                        var response = JSON.parse(xhr.responseText);
                        if (response.error) {
                            mensajeError = 'Error: ' + response.error;
                        }
                    } catch (e) {
                        console.error('Error al parsear respuesta:', e);
                    }
                    
                    alert(mensajeError);
                    botonCopiar.prop('disabled', false).html('✓ Copiar datos y agregar a mi institución');
                }
            });
        }
    });

})(django.jQuery);

