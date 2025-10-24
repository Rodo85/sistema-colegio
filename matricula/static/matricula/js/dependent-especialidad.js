// ESPECIALIDAD DEPENDIENTE - CAPTURA DIRECTA DE AUTOCOMPLETE (VERSIÓN QUE FUNCIONA)
(function($) {
    if (!$) {
        console.error("dependent-especialidad.js: jQuery no encontrado");
        return;
    }
    
    $(function() {
        // Evitar interferir con la lista de admin (filtros de Jazzmin)
        try {
            var bodyClass = document && document.body ? document.body.className : '';
            if (bodyClass && bodyClass.indexOf('change-list') !== -1) {
                console.log('dependent-especialidad: detectada changelist; no aplicar lógica de ocultar/mostrar');
                return; // no correr en la lista para no ocultar el filtro "Especialidad"
            }
        } catch (e) {}
        console.log("=== ESPECIALIDAD DEPENDIENTE (CAPTURA AUTOCOMPLETE) ===");
        console.log("jQuery version:", $.fn.jquery);
        
        var especialidadOculta = false;
        var inicializando = false; // evita limpiar valores pre-cargados durante la carga inicial
        var especialidadInicial = null; // guardar valor inicial para modo edición
        var nivelInicialCargado = false; // bandera para saber si ya cargamos el nivel inicial
        
        // ══════════ CAPTURA TEMPRANA DE ESPECIALIDAD (INMEDIATA) ══════════
        // Capturar el valor de especialidad ANTES de cualquier manipulación
        $('select[name*="especialidad"]').each(function() {
            if (!$(this).attr('name').includes('__prefix__')) {
                var valorActual = $(this).val();
                if (valorActual) {
                    especialidadInicial = valorActual;
                    console.log("🔒 CAPTURA TEMPRANA - Especialidad inicial:", especialidadInicial);
                }
            }
        });
        
        // ──────────────── CONTROL DE ESPECIALIDAD ────────────────
        function mostrarEspecialidad() {
            // Mostrar SIEMPRE el contenedor completo del campo y su select2
            console.log("🟢 MOSTRANDO especialidad");
            $('select[name*="especialidad"]').each(function() {
                if ($(this).attr('name').includes('__prefix__')) return;
                var $row = $(this).closest('[class*="field-especialidad"], .form-row, .form-group');
                var $wrapper = $(this).closest('.related-widget-wrapper');
                $row.show();
                $wrapper.show();
                $row.find('.select2-container').show();
                
                // Si hay especialidadInicial y el campo está vacío, restaurar
                if (especialidadInicial && !$(this).val() && !nivelInicialCargado) {
                    console.log("🔄 Restaurando especialidad inicial:", especialidadInicial);
                    $(this).val(especialidadInicial).trigger('change');
                }
            });
            especialidadOculta = false;
        }
        
        function ocultarEspecialidad() {
            console.log("🔴 OCULTANDO especialidad");
            $('select[name*="especialidad"]').each(function() {
                if ($(this).attr('name').includes('__prefix__')) return;
                var $row = $(this).closest('[class*="field-especialidad"], .form-row, .form-group');
                var $wrapper = $(this).closest('.related-widget-wrapper');
                // Limpiar selección SOLO si no estamos en inicialización Y si no hay valor inicial guardado
                if (!inicializando && (!especialidadInicial || nivelInicialCargado)) {
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
            
            var textoLower = texto.toLowerCase();
            var esEspecialidad = textoLower.includes('décimo') || 
                                textoLower.includes('undécimo') || 
                                textoLower.includes('duodécimo') ||
                                textoLower.includes('(10)') ||
                                textoLower.includes('(11)') ||
                                textoLower.includes('(12)') ||
                                textoLower === '10' ||
                                textoLower === '11' ||
                                textoLower === '12';
            
            console.log("🧪 Verificando texto:", texto, "-> ¿Es especialidad?", esEspecialidad);
            return esEspecialidad;
        }
        
        // ──────────────── ACTUALIZAR ESPECIALIDADES DISPONIBLES ────────────────
        function actualizarEspecialidadesDisponibles() {
            console.log("🔄 Actualizando especialidades disponibles...");
            
            // Obtener el curso lectivo seleccionado (curso_lectivo NO es autocomplete)
            var $cursoLectivo = $('select[name*="curso_lectivo"]');
            var cursoLectivoId = $cursoLectivo.val();
            
            // Obtener el nivel seleccionado
            var nivelId = null;
            var nivelTexto = '';
            
            // Buscar nivel en select
            $('select[name*="nivel"]').each(function() {
                if (!$(this).attr('name').includes('__prefix__')) {
                    nivelId = $(this).val();
                    nivelTexto = $(this).find('option:selected').text() || '';
                }
            });
            
            // Si no encontramos en select, buscar en select2 rendered
            if (!nivelId) {
                $('.select2-container').each(function() {
                    var selectId = $(this).attr('id');
                    if (selectId && selectId.includes('nivel')) {
                        var originalSelectId = selectId.replace('select2-', '').replace('-container', '');
                        var $originalSelect = $('#' + originalSelectId);
                        if ($originalSelect.length) {
                            nivelId = $originalSelect.val();
                            nivelTexto = $(this).find('.select2-selection__rendered').text() || '';
                        }
                    }
                });
            }
            
            console.log("📊 Nivel seleccionado:", nivelId, "- Texto:", nivelTexto);
            
            if (!cursoLectivoId) {
                console.log("⚠️ No hay curso lectivo seleccionado");
                return;
            }
            
            if (!nivelId) {
                console.log("⚠️ No hay nivel seleccionado - no actualizar especialidades");
                return;
            }
            
            // Verificar si el nivel requiere especialidad
            if (!esNivelEspecialidad(nivelTexto)) {
                console.log("⚠️ Nivel no requiere especialidad - ocultar campo");
                ocultarEspecialidad();
                return;
            }
            
            console.log("📚 Curso lectivo:", cursoLectivoId, "- Nivel:", nivelId);
            
            // NO USAR AJAX - Dejar que el autocomplete de DAL maneje el filtrado
            // El autocomplete ya filtra correctamente por nivel en el backend
            console.log("✅ Autocomplete DAL manejará el filtrado por nivel automáticamente");
            mostrarEspecialidad();
            
            // FORZAR recarga del autocomplete para que use los parámetros forward actualizados
            // PERO: NO limpiar si estamos en carga inicial y hay valor inicial
            $('select[name*="especialidad"]').each(function() {
                if ($(this).attr('name').includes('__prefix__')) return;
                
                var $select = $(this);
                
                // Destruir y reinicializar Select2 para forzar nueva carga
                if ($select.hasClass('select2-hidden-accessible')) {
                    try {
                        // Solo limpiar si ya pasó la carga inicial (usuario cambió el nivel manualmente)
                        // Y NO limpiar si hay especialidadInicial guardada y aún no se completó la carga
                        if (nivelInicialCargado) {
                            // Limpiar valor y forzar recarga
                            $select.val(null).trigger('change');
                            console.log("🔄 Especialidad limpiada para recarga con nivel:", nivelId);
                        } else if (especialidadInicial && $select.val() == especialidadInicial) {
                            console.log("⏭️ Carga inicial con especialidad - MANTENER valor:", especialidadInicial);
                            // NO hacer nada - mantener el valor existente
                        } else if (!especialidadInicial) {
                            // Es creación nueva, permitir limpiar
                            $select.val(null).trigger('change');
                            console.log("🔄 Especialidad limpiada (nueva matrícula)");
                        }
                    } catch (e) {
                        console.log("⚠️ Error limpiando especialidad:", e);
                    }
                }
            });
        }
        
        function actualizarOpcionesEspecialidadAutocomplete(especialidades) {
            console.log("🔄 Actualizando opciones de especialidad (AUTOCOMPLETE)...");
            
            // especialidad ES un autocomplete_field, necesitamos actualizar las opciones disponibles
            // Esto es más complejo porque Select2 maneja las opciones dinámicamente
            
            $('select[name*="especialidad"]').each(function() {
                if ($(this).attr('name').includes('__prefix__')) return;
                
                var $select = $(this);
                var valorActual = $select.val();
                
                console.log("🎯 Procesando select especialidad:", $select.attr('name'));
                
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
                        .text(esp.nombre);
                    
                    // Marcar como seleccionada si era la opción actual
                    if (esp.id == valorActual) {
                        $option.prop('selected', true);
                    }
                    
                    $select.append($option);
                });
                
                // Reinicializar Select2 para autocomplete
                if (typeof $select.select2 === 'function') {
                    try {
                        $select.select2();
                    } catch (e) {
                        console.log("⚠️ Error inicializando Select2:", e);
                    }
                }
                
                console.log("✅ Especialidad actualizada con", especialidades.length, "opciones");
            });
        }
        
        // ──────────────── CONFIGURAR EVENTOS CURSO LECTIVO (COPIADO DE DEPENDENT-DROPDOWNS.JS) ────────────────
        function configurarEventosCursoLectivo() {
            console.log("🎯 Configurando eventos curso lectivo (copiado de dependent-dropdowns.js)...");
            var $cursoLectivo = $('#id_curso_lectivo');
            
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
            
            // LÓGICA EXACTA DE DEPENDENT-DROPDOWNS.JS QUE FUNCIONA
            if ($cursoLectivo.hasClass('select2-hidden-accessible') && typeof $cursoLectivo.select2 === 'function') {
                console.log("🔧 Destruyendo Select2 del curso lectivo (método 1)...");
                try {
                    $cursoLectivo.select2('destroy');
                } catch (e) {
                    console.log("⚠️ Error destruyendo Select2:", e);
                }
                $cursoLectivo.removeClass('select2-hidden-accessible');
                $cursoLectivo.attr('aria-hidden', 'false');
            } else if ($cursoLectivo.hasClass('select2-hidden-accessible')) {
                console.log("🔧 Limpiando Select2 manualmente (método 2)...");
                $cursoLectivo.removeClass('select2-hidden-accessible');
                $cursoLectivo.attr('aria-hidden', 'false');
                $cursoLectivo.next('.select2-container').remove();
            }
            
            // Configurar evento change exactamente como provincia/cantón
            $(document).off('change', '#id_curso_lectivo');
            $(document).on('change', '#id_curso_lectivo', function() {
                console.log('📚 Change event curso_lectivo:', this.value);
                actualizarEspecialidadesDisponibles();
            });
            
            // Marcar como configurado
            $cursoLectivo.data('eventos-configurados', true);
            
            console.log("✅ Eventos curso lectivo configurados");
        }
        
        // ──────────────── INTERCEPTOR DE AUTOCOMPLETE ────────────────
        function configurarInterceptorAutocomplete() {
            console.log("🎯 Configurando interceptor de autocomplete...");
            
            // Interceptar clicks SOLO en opciones de nivel
            $(document).on('click', '.select2-results__option', function(e) {
                var textoOpcion = $(this).text() || '';
                
                // Verificar si el dropdown que está abierto es específicamente del campo nivel
                var $activeDropdown = $(this).closest('.select2-dropdown');
                var $activeSelect = null;
                
                // Buscar el select que está activo
                $('.select2-container--open').each(function() {
                    var selectId = $(this).attr('id');
                    if (selectId) {
                        var originalSelectId = selectId.replace('select2-', '').replace('-container', '');
                        var $originalSelect = $('#' + originalSelectId);
                        if ($originalSelect.attr('name') && $originalSelect.attr('name').includes('nivel')) {
                            $activeSelect = $originalSelect;
                        }
                    }
                });
                
                // Solo procesar si es realmente una selección de nivel
                if ($activeSelect && $activeSelect.attr('name').includes('nivel')) {
                    console.log("🖱️ CLICK EN NIVEL:", textoOpcion);
                    
                    // Solo limpiar si ya pasó la carga inicial (evita limpiar en edición)
                    if (nivelInicialCargado) {
                        // LIMPIAR especialidad cuando cambia el nivel para forzar recarga
                        $('select[name*="especialidad"]').each(function() {
                            if (!$(this).attr('name').includes('__prefix__')) {
                                $(this).val(null).trigger('change');
                                console.log("🧹 Especialidad limpiada por click en nivel");
                            }
                        });
                    } else {
                        console.log("⏭️ Carga inicial - no limpiar especialidad");
                    }
                    
                    setTimeout(function() {
                        if (esNivelEspecialidad(textoOpcion)) {
                            mostrarEspecialidad();
                        } else {
                            ocultarEspecialidad();
                        }
                    }, 200);
                }
            });
            
            // Interceptar eventos Select2 específicos SOLO para nivel
            $(document).on('select2:select', function(e) {
                var $target = $(e.target);
                
                // Solo procesar si es el campo nivel
                if ($target.attr('name') && $target.attr('name').includes('nivel')) {
                    var data = e.params.data;
                    if (data && data.text) {
                        console.log("📡 SELECT2:SELECT NIVEL detectado:", data.text);
                        
                        // Solo limpiar si ya pasó la carga inicial (evita limpiar en edición)
                        if (nivelInicialCargado) {
                            // LIMPIAR especialidad cuando cambia el nivel para forzar recarga
                            $('select[name*="especialidad"]').each(function() {
                                if (!$(this).attr('name').includes('__prefix__')) {
                                    $(this).val(null).trigger('change');
                                    console.log("🧹 Especialidad limpiada por cambio de nivel");
                                }
                            });
                        } else {
                            console.log("⏭️ Carga inicial - no limpiar especialidad");
                        }
                        
                        setTimeout(function() {
                            if (esNivelEspecialidad(data.text)) {
                                mostrarEspecialidad();
                            } else {
                                ocultarEspecialidad();
                            }
                        }, 200);
                    }
                }
                
                // curso_lectivo NO es autocomplete, se maneja con eventos change normales
            });
            
            // Interceptar eventos en campos de entrada del autocomplete (nivel)
            $('input[name*="nivel"]').off('input change blur.dependEspecialidad').on('input change blur.dependEspecialidad', function() {
                var valor = $(this).val();
                console.log("⌨️ INPUT NIVEL:", valor);
                
                setTimeout(function() {
                    if (esNivelEspecialidad(valor)) {
                        mostrarEspecialidad();
                    } else {
                        ocultarEspecialidad();
                    }
                }, 200);
            });
            
            // Configurar eventos para curso lectivo (estrategia probada)
            configurarEventosCursoLectivo();
            
            // Vigilar cambios en el DOM para nuevos elementos
            var observer = new MutationObserver(function(mutations) {
                mutations.forEach(function(mutation) {
                    if (mutation.addedNodes.length > 0) {
                        mutation.addedNodes.forEach(function(node) {
                            if (node.nodeType === 1) {
                                // Si se añaden nuevos elementos autocomplete
                                var $newInputs = $(node).find('input[name*="nivel"]');
                                if ($newInputs.length > 0) {
                                    console.log("👁️ Nuevos campos de nivel detectados");
                                    $newInputs.off('input change blur.dependEspecialidad').on('input change blur.dependEspecialidad', function() {
                                        var valor = $(this).val();
                                        console.log("⌨️ NUEVO INPUT NIVEL:", valor);
                                        
                                        setTimeout(function() {
                                            if (esNivelEspecialidad(valor)) {
                                                mostrarEspecialidad();
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
            console.log("🚀 Inicializando especialidad dependiente...");
            inicializando = true;
            
            // CAPTURAR VALOR INICIAL DE ESPECIALIDAD (para modo edición)
            // IMPORTANTE: Capturar solo UNA VEZ para evitar sobreescribir con null
            if (especialidadInicial === null) {
                $('select[name*="especialidad"]').each(function() {
                    if (!$(this).attr('name').includes('__prefix__')) {
                        var valorActual = $(this).val();
                        if (valorActual) {
                            especialidadInicial = valorActual;
                            console.log("💾 Especialidad inicial capturada:", especialidadInicial);
                        }
                    }
                });
            } else {
                console.log("💾 Especialidad inicial ya existía:", especialidadInicial);
            }
            
            // Ocultar por defecto
            ocultarEspecialidad();
            
            // Configurar eventos curso lectivo (estrategia probada)
            configurarEventosCursoLectivo();
            
            // Configurar interceptores
            configurarInterceptorAutocomplete();
            
            // Verificar estado inicial cuando el widget es input (algunas variantes de select2)
            $('input[name*="nivel"]').each(function() {
                if ($(this).attr('name') && !$(this).attr('name').includes('__prefix__')) {
                    var valor = $(this).val();
                    if (valor && esNivelEspecialidad(valor)) {
                        console.log("🏁 Inicial (input) nivel:", valor);
                        mostrarEspecialidad();
                    }
                }
            });

            // Verificar estado inicial cuando el widget es select (admin autocomplete clásico)
            $('select[name*="nivel"]').each(function() {
                if ($(this).attr('name') && !$(this).attr('name').includes('__prefix__')) {
                    var texto = $(this).find('option:selected').text() || '';
                    // Si no hay option (select2), intentar leer del contenedor select2
                    if (!texto) {
                        var $cont = $(this).siblings('.select2-container');
                        var selectedText = $cont.find('.select2-selection__rendered').attr('title') || $cont.find('.select2-selection__rendered').text();
                        texto = selectedText || '';
                    }
                    if (texto && esNivelEspecialidad(texto)) {
                        console.log("🏁 Inicial (select) nivel:", texto);
                        mostrarEspecialidad();
                    } else {
                        ocultarEspecialidad();
                    }
                }
            });
            
            // Actualizar especialidades disponibles al inicializar SOLO si NO hay especialidad inicial
            if (!especialidadInicial) {
                console.log("🆕 Nueva matrícula - actualizar especialidades disponibles");
                setTimeout(actualizarEspecialidadesDisponibles, 500);
            } else {
                console.log("✏️ Edición de matrícula - NO actualizar (mantener especialidad)");
            }
            
            // Marcar que la carga inicial está completa después de un tiempo suficiente
            setTimeout(function() {
                nivelInicialCargado = true;
                console.log("✅ Carga inicial completada - cambios futuros limpiarán especialidad");
            }, 5000); // Aumentado a 5 segundos para dar tiempo a todo el DOM y Select2
            
            console.log("✅ Configuración completada");
            inicializando = false;
        }
        
        // Múltiples puntos de entrada para asegurar inicialización (como dependent-dropdowns.js)
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
        
        console.log("🎪 INTERCEPTOR DE AUTOCOMPLETE CONFIGURADO");
    });
    
})(typeof django !== 'undefined' && django.jQuery ? django.jQuery : (typeof $ !== 'undefined' ? $ : null));
