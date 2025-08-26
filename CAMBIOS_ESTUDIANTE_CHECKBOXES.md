# Cambios en Modelo Estudiante - Checkboxes y Auto-completado

## Cambios Implementados

### 1. **Campos Booleanos Simplificados**
**Archivo**: `matricula/models.py`

Los siguientes campos ahora son simples checkboxes sin opción NULL:

#### Antes:
```python
ed_religiosa = models.BooleanField("Recibe Ed. Religiosa", blank=True, null=True)
presenta_enfermedad = models.BooleanField("Presenta alguna enfermedad", blank=True, null=True)
autoriza_derecho_imagen = models.BooleanField("Autoriza derecho de imagen", blank=True, null=True)
```

#### Después:
```python
ed_religiosa = models.BooleanField("Recibe Ed. Religiosa", default=False)
presenta_enfermedad = models.BooleanField("Presenta alguna enfermedad", default=False)
autoriza_derecho_imagen = models.BooleanField("Autoriza derecho de imagen", default=False)
```

### 2. **Auto-completado de "Vence Póliza"**
**Archivo**: `matricula/models.py`

Se agregó lógica automática para completar la fecha de vencimiento de póliza:

```python
# Auto-completar "Vence Póliza" un año después de "Rige Póliza"
if self.rige_poliza and not self.vence_poliza:
    from datetime import date
    # Calcular un año después
    vence_anio = self.rige_poliza.year + 1
    vence_mes = self.rige_poliza.month
    vence_dia = self.rige_poliza.day
    
    # Manejar años bisiestos (29 de febrero)
    try:
        self.vence_poliza = date(vence_anio, vence_mes, vence_dia)
    except ValueError:
        # Si es 29 de febrero en año no bisiesto, usar 28 de febrero
        self.vence_poliza = date(vence_anio, vence_mes, 28)
```

## Beneficios de los Cambios

### ✅ **Checkboxes Simplificados**
- **Sin opción NULL**: Los campos booleanos ahora solo tienen dos estados: True/False
- **Valor por defecto**: Todos los campos booleanos tienen `default=False`
- **Interfaz más clara**: Solo checkboxes, sin opciones confusas
- **Datos más consistentes**: No hay estados intermedios o indefinidos

### ✅ **Auto-completado de Fechas**
- **Ahorro de tiempo**: No hay que calcular manualmente la fecha de vencimiento
- **Precisión**: Se calcula exactamente un año después
- **Manejo de años bisiestos**: Se resuelve automáticamente el caso del 29 de febrero
- **Solo cuando es necesario**: Solo se auto-completa si no hay fecha de vencimiento

## Comportamiento de los Campos

### 🔘 **Recibe Ed. Religiosa**
- **Default**: `False` (no marcado)
- **Comportamiento**: Checkbox simple
- **Uso**: Marcar si el estudiante recibe educación religiosa

### 🔘 **Presenta alguna enfermedad**
- **Default**: `False` (no marcado)
- **Comportamiento**: Checkbox simple
- **Uso**: Marcar si el estudiante tiene alguna condición médica
- **Relacionado**: Si se marca, se debe completar "Detalle de enfermedad"

### 🔘 **Autoriza derecho de imagen**
- **Default**: `False` (no marcado)
- **Comportamiento**: Checkbox simple
- **Uso**: Marcar si se autoriza el uso de la imagen del estudiante

### 📅 **Rige Póliza**
- **Comportamiento**: Campo de fecha editable
- **Uso**: Fecha desde cuando rige la póliza de seguro

### 📅 **Vence Póliza**
- **Comportamiento**: Se auto-completa un año después de "Rige Póliza"
- **Editable**: Se puede modificar manualmente si es necesario
- **Lógica**: 
  - Si se establece "Rige Póliza" y no hay "Vence Póliza" → Se calcula automáticamente
  - Si ya hay "Vence Póliza" → No se modifica
  - Si se cambia "Rige Póliza" → Se puede recalcular manualmente

## Ejemplos de Uso

### 📝 **Crear Estudiante Nuevo**
1. Marcar checkbox "Recibe Ed. Religiosa" si aplica
2. Marcar checkbox "Presenta alguna enfermedad" si aplica
3. Marcar checkbox "Autoriza derecho de imagen" si aplica
4. Establecer fecha "Rige Póliza"
5. **"Vence Póliza" se completa automáticamente**

### 📝 **Editar Estudiante Existente**
1. Cambiar estado de checkboxes según sea necesario
2. Modificar "Rige Póliza" si es necesario
3. **"Vence Póliza" se mantiene** (no se recalcula automáticamente)

### 📅 **Ejemplo de Fechas**
- **Rige Póliza**: 15 de marzo de 2025
- **Vence Póliza**: 15 de marzo de 2026 (auto-calculado)

## Casos Especiales

### 🗓️ **Años Bisiestos**
- **Entrada**: 29 de febrero de 2024 (año bisiesto)
- **Salida**: 28 de febrero de 2025 (año no bisiesto)
- **Lógica**: Se maneja automáticamente para evitar errores de fecha

### 📅 **Fechas de Fin de Mes**
- **Entrada**: 31 de enero de 2025
- **Salida**: 31 de enero de 2026
- **Lógica**: Se mantiene el día exacto cuando es posible

## Impacto en la Base de Datos

### 🔄 **Migración Necesaria**
Los cambios en los campos booleanos requieren una migración de Django para:
- Cambiar `null=True` a `default=False`
- Actualizar registros existentes con NULL a False

### 📊 **Datos Existentes**
- **Campos booleanos**: Se convertirán de NULL a False
- **Fechas de póliza**: No se verán afectadas
- **Nuevos registros**: Tendrán valores por defecto apropiados

## Recomendaciones de Uso

### ✅ **Mejores Prácticas**
1. **Siempre marcar los checkboxes** según corresponda
2. **Establecer "Rige Póliza"** para activar el auto-completado
3. **Verificar "Vence Póliza"** después de establecer "Rige Póliza"
4. **Revisar "Detalle de enfermedad"** si se marca "Presenta alguna enfermedad"

### ⚠️ **Consideraciones**
1. **Los checkboxes ahora son obligatorios** (siempre tienen un valor)
2. **"Vence Póliza" solo se auto-completa** en la creación inicial
3. **Se puede editar manualmente** cualquier fecha si es necesario

## Conclusión

Los cambios implementados:
- ✅ Simplifican la interfaz de usuario con checkboxes claros
- ✅ Eliminan la confusión de campos NULL en booleanos
- ✅ Automatizan el cálculo de fechas de vencimiento de póliza
- ✅ Mejoran la consistencia de datos
- ✅ Reducen errores de entrada de datos

El sistema ahora es más intuitivo y eficiente para la gestión de estudiantes.
