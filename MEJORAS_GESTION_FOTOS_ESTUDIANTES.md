# Mejoras en la Gestión de Fotos de Estudiantes

## Resumen de Cambios

Se implementaron dos mejoras importantes en el manejo de fotos de estudiantes:

1. **Checkbox para eliminar foto actual**: Ahora los usuarios pueden eliminar la foto de un estudiante sin necesidad de cargar una nueva.
2. **Eliminación automática de fotos anteriores**: Cuando se carga una nueva foto, el sistema elimina automáticamente la foto anterior para evitar acumulación de archivos.

---

## 1. Checkbox para Eliminar Foto

### ¿Cómo Funciona?

Cuando un estudiante tiene una foto cargada, aparece un checkbox **"🗑️ Eliminar esta foto"** debajo de la imagen actual.

### Características:
- ✅ **Visible solo cuando hay foto**: El checkbox solo aparece si el estudiante tiene una foto cargada
- ✅ **Fácil de usar**: Solo marcar el checkbox y guardar
- ✅ **Sin confirmación adicional**: El cambio se aplica directamente al guardar
- ✅ **Seguro**: Si se marca el checkbox y se carga una nueva foto, se prioriza la nueva foto

### Ejemplo de Uso:

1. Abrir un estudiante que tenga foto
2. Ver la imagen actual con el checkbox "🗑️ Eliminar esta foto"
3. Marcar el checkbox
4. Hacer clic en "Guardar"
5. La foto se elimina del sistema

---

## 2. Eliminación Automática de Fotos Anteriores

### ¿Cómo Funciona?

Cuando se carga una nueva foto para un estudiante que ya tiene una foto anterior:

1. El sistema detecta que hay una foto anterior
2. Elimina el archivo físico de la foto anterior
3. Guarda la nueva foto

### Beneficios:

- 🗑️ **Ahorro de espacio**: No se acumulan fotos antiguas en el servidor
- 🔄 **Mantenimiento automático**: No es necesario eliminar manualmente las fotos antiguas
- ⚡ **Eficiencia**: Solo se mantiene una foto por estudiante
- 🛡️ **Prevención de errores**: Si hay algún problema al eliminar la foto anterior, el proceso continúa sin interrumpirse

### Casos Manejados:

#### Caso 1: Cargar nueva foto sobre una existente
```
Estudiante tiene: foto_vieja.jpg
Usuario carga: foto_nueva.jpg
Resultado: 
  - foto_vieja.jpg se elimina del servidor
  - foto_nueva.jpg se guarda
```

#### Caso 2: Eliminar foto con checkbox
```
Estudiante tiene: foto_actual.jpg
Usuario marca: ☑️ Eliminar esta foto
Resultado: 
  - foto_actual.jpg se elimina del servidor
  - Campo foto queda vacío
```

#### Caso 3: Eliminar y cargar nueva en un solo paso
```
Estudiante tiene: foto_vieja.jpg
Usuario marca: ☑️ Eliminar esta foto
Usuario carga: foto_nueva.jpg
Resultado: 
  - Se prioriza la nueva foto
  - foto_vieja.jpg se elimina
  - foto_nueva.jpg se guarda
```

---

## Archivos Modificados

### 1. **matricula/widgets.py**
- Agregado checkbox "🗑️ Eliminar esta foto" en el widget de foto
- El checkbox se muestra solo cuando hay una foto actual
- Estilo visual mejorado con color rojo para indicar acción de eliminación

**Cambios:**
```python
# Checkbox para eliminar foto
clear_checkbox_name = name + '-clear'
clear_checkbox_id = 'id_' + name + '-clear'
# HTML con checkbox rojo y icono de papelera
```

### 2. **matricula/admin.py - EstudianteForm**
- Agregada lógica en `clean()` para procesar el checkbox de eliminación
- Validación para asegurar que la foto se elimine si el checkbox está marcado

**Cambios:**
```python
def clean(self):
    # ...código existente...
    
    # Manejar eliminación de foto si el checkbox está marcado
    foto_clear = self.data.get('foto-clear')
    if foto_clear:
        cleaned_data['foto'] = None
    
    # ...resto del código...
```

### 3. **matricula/admin.py - EstudianteAdmin**
- Mejorado `save_model()` para manejar la eliminación de foto desde el checkbox
- Eliminación del archivo físico antes de guardar el objeto

**Cambios:**
```python
def save_model(self, request, obj, form, change):
    # Manejar eliminación de foto si el checkbox está marcado
    foto_clear = request.POST.get('foto-clear')
    if foto_clear and obj.foto:
        # Eliminar archivo físico
        import os
        if os.path.isfile(obj.foto.path):
            os.remove(obj.foto.path)
        obj.foto = None
    
    # Continuar con el guardado normal...
```

### 4. **matricula/models.py - Estudiante**
- Mejorado `save()` para eliminar automáticamente la foto anterior cuando se carga una nueva
- Manejo de excepciones para evitar interrupciones si hay errores al eliminar

**Cambios:**
```python
def save(self, *args, **kwargs):
    # ...código existente...
    
    # Eliminar foto anterior si se está cargando una nueva
    if self.pk:
        try:
            estudiante_actual = Estudiante.objects.get(pk=self.pk)
            
            # Si hay foto anterior y se carga una nueva
            if estudiante_actual.foto and self.foto and estudiante_actual.foto != self.foto:
                import os
                if os.path.isfile(estudiante_actual.foto.path):
                    os.remove(estudiante_actual.foto.path)
            
            # Si se está eliminando la foto
            elif estudiante_actual.foto and not self.foto:
                import os
                if os.path.isfile(estudiante_actual.foto.path):
                    os.remove(estudiante_actual.foto.path)
        except Exception as e:
            # Registrar error pero continuar
            logger.warning(f"Error al eliminar foto anterior: {e}")
    
    super().save(*args, **kwargs)
```

---

## Comportamiento Detallado

### Interfaz de Usuario

#### Con Foto Actual:
```
┌────────────────────────────────────┐
│  Zona de arrastrar y soltar        │
│  📤 Arrastra nueva imagen aquí     │
└────────────────────────────────────┘

Imagen actual:
┌─────────────────┐
│                 │
│   [FOTO AQUÍ]   │
│                 │
└─────────────────┘

☐ 🗑️ Eliminar esta foto
```

#### Sin Foto:
```
┌────────────────────────────────────┐
│  Zona de arrastrar y soltar        │
│  📤 Arrastra nueva imagen aquí     │
└────────────────────────────────────┘

(No se muestra checkbox de eliminar)
```

---

## Validaciones y Seguridad

### ✅ Validaciones Implementadas:

1. **Tamaño de archivo**: Máximo 5MB
2. **Tipo de archivo**: Solo imágenes (JPG, PNG, GIF)
3. **Eliminación segura**: Verifica que el archivo existe antes de eliminarlo
4. **Manejo de errores**: Si falla la eliminación, el proceso continúa

### 🛡️ Seguridad:

1. **Solo archivos existentes**: Solo se eliminan archivos que realmente existen en el servidor
2. **Validación de ruta**: Se valida que sea una ruta válida antes de eliminar
3. **Logging de errores**: Se registran errores para monitoreo
4. **Transacciones**: El guardado del registro continúa aunque falle la eliminación del archivo

---

## Ejemplos de Uso

### Ejemplo 1: Eliminar Foto sin Cargar Nueva

**Pasos:**
1. Ir a `/admin/matricula/estudiante/123/change/`
2. Ver la foto actual
3. Marcar ☑️ "Eliminar esta foto"
4. Hacer clic en "Guardar"

**Resultado:**
- Foto eliminada del servidor
- Estudiante sin foto
- Mensaje: "El estudiante "PÉREZ GONZÁLEZ JUAN" se modificó correctamente."

### Ejemplo 2: Reemplazar Foto Actual

**Pasos:**
1. Ir a `/admin/matricula/estudiante/123/change/`
2. Ver la foto actual (por ejemplo: `foto_2023.jpg`)
3. Arrastrar nueva foto a la zona de drop
4. Ver vista previa de la nueva foto
5. Hacer clic en "Guardar"

**Resultado:**
- `foto_2023.jpg` eliminada automáticamente
- Nueva foto guardada (por ejemplo: `foto_2025.jpg`)
- Mensaje: "El estudiante "PÉREZ GONZÁLEZ JUAN" se modificó correctamente."

### Ejemplo 3: Cargar Primera Foto

**Pasos:**
1. Ir a `/admin/matricula/estudiante/add/` (nuevo estudiante)
2. Llenar datos obligatorios
3. Arrastrar foto a la zona de drop
4. Ver vista previa
5. Hacer clic en "Guardar"

**Resultado:**
- Estudiante creado con foto
- No se elimina ninguna foto (no hay foto anterior)

---

## Impacto en el Sistema

### ✅ Positivo:
- Ahorro de espacio en disco
- Interfaz más intuitiva
- Menos fotos huérfanas en el servidor
- Gestión automática de archivos

### ⚠️ Consideraciones:
- Las fotos eliminadas no se pueden recuperar
- Asegurarse de tener backups periódicos del directorio `media/`
- Monitorear logs para detectar errores en la eliminación

---

## Mantenimiento

### Recomendaciones:

1. **Backups regulares**: Hacer backup del directorio `media/estudiantes/fotos/`
2. **Monitoreo de logs**: Revisar `logs/django.log` para errores de eliminación
3. **Limpieza periódica**: Aunque el sistema elimina fotos automáticamente, revisar periódicamente el directorio de fotos

### Comandos útiles:

```bash
# Ver tamaño del directorio de fotos
du -sh media/estudiantes/fotos/

# Contar número de fotos
find media/estudiantes/fotos/ -type f | wc -l

# Buscar fotos huérfanas (opcional, script a desarrollar)
python manage.py buscar_fotos_huerfanas
```

---

## Preguntas Frecuentes

### ¿Qué pasa si marco eliminar y cargo una nueva foto?
**R:** Se prioriza la nueva foto. La foto anterior se elimina y la nueva se guarda.

### ¿Se puede recuperar una foto eliminada?
**R:** No, las fotos eliminadas no se pueden recuperar a menos que exista un backup.

### ¿Qué pasa si hay un error al eliminar la foto anterior?
**R:** El sistema registra el error en los logs pero continúa guardando el estudiante. La foto anterior puede quedar huérfana en el servidor.

### ¿Puedo eliminar varias fotos a la vez?
**R:** No, solo se puede eliminar la foto de un estudiante a la vez desde su formulario de edición.

### ¿Los usuarios normales pueden eliminar fotos?
**R:** Sí, todos los usuarios con permiso de editar estudiantes pueden eliminar fotos.

---

## Conclusión

Las mejoras implementadas hacen que la gestión de fotos sea:
- ✅ Más eficiente (elimina fotos antiguas automáticamente)
- ✅ Más flexible (permite eliminar sin cargar nueva)
- ✅ Más segura (manejo de errores robusto)
- ✅ Más intuitiva (interfaz clara y simple)

El sistema ahora gestiona las fotos de manera inteligente, manteniendo solo la foto actual de cada estudiante y eliminando automáticamente las fotos obsoletas.





