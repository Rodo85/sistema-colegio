# Corrección del Botón de Matrícula en Lista de Estudiantes

## Problema Reportado
El usuario reportó que al hacer clic en el botón de matrícula en la lista de estudiantes, se producían errores.

## Cambios Implementados

### 1. **matricula/admin.py - EstudianteAdmin**

#### Método `get_list_display()`
- **Cambio**: Ahora guarda el `request` en `self._request` para poder usarlo en el método `acciones()`
- **Razón**: El método `acciones()` necesita acceso al request para determinar si el usuario es superusuario y obtener la institución activa

```python
def get_list_display(self, request):
    # Guardar el request para usarlo en acciones
    self._request = request
    base_display = ("identificacion", "primer_apellido", "segundo_apellido", "nombres", "tipo_estudiante", "acciones")
    return base_display
```

#### Método `acciones()`
- **Cambios**:
  1. Usa `reverse()` para generar URLs dinámicamente
  2. Agrega el parámetro `_institucion` para usuarios no superusuarios
  3. Mejora el estilo del botón con CSS inline
  4. Agrega `allow_tags = True` para permitir HTML

```python
def acciones(self, obj):
    if obj.pk:
        url = reverse('admin:matricula_matriculaacademica_add')
        url += f'?estudiante={obj.pk}'
        
        # Si no es superusuario, agregar la institución
        if hasattr(self, '_request') and not self._request.user.is_superuser:
            institucion_id = getattr(self._request, 'institucion_activa_id', None)
            if institucion_id:
                url += f'&_institucion={institucion_id}'
        
        return format_html(
            '<a class="button" href="{}" style="...">📚 Matrícula</a>',
            url
        )
```

### 2. **matricula/admin.py - MatriculaAcademicaAdmin**

#### Método `get_form()`
- **Cambio**: Mejorado para pasar el request al formulario y validar que el estudiante pertenece a la institución del usuario
- **Razón**: Asegurar que los usuarios solo pueden matricular estudiantes de su propia institución

```python
def get_form(self, request, obj=None, **kwargs):
    # Crear formulario con request incluido
    class FormWithRequest(Form):
        def __init__(self, *args, **kwargs):
            kwargs['request'] = request
            super().__init__(*args, **kwargs)
    
    # Validar estudiante según permisos del usuario
    if not request.user.is_superuser:
        institucion_id = getattr(request, 'institucion_activa_id', None)
        if institucion_id:
            estudiante = Estudiante.objects.get(pk=estudiante_id, institucion_id=institucion_id)
```

### 3. **matricula/forms.py - MatriculaAcademicaForm**

#### Método `__init__()`
- **Cambio**: Acepta y guarda el request para poder acceder a la institución activa
- **Razón**: Permite filtrar especialidades según la institución del usuario

```python
def __init__(self, *args, **kwargs):
    # Extraer el request si viene en kwargs
    self.request = kwargs.pop('request', None)
    super().__init__(*args, **kwargs)
```

## Comportamiento del Botón

### Para Usuarios Normales (No Superusuarios)
- URL generada: `/admin/matricula/matriculaacademica/add/?estudiante=123&_institucion=1`
- El parámetro `_institucion` asegura que la matrícula se cree en la institución correcta
- Solo pueden ver y matricular estudiantes de su propia institución

### Para Superusuarios
- URL generada: `/admin/matricula/matriculaacademica/add/?estudiante=123`
- No se incluye el parámetro `_institucion` porque pueden trabajar con cualquier institución
- Pueden ver y matricular estudiantes de cualquier institución

## Validaciones de Seguridad

1. **Filtrado por Institución**: Los usuarios normales solo ven estudiantes de su institución
2. **Validación en el Formulario**: Se verifica que el estudiante pertenece a la institución del usuario
3. **Request en Contexto**: El request se pasa correctamente al formulario para mantener el contexto de seguridad

## Pruebas Realizadas

Se crearon scripts de prueba que verificaron:
- ✅ Generación correcta de URLs con parámetros
- ✅ Diferenciación entre usuarios normales y superusuarios
- ✅ Inclusión del parámetro `_institucion` solo cuando es necesario
- ✅ Manejo correcto de casos sin estudiante (obj.pk = None)

## Impacto

- **Usuarios afectados**: Todos los usuarios del sistema que gestionan matrículas
- **Funcionalidad mejorada**: El botón de matrícula ahora funciona correctamente y respeta las reglas de multi-institucionalidad
- **Seguridad**: Se mantiene el aislamiento de datos entre instituciones
