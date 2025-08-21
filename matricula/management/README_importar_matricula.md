# 📚 Comando de Importación Completa de Matrícula

## 🎯 Descripción

El comando `importar_matricula` es una herramienta robusta y completa para importar datos de matrícula desde archivos CSV a la base de datos PostgreSQL. Este comando procesa **estudiantes**, **encargados** y **matrícula académica** en una sola operación, manteniendo la integridad referencial y la atomicidad de los datos.

## 🚀 Características Principales

### ✅ **Atomicidad Completa**
- Cada fila del CSV se procesa dentro de una transacción de base de datos
- Si falla cualquier parte de una fila, se revierte toda la operación para esa fila
- Evita datos corruptos o inconsistentes

### 🔄 **Patrón "Get or Create" Inteligente**
- **Catálogos**: Busca valores existentes antes de crear nuevos
- **Personas**: Actualiza si existe, crea si no existe
- **Matrículas**: Mantiene historial y evita duplicados

### 🧹 **Limpieza y Validación Automática**
- Maneja nombres de columnas con espacios, tildes y caracteres especiales
- Limpia datos sucios (espacios, NaN, formatos mixtos)
- Valida cédulas costarricenses (9 dígitos)
- Procesa múltiples formatos de fecha

### 📊 **Feedback Detallado**
- Progreso en tiempo real
- Estadísticas completas de la operación
- Manejo de errores y advertencias
- Modo verbose para debugging

## 📋 Requisitos del Archivo CSV

### 🔴 **Columnas Obligatorias**

#### **Estudiante:**
- `cedula de estudiante` - 9 dígitos sin guiones
- `1er apellido estudiante` - Primer apellido
- `2do apellido estudiante` - Segundo apellido (puede estar vacío)
- `Nombre estudiante2` - Nombres del estudiante
- `Fecha nacimiento` - Fecha en formato DD/MM/YYYY o YYYY-MM-DD
- `id_Genero` - Género (M, F, Masculino, Femenino, 1, 2)
- `id_nacionalidad` - Nacionalidad (Costarricense, etc.)

#### **Encargado:**
- `cedula encargado` - 9 dígitos sin guiones
- `Nombre encargado` - Nombre completo del encargado
- `Parentesco` - Relación con el estudiante (Madre, Padre, etc.)

#### **Matrícula:**
- `Nivel que Matricula` - Nivel académico (ej: "9 (Noveno)")
- `SecciónMatricular` - Sección (ej: "9-4")

### 🟡 **Columnas Opcionales**

#### **Ubicación:**
- `Provincia Residencia` - Nombre de la provincia
- `id_canton` - Nombre del cantón
- `id_didistrito` - Nombre del distrito
- `Direccion exacta` - Dirección completa

#### **Contacto:**
- `Telefono estudiante` - Teléfono del estudiante
- `Telefono casa` - Teléfono de la casa
- `Correo electronico` - Correo electrónico

#### **Encargado:**
- `Estado civil` - Estado civil del encargado
- `Escolaridad` - Nivel de escolaridad
- `Ocupacion` - Ocupación del encargado
- `Teléfono encargado` - Teléfono del encargado
- `Lugar de trabajo` - Lugar de trabajo
- `Telefono del trabajo` - Teléfono del trabajo
- `Vive con el estudiante` - Si/No

#### **Matrícula:**
- `Especialidad` - Especialidad (solo niveles 10, 11, 12)

## 🛠️ Uso del Comando

### **Sintaxis Básica:**
```bash
python manage.py importar_matricula <archivo.csv>
```

### **Parámetros Disponibles:**

#### **Argumentos Posicionales:**
- `archivo` - Ruta al archivo CSV (obligatorio)

#### **Argumentos Opcionales:**
- `--institucion-id <id>` - ID de la institución específica
- `--dry-run` - Solo validar, no guardar en la base de datos
- `--verbose, -v` - Mostrar información detallada del proceso

### **Ejemplos de Uso:**

#### **1. Validación sin Guardar (Recomendado para pruebas):**
```bash
python manage.py importar_matricula estudiantes.csv --dry-run --verbose
```

#### **2. Importación Real:**
```bash
python manage.py importar_matricula estudiantes.csv --verbose
```

#### **3. Importación a Institución Específica:**
```bash
python manage.py importar_matricula estudiantes.csv --institucion-id 2 --verbose
```

#### **4. Importación Silenciosa:**
```bash
python manage.py importar_matricula estudiantes.csv
```

## 📊 Estructura de Salida

### **Progreso en Tiempo Real:**
```
🚀 Iniciando importación de matrícula desde: estudiantes.csv
✅ Archivo leído: 1000 filas, 35 columnas
✅ Estructura del archivo válida
🏢 Usando institución: COLEGIO MÁXIMO QUESADA
📝 Procesando fila 2: 120470190
🆕 Estudiante creado: 120470190
🆕 Encargado creado: 303600123
🔗 Relación creada: 120470190 - 303600123
🎓 Matrícula creada: 120470190 - Nivel 9
...
```

### **Resumen Final:**
```
============================================================
📊 RESUMEN COMPLETO DE IMPORTACIÓN DE MATRÍCULA
============================================================

📈 ESTADÍSTICAS GENERALES:
   • Total de filas procesadas: 1000
   • Filas procesadas exitosamente: 998
   • Errores encontrados: 2
   • Advertencias: 5

👨‍🎓 ESTUDIANTES:
   • Creados: 850
   • Actualizados: 148
   • Total: 998

👨‍👩‍👧‍👦 ENCARGADOS:
   • Creados: 920
   • Actualizados: 78
   • Total: 998

🎓 MATRÍCULAS ACADÉMICAS:
   • Creadas: 850
   • Actualizadas: 148
   • Total: 998

🎯 RESUMEN FINAL:
   ⚠️ Importación completada con algunos errores
============================================================
```

## 🔧 Funcionalidades Técnicas

### **Manejo de Transacciones:**
- Cada fila se procesa en una transacción atómica
- Rollback automático si falla cualquier operación
- Consistencia de datos garantizada

### **Procesamiento de Catálogos:**
- Búsqueda insensible a mayúsculas/minúsculas
- Creación automática de valores faltantes
- Manejo de relaciones jerárquicas (Provincia → Cantón → Distrito)

### **Validación de Datos:**
- Cédulas costarricenses (9 dígitos)
- Formatos de fecha múltiples
- Campos obligatorios verificados
- Limpieza automática de texto

### **Manejo de Errores:**
- Errores críticos detienen la fila
- Advertencias no detienen el proceso
- Logging detallado para debugging
- Continuación con otras filas si es posible

## ⚠️ Consideraciones Importantes

### **Antes de la Importación:**
1. **Hacer backup** de la base de datos
2. **Probar con `--dry-run`** primero
3. **Verificar** que el CSV tenga la estructura correcta
4. **Revisar** que existan los catálogos básicos

### **Durante la Importación:**
1. **No interrumpir** el proceso
2. **Monitorear** los logs de error
3. **Verificar** el progreso en tiempo real

### **Después de la Importación:**
1. **Revisar** el resumen final
2. **Verificar** que los datos se importaron correctamente
3. **Revisar** errores y advertencias
4. **Hacer backup** de la nueva base de datos

## 🐛 Solución de Problemas

### **Error: "Columnas faltantes"**
- Verificar que el CSV tenga todas las columnas obligatorias
- Revisar nombres exactos de las columnas
- Usar `--verbose` para ver el mapeo de columnas

### **Error: "Cédula inválida"**
- Verificar que las cédulas tengan 9 dígitos
- Remover guiones y espacios
- Verificar que no haya caracteres especiales

### **Error: "Fecha inválida"**
- Verificar formato de fecha en el CSV
- Usar formato DD/MM/YYYY o YYYY-MM-DD
- Verificar que no haya fechas futuras

### **Error: "Nivel no encontrado"**
- Verificar que el nivel exista en los catálogos
- Crear el nivel en `catalogos.Nivel` si no existe
- Verificar que el número del nivel sea correcto

## 📈 Rendimiento

### **Optimizaciones Implementadas:**
- Transacciones por fila (no por archivo completo)
- Uso de `update_or_create` para evitar duplicados
- Búsquedas optimizadas en catálogos
- Manejo eficiente de memoria

### **Tiempos Estimados:**
- **100 filas**: ~30 segundos
- **1,000 filas**: ~5 minutos
- **10,000 filas**: ~45 minutos
- **100,000 filas**: ~6 horas

### **Recomendaciones:**
- Usar `--dry-run` para archivos grandes
- Procesar en lotes si es posible
- Monitorear uso de memoria
- Hacer backup antes de archivos grandes

## 🔒 Seguridad

### **Validaciones Implementadas:**
- Sanitización de entrada
- Validación de tipos de datos
- Prevención de inyección SQL
- Verificación de permisos de usuario

### **Buenas Prácticas:**
- Usar archivos CSV de fuentes confiables
- Verificar datos antes de la importación
- Hacer backup antes de cada importación
- Revisar logs de error después de la importación

## 📞 Soporte

### **Para Reportar Errores:**
1. Usar `--verbose` para obtener más información
2. Guardar el log completo de la operación
3. Incluir el archivo CSV de ejemplo (sin datos sensibles)
4. Describir el error específico que ocurrió

### **Para Solicitar Mejoras:**
1. Describir la funcionalidad deseada
2. Proporcionar ejemplos de uso
3. Explicar el beneficio esperado
4. Incluir casos de uso específicos

---

**🎉 ¡El comando está listo para usar! Comienza con `--dry-run` para validar tu archivo CSV.**
