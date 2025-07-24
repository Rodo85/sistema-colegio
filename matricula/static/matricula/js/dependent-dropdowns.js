(function($) {
    if (!$) {
        console.error("dependent-dropdowns.js: jQuery no encontrado");
        return;
    }
    
    $(function() {
        console.log("=== INICIALIZANDO DEPENDENT DROPDOWNS ===");
        console.log("jQuery version:", $.fn.jquery);
        console.log("Select2 disponible:", typeof $.fn.select2 !== 'undefined');
        
        // Verificar elementos al inicio
        var $provincia = $('#id_provincia');
        var $canton = $('#id_canton');
        var $distrito = $('#id_distrito');
        
        console.log("Elementos encontrados:");
        console.log("- Provincia:", $provincia.length > 0 ? "SÍ" : "NO", "Valor:", $provincia.val());
        console.log("- Cantón:", $canton.length > 0 ? "SÍ" : "NO", "Valor:", $canton.val());
        console.log("- Distrito:", $distrito.length > 0 ? "SÍ" : "NO", "Valor:", $distrito.val());
        
        // ──────────────── PROVINCIA → CANTÓN ────────────────
        function cargarCantones(provinciaId) {
            var $canton = $('#id_canton');
            var $distrito = $('#id_distrito');
            console.log("cargarCantones llamado con provinciaId:", provinciaId);
            if (!provinciaId) {
                            $canton.html('<option value="">----</option>');
            $distrito.html('<option value="">----</option>');
            
            // Limpiar Select2 cantón
            if ($canton.hasClass('select2-hidden-accessible')) {
                try {
                    if (typeof $canton.select2 === 'function') {
                        $canton.select2('destroy');
                    }
                } catch (e) {
                    console.log("⚠️ Error destruyendo Select2 cantón en cargarCantones (limpiar):", e);
                    $canton.removeClass('select2-hidden-accessible');
                    $canton.next('.select2-container').remove();
                }
            }
            if (typeof $canton.select2 === 'function') {
                try {
                    $canton.select2();
                } catch (e) {
                    console.log("⚠️ Error inicializando Select2 cantón en cargarCantones (limpiar):", e);
                }
            }
            
            // Limpiar Select2 distrito
            if ($distrito.hasClass('select2-hidden-accessible')) {
                try {
                    if (typeof $distrito.select2 === 'function') {
                        $distrito.select2('destroy');
                    }
                } catch (e) {
                    console.log("⚠️ Error destruyendo Select2 distrito en cargarCantones (limpiar):", e);
                    $distrito.removeClass('select2-hidden-accessible');
                    $distrito.next('.select2-container').remove();
                }
            }
            if (typeof $distrito.select2 === 'function') {
                try {
                    $distrito.select2();
                } catch (e) {
                    console.log("⚠️ Error inicializando Select2 distrito en cargarCantones (limpiar):", e);
                }
            }
                return;
            }
            console.log("Cargando cantones para provincia", provinciaId);
            $.getJSON('/catalogos/api/cantones/' + provinciaId + '/', function(data) {
                var html = '<option value="">----</option>';
                $.each(data, function(_, item) {
                    html += '<option value="' + item.id + '">' + item.nombre + '</option>';
                });
                $canton.html(html);
                if ($canton.hasClass('select2-hidden-accessible')) {
                    try {
                        if (typeof $canton.select2 === 'function') {
                            $canton.select2('destroy');
                        }
                    } catch (e) {
                        console.log("⚠️ Error destruyendo Select2 cantón en cargarCantones:", e);
                        $canton.removeClass('select2-hidden-accessible');
                        $canton.next('.select2-container').remove();
                    }
                }
                if (typeof $canton.select2 === 'function') {
                    try {
                        $canton.select2();
                    } catch (e) {
                        console.log("⚠️ Error inicializando Select2 cantón en cargarCantones:", e);
                    }
                }
                // Limpiar distritos
                $distrito.html('<option value="">----</option>');
                if ($distrito.hasClass('select2-hidden-accessible')) {
                    try {
                        if (typeof $distrito.select2 === 'function') {
                            $distrito.select2('destroy');
                        }
                    } catch (e) {
                        console.log("⚠️ Error destruyendo Select2 distrito al limpiar:", e);
                        $distrito.removeClass('select2-hidden-accessible');
                        $distrito.next('.select2-container').remove();
                    }
                }
                if (typeof $distrito.select2 === 'function') {
                    try {
                        $distrito.select2();
                    } catch (e) {
                        console.log("⚠️ Error inicializando Select2 distrito al limpiar:", e);
                    }
                }
                console.log("Cantones cargados:", data.length);
            }).fail(function(jqXHR, status, err) {
                console.error("Error cargando cantones:", status, err);
            });
        }

        // ──────────────── CANTÓN → DISTRITO ────────────────
        function cargarDistritos(cantonId) {
            var $distrito = $('#id_distrito');
            console.log("cargarDistritos llamado con cantonId:", cantonId);
            if (!cantonId) {
                            $distrito.html('<option value="">----</option>');
            if ($distrito.hasClass('select2-hidden-accessible')) {
                try {
                    if (typeof $distrito.select2 === 'function') {
                        $distrito.select2('destroy');
                    }
                } catch (e) {
                    console.log("⚠️ Error destruyendo Select2 distrito en cargarDistritos (limpiar):", e);
                    $distrito.removeClass('select2-hidden-accessible');
                    $distrito.next('.select2-container').remove();
                }
            }
            if (typeof $distrito.select2 === 'function') {
                try {
                    $distrito.select2();
                } catch (e) {
                    console.log("⚠️ Error inicializando Select2 distrito en cargarDistritos (limpiar):", e);
                }
            }
                return;
            }
            console.log("Cargando distritos para cantón", cantonId);
            $.getJSON('/catalogos/api/distritos/' + cantonId + '/', function(data) {
                var html = '<option value="">----</option>';
                $.each(data, function(_, item) {
                    html += '<option value="' + item.id + '">' + item.nombre + '</option>';
                });
                $distrito.html(html);
                if ($distrito.hasClass('select2-hidden-accessible')) {
                    try {
                        if (typeof $distrito.select2 === 'function') {
                            $distrito.select2('destroy');
                        }
                    } catch (e) {
                        console.log("⚠️ Error destruyendo Select2 distrito en cargarDistritos:", e);
                        $distrito.removeClass('select2-hidden-accessible');
                        $distrito.next('.select2-container').remove();
                    }
                }
                if (typeof $distrito.select2 === 'function') {
                    try {
                        $distrito.select2();
                    } catch (e) {
                        console.log("⚠️ Error inicializando Select2 distrito en cargarDistritos:", e);
                    }
                }
                console.log("Distritos cargados:", data.length);
            }).fail(function(jqXHR, status, err) {
                console.error("Error cargando distritos:", status, err);
            });
        }

        // ──────────────── Inicialización de eventos ────────────────
        function inicializarEventos() {
            console.log("Inicializando eventos para provincia y cantón...");
            var $provincia = $('#id_provincia');
            var $canton = $('#id_canton');

            // --- Provincia ---
            if ($provincia.hasClass('select2-hidden-accessible') && typeof $provincia.select2 === 'function') {
                $provincia.select2('destroy');
                $provincia.removeClass('select2-hidden-accessible');
                $provincia.attr('aria-hidden', 'false');
            } else if ($provincia.hasClass('select2-hidden-accessible')) {
                $provincia.removeClass('select2-hidden-accessible');
                $provincia.attr('aria-hidden', 'false');
                $provincia.next('.select2-container').remove();
            }
            $(document).off('change', '#id_provincia');
            $(document).on('change', '#id_provincia', function() {
                console.log('Change event provincia:', this.value);
                cargarCantones(this.value);
            });

            // --- Cantón ---
            if ($canton.hasClass('select2-hidden-accessible') && typeof $canton.select2 === 'function') {
                $canton.select2('destroy');
                $canton.removeClass('select2-hidden-accessible');
                $canton.attr('aria-hidden', 'false');
            } else if ($canton.hasClass('select2-hidden-accessible')) {
                $canton.removeClass('select2-hidden-accessible');
                $canton.attr('aria-hidden', 'false');
                $canton.next('.select2-container').remove();
            }
            $(document).off('change', '#id_canton');
            $(document).on('change', '#id_canton', function() {
                console.log('Change event canton:', this.value);
                cargarDistritos(this.value);
            });
        }

        setTimeout(function() { inicializarEventos(); }, 1000);
        setTimeout(function() { inicializarEventos(); }, 2000);
        $(document).on('select2:ready', function() { inicializarEventos(); });

        // ──────────────── Carga inicial para edición ────────────────
        function cargarValoresIniciales() {
            console.log("=== CARGANDO VALORES INICIALES ===");
            var $provincia = $('#id_provincia');
            var $canton = $('#id_canton');
            var $distrito = $('#id_distrito');
            
            // Verificar que los elementos existan
            if ($provincia.length === 0) {
                console.log("❌ Elemento provincia no encontrado");
                return;
            }
            if ($canton.length === 0) {
                console.log("❌ Elemento cantón no encontrado");
                return;
            }
            if ($distrito.length === 0) {
                console.log("❌ Elemento distrito no encontrado");
                return;
            }
            
            var provinciaId = $provincia.val();
            var cantonId = $canton.val();
            var distritoId = $distrito.val();
            
            console.log("📊 Valores actuales:");
            console.log("- Provincia ID:", provinciaId);
            console.log("- Cantón ID:", cantonId);
            console.log("- Distrito ID:", distritoId);
            
            // Si hay provincia seleccionada, cargar cantones
            if (provinciaId && provinciaId !== '') {
                console.log("🔄 Cargando cantones para provincia:", provinciaId);
                $.getJSON('/catalogos/api/cantones/' + provinciaId + '/', function(data) {
                    console.log("✅ Cantones recibidos:", data.length, "elementos");
                    var html = '<option value="">----</option>';
                    $.each(data, function(_, item) {
                        var selected = (item.id == cantonId) ? ' selected' : '';
                        html += '<option value="' + item.id + '"' + selected + '>' + item.nombre + '</option>';
                    });
                    $canton.html(html);
                    
                    // Reinicializar Select2 si existe
                    if ($canton.hasClass('select2-hidden-accessible')) {
                        try {
                            if (typeof $canton.select2 === 'function') {
                                $canton.select2('destroy');
                            }
                        } catch (e) {
                            console.log("⚠️ Error destruyendo Select2 cantón:", e);
                            $canton.removeClass('select2-hidden-accessible');
                            $canton.next('.select2-container').remove();
                        }
                    }
                    if (typeof $canton.select2 === 'function') {
                        try {
                            $canton.select2();
                        } catch (e) {
                            console.log("⚠️ Error inicializando Select2 cantón:", e);
                        }
                    }
                    
                    console.log("✅ Cantones cargados, cantón seleccionado:", cantonId);
                    
                    // Si hay cantón seleccionado, cargar distritos
                    if (cantonId && cantonId !== '') {
                        console.log("🔄 Cargando distritos para cantón:", cantonId);
                        $.getJSON('/catalogos/api/distritos/' + cantonId + '/', function(data) {
                            var html = '<option value="">----</option>';
                            $.each(data, function(_, item) {
                                var selected = (item.id == distritoId) ? ' selected' : '';
                                html += '<option value="' + item.id + '"' + selected + '>' + item.nombre + '</option>';
                            });
                            $distrito.html(html);
                            
                            // Reinicializar Select2 si existe
                            if ($distrito.hasClass('select2-hidden-accessible')) {
                                try {
                                    if (typeof $distrito.select2 === 'function') {
                                        $distrito.select2('destroy');
                                    }
                                } catch (e) {
                                    console.log("⚠️ Error destruyendo Select2 distrito:", e);
                                    $distrito.removeClass('select2-hidden-accessible');
                                    $distrito.next('.select2-container').remove();
                                }
                            }
                            if (typeof $distrito.select2 === 'function') {
                                try {
                                    $distrito.select2();
                                } catch (e) {
                                    console.log("⚠️ Error inicializando Select2 distrito:", e);
                                }
                            }
                            
                            console.log("✅ Distritos cargados, distrito seleccionado:", distritoId);
                            console.log("🎉 Carga inicial completada exitosamente");
                        }).fail(function(jqXHR, status, err) {
                            console.error("Error cargando distritos iniciales:", status, err);
                        });
                    }
                }).fail(function(jqXHR, status, err) {
                    console.error("❌ Error cargando cantones iniciales:", status, err);
                });
            } else {
                console.log("ℹ️ No hay provincia seleccionada, saltando carga inicial");
            }
        }
        
        // Ejecutar carga inicial con múltiples intentos
        setTimeout(cargarValoresIniciales, 500);
        setTimeout(cargarValoresIniciales, 1500);
        setTimeout(cargarValoresIniciales, 2500);
        setTimeout(cargarValoresIniciales, 3500);
        
        // También ejecutar cuando Select2 esté listo
        $(document).on('select2:ready', function() {
            setTimeout(cargarValoresIniciales, 100);
        });
        
        // Ejecutar cuando la página esté completamente cargada
        $(window).on('load', function() {
            setTimeout(cargarValoresIniciales, 200);
        });
        
        // Ejecutar cuando el DOM esté listo (múltiples veces)
        $(document).ready(function() {
            setTimeout(cargarValoresIniciales, 300);
            setTimeout(cargarValoresIniciales, 1000);
            setTimeout(cargarValoresIniciales, 2000);
        });
    });
})(window.django && window.django.jQuery ? window.django.jQuery : window.jQuery);
