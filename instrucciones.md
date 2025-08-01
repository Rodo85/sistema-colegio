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

