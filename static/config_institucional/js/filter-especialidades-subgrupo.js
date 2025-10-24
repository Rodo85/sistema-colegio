// FILTRO DE ESPECIALIDADES PARA SUBGRUPO CURSO LECTIVO
// Adaptado de dependent-especialidad.js (Matrículas Académicas)
(function($) {
    if (!$) {
        console.error("filter-especialidades-subgrupo.js: jQuery no encontrado");
        return;
    }
    
    $(function() {
        // Evitar interferir con la lista de admin (filtros de Jazzmin)
        try {
            var bodyClass = document && document.body ? document.body.className : '';
            if (bodyClass && bodyClass.indexOf('change-list') !== -1) {
                console.log('filter-especialidades-subgrupo: detectada changelist; no aplicar lógica de ocultar/mostrar');
                return;
            }
        } catch (e) {}
        
        console.log("=== ESPECIALIDAD DEPENDIENTE - SUBGRUPO CURSO LECTIVO ===");
        console.log("jQuery version:", $.fn.jquery);
        
        var especialidadOculta = false;
        var inicializando = false;
        
        // ──────────────── CONTROL DE ESPECIALIDAD ────────────────
        function mostrarEspecialidad() {
            console.log("🟢 MOSTRANDO especialidad");
            $('select[name*="especialidad_curso"]').each(function() {
                if ($(this).attr('name').includes('__prefix__')) return;
                var $row = $(this).closest('[class*="field-especialidad"], .form-row, .form-group');
                var $wrapper = $(this).closest('.related-widget-wrapper');
                $row.show();
                $wrapper.show();
                $row.find('.select2-container').show();
            });
            especialidadOculta = false;
        }
        
        function ocultarEspecialidad() {
            console.log("🔴 OCULTANDO especialidad");
            $('select[name*="especialidad_curso"]').each(function() {
                if ($(this).attr('name').includes('__prefix__')) return;
                var $row = $(this).closest('[class*="field-especialidad"], .form-row, .form-group');
                var $wrapper = $(this).closest('.related-widget-wrapper');
                // Limpiar selección SOLO si no estamos en inicialización
                if (!inicializando) {
                    try { $(this).val(null).trigger('change'); } catch(e) { $(this).val(''); }
                }
                $row.hide();
                $wrapper.hide();
                $row.find('.select2-container').hide();
            });
            especialidadOculta = true;
        }
        
        function esNivelEspecialidad(texto) {
            if (!texto) return false;
            
            // El subgrupo viene en formato "10-1A", "11-2B", "7-1A", etc.
            // Extraer el número antes del guion
            var match = texto.match(/^(\d+)-/);
            if (match) {
                var nivel = parseInt(match[1], 10);
                var esEspecialidad = (nivel === 10 || nivel === 11 || nivel === 12);
                console.log("🧪 Verificando subgrupo:", texto, "-> Nivel:", nivel, "-> ¿Es especialidad?", esEspecialidad);
                return esEspecialidad;
            }
            
            console.log("⚠️ No se pudo extraer nivel de:", texto);
            return false;
        }
        
        // ──────────────── ACTUALIZAR ESPECIALIDADES DISPONIBLES ────────────────
        function actualizarEspecialidadesDisponibles() {
            console.log("🔄 Actualizando especialidades disponibles...");
            
            // Obtener el curso lectivo seleccionado
            var $cursoLectivo = $('select[name*="curso_lectivo"]').not('[name*="__prefix__"]');
            var cursoLectivoId = $cursoLectivo.val();
            
            // Obtener la institución
            var institucionId = $('input[name="institucion"]').val() || 
                              $('select[name="institucion"]').val() ||
                              $('#id_institucion').val() ||
                              $('input[name*="institucion"]').not('[name*="__prefix__"]').val() ||
                              $('select[name*="institucion"]').not('[name*="__prefix__"]').val();
            
            console.log("📚 Curso lectivo:", cursoLectivoId);
            console.log("🏫 Institución:", institucionId);
            
            if (!cursoLectivoId || !institucionId) {
                console.log("❌ Faltan datos requeridos");
                return;
            }
            
            console.log("✅ Datos válidos - haciendo petición AJAX");
            
            var ajaxData = {
                'forward': JSON.stringify({
                    'curso_lectivo_id': cursoLectivoId,
                    'institucion_id': institucionId
                })
            };
            
            // Hacer petición AJAX para obtener especialidades disponibles
            $.ajax({
                url: '/config/especialidad-curso-lectivo-autocomplete/',
                method: 'GET',
                data: ajaxData,
                success: function(response) {
                    console.log("✅ Respuesta recibida:", response);
                    
                    if (response.results && response.results.length > 0) {
                        console.log("✅ Especialidades obtenidas:", response.results.length);
                        actualizarOpcionesEspecialidadAutocomplete(response.results);
                    } else {
                        console.log("⚠️ No hay especialidades disponibles");
                    }
                },
                error: function(xhr, status, error) {
                    console.error("❌ Error AJAX:", status, error);
                }
            });
        }
        
        function actualizarOpcionesEspecialidadAutocomplete(especialidades) {
            console.log("🔄 Actualizando opciones de especialidad (AUTOCOMPLETE)...");
            
            $('select[name*="especialidad_curso"]').each(function() {
                if ($(this).attr('name').includes('__prefix__')) return;
                
                var $select = $(this);
                var valorActual = $select.val();
                
                console.log("🎯 Procesando select especialidad_curso:", $select.attr('name'));
                
                // Destruir Select2 si existe
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
                
                // Reinicializar Select2
                if (typeof $select.select2 === 'function') {
                    try {
                        $select.select2();
                        console.log("✅ Select2 reinicializado");
                    } catch (e) {
                        console.log("⚠️ Error inicializando Select2:", e);
                    }
                }
                
                console.log("✅ Especialidad actualizada con", especialidades.length, "opciones");
            });
        }
        
        // ──────────────── CONFIGURAR EVENTOS CURSO LECTIVO ────────────────
        function configurarEventosCursoLectivo() {
            console.log("🎯 Configurando eventos curso lectivo...");
            var $cursoLectivo = $('select[name*="curso_lectivo"]').not('[name*="__prefix__"]').first();
            
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
            
            // Configurar evento change
            $(document).off('change', 'select[name*="curso_lectivo"]');
            $(document).on('change', 'select[name*="curso_lectivo"]', function() {
                if ($(this).attr('name').includes('__prefix__')) return;
                console.log('📚 Change event curso_lectivo:', this.value);
                actualizarEspecialidadesDisponibles();
            });
            
            // Marcar como configurado
            $cursoLectivo.data('eventos-configurados', true);
            
            console.log("✅ Eventos curso lectivo configurados");
        }
        
        // ──────────────── INTERCEPTOR DE AUTOCOMPLETE PARA SUBGRUPO ────────────────
        function configurarInterceptorAutocomplete() {
            console.log("🎯 Configurando interceptor de autocomplete...");
            
            // Interceptar clicks en opciones de subgrupo
            $(document).on('click', '.select2-results__option', function(e) {
                var textoOpcion = $(this).text() || '';
                
                // Verificar si el dropdown que está abierto es del campo subgrupo
                var $activeDropdown = $(this).closest('.select2-dropdown');
                var $activeSelect = null;
                
                // Buscar el select que está activo
                $('.select2-container--open').each(function() {
                    var selectId = $(this).attr('id');
                    if (selectId) {
                        var originalSelectId = selectId.replace('select2-', '').replace('-container', '');
                        var $originalSelect = $('#' + originalSelectId);
                        if ($originalSelect.attr('name') && $originalSelect.attr('name').includes('subgrupo')) {
                            $activeSelect = $originalSelect;
                        }
                    }
                });
                
                // Solo procesar si es realmente una selección de subgrupo
                if ($activeSelect && $activeSelect.attr('name').includes('subgrupo')) {
                    console.log("🖱️ CLICK EN SUBGRUPO:", textoOpcion);
                    
                    setTimeout(function() {
                        if (esNivelEspecialidad(textoOpcion)) {
                            mostrarEspecialidad();
                            actualizarEspecialidadesDisponibles();
                        } else {
                            ocultarEspecialidad();
                        }
                    }, 200);
                }
            });
            
            // Interceptar eventos Select2 específicos para subgrupo
            $(document).on('select2:select', function(e) {
                var $target = $(e.target);
                
                // Solo procesar si es el campo subgrupo
                if ($target.attr('name') && $target.attr('name').includes('subgrupo')) {
                    var data = e.params.data;
                    if (data && data.text) {
                        console.log("📡 SELECT2:SELECT SUBGRUPO detectado:", data.text);
                        
                        setTimeout(function() {
                            if (esNivelEspecialidad(data.text)) {
                                mostrarEspecialidad();
                                actualizarEspecialidadesDisponibles();
                            } else {
                                ocultarEspecialidad();
                            }
                        }, 200);
                    }
                }
            });
            
            // Interceptar eventos en campos de entrada del autocomplete (subgrupo)
            $('input[name*="subgrupo"]').off('input change blur.dependEspecialidad').on('input change blur.dependEspecialidad', function() {
                var valor = $(this).val();
                console.log("⌨️ INPUT SUBGRUPO:", valor);
                
                setTimeout(function() {
                    if (esNivelEspecialidad(valor)) {
                        mostrarEspecialidad();
                        actualizarEspecialidadesDisponibles();
                    } else {
                        ocultarEspecialidad();
                    }
                }, 200);
            });
            
            // Configurar eventos para curso lectivo
            configurarEventosCursoLectivo();
            
            // Vigilar cambios en el DOM para nuevos elementos
            var observer = new MutationObserver(function(mutations) {
                mutations.forEach(function(mutation) {
                    if (mutation.addedNodes.length > 0) {
                        mutation.addedNodes.forEach(function(node) {
                            if (node.nodeType === 1) {
                                // Si se añaden nuevos elementos autocomplete de subgrupo
                                var $newInputs = $(node).find('input[name*="subgrupo"]');
                                if ($newInputs.length > 0) {
                                    console.log("👁️ Nuevos campos de subgrupo detectados");
                                    $newInputs.off('input change blur.dependEspecialidad').on('input change blur.dependEspecialidad', function() {
                                        var valor = $(this).val();
                                        console.log("⌨️ NUEVO INPUT SUBGRUPO:", valor);
                                        
                                        setTimeout(function() {
                                            if (esNivelEspecialidad(valor)) {
                                                mostrarEspecialidad();
                                                actualizarEspecialidadesDisponibles();
                                            } else {
                                                ocultarEspecialidad();
                                            }
                                        }, 200);
                                    });
                                }
                                
                                // Si se añaden nuevos campos de curso lectivo, reconfigurar eventos
                                var $newCursoLectivo = $(node).find('select[name*="curso_lectivo"]');
                                if ($newCursoLectivo.length > 0) {
                                    console.log("👁️ Nuevos campos de curso lectivo detectados - reconfigurando...");
                                    setTimeout(configurarEventosCursoLectivo, 100);
                                }
                            }
                        });
                    }
                });
            });
            
            observer.observe(document.body, { childList: true, subtree: true });
            console.log("👁️ Observer configurado para nuevos elementos");
        }
        
        // ──────────────── INICIALIZACIÓN ────────────────
        function inicializar() {
            console.log("🚀 Inicializando especialidad dependiente - SubgrupoCursoLectivo...");
            inicializando = true;
            
            // Ocultar por defecto
            ocultarEspecialidad();
            
            // Configurar eventos curso lectivo
            configurarEventosCursoLectivo();
            
            // Configurar interceptores
            configurarInterceptorAutocomplete();
            
            // Verificar estado inicial cuando el widget es input (select2)
            $('input[name*="subgrupo"]').each(function() {
                if ($(this).attr('name') && !$(this).attr('name').includes('__prefix__')) {
                    var valor = $(this).val();
                    if (valor && esNivelEspecialidad(valor)) {
                        console.log("🏁 Inicial (input) subgrupo:", valor);
                        mostrarEspecialidad();
                        actualizarEspecialidadesDisponibles();
                    }
                }
            });

            // Verificar estado inicial cuando el widget es select (autocomplete clásico)
            $('select[name*="subgrupo"]').each(function() {
                if ($(this).attr('name') && !$(this).attr('name').includes('__prefix__')) {
                    var texto = $(this).find('option:selected').text() || '';
                    // Si no hay option (select2), intentar leer del contenedor select2
                    if (!texto) {
                        var $cont = $(this).siblings('.select2-container');
                        var selectedText = $cont.find('.select2-selection__rendered').attr('title') || $cont.find('.select2-selection__rendered').text();
                        texto = selectedText || '';
                    }
                    if (texto && esNivelEspecialidad(texto)) {
                        console.log("🏁 Inicial (select) subgrupo:", texto);
                        mostrarEspecialidad();
                        actualizarEspecialidadesDisponibles();
                    } else {
                        ocultarEspecialidad();
                    }
                }
            });
            
            console.log("✅ Configuración completada");
            inicializando = false;
        }
        
        // Múltiples puntos de entrada para asegurar inicialización (como en Matrículas)
        setTimeout(inicializar, 500);
        setTimeout(inicializar, 1500);
        setTimeout(inicializar, 3000);
        
        // También configurar eventos curso lectivo múltiples veces
        setTimeout(function() { configurarEventosCursoLectivo(); }, 1000);
        setTimeout(function() { configurarEventosCursoLectivo(); }, 2000);
        
        $(document).on('select2:ready', function() {
            console.log("📡 Select2 ready - reinicializando");
            setTimeout(inicializar, 100);
        });
        
        // También cuando el DOM esté completamente listo
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', inicializar);
        } else {
            inicializar();
        }
        
        console.log("🎪 INTERCEPTOR DE AUTOCOMPLETE CONFIGURADO - SubgrupoCursoLectivo");
    });
    
})(typeof django !== 'undefined' && django.jQuery ? django.jQuery : (typeof $ !== 'undefined' ? $ : null));
