// LIMPIEZA AUTOMÁTICA DE CAMPOS DEPENDIENTES (VERSIÓN FINAL Y MEJORADA)
(function($) {
    'use strict';

    if (!$) {
        console.error("clear-dependent-fields.js: jQuery no encontrado");
        return;
    }

    /**
     * Limpia y reinicializa un campo Select2.
     * @param {jQuery} $field - El elemento jQuery del campo.
     * @param {string} placeholderText - El texto del placeholder.
     */
    function limpiarCampoSelect2($field, placeholderText) {
        if ($field.length === 0 || $field.attr('name').includes('__prefix__')) {
            return;
        }
        
        console.log(`🧹 Limpiando y re-renderizando campo: ${$field.attr('name')}`);
        
        try {
            // Limpiar el valor directamente y forzar un evento de cambio
            $field.val(null).trigger('change');

            // Actualizar el texto del placeholder en la interfaz visible de Select2
            const $select2Container = $field.next('.select2-container');
            if ($select2Container.length) {
                const $selection = $select2Container.find('.select2-selection__rendered');
                $selection.empty().text(placeholderText).attr('title', placeholderText);
            }
        } catch(e) {
            console.warn(`⚠️ Error al limpiar campo ${$field.attr('name')}:`, e);
        }
    }

    /**
     * Aplica la lógica de limpieza y actualización a los campos dependientes.
     * @param {string} changedFieldName - El nombre del campo que cambió.
     */
    function aplicarLimpiezaDependiente(changedFieldName) {
        console.log(`🔄 Cambio detectado en: ${changedFieldName}`);

        // Si el cambio es en 'curso_lectivo' o 'nivel', limpiar todos los campos dependientes.
        if (changedFieldName.includes('curso_lectivo') || changedFieldName.includes('nivel')) {
            const $seccionField = $('select[name*="seccion"]');
            const $subgrupoField = $('select[name*="subgrupo"]');
            const $especialidadField = $('select[name*="especialidad"]');

            limpiarCampoSelect2($seccionField, 'Seleccione primero un curso lectivo y un nivel...');
            limpiarCampoSelect2($subgrupoField, 'Seleccione primero un curso lectivo y una sección...');
            limpiarCampoSelect2($especialidadField, 'Seleccione primero un curso lectivo y un nivel...');
            
            // Forzar la recarga de los datos de autocompletado en los campos
            // esto hace que se actualicen las opciones automáticamente
            $seccionField.trigger('change');
            $subgrupoField.trigger('change');
            $especialidadField.trigger('change');

        // Si el cambio es en 'seccion', solo limpiar 'subgrupo'.
        } else if (changedFieldName.includes('seccion')) {
            const $subgrupoField = $('select[name*="subgrupo"]');
            limpiarCampoSelect2($subgrupoField, 'Seleccione primero un curso lectivo y una sección...');
            $subgrupoField.trigger('change');
        }
    }
    
    /**
     * Configura todos los oyentes de eventos.
     */
    function configurarEventos() {
        console.log("🔧 Re-configurando eventos para campos dependientes...");
        
        $(document).off('.dalDependentFields');
        
        // Vínculo a eventos de cambio y selección para todos los campos padres
        $(document).on('change.dalDependentFields select2:select.dalDependentFields select2:unselect.dalDependentFields', 
            'select[name*="curso_lectivo"], select[name*="nivel"], select[name*="seccion"]', function(e) {
            const fieldName = $(this).attr('name');
            // Un pequeño retraso para asegurar que la lógica de DAL se ejecute primero
            setTimeout(() => {
                aplicarLimpiezaDependiente(fieldName);
            }, 50);
        });
    }

    /**
     * Inicializa el script y sus oyentes, usando múltiples intentos.
     */
    function inicializar() {
        if (!$) return;
        console.log('🚀 Inicializando sistema de limpieza... (Intento)');
        configurarEventos();
    }
    
    $(document).ready(function() {
        inicializar();
        setTimeout(inicializar, 500);
        setTimeout(inicializar, 1500);
        setTimeout(inicializar, 3000);
    });

    if (window.MutationObserver) {
        const observer = new MutationObserver(function(mutations) {
            mutations.forEach(function(mutation) {
                if (mutation.type === 'childList') {
                    const newFields = $(mutation.addedNodes).find('select[name*="nivel"], select[name*="seccion"], select[name*="subgrupo"]');
                    if (newFields.length > 0) {
                        console.log('🔄 Nuevos campos de formulario dependientes detectados. Reinicializando...');
                        setTimeout(inicializar, 100); 
                    }
                }
            });
        });
        
        observer.observe(document.body, { childList: true, subtree: true });
    }
    
})(window.django && window.django.jQuery ? window.django.jQuery : window.jQuery);