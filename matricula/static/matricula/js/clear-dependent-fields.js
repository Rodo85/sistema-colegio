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
     * Verifica si el nivel actual requiere especialidad (10, 11, 12)
     */
    function nivelRequiereEspecialidad() {
        const $nivel = $('select[name="nivel"]').not('[name*="__prefix__"]');
        
        if ($nivel.length === 0) {
            return false;
        }
        
        const nivelTexto = $nivel.find('option:selected').text().trim();
        return /\b(10|11|12|décimo|undécimo|duodécimo)\b/i.test(nivelTexto);
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

        // Si el cambio es en 'especialidad', limpiar 'seccion' y 'subgrupo' para forzar reselección.
        } else if (changedFieldName.includes('especialidad')) {
            // CRÍTICO: Solo limpiar si el nivel requiere especialidad (10, 11, 12)
            if (!nivelRequiereEspecialidad()) {
                console.log("⚠️ Nivel NO requiere especialidad - NO se limpiarán sección/subgrupo");
                return;
            }
            
            console.log("🎓 Especialidad cambió (nivel 10-12) - limpiando sección y subgrupo");
            const $seccionField = $('select[name*="seccion"]').not('[name*="__prefix__"]');
            const $subgrupoField = $('select[name*="subgrupo"]').not('[name*="__prefix__"]');
            
            limpiarCampoSelect2($seccionField, 'Seleccione la sección correspondiente a la especialidad...');
            limpiarCampoSelect2($subgrupoField, 'Seleccione primero una sección...');
            
            // Forzar actualización de los campos
            $seccionField.trigger('change');
            $subgrupoField.trigger('change');
            
            console.log("✅ Sección y subgrupo limpiados por cambio de especialidad");

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
        // Incluye múltiples eventos de Select2 para capturar todos los cambios
        $(document).on('change.dalDependentFields select2:select.dalDependentFields select2:unselect.dalDependentFields select2:clear.dalDependentFields', 
            'select[name*="curso_lectivo"], select[name*="nivel"], select[name*="seccion"], select[name*="especialidad"]', function(e) {
            const fieldName = $(this).attr('name');
            console.log("🔔 Evento detectado:", e.type, "en campo:", fieldName);
            
            // Un pequeño retraso para asegurar que la lógica de DAL se ejecute primero
            setTimeout(() => {
                aplicarLimpiezaDependiente(fieldName);
            }, 100); // Aumentado a 100ms para dar más tiempo
        });
        
        console.log("✅ Eventos configurados para: curso_lectivo, nivel, seccion, especialidad");
    }

    /**
     * Monitoreo adicional para especialidad (verificación periódica del valor)
     */
    let especialidadAnterior = null;
    function monitoreoContinuoEspecialidad() {
        // CRÍTICO: Solo monitorear si el nivel requiere especialidad
        if (!nivelRequiereEspecialidad()) {
            return; // No monitorear para niveles 7, 8, 9
        }
        
        const $especialidad = $('select[name*="especialidad"]').not('[name*="__prefix__"]');
        if ($especialidad.length > 0) {
            const valorActual = $especialidad.val();
            
            // Si cambió el valor de especialidad
            if (especialidadAnterior !== null && especialidadAnterior !== valorActual && valorActual !== null && valorActual !== '') {
                console.log("🔔 MONITOREO: Especialidad cambió de", especialidadAnterior, "a", valorActual);
                aplicarLimpiezaDependiente($especialidad.attr('name'));
            }
            
            especialidadAnterior = valorActual;
        }
    }
    
    /**
     * Inicializa el script y sus oyentes, usando múltiples intentos.
     */
    function inicializar() {
        if (!$) return;
        console.log('🚀 Inicializando sistema de limpieza... (Intento)');
        configurarEventos();
        
        // Iniciar monitoreo continuo de especialidad (cada 500ms)
        setInterval(monitoreoContinuoEspecialidad, 500);
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