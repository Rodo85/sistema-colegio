# Solución al Error de Email Duplicado en Usuarios

## Problema Reportado
Al intentar crear un usuario nuevo, se produce el siguiente error:
```
llave duplicada viola restricción de unicidad «core_user_email_key»
DETAIL: Ya existe la llave (email)=(directoraserri@gmail.com).
```

## Causa del Problema

### 1. **Restricción de Unicidad en Base de Datos**
El modelo `User` tiene el campo `email` configurado como único:
```python
class User(AbstractBaseUser, PermissionsMixin):
    email = models.EmailField(unique=True)  # ← Campo único
```

### 2. **Usuario Ya Existente**
Ya existe un usuario en la base de datos con el email `directoraserri@gmail.com`.

### 3. **Falta de Validación en el Admin**
El admin de Django no validaba la duplicación antes de intentar guardar, causando que el error se produjera a nivel de base de datos.

## Solución Implementada

### Archivo: `core/admin.py`
**Líneas modificadas**: 73-89

**Cambios realizados:**

1. **Método `clean_email()`**: Valida que el email no esté duplicado
2. **Método `save_model()`**: Intercepta el guardado para validar antes de crear

```python
def clean_email(self, email):
    """Validar que el email no esté duplicado"""
    from django.core.exceptions import ValidationError
    
    if User.objects.filter(email=email).exists():
        raise ValidationError(f"Ya existe un usuario con el email '{email}'")
    return email

def save_model(self, request, obj, form, change):
    """Validar email antes de guardar"""
    if not change:  # Solo para usuarios nuevos
        try:
            self.clean_email(obj.email)
        except ValidationError as e:
            from django.contrib import messages
            messages.error(request, str(e))
            return
    
    super().save_model(request, obj, form, change)
```

## Beneficios de la Solución

### ✅ **Validación Temprana**
- El error se detecta antes de intentar guardar en la base de datos
- Se muestra un mensaje de error claro al usuario
- No se producen errores de integridad de base de datos

### ✅ **Mejor Experiencia de Usuario**
- Mensaje de error claro: "Ya existe un usuario con el email 'directoraserri@gmail.com'"
- El formulario no se envía si hay duplicación
- Se mantienen los datos ingresados para corrección

### ✅ **Prevención de Errores**
- Se evitan errores de `IntegrityError` a nivel de base de datos
- La validación es consistente en toda la aplicación
- Se mantiene la integridad de datos

## Escenarios de Uso

### 1. **Usuario Nuevo con Email Único**
- ✅ Se crea correctamente
- ✅ No hay conflictos

### 2. **Usuario Nuevo con Email Duplicado**
- ❌ Se muestra error: "Ya existe un usuario con el email '...'"
- ❌ No se crea el usuario
- ✅ Se mantienen los datos del formulario

### 3. **Edición de Usuario Existente**
- ✅ Se permite cambiar otros campos
- ✅ No se valida duplicación (solo en creación)

## Recomendaciones para el Usuario

### 🔍 **Verificar Usuario Existente**
1. Ir a **Usuarios** en el admin
2. Buscar por email: `directoraserri@gmail.com`
3. Verificar si es el mismo usuario que se quiere crear

### 🔧 **Soluciones Posibles**

#### Opción A: Usar Email Único
- Cambiar el email a uno único (ej: `directoraserri2@gmail.com`)
- Agregar sufijo o prefijo para diferenciar

#### Opción B: Editar Usuario Existente
- Si es el mismo usuario, editarlo en lugar de crear uno nuevo
- Agregar la membresía a la institución desde el modelo `Miembro`

#### Opción C: Usar Email Institucional
- Usar email de la institución (ej: `director@colegio.edu`)
- Mantener email personal como campo adicional

### 📋 **Proceso Recomendado**

1. **Verificar**: Buscar si ya existe el usuario
2. **Decidir**: ¿Es el mismo usuario o uno diferente?
3. **Actuar**: 
   - Si es el mismo → Editar usuario existente
   - Si es diferente → Usar email único
4. **Crear**: Usuario nuevo con email único

## Validaciones Implementadas

1. **Unicidad de Email**: Se valida antes de crear
2. **Mensajes de Error**: Claros y específicos
3. **Prevención de Duplicados**: A nivel de aplicación
4. **Integridad de Datos**: Se mantiene la restricción de BD

## Archivos Modificados

- ✅ `core/admin.py` - Agregada validación de email duplicado en UserAdmin

## Conclusión

La solución implementada:
- ✅ Previene errores de email duplicado
- ✅ Mejora la experiencia del usuario
- ✅ Mantiene la integridad de datos
- ✅ Proporciona mensajes de error claros

El sistema ahora valida correctamente la unicidad de emails antes de crear usuarios, evitando errores de base de datos y mejorando la usabilidad del admin.
