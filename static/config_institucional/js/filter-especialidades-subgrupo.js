// FILTRO DE ESPECIALIDADES PARA SUBGRUPO CURSO LECTIVO
(function($) {
    if (!$) {
        console.error("filter-especialidades-subgrupo.js: jQuery no encontrado");
        return;
    }
    
    $(function() {
        console.log("=== FILTRO DE ESPECIALIDADES PARA SUBGRUPO CURSO LECTIVO ===");
        console.log("jQuery version:", $.fn.jquery);
        
        // ──────────────── ACTUALIZAR ESPECIALIDADES DISPONIBLES ────────────────
        function actualizarEspecialidadesDisponibles() {
            console.log("🔄 Actualizando especialidades disponibles...");
            console.log("===========================================");
            
            // DEBUG: Mostrar todos los campos disponibles
            console.log("🔍 CAMPOS DISPONIBLES EN LA PÁGINA:");
            $('select[name*="curso_lectivo"]').each(function(i) {
                console.log("   - Select curso_lectivo[" + i + "]:", $(this).attr('name'), "=", $(this).val());
            });
            $('select[name*="institucion"]').each(function(i) {
                console.log("   - Select institucion[" + i + "]:", $(this).attr('name'), "=", $(this).val());
            });
            $('input[name*="institucion"]').each(function(i) {
                console.log("   - Input institucion[" + i + "]:", $(this).attr('name'), "=", $(this).val());
            });
            $('select[name*="especialidad_curso"]').each(function(i) {
                console.log("   - Select especialidad_curso[" + i + "]:", $(this).attr('name'), "=", $(this).val());
            });
            
            // Obtener el curso lectivo seleccionado
            var $cursoLectivo = $('select[name*="curso_lectivo"]');
            var cursoLectivoId = $cursoLectivo.val();
            
            // Obtener la institución (puede ser hidden input o select)
            var institucionId = $('input[name="institucion"]').val() || 
                              $('select[name="institucion"]').val() ||
                              $('#id_institucion').val() ||
                              $('input[name*="institucion"]').val() ||
                              $('select[name*="institucion"]').val();
            
            console.log("📚 RESULTADO - Curso lectivo seleccionado:", cursoLectivoId);
            console.log("🏫 RESULTADO - Institución:", institucionId);
            console.log("🔍 TIPO DE DATOS:");
            console.log("   - Curso lectivo tipo:", typeof cursoLectivoId, "vacío?", !cursoLectivoId);
            console.log("   - Institución tipo:", typeof institucionId, "vacío?", !institucionId);
            
            // LÓGICA CRÍTICA: Si no hay curso lectivo O institución, limpiar especialidades
            if (!cursoLectivoId || !institucionId) {
                console.log("❌ FALTAN DATOS REQUERIDOS - limpiando especialidades");
                console.log("   - Curso lectivo:", cursoLectivoId ? "✓ PRESENTE" : "✗ FALTA");
                console.log("   - Institución:", institucionId ? "✓ PRESENTE" : "✗ FALTA");
                limpiarEspecialidades();
                return;
            }
            
            console.log("✅ DATOS VÁLIDOS - Haciendo petición AJAX");
            
            var ajaxData = {
                'forward': JSON.stringify({
                    'curso_lectivo_id': cursoLectivoId,
                    'institucion_id': institucionId
                })
            };
            
            console.log("📡 URL:", '/config/especialidad-curso-lectivo-autocomplete/');
            console.log("📡 Datos enviados:", ajaxData);
            
            // Hacer petición AJAX para obtener especialidades disponibles
            $.ajax({
                url: '/config/especialidad-curso-lectivo-autocomplete/',
                method: 'GET',
                data: ajaxData,
                beforeSend: function(xhr, settings) {
                    console.log("🚀 Enviando petición AJAX...");
                    console.log("   - URL completa:", settings.url + '?' + $.param(settings.data));
                },
                success: function(response) {
                    console.log("✅ RESPUESTA RECIBIDA:");
                    console.log("   - Respuesta completa:", response);
                    console.log("   - Tipo de respuesta:", typeof response);
                    console.log("   - Tiene 'results'?", response.hasOwnProperty('results'));
                    
                    if (response.results) {
                        console.log("   - Cantidad de results:", response.results.length);
                        console.log("   - Primer result:", response.results[0]);
                    }
                    
                    if (response.results && response.results.length > 0) {
                        console.log("✅ Especialidades obtenidas:", response.results);
                        actualizarOpcionesEspecialidad(response.results);
                    } else {
                        console.log("⚠️ No hay especialidades disponibles para este curso lectivo e institución");
                        limpiarEspecialidades();
                    }
                },
                error: function(xhr, status, error) {
                    console.error("❌ ERROR AJAX:");
                    console.error("   - Status:", status);
                    console.error("   - Error:", error);
                    console.error("   - Response status:", xhr.status);
                    console.error("   - Response text:", xhr.responseText);
                    limpiarEspecialidades();
                }
            });
        }
        
        function actualizarOpcionesEspecialidad(especialidades) {
            console.log("🔄 Actualizando opciones de especialidad...");
            
            $('select[name*="especialidad_curso"]').each(function() {
                if ($(this).attr('name').includes('__prefix__')) return;
                
                var $select = $(this);
                var valorActual = $select.val();
                
                console.log("🎯 Procesando select especialidad_curso:", $select.attr('name'));
                console.log("   - Valor actual:", valorActual);
                
                // Para autocomplete fields, necesitamos destruir y recrear Select2
                if ($select.hasClass('select2-hidden-accessible')) {
                    try {
                        $select.select2('destroy');
                    } catch (e) {
                        console.log("⚠️ Error destruyendo Select2:", e);
                        $select.removeClass('select2-hidden-accessible');
                        $select.next('.select2-container').remove();
                    }
                }
                
                // Limpiar opciones existentes
                $select.empty();
                
                // Agregar opción vacía
                $select.append('<option value="">---------</option>');
                
                // Agregar especialidades disponibles
                especialidades.forEach(function(esp) {
                    var $option = $('<option></option>')
                        .val(esp.id)
                        .text(esp.text);
                    
                    // Marcar como seleccionada si era la opción actual
                    if (esp.id == valorActual) {
                        $option.prop('selected', true);
                        console.log("✅ Manteniendo especialidad seleccionada:", esp.text);
                    }
                    
                    $select.append($option);
                });
                
                // Reinicializar Select2 para autocomplete
                if (typeof $select.select2 === 'function') {
                    try {
                        $select.select2();
                        console.log("✅ Select2 reinicializado para especialidad_curso");
                    } catch (e) {
                        console.log("⚠️ Error inicializando Select2:", e);
                    }
                }
                
                console.log("✅ Especialidad actualizada con", especialidades.length, "opciones");
            });
        }
        
        function limpiarEspecialidades() {
            console.log("🧹 Limpiando especialidades...");
            
            $('select[name*="especialidad_curso"]').each(function() {
                if ($(this).attr('name').includes('__prefix__')) return;
                
                var $select = $(this);
                var valorActual = $select.val();
                
                // Solo limpiar si no estamos en modo edición (evita perder valor existente)
                if (!valorActual) {
                    // Destruir Select2 si existe
                    if ($select.hasClass('select2-hidden-accessible')) {
                        try {
                            $select.select2('destroy');
                        } catch (e) {
                            console.log("⚠️ Error destruyendo Select2:", e);
                        }
                    }
                    
                    // Limpiar opciones
                    $select.empty();
                    $select.append('<option value="">---------</option>');
                    $select.append('<option value="" disabled>Seleccione un curso lectivo primero</option>');
                    
                    // Reinicializar Select2
                    if (typeof $select.select2 === 'function') {
                        try {
                            $select.select2();
                        } catch (e) {
                            console.log("⚠️ Error inicializando Select2:", e);
                        }
                    }
                }
            });
        }
        
        // ──────────────── CONFIGURAR EVENTOS CURSO LECTIVO ────────────────
        function configurarEventosCursoLectivo() {
            console.log("🎯 Configurando eventos curso lectivo...");
            var $cursoLectivo = $('select[name*="curso_lectivo"]');
            
            if ($cursoLectivo.length === 0) {
                console.log("❌ Campo curso_lectivo no encontrado");
                return;
            }
            
            // Verificar si ya está configurado
            if ($cursoLectivo.data('eventos-configurados')) {
                console.log("ℹ️ Eventos ya configurados para curso_lectivo");
                return;
            }
            
            console.log("✅ Campo curso_lectivo encontrado:", $cursoLectivo.attr('name'));
            console.log("   - Tiene Select2:", $cursoLectivo.hasClass('select2-hidden-accessible'));
            
            // Configurar evento change
            $(document).off('change', 'select[name*="curso_lectivo"]');
            $(document).on('change', 'select[name*="curso_lectivo"]', function() {
                console.log('📚 Change event curso_lectivo:', this.value);
                actualizarEspecialidadesDisponibles();
            });
            
            // TAMBIÉN configurar evento para cambios en institución (superusuarios)
            $(document).off('change', 'select[name*="institucion"]');
            $(document).on('change', 'select[name*="institucion"]', function() {
                console.log('🏫 Change event institucion:', this.value);
                actualizarEspecialidadesDisponibles();
            });
            
            // Marcar como configurado
            $cursoLectivo.data('eventos-configurados', true);
            
            console.log("✅ Eventos curso lectivo configurados");
        }
        
        // ──────────────── INTERCEPTOR DE AUTOCOMPLETE ────────────────
        function configurarInterceptorAutocomplete() {
            console.log("🎯 Configurando interceptor de autocomplete...");
            
            // Interceptar eventos Select2 para curso lectivo
            $(document).on('select2:select', function(e) {
                var $target = $(e.target);
                
                // Solo procesar si es el campo curso_lectivo
                if ($target.attr('name') && $target.attr('name').includes('curso_lectivo')) {
                    var data = e.params.data;
                    if (data && data.text) {
                        console.log("📡 SELECT2:SELECT CURSO_LECTIVO detectado:", data.text);
                        
                        setTimeout(function() {
                            actualizarEspecialidadesDisponibles();
                        }, 200);
                    }
                }
            });
            
            // Configurar eventos para curso lectivo
            configurarEventosCursoLectivo();
            
            console.log("✅ Interceptor de autocomplete configurado");
        }
        
        // ──────────────── INICIALIZACIÓN ────────────────
        function inicializar() {
            console.log("🚀 Inicializando filtro de especialidades...");
            
            // Configurar interceptores
            configurarInterceptorAutocomplete();
            
            // SIEMPRE ejecutar la actualización al inicializar para evaluar estado actual
            console.log("🔍 Evaluando estado inicial...");
            actualizarEspecialidadesDisponibles();
            
            console.log("✅ Filtro de especialidades inicializado");
        }
        
        // ──────────────── MÚLTIPLES PUNTOS DE ENTRADA ────────────────
        // Inicializar cuando el DOM esté listo
        inicializar();
        
        // También inicializar cuando Django Admin termine de cargar
        $(document).on('DOMContentLoaded', inicializar);
        
        // Inicializar en cada cambio de página (para navegación AJAX)
        $(document).on('shown.bs.tab', inicializar);
        $(document).on('shown.bs.modal', inicializar);
        
        // Inicializar después de un tiempo (fallback)
        setTimeout(inicializar, 1000);
        setTimeout(inicializar, 2000);
        
        console.log("✅ Múltiples puntos de entrada configurados");
    });
})(window.django && window.django.jQuery ? window.django.jQuery : window.jQuery);

