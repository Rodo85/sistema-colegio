# INSTRUCCIONES GENERALES DEL PROYECTO

## 1. Multi-institucionalidad
- **Este sistema es multi-institucional (multi-colegio).**
- Cada colegio (institución) solo puede ver y gestionar la información referente a su propia institución.
- El **superusuario (super admin)** tiene acceso total y puede ver, crear, editar y eliminar datos de todas las instituciones.

## 2. Visibilidad y permisos de la institución
- Al crear o editar cualquier registro, **solo el superusuario** debe tener la opción de escoger la institución.
- Los usuarios comunes (directores, administrativos, etc.) **no pueden ver ni editar el campo institución** en los formularios; su acceso siempre estará restringido a su institución activa.

## 3. Consistencia de datos
- **Todos los campos de texto** (nombres, apellidos, direcciones, etc.) deben ser **almacenados en mayúsculas** y **sin espacios en blanco al inicio o al final**.
- Esta normalización debe ser **automática**, sin requerir confirmación del usuario ni pasos extra.
- Solo se pedirá aprobación si el usuario da una instrucción explícita de no aplicar estos cambios en un caso particular.

## 4. Catálogos y tablas globales
- **Los catálogos globales** (provincias, niveles, especialidades, etc.) **solo pueden ser modificados por el superusuario**.
- Los usuarios de las instituciones solo pueden consultar los catálogos globales, no modificarlos.

## 5. Buenas prácticas en desarrollo
- **No modificar estas reglas** a menos que el usuario dé una instrucción clara y directa para hacerlo.
- Todas las nuevas funcionalidades deben ajustarse a estas reglas por defecto.

---

**Nota:**  
Si tienes dudas sobre la aplicación de alguna regla, asume siempre la política más restrictiva para los usuarios normales y más permisiva solo para el superusuario.

**Importante**
Aplica todos los cambios que te solicite de manera automática y directa, sin pedirme confirmación ni aprobación extra.
Solo detente o pide confirmación si te indico explícitamente que NO hagas un cambio al instante, o si te lo aclaro en la instrucción.
En cualquier otro caso, ejecuta los cambios solicitados en el momento.

**Super Importante - Dropdowns Dependientes**
Cuando trabajemos con dropdown al parecer hay problemas de dependencia, con mucha dificultad arreglamos los dropdown del estudiante donde tenemos, provincia, canton y distrito, creo que util analizar como trabaja eso para aplicarlo en las demas dependcias del sistema enfocada en los ddropdown, Ojo nunca cambies esa logica, porque costo mucho llegar a ella

**SOLUCIÓN DOCUMENTADA PARA DROPDOWNS DEPENDIENTES:**

1. **Problema principal**: Los campos `autocomplete_fields` en Django Admin funcionan diferente a los `<select>` normales
   - Select normal: Un solo evento `change` en el elemento
   - Autocomplete: Dos campos (hidden + visible) + interfaz Select2

2. **Estrategia exitosa para autocomplete:**
   - Interceptar clicks directos en `.select2-results__option` (opciones del dropdown)
   - Escuchar eventos `select2:select` y `select2:unselect`
   - Monitorear campos `input[name*="campo"]` con eventos `input`, `change`, `blur`
   - Usar `MutationObserver` para detectar elementos dinámicos (inlines)

3. **Estructura del JavaScript:**
   ```javascript
   // Interceptar clicks en opciones del autocomplete
   $(document).on('click', '.select2-results__option', function(e) {
       var textoOpcion = $(this).text();
       // Lógica para mostrar/ocultar campos dependientes
   });
   
   // Interceptar eventos Select2
   $(document).on('select2:select', function(e) {
       var data = e.params.data;
       // Lógica basada en data.text
   });
   
   // Observer para elementos dinámicos
   var observer = new MutationObserver(function(mutations) {
       // Re-configurar eventos en nuevos elementos
   });
   ```

4. **Incluir el JavaScript:**
   - En `FormAdmin.Media.js` para formularios directos
   - En `ModelAdmin.Media.js` para formularios con inlines
   - Ambos lugares si el campo puede aparecer en ambos contextos

5. **Casos exitosos implementados:**
   - Provincia → Cantón → Distrito (dependent-dropdowns.js)
   - Nivel → Especialidad (dependent-especialidad.js)

**Nota importante**
Cuando te pida algo haz los cambios automaticamente, no me preguntes si quiero que tu lo hagas solo hazlo
