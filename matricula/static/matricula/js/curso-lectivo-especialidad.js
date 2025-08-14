// CURSO LECTIVO → ESPECIALIDAD (COPIADO EXACTO DE DEPENDENT-DROPDOWNS.JS)
(function($) {
    if (!$) {
        console.error("curso-lectivo-especialidad.js: jQuery no encontrado");
        return;
    }
    
    $(function() {
        console.log("=== CURSO LECTIVO → ESPECIALIDAD ===");
        console.log("jQuery version:", $.fn.jquery);
        
        // ──────────────── CURSO LECTIVO → ESPECIALIDAD ────────────────
        function cargarEspecialidades(cursoLectivoId) {
            var $especialidad = $('#id_especialidad');
            console.log("cargarEspecialidades llamado con cursoLectivoId:", cursoLectivoId);
            
            if (!cursoLectivoId) {
                $especialidad.html('<option value="">---------</option>');
                
                // Limpiar Select2 especialidad
                if ($especialidad.hasClass('select2-hidden-accessible')) {
                    try {
                        if (typeof $especialidad.select2 === 'function') {
                            $especialidad.select2('destroy');
                        }
                    } catch (e) {
                        console.log("⚠️ Error destruyendo Select2 especialidad:", e);
                        $especialidad.removeClass('select2-hidden-accessible');
                        $especialidad.next('.select2-container').remove();
                    }
                }
                if (typeof $especialidad.select2 === 'function') {
                    try {
                        $especialidad.select2();
                    } catch (e) {
                        console.log("⚠️ Error inicializando Select2 especialidad:", e);
                    }
                }
                return;
            }
            
            console.log("Cargando especialidades para curso lectivo", cursoLectivoId);
            
            $.ajax({
                url: '/matricula/get-especialidades-disponibles/',
                method: 'POST',
                data: {
                    curso_lectivo_id: cursoLectivoId,
                    csrfmiddlewaretoken: $('[name=csrfmiddlewaretoken]').val()
                },
                success: function(response) {
                    if (response.success) {
                        console.log("✅ Especialidades obtenidas:", response.especialidades);
                        console.log("🔍 DEBUG INFO:", response.debug);
                        
                        var html = '<option value="">---------</option>';
                        response.especialidades.forEach(function(esp) {
                            html += '<option value="' + esp.id + '">' + esp.nombre + '</option>';
                        });
                        
                        $especialidad.html(html);
                        
                        // Reinicializar Select2
                        if ($especialidad.hasClass('select2-hidden-accessible')) {
                            try {
                                if (typeof $especialidad.select2 === 'function') {
                                    $especialidad.select2('destroy');
                                }
                            } catch (e) {
                                console.log("⚠️ Error destruyendo Select2 especialidad:", e);
                                $especialidad.removeClass('select2-hidden-accessible');
                                $especialidad.next('.select2-container').remove();
                            }
                        }
                        if (typeof $especialidad.select2 === 'function') {
                            try {
                                $especialidad.select2();
                            } catch (e) {
                                console.log("⚠️ Error inicializando Select2 especialidad:", e);
                            }
                        }
                        
                        console.log("Especialidades cargadas:", response.especialidades.length);
                        
                        if (response.debug && response.debug.configuraciones_activas === 0) {
                            console.warn("⚠️ NO HAY CONFIGURACIONES ACTIVAS para esta institución y curso lectivo");
                            console.log("   - Institución:", response.debug.institucion_nombre);
                            console.log("   - Curso lectivo ID:", response.debug.curso_lectivo_id);
                            console.log("   - Necesitas configurar especialidades en el admin");
                        }
                    } else {
                        console.error("❌ Error al obtener especialidades:", response.error);
                    }
                },
                error: function(xhr, status, error) {
                    console.error("❌ Error AJAX:", error);
                }
            });
        }

        // ──────────────── Inicialización de eventos ────────────────
        function inicializarEventos() {
            console.log("Inicializando eventos para curso lectivo...");
            var $cursoLectivo = $('#id_curso_lectivo');

            if ($cursoLectivo.length === 0) {
                console.log("❌ Campo curso_lectivo no encontrado");
                return;
            }

            // --- Curso Lectivo --- (EXACTO COMO PROVINCIA EN DEPENDENT-DROPDOWNS.JS)
            if ($cursoLectivo.hasClass('select2-hidden-accessible') && typeof $cursoLectivo.select2 === 'function') {
                $cursoLectivo.select2('destroy');
                $cursoLectivo.removeClass('select2-hidden-accessible');
                $cursoLectivo.attr('aria-hidden', 'false');
            } else if ($cursoLectivo.hasClass('select2-hidden-accessible')) {
                $cursoLectivo.removeClass('select2-hidden-accessible');
                $cursoLectivo.attr('aria-hidden', 'false');
                $cursoLectivo.next('.select2-container').remove();
            }
            
            $(document).off('change', '#id_curso_lectivo');
            $(document).on('change', '#id_curso_lectivo', function() {
                console.log('📚 Change event curso_lectivo:', this.value);
                cargarEspecialidades(this.value);
            });
            
            console.log("✅ Eventos configurados para curso_lectivo");
        }

        // MÚLTIPLES TIMEOUTS COMO EN DEPENDENT-DROPDOWNS.JS
        setTimeout(function() { inicializarEventos(); }, 1000);
        setTimeout(function() { inicializarEventos(); }, 2000);
        
        $(document).on('select2:ready', function() { 
            console.log("📡 Select2 ready - inicializando curso lectivo");
            inicializarEventos(); 
        });
        
        console.log("🎪 CURSO LECTIVO → ESPECIALIDAD CONFIGURADO");
    });
    
})(window.django && window.django.jQuery ? window.django.jQuery : window.jQuery);

