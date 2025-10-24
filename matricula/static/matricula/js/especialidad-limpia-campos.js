// LIMPIAR SECCIÓN Y SUBGRUPO CUANDO CAMBIA LA ESPECIALIDAD
// Script dedicado y agresivo para garantizar la limpieza
(function() {
    'use strict';
    
    console.log("═══════════════════════════════════════════════════");
    console.log("🔧 ESPECIALIDAD-LIMPIA-CAMPOS.JS CARGADO");
    console.log("═══════════════════════════════════════════════════");
    
    // Variable para almacenar el valor anterior de especialidad
    let especialidadValorAnterior = null;
    let primeraVez = true;
    
    /**
     * Limpia completamente un campo Select2
     */
    function limpiarCampoCompletamente($campo, placeholder) {
        if (!$campo || $campo.length === 0) {
            return;
        }
        
        console.log("🧹 Limpiando campo:", $campo.attr('name'));
        
        try {
            // Método 1: val(null)
            $campo.val(null);
            
            // Método 2: empty() para Select2
            if ($campo.hasClass('select2-hidden-accessible')) {
                $campo.empty();
            }
            
            // Método 3: Trigger de cambios
            $campo.trigger('change.select2');
            $campo.trigger('change');
            
            // Método 4: Actualizar el placeholder visual
            const $container = $campo.next('.select2-container');
            if ($container.length > 0) {
                const $rendered = $container.find('.select2-selection__rendered');
                if ($rendered.length > 0) {
                    $rendered.text(placeholder || '');
                    $rendered.attr('title', placeholder || '');
                }
            }
            
            console.log("✅ Campo limpiado:", $campo.attr('name'));
        } catch (e) {
            console.error("❌ Error limpiando campo:", e);
        }
    }
    
    /**
     * Verifica si el nivel actual requiere especialidad (10, 11, 12)
     */
    function nivelRequiereEspecialidad() {
        const $nivel = $('select[name="nivel"]').not('[name*="__prefix__"]');
        
        if ($nivel.length === 0) {
            return false; // Si no hay campo nivel, no requerir
        }
        
        // Obtener el texto del option seleccionado
        const nivelTexto = $nivel.find('option:selected').text().trim();
        
        // Verificar si contiene 10, 11 o 12 (puede ser "Décimo", "10°", etc.)
        const requiereEspecialidad = /\b(10|11|12|décimo|undécimo|duodécimo)\b/i.test(nivelTexto);
        
        console.log("🎯 Nivel actual:", nivelTexto, "| Requiere especialidad:", requiereEspecialidad);
        
        return requiereEspecialidad;
    }
    
    /**
     * Verifica y limpia sección y subgrupo si cambió la especialidad
     */
    function verificarYLimpiar() {
        // CRÍTICO: Verificar PRIMERO si el nivel requiere especialidad
        // Si NO requiere (7, 8, 9), no hacer NADA
        if (!nivelRequiereEspecialidad()) {
            return; // Salir inmediatamente - no monitorear especialidad para estos niveles
        }
        
        // Solo continuar si el nivel es 10, 11 o 12
        // Buscar el campo de especialidad (excluyendo templates de inline)
        const $especialidad = $('select[name="especialidad"]').not('[name*="__prefix__"]');
        
        if ($especialidad.length === 0) {
            return; // Campo no encontrado
        }
        
        // VERIFICAR SI EL CAMPO ESTÁ VISIBLE (no oculto por CSS)
        // Si está oculto, no monitorear cambios
        if (!$especialidad.is(':visible')) {
            return; // Campo oculto - no hacer nada
        }
        
        const valorActual = $especialidad.val();
        
        // En la primera verificación, solo guardar el valor sin limpiar
        if (primeraVez) {
            especialidadValorAnterior = valorActual;
            primeraVez = false;
            console.log("📝 Valor inicial de especialidad:", valorActual);
            return;
        }
        
        // Si el valor cambió y no es null/vacío
        if (especialidadValorAnterior !== valorActual && valorActual !== null && valorActual !== '') {
            console.log("═══════════════════════════════════════════════════");
            console.log("🎓 ESPECIALIDAD CAMBIÓ!");
            console.log("   Anterior:", especialidadValorAnterior);
            console.log("   Actual:", valorActual);
            console.log("✅ Nivel requiere especialidad (10, 11, 12) - procediendo con limpieza");
            console.log("═══════════════════════════════════════════════════");
            
            // Buscar campos de sección y subgrupo
            const $seccion = $('select[name="seccion"]').not('[name*="__prefix__"]');
            const $subgrupo = $('select[name="subgrupo"]').not('[name*="__prefix__"]');
            
            console.log("🔍 Campos encontrados:");
            console.log("   - Sección:", $seccion.length > 0 ? "✅" : "❌");
            console.log("   - Subgrupo:", $subgrupo.length > 0 ? "✅" : "❌");
            
            // Limpiar sección
            if ($seccion.length > 0) {
                limpiarCampoCompletamente($seccion, 'Seleccione la sección correspondiente a la especialidad...');
            }
            
            // Limpiar subgrupo
            if ($subgrupo.length > 0) {
                limpiarCampoCompletamente($subgrupo, 'Seleccione primero una sección...');
            }
            
            console.log("✅ LIMPIEZA COMPLETADA");
            console.log("═══════════════════════════════════════════════════");
            
            // Actualizar el valor anterior
            especialidadValorAnterior = valorActual;
        } else if (especialidadValorAnterior !== valorActual) {
            // Solo actualizar el valor sin limpiar (cambio a null/vacío)
            especialidadValorAnterior = valorActual;
        }
    }
    
    /**
     * Inicializa el sistema de monitoreo
     */
    function inicializar() {
        // Verificación cada 300ms (más frecuente)
        setInterval(verificarYLimpiar, 300);
        console.log("✅ Monitoreo de especialidad iniciado (cada 300ms)");
        
        // También configurar eventos directos
        $(document).on('change', 'select[name="especialidad"]', function() {
            console.log("📡 Evento 'change' detectado en especialidad");
            setTimeout(verificarYLimpiar, 100);
        });
        
        $(document).on('select2:select', 'select[name="especialidad"]', function(e) {
            console.log("📡 Evento 'select2:select' detectado en especialidad");
            setTimeout(verificarYLimpiar, 100);
        });
        
        $(document).on('select2:unselect', 'select[name="especialidad"]', function(e) {
            console.log("📡 Evento 'select2:unselect' detectado en especialidad");
            setTimeout(verificarYLimpiar, 100);
        });
        
        console.log("✅ Eventos configurados para especialidad");
    }
    
    // Esperar a que jQuery esté disponible
    function esperarJQuery() {
        if (typeof jQuery !== 'undefined') {
            window.$ = jQuery;
            $(document).ready(function() {
                console.log("📦 jQuery listo - iniciando sistema");
                inicializar();
            });
        } else {
            setTimeout(esperarJQuery, 100);
        }
    }
    
    esperarJQuery();
})();

