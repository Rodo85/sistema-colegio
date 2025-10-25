# Sistema de Historial Institucional

## Resumen de Cambios

Se ha implementado un sistema de **historial institucional** que permite que un estudiante pueda cambiar de colegio sin necesidad de duplicar toda su información personal. Los estudiantes ahora son **únicos a nivel global** (no por institución).

---

## 🎯 Problema Resuelto

**Antes:**
- Un estudiante tenía una relación directa con una sola institución
- Si un estudiante se trasladaba de colegio, había que ingresar toda su información nuevamente
- La identificación (cédula) era única solo **por institución**, permitiendo duplicados

**Después:**
- Un estudiante existe una sola vez en el sistema (identificación única **globalmente**)
- El estudiante puede tener relaciones con múltiples instituciones a lo largo del tiempo
- Se mantiene un historial completo de todas las instituciones por las que ha pasado

---

## 📊 Nueva Arquitectura

### 1. Modelo Estudiante
- **Identificación única a nivel GLOBAL** (no se puede duplicar en todo el sistema)
- Campo `institucion` ahora es **nullable** (deprecado, se mantiene temporalmente)
- Información personal del estudiante (nombre, apellidos, fecha nacimiento, etc.)

### 2. Modelo EstudianteInstitucion (NUEVO)
Tabla intermedia que registra el historial de instituciones:

| Campo | Descripción |
|-------|-------------|
| `estudiante` | FK al estudiante |
| `institucion` | FK a la institución |
| `estado` | activo / inactivo / trasladado / retirado |
| `fecha_ingreso` | Cuándo ingresó a la institución |
| `fecha_salida` | Cuándo salió (nullable) |
| `observaciones` | Notas adicionales |
| `usuario_registro` | Quién registró la relación |

**Regla importante:** Un estudiante solo puede tener **UNA relación activa** a la vez.

### 3. Modelo MatriculaAcademica
- Ahora valida que el estudiante tenga una relación activa con la institución antes de permitir matricular
- El campo `institucion` de la matrícula se asigna automáticamente desde la relación activa

---

## 🔧 Funcionalidades Implementadas

### Administración de Estudiantes
1. **Vista de estudiante individual:**
   - Muestra inline con historial de instituciones
   - Se puede agregar/editar relaciones institucionales directamente

2. **Lista de estudiantes:**
   - Solo muestra estudiantes con relación activa en la institución del usuario
   - Superusuarios ven todos los estudiantes

3. **Validación de identificación:**
   - Si intentas crear un estudiante con cédula existente:
     - Muestra mensaje: *"Ya existe un estudiante con la identificación X: NOMBRE COMPLETO (Institución: Y)"*
     - En el futuro, se agregará opción para agregar al estudiante a tu institución

### Admin de Historial Institucional (EstudianteInstitucion)
- Permite gestionar manualmente las relaciones estudiante-institución
- Filtros por estado, institución, fecha
- Búsqueda por identificación o nombre del estudiante
- Usuarios normales solo ven relaciones de su institución

### Migraciones
- **Migración automática de datos:**
  - Los 944 estudiantes existentes fueron migrados automáticamente
  - Se creó una relación activa para cada uno en su institución original
  - No se perdió ningún dato

---

## 📝 Casos de Uso

### Caso 1: Estudiante nuevo en el sistema
```
1. Usuario crea estudiante con identificación 123456789
2. Sistema valida que la identificación no exista globalmente
3. Se crea el estudiante
4. Automáticamente se crea la relación EstudianteInstitucion con estado "activo"
5. El estudiante ya puede ser matriculado
```

### Caso 2: Estudiante se traslada a otra institución
```
1. Institución A marca la relación como "trasladado" y establece fecha_salida
2. Institución B busca al estudiante por identificación
3. Institución B agrega al estudiante a su institución (estado "activo")
4. El estudiante ahora aparece en la lista de estudiantes de la Institución B
5. Todo el historial académico se mantiene intacto
```

### Caso 3: Estudiante regresa a una institución anterior
```
1. Estudiante estuvo en Institución A (relación "trasladado")
2. Regresa a Institución A
3. Se puede reactivar la relación existente o crear una nueva
4. El historial muestra todos los períodos
```

---

## ⚙️ Comandos de Gestión

### limpiar_estudiantes_duplicados
Limpia estudiantes duplicados consolidando sus datos:
```bash
python manage.py limpiar_estudiantes_duplicados
```

Este comando:
- Encuentra identificaciones duplicadas
- Mantiene el primer estudiante encontrado
- Mueve todas las matrículas y encargados al estudiante principal
- Elimina los duplicados

---

## 🔒 Seguridad y Permisos

### Usuarios Normales (Directores, Administrativos)
- Solo ven estudiantes con relación activa en su institución
- Pueden agregar estudiantes a su institución
- No pueden editar la institución de un estudiante existente
- No pueden ver estudiantes de otras instituciones

### Superusuarios
- Ven todos los estudiantes de todas las instituciones
- Pueden editar cualquier relación institucional
- Pueden mover estudiantes entre instituciones
- Tienen acceso completo al historial

---

## 📚 Próximas Mejoras

1. **Búsqueda inteligente de estudiantes:**
   - Al intentar crear un estudiante con cédula existente
   - Mostrar opción: "Ya existe este estudiante, ¿deseas agregarlo a tu institución?"
   - Flujo guiado para trasladar estudiantes

2. **Reportes de historial:**
   - Reporte de estudiantes trasladados
   - Reporte de estudiantes que han estado en múltiples instituciones
   - Estadísticas de movilidad estudiantil

3. **Notificaciones:**
   - Notificar a la institución origen cuando un estudiante es agregado a otra institución
   - Alertas de traslados pendientes

4. **Dashboard:**
   - Visualización del historial institucional en el perfil del estudiante
   - Línea de tiempo con todas las instituciones

---

## 🛠️ Notas Técnicas

### Constraint de Base de Datos
```sql
-- Identificación única globalmente
CONSTRAINT unique_estudiante_identificacion_global 
    UNIQUE (identificacion)

-- Solo una relación activa por estudiante
CONSTRAINT unique_estudiante_institucion_activa
    UNIQUE (estudiante_id) WHERE estado = 'activo'
```

### Métodos Útiles del Modelo Estudiante
```python
# Obtener la institución activa actual
institucion = estudiante.get_institucion_activa()

# Obtener todo el historial
historial = estudiante.get_instituciones_historial()
```

### Compatibilidad Temporal
El campo `Estudiante.institucion` se mantiene temporalmente para compatibilidad pero está deprecado. Las nuevas funcionalidades deben usar `EstudianteInstitucion`.

---

## ✅ Estado Actual

- ✅ Modelo EstudianteInstitucion creado
- ✅ Migración de datos completada (944 estudiantes)
- ✅ Admin configurado con inline de historial
- ✅ Validaciones implementadas
- ✅ Querysets y filtros actualizados
- ✅ Vistas actualizadas
- ✅ Formularios actualizados
- ⏳ Búsqueda inteligente (pendiente)
- ⏳ Reportes (pendiente)

---

## 🚀 Conclusión

El nuevo sistema permite una gestión mucho más flexible y realista del ciclo de vida de los estudiantes en el sistema educativo, eliminando la necesidad de duplicar información y manteniendo un historial completo de la trayectoria académica de cada estudiante.

