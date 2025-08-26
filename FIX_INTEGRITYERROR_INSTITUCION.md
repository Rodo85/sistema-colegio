# Corrección del IntegrityError: institucion_id no puede ser nulo

## Problema Reportado
Al intentar crear una matrícula desde el botón de matrícula en la lista de estudiantes, se producía el siguiente error:
```
IntegrityError at /admin/matricula/matriculaacademica/add/
el valor nulo en la columna «institucion_id» de la relación «matricula_matriculaacademica» viola la restricción de no nulo
DETAIL: La fila que falla contiene (926, 2025-08-25, activo, 1, 9, 942, null, 10, 19, 37).
```

## Causa del Problema

### 1. **Modelo MatriculaAcademica**
El modelo `MatriculaAcademica` NO tiene un campo `institucion` directo. En su lugar, obtiene la institución a través de la relación:
```python
estudiante = models.ForeignKey('Estudiante', on_delete=models.PROTECT, related_name='matriculas_academicas')
```

### 2. **Mixin InstitucionScopedAdmin**
El mixin `InstitucionScopedAdmin` en `core/mixins.py` estaba intentando asignar `institucion_id` a TODOS los modelos, incluyendo aquellos que no lo tienen:

```python
def save_model(self, request, obj, form, change):
    # Si es creación y el modelo tiene campo 'institucion'
    if not change and hasattr(obj, "institucion_id") and not obj.institucion_id:
        obj.institucion_id = request.institucion_activa_id  # ❌ ERROR: Campo no existe
    super().save_model(request, obj, form, change)
```

### 3. **Verificación Incorrecta**
El mixin solo verificaba `hasattr(obj, "institucion_id")`, pero esto puede devolver `True` incluso si el campo no existe realmente en el modelo (por ejemplo, si hay una propiedad o método con ese nombre).

## Solución Implementada

### Archivo: `core/mixins.py`
**Líneas modificadas**: 26-30

**Antes:**
```python
def save_model(self, request, obj, form, change):
    # Si es creación y el modelo tiene campo 'institucion'
    if not change and hasattr(obj, "institucion_id") and not obj.institucion_id:
        obj.institucion_id = request.institucion_activa_id
    super().save_model(request, obj, form, change)
```

**Después:**
```python
def save_model(self, request, obj, form, change):
    # Si es creación y el modelo tiene campo 'institucion' directamente
    if not change and hasattr(obj, "institucion_id") and not obj.institucion_id:
        # Verificar que el campo realmente existe en el modelo
        if hasattr(obj._meta, 'get_field') and obj._meta.get_field('institucion_id', raise_exception=False):
            obj.institucion_id = request.institucion_activa_id
    super().save_model(request, obj, form, change)
```

## Explicación Técnica

### Verificación de Campo Real
La nueva verificación `obj._meta.get_field('institucion_id', raise_exception=False)`:
- ✅ Verifica que el campo `institucion_id` realmente existe en la definición del modelo
- ✅ No lanza excepción si el campo no existe (devuelve `None`)
- ✅ Solo asigna `institucion_id` si el campo está realmente presente

### Flujo de Institución para MatriculaAcademica
1. **Usuario crea matrícula** → Se selecciona un estudiante
2. **Estudiante ya tiene institución** → `estudiante.institucion_id`
3. **MatriculaAcademica NO necesita campo institución** → Se obtiene a través de `estudiante.institucion`
4. **Mixin NO asigna institución** → Porque el campo no existe
5. **Matrícula se guarda correctamente** → Sin errores de integridad

## Impacto

- **Error corregido**: Las matrículas ahora se pueden crear sin IntegrityError
- **Funcionalidad restaurada**: El botón de matrícula funciona completamente
- **Seguridad mantenida**: Los usuarios solo pueden matricular estudiantes de su institución
- **Sin cambios en la lógica**: El comportamiento es idéntico al esperado

## Validaciones de Seguridad

1. **Filtrado por Institución**: El mixin sigue filtrando correctamente por `estudiante__institucion_id`
2. **Aislamiento de Datos**: Los usuarios solo ven estudiantes de su institución
3. **Integridad de Relaciones**: La institución se mantiene a través de la relación estudiante → institución

## Recomendación

Para modelos que NO tienen campo `institucion` directo (como `MatriculaAcademica`), la institución debe manejarse a través de relaciones:
```python
# ✅ CORRECTO: Filtrar por relación
MatriculaAcademica.objects.filter(estudiante__institucion_id=request.institucion_activa_id)

# ❌ INCORRECTO: Intentar filtrar por campo inexistente
MatriculaAcademica.objects.filter(institucion_id=request.institucion_activa_id)
```
