# Vistas Masivas para Gestión de Secciones, Especialidades y Subgrupos

## Descripción

Se han implementado nuevas vistas masivas para gestionar de forma eficiente las secciones, especialidades y subgrupos por curso lectivo en el sistema multi-institucional. Estas vistas permiten seleccionar múltiples elementos usando checkboxes en lugar de crear registros uno por uno.

## Funcionalidades Implementadas

### 1. Gestión Masiva de Secciones por Curso Lectivo

**URL:** `/config/gestionar-secciones-curso-lectivo/`

**Características:**
- Vista con checkboxes para todas las secciones disponibles
- Filtros por institución y curso lectivo
- Selección masiva (seleccionar/deseleccionar todas)
- Paginación para manejar grandes cantidades de secciones
- Guardado masivo de cambios
- Interfaz moderna y responsiva

**Acceso desde Admin:**
- En el admin de `SeccionCursoLectivo`, cada registro tiene un enlace "📋 Vista Masiva"
- El enlace abre la vista masiva con los filtros pre-seleccionados

### 2. Gestión Masiva de Especialidades por Curso Lectivo

**URL:** `/config/gestionar-especialidades-curso-lectivo/`

**Características:**
- Vista con checkboxes para todas las especialidades disponibles
- Filtros por institución, curso lectivo y modalidad (Académico/Técnico)
- Selección masiva (seleccionar/deseleccionar todas)
- Paginación para manejar grandes cantidades de especialidades
- Guardado masivo de cambios
- Interfaz moderna y responsiva

**Acceso desde Admin:**
- En el admin de `EspecialidadCursoLectivo`, cada registro tiene un enlace "📋 Vista Masiva"
- El enlace abre la vista masiva con los filtros pre-seleccionados

### 3. Gestión Masiva de Subgrupos por Curso Lectivo

**URL:** `/config/gestionar-subgrupos-curso-lectivo/`

**Características:**
- Vista con checkboxes para todos los subgrupos disponibles
- Filtros por institución, curso lectivo y nivel (7mo, 8vo, 9no, etc.)
- Selección masiva (seleccionar/deseleccionar todas)
- Paginación para manejar grandes cantidades de subgrupos
- Guardado masivo de cambios
- Interfaz moderna y responsiva con visualización de letras de subgrupo
- Filtro por nivel educativo para facilitar la gestión

**Acceso desde Admin:**
- En el admin de `SubgrupoCursoLectivo`, cada registro tiene un enlace "📋 Vista Masiva"
- El enlace abre la vista masiva con los filtros pre-seleccionados

## Cómo Usar

### Para Usuarios Normales (Directores de Institución)

1. **Acceder a la vista masiva:**
   - Ir al admin de Django
   - Navegar a `Config Institucional` > `Secciones por Curso Lectivo`, `Especialidades por Curso Lectivo` o `Subgrupos por Curso Lectivo`
   - Hacer clic en el enlace "📋 Vista Masiva" de cualquier registro

2. **Seleccionar elementos:**
   - La vista se abrirá con la institución y curso lectivo pre-seleccionados
   - Usar los checkboxes para marcar las secciones/especialidades/subgrupos que se desean activar
   - Usar los botones "✅ Seleccionar Todas" o "❌ Deseleccionar Todas" para acciones masivas

3. **Guardar cambios:**
   - Hacer clic en "💾 Guardar Cambios"
   - Los cambios se procesarán y se mostrará un mensaje de confirmación

### Para Superusuarios

1. **Seleccionar institución y curso lectivo:**
   - La vista permite seleccionar cualquier institución del sistema
   - Seleccionar el curso lectivo deseado

2. **Gestionar elementos:**
   - Usar los mismos controles que los usuarios normales
   - Acceso completo a todas las instituciones

## Ventajas de las Nuevas Vistas

### Antes (Admin tradicional)
- Crear registros uno por uno
- Navegación entre páginas del admin
- Proceso lento y tedioso
- Riesgo de errores por repetición

### Ahora (Vistas masivas)
- Selección múltiple con checkboxes
- Vista clara de todos los elementos disponibles
- Acciones masivas (seleccionar/deseleccionar todas)
- Guardado en lote
- Interfaz intuitiva y moderna
- Filtros por modalidad (especialidades)
- Filtros por nivel (subgrupos)
- Visualización mejorada con letras de subgrupo destacadas

## Características Técnicas

### Seguridad
- Autenticación requerida (`@staff_member_required`)
- Validación de permisos por institución
- Tokens CSRF para protección contra ataques
- Transacciones atómicas para consistencia de datos

### Rendimiento
- Paginación (50 elementos por página)
- Consultas optimizadas con `select_related`
- Procesamiento en lote de cambios
- Respuestas AJAX para mejor experiencia de usuario

### Interfaz
- Diseño responsivo con CSS Grid
- Animaciones y transiciones suaves
- Indicadores de carga
- Mensajes de confirmación y error
- Filtros en tiempo real
- Visualización especial para subgrupos con letras destacadas

## URLs Disponibles

```python
# Gestión masiva de secciones
path('gestionar-secciones-curso-lectivo/', 
     views.gestionar_secciones_curso_lectivo, 
     name='gestionar_secciones_curso_lectivo'),

# Actualización AJAX de secciones
path('actualizar-secciones-curso-lectivo/', 
     views.actualizar_secciones_curso_lectivo, 
     name='actualizar_secciones_curso_lectivo'),

# Gestión masiva de especialidades
path('gestionar-especialidades-curso-lectivo/', 
     views.gestionar_especialidades_curso_lectivo, 
     name='gestionar_especialidades_curso_lectivo'),

# Actualización AJAX de especialidades
path('actualizar-especialidades-curso-lectivo/', 
     views.actualizar_especialidades_curso_lectivo, 
     name='actualizar_especialidades_curso_lectivo'),

# Gestión masiva de subgrupos
path('gestionar-subgrupos-curso-lectivo/', 
     views.gestionar_subgrupos_curso_lectivo, 
     name='gestionar_subgrupos_curso_lectivo'),

# Actualización AJAX de subgrupos
path('actualizar-subgrupos-curso-lectivo/', 
     views.actualizar_subgrupos_curso_lectivo, 
     name='actualizar_subgrupos_curso_lectivo'),
```

## Archivos Creados/Modificados

### Nuevos Archivos
- `config_institucional/views.py` - Vistas masivas (actualizado con subgrupos)
- `config_institucional/urls.py` - URLs de las vistas (actualizado con subgrupos)
- `config_institucional/templates/config_institucional/gestionar_secciones_curso_lectivo.html`
- `config_institucional/templates/config_institucional/gestionar_especialidades_curso_lectivo.html`
- `config_institucional/templates/config_institucional/gestionar_subgrupos_curso_lectivo.html` - **NUEVO**
- `config_institucional/templatetags/config_extras.py` - Template tags personalizados

### Archivos Modificados
- `config_institucional/admin.py` - Enlaces a vistas masivas (actualizado con subgrupos)
- `sis_colegio/urls.py` - Inclusión de URLs de config_institucional

## Compatibilidad

- **Django:** 5.2+
- **Navegadores:** Modernos con soporte para ES6+
- **Permisos:** Requiere ser staff member
- **Instituciones:** Multi-institucional con restricciones por usuario

## Notas de Implementación

1. **Template Tags:** Se creó un filtro personalizado `get_item` para acceder a valores de diccionarios en las plantillas
2. **CSRF:** Todas las operaciones AJAX incluyen tokens CSRF para seguridad
3. **Paginación:** Las vistas manejan grandes cantidades de datos con paginación eficiente
4. **Responsive:** El diseño se adapta a diferentes tamaños de pantalla
5. **Accesibilidad:** Los elementos tienen etiquetas y atributos apropiados para lectores de pantalla
6. **Subgrupos:** Visualización especial con letras destacadas y filtro por nivel educativo

## Próximas Mejoras Sugeridas

1. **Búsqueda en tiempo real** para filtrar elementos por nombre
2. **Exportación** de configuraciones a Excel/CSV
3. **Importación masiva** desde archivos
4. **Historial de cambios** para auditoría
5. **Notificaciones** por email cuando se realizan cambios masivos
6. **Plantillas predefinidas** para configuraciones comunes
7. **Sincronización automática** entre secciones, especialidades y subgrupos
8. **Validación cruzada** para asegurar consistencia entre elementos relacionados
