// MOSTRAR/OCULTAR PESTAÑA PLAN NACIONAL SEGÚN TIPO DE ESTUDIANTE
// Estrategia: POLLING (revisión constante del valor)
(function($) {
    if (!$) {
        console.error("toggle-plan-nacional.js: jQuery no encontrado");
        return;
    }
    
    $(function() {
        console.log("=== TOGGLE PLAN NACIONAL (POLLING) ===");
        
        var valorAnterior = null;
        var intervalo = null;
        
        // ──────────────── FUNCIONES MOSTRAR/OCULTAR ────────────────
        function mostrarPlanNacional() {
            // Mostrar la pestaña en el nav-tabs
            $('.nav-tabs li').each(function() {
                var texto = $(this).find('a').text().trim().toLowerCase();
                if (texto.indexOf('plan nacional') !== -1) {
                    $(this).show();
                    $(this).removeClass('d-none');
                }
            });
            
            // Mostrar el contenido del fieldset Y LIMPIAR TODOS LOS ESTILOS CSS INLINE
            $('.plannacional-section').show();
            $('.plannacional-section').removeClass('d-none');
            $('.plannacional-section').css({
                'display': '',      // Limpiar display
                'position': '',     // Limpiar position
                'visibility': '',   // Limpiar visibility
                'height': '',       // Limpiar height
                'overflow': ''      // Limpiar overflow
            });
            
            // Asegurar que los campos dentro también sean visibles
            $('.plannacional-section .form-row').each(function() {
                $(this).show();
                $(this).css({
                    'display': '',
                    'visibility': '',
                    'height': '',
                    'overflow': ''
                });
            });
            
            console.log("✅ Plan Nacional VISIBLE");
        }
        
        function ocultarPlanNacional() {
            // Ocultar la pestaña en el nav-tabs
            $('.nav-tabs li').each(function() {
                var texto = $(this).find('a').text().trim().toLowerCase();
                if (texto.indexOf('plan nacional') !== -1) {
                    $(this).hide();
                    $(this).addClass('d-none');
                }
            });
            
            // Ocultar el contenido del fieldset Y removerlo del flujo del documento
            $('.plannacional-section').hide();
            $('.plannacional-section').addClass('d-none');
            $('.plannacional-section').css({
                'display': 'none',
                'position': 'absolute',
                'visibility': 'hidden',
                'height': '0',
                'overflow': 'hidden'
            });
            
            // Limpiar valores
            $('input[name*="posee_carnet"], input[name*="posee_valvula"], input[name*="usa_apoyo"], input[name*="posee_control"], input[name*="orden_alejamiento"]').prop('checked', false);
            $('input[name*="apoyo_cual"], input[name*="tipo_condicion"], input[name*="control_cual"], input[name*="orden_alejamiento_nombre"]').val('');
            
            console.log("✅ Plan Nacional OCULTO");
        }
        
        function actualizarVisibilidad(valor) {
            if (valor === 'PN') {
                mostrarPlanNacional();
            } else {
                ocultarPlanNacional();
            }
        }
        
        // ──────────────── POLLING: REVISAR VALOR CADA SEGUNDO ────────────────
        function iniciarPolling() {
            console.log("🔄 Iniciando polling (revisión cada 500ms)");
            
            intervalo = setInterval(function() {
                var $campo = $('#id_tipo_estudiante');
                
                if ($campo.length === 0) {
                    return; // Campo no encontrado aún
                }
                
                var valorActual = $campo.val();
                
                // Solo actualizar si el valor cambió
                if (valorActual !== valorAnterior) {
                    console.log("🔔 CAMBIO DETECTADO:", valorAnterior, "→", valorActual);
                    valorAnterior = valorActual;
                    actualizarVisibilidad(valorActual);
                }
            }, 500); // Revisar cada medio segundo
            
            console.log("✅ Polling iniciado");
        }
        
        // ──────────────── INICIALIZACIÓN ────────────────
        function inicializar() {
            console.log("🚀 Inicializando...");
            
            var $campo = $('#id_tipo_estudiante');
            
            if ($campo.length === 0) {
                console.log("⏳ Campo no encontrado, esperando...");
                setTimeout(inicializar, 500);
                return;
            }
            
            console.log("✅ Campo encontrado");
            
            // Valor inicial
            valorAnterior = $campo.val();
            console.log("📝 Valor inicial:", valorAnterior);
            actualizarVisibilidad(valorAnterior);
            
            // Iniciar polling
            iniciarPolling();
            
            // También configurar evento change por si acaso
            $(document).on('change', '#id_tipo_estudiante', function() {
                console.log("✨ Change event detectado:", this.value);
                valorAnterior = this.value;
                actualizarVisibilidad(this.value);
            });
        }
        
        // Iniciar
        inicializar();
        
        console.log("🎪 TOGGLE PLAN NACIONAL CONFIGURADO (POLLING)");
    });
    
})(typeof django !== 'undefined' && django.jQuery ? django.jQuery : (typeof $ !== 'undefined' ? $ : null));
