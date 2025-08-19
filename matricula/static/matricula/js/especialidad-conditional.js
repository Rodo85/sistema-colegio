/**
 * Script para mostrar/ocultar el campo de especialidad según el nivel seleccionado
 * Solo se muestra para niveles 10, 11, 12 (Décimo, Undécimo, Duodécimo)
 */

(function($) {
    'use strict';

    // Configuración: niveles que requieren especialidad
    const NIVELES_CON_ESPECIALIDAD = [10, 11, 12];

    /**
     * Obtiene el número del nivel desde el texto mostrado
     */
    function obtenerNumeroNivel(texto) {
        if (!texto) return null;
        
        // Buscar número al inicio o entre paréntesis
        const match = texto.match(/(\d+)/);
        return match ? parseInt(match[1]) : null;
    }

    /**
     * Muestra u oculta el campo de especialidad
     */
    function toggleEspecialidad(mostrar) {
        const $especialidadField = $('.field-especialidad');
        
        if (mostrar) {
            console.log('✅ Mostrando campo especialidad');
            $especialidadField.show();
        } else {
            console.log('❌ Ocultando campo especialidad');
            $especialidadField.hide();
            
            // Limpiar el valor de especialidad cuando se oculta
            const $especialidadSelect = $('#id_especialidad');
            if ($especialidadSelect.length > 0) {
                $especialidadSelect.val(null).trigger('change');
            }
        }
    }

    /**
     * Maneja el cambio de nivel
     */
    function onNivelChange() {
        const $nivelSelect = $('#id_nivel');
        const nivelText = $nivelSelect.find('option:selected').text();
        const numeroNivel = obtenerNumeroNivel(nivelText);
        
        console.log(`🔄 Nivel cambiado: "${nivelText}" -> Número: ${numeroNivel}`);
        
        if (numeroNivel && NIVELES_CON_ESPECIALIDAD.includes(numeroNivel)) {
            console.log(`✅ Nivel ${numeroNivel} requiere especialidad`);
            toggleEspecialidad(true);
        } else {
            console.log(`❌ Nivel ${numeroNivel} NO requiere especialidad`);
            toggleEspecialidad(false);
        }
    }

    /**
     * Inicializa el comportamiento
     */
    function inicializar() {
        console.log('🚀 Inicializando control de especialidad por nivel...');
        
        const $nivelSelect = $('#id_nivel');
        
        if ($nivelSelect.length === 0) {
            console.log('❌ Campo nivel no encontrado');
            return;
        }
        
        // Estado inicial
        onNivelChange();
        
        // Configurar evento de cambio
        $nivelSelect.off('change.especialidadConditional').on('change.especialidadConditional', function() {
            setTimeout(onNivelChange, 100); // Pequeño delay para que se actualice el texto
        });
        
        console.log('✅ Control de especialidad configurado');
    }

    // Inicializar cuando el DOM esté listo
    $(document).ready(function() {
        setTimeout(inicializar, 500); // Delay para que se carguen otros scripts
    });

    // También reinicializar si se detectan cambios en el DOM (para formularios dinámicos)
    if (window.MutationObserver) {
        const observer = new MutationObserver(function(mutations) {
            let shouldReinit = false;
            mutations.forEach(function(mutation) {
                if (mutation.type === 'childList' && mutation.addedNodes.length > 0) {
                    for (let node of mutation.addedNodes) {
                        if (node.nodeType === 1 && node.querySelector && node.querySelector('#id_nivel')) {
                            shouldReinit = true;
                            break;
                        }
                    }
                }
            });
            
            if (shouldReinit) {
                console.log('🔄 Detectado cambio en DOM, reinicializando...');
                setTimeout(inicializar, 500);
            }
        });
        
        observer.observe(document.body, {
            childList: true,
            subtree: true
        });
    }

})(django.jQuery || jQuery);
