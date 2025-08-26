# Corrección del FieldError: Cannot resolve keyword 'activa'

## Problema Reportado
Al hacer clic en "Matrículas Académicas" en el menú Matrícula, se producía el siguiente error:
```
FieldError at /admin/matricula/matriculaacademica/
Cannot resolve keyword 'activa' into field.
```

## Causa del Problema
El error ocurría porque en `matricula/admin.py`, el filtro `InstitucionMatriculaFilter` intentaba filtrar instituciones usando:
```python
Institucion.objects.filter(activa=True)
```

Sin embargo, en el modelo `Institucion` (en `core/models.py`), `activa` NO es un campo de la base de datos, sino una propiedad calculada:
```python
@property
def activa(self):
    from django.utils import timezone
    return self.fecha_fin >= timezone.now().date()
```

Las propiedades `@property` no se pueden usar en filtros de QuerySet de Django porque no existen en la base de datos.

## Solución Implementada

### Archivo: `matricula/admin.py`
**Líneas modificadas**: 98-108

**Antes:**
```python
def lookups(self, request, model_admin):
    if not request.user.is_superuser:
        return []
    
    from core.models import Institucion
    instituciones = Institucion.objects.filter(activa=True).order_by('nombre')
    return [(inst.id, inst.nombre) for inst in instituciones]
```

**Después:**
```python
def lookups(self, request, model_admin):
    if not request.user.is_superuser:
        return []
    
    from core.models import Institucion
    from django.utils import timezone
    # Filtrar instituciones activas usando fecha_fin >= hoy
    instituciones = Institucion.objects.filter(
        fecha_fin__gte=timezone.now().date()
    ).order_by('nombre')
    return [(inst.id, inst.nombre) for inst in instituciones]
```

## Explicación Técnica

La propiedad `activa` en el modelo `Institucion` verifica si `fecha_fin >= timezone.now().date()`. Por lo tanto, para obtener el mismo resultado en un filtro de QuerySet, debemos usar directamente:
```python
fecha_fin__gte=timezone.now().date()
```

Esto:
- ✅ Funciona correctamente con el ORM de Django
- ✅ Se ejecuta directamente en la base de datos (más eficiente)
- ✅ Produce el mismo resultado que la propiedad `activa`

## Impacto

- **Funcionalidad restaurada**: El listado de Matrículas Académicas ahora carga correctamente
- **Filtro mejorado**: El filtro de instituciones para superusuarios ahora funciona correctamente
- **Sin cambios en la lógica**: El comportamiento es idéntico al esperado, solo se cambió la implementación

## Pruebas Realizadas

Se verificó que:
1. ✅ El filtro identifica correctamente las instituciones activas (fecha_fin >= hoy)
2. ✅ Las instituciones con fecha_fin < hoy no aparecen en el filtro
3. ✅ Las instituciones con fecha_fin = hoy SÍ aparecen (están activas)
4. ✅ El listado de Matrículas Académicas carga sin errores

## Recomendación

Para evitar este error en el futuro, cuando se necesite filtrar por el estado activo de una institución, usar siempre:
```python
# ✅ CORRECTO
Institucion.objects.filter(fecha_fin__gte=timezone.now().date())

# ❌ INCORRECTO (causa FieldError)
Institucion.objects.filter(activa=True)
```
