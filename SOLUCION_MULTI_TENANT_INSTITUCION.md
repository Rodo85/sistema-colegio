# Solución al Problema de Multi-Tenancy - Reconocimiento de Institución

## Problema Identificado

El sistema multi-tenant tenía varios problemas que impedían el correcto reconocimiento de la institución logueada:

1. **Referencias incorrectas en vistas**: Se usaba `request.institucion_activa` en lugar de `request.institucion_activa_id`
2. **Modelo faltante**: No existía el modelo `SubAreaInstitucion` para manejar subáreas por institución
3. **Validaciones incompletas**: Faltaban validaciones para asegurar que los elementos pertenezcan a la institución correcta
4. **Context processor faltante**: No había un context processor para hacer disponible la institución activa en todas las plantillas

## Soluciones Implementadas

### 1. Context Processor para Institución Activa

Se creó `core/context_processors.py` que hace disponible la institución activa en todas las plantillas:

```python
def institucion_activa(request):
    """
    Context processor que hace disponible la institución activa
    en todas las plantillas y vistas.
    """
    if hasattr(request, 'institucion_activa_id') and request.institucion_activa_id:
        try:
            institucion = Institucion.objects.get(pk=request.institucion_activa_id)
            return {
                'institucion_activa': institucion,
                'institucion_activa_id': request.institucion_activa_id
            }
        except Institucion.DoesNotExist:
            pass
    
    return {
        'institucion_activa': None,
        'institucion_activa_id': None
    }
```

### 2. Decorador para Asegurar Institución Activa

Se creó el decorador `ensure_institucion_activa` que asigna automáticamente la institución activa sin redirigir:

```python
@ensure_institucion_activa
def gestionar_secciones_curso_lectivo(request):
    # La institución activa estará disponible en request.institucion_activa_id
```

### 3. Modelo SubAreaInstitucion

Se creó el modelo para manejar las subáreas por institución:

```python
class SubAreaInstitucion(models.Model):
    institucion = models.ForeignKey('core.Institucion', on_delete=models.CASCADE)
    subarea = models.ForeignKey(SubArea, on_delete=models.PROTECT)
    activa = models.BooleanField(default=True)
    
    class Meta:
        unique_together = ("institucion", "subarea")
```

### 4. Corrección de Vistas

Se corrigieron las vistas para usar correctamente la institución activa:

```python
# ANTES (INCORRECTO)
institucion = request.institucion_activa

# DESPUÉS (CORRECTO)
if hasattr(request, 'institucion_activa_id') and request.institucion_activa_id:
    try:
        institucion = Institucion.objects.get(pk=request.institucion_activa_id)
    except Institucion.DoesNotExist:
        institucion = None
else:
    institucion = None
```

### 5. Validaciones Corregidas

Se implementaron validaciones correctas en el modelo Clase:

```python
def clean(self):
    # Validar que la subárea esté habilitada para esta institución
    if self.subarea_id and self.institucion_id:
        from catalogos.models import SubAreaInstitucion
        subarea_habilitada = SubAreaInstitucion.objects.filter(
            institucion=self.institucion,
            subarea=self.subarea,
            activa=True
        ).exists()
        if not subarea_habilitada:
            raise ValidationError("Esta subárea no está habilitada para esta institución.")
```

## Comandos de Gestión Creados

### 1. Crear Subáreas por Institución

```bash
# Ver qué se haría sin ejecutar cambios
python manage.py crear_subareas_institucion --dry-run

# Crear configuraciones para todas las instituciones
python manage.py crear_subareas_institucion

# Crear solo para una institución específica
python manage.py crear_subareas_institucion --institucion "NOMBRE_INSTITUCION"
```

### 2. Crear Configuraciones de Curso Lectivo

```bash
# Ver qué se haría sin ejecutar cambios
python manage.py crear_configuraciones_curso_lectivo --dry-run

# Crear configuraciones para todos los cursos lectivos activos
python manage.py crear_configuraciones_curso_lectivo

# Crear solo para un curso lectivo específico
python manage.py crear_configuraciones_curso_lectivo --curso-lectivo 2025
```

## Pasos para Aplicar la Solución

### 1. Crear y Aplicar Migraciones

```bash
python manage.py makemigrations catalogos
python manage.py makemigrations config_institucional
python manage.py migrate
```

### 2. Crear Configuraciones Iniciales

```bash
# Crear subáreas por institución
python manage.py crear_subareas_institucion

# Crear configuraciones de curso lectivo
python manage.py crear_configuraciones_curso_lectivo
```

### 3. Verificar Funcionamiento

1. Iniciar sesión con un usuario de una institución
2. Verificar que la institución se reconozca correctamente
3. Probar la creación de especialidades, secciones y subgrupos por curso lectivo
4. Verificar que solo se muestren los elementos de la institución correcta

## Archivos Modificados

- `core/context_processors.py` - Nuevo context processor
- `core/decorators.py` - Nuevo decorador `ensure_institucion_activa`
- `catalogos/models.py` - Nuevo modelo `SubAreaInstitucion`
- `catalogos/admin.py` - Admin para `SubAreaInstitucion`
- `config_institucional/views.py` - Vistas corregidas
- `config_institucional/models.py` - Validaciones corregidas
- `config_institucional/admin.py` - Admin corregido
- `sis_colegio/settings.py` - Context processor agregado
- `core/management/commands/` - Comandos de gestión

## Verificación de la Solución

Después de aplicar todos los cambios:

1. **Middleware**: El middleware asigna correctamente `request.institucion_activa_id`
2. **Context Processor**: La institución activa está disponible en todas las plantillas
3. **Decoradores**: Las vistas tienen acceso garantizado a la institución activa
4. **Validaciones**: Los modelos validan que los elementos pertenezcan a la institución correcta
5. **Admin**: Los formularios del admin filtran correctamente por institución

## Notas Importantes

- Los cambios son compatibles con el código existente
- Se mantiene la funcionalidad para superusuarios
- Las validaciones son robustas y manejan errores graciosamente
- Los comandos de gestión permiten crear configuraciones masivamente
- El sistema es escalable para múltiples instituciones

## Próximos Pasos Recomendados

1. **Monitoreo**: Verificar que no haya errores en los logs
2. **Testing**: Probar todas las funcionalidades del catálogo institucional
3. **Performance**: Monitorear el rendimiento con múltiples instituciones
4. **Documentación**: Actualizar la documentación del usuario final
5. **Backup**: Hacer backup antes de aplicar en producción