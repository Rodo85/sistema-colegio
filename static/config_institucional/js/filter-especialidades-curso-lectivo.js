$(document).ready(function() {
    console.log("🔧 Inicializando filtro de especialidades por curso lectivo...");
    
    // Función para filtrar especialidades según el curso lectivo
    function filtrarEspecialidadesPorCursoLectivo() {
        var cursoLectivoId = $('#id_curso_lectivo').val();
        var institucionId = $('input[name="institucion"]').val() || $('#id_institucion').val();
        
        console.log("📚 Curso lectivo seleccionado:", cursoLectivoId);
        console.log("🏫 Institución:", institucionId);
        
        if (cursoLectivoId) {
            // Hacer petición AJAX para obtener especialidades del curso lectivo
            $.ajax({
                url: '/admin/config_institucional/especialidadcursolectivo/autocomplete/',
                data: {
                    'forward': JSON.stringify({
                        'curso_lectivo_id': cursoLectivoId,
                        'institucion_id': institucionId
                    })
                },
                success: function(data) {
                    console.log("✅ Especialidades obtenidas:", data);
                    
                    var $especialidadSelect = $('#id_especialidad_curso');
                    var valorActual = $especialidadSelect.val();
                    
                    // Limpiar opciones actuales
                    $especialidadSelect.empty();
                    
                    // Agregar opción vacía
                    $especialidadSelect.append('<option value="">---------</option>');
                    
                    // Agregar especialidades filtradas
                    if (data.results && data.results.length > 0) {
                        data.results.forEach(function(especialidad) {
                            var selected = especialidad.id == valorActual ? 'selected' : '';
                            $especialidadSelect.append(
                                '<option value="' + especialidad.id + '" ' + selected + '>' + 
                                especialidad.text + '</option>'
                            );
                        });
                    }
                    
                    // Si no hay especialidades, mostrar mensaje
                    if (!data.results || data.results.length === 0) {
                        $especialidadSelect.append('<option value="" disabled>No hay especialidades disponibles para este curso lectivo</option>');
                    }
                },
                error: function(xhr, status, error) {
                    console.error("❌ Error al obtener especialidades:", error);
                }
            });
        } else {
            // Si no hay curso lectivo seleccionado, limpiar especialidades
            var $especialidadSelect = $('#id_especialidad_curso');
            $especialidadSelect.empty();
            $especialidadSelect.append('<option value="">---------</option>');
            $especialidadSelect.append('<option value="" disabled>Seleccione un curso lectivo primero</option>');
        }
    }
    
    // Evento cuando cambia el curso lectivo
    $('#id_curso_lectivo').on('change', function() {
        console.log("🔄 Curso lectivo cambiado, filtrando especialidades...");
        filtrarEspecialidadesPorCursoLectivo();
    });
    
    // Filtrar al cargar la página si ya hay un curso lectivo seleccionado
    if ($('#id_curso_lectivo').val()) {
        console.log("🚀 Cargando especialidades para curso lectivo existente...");
        filtrarEspecialidadesPorCursoLectivo();
    }
    
    // También escuchar cambios en el autocomplete de Django
    $(document).on('select2:select', '#id_curso_lectivo', function(e) {
        console.log("🎯 Select2 cambio en curso lectivo");
        setTimeout(filtrarEspecialidadesPorCursoLectivo, 100);
    });
});

























