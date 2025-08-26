# 🔒 GUÍA DE DESPLIEGUE SEGURO - SISTEMA COLEGIO

## **⚠️ CONFIGURACIÓN CRÍTICA ANTES DEL DESPLIEGUE**

### **1. Variables de Entorno REQUERIDAS**

Crea un archivo `.env` en la raíz del proyecto con las siguientes variables:

```bash
# 🔐 SEGURIDAD CRÍTICA
SECRET_KEY=tu-clave-super-secreta-aqui-cambiala-en-produccion
DEBUG=False
ALLOWED_HOSTS=tu-dominio.com,www.tu-dominio.com

# 🗄️ BASE DE DATOS
DB_NAME=db_sistema_colegio
DB_USER=tu_usuario_db
DB_PASSWORD=tu_password_super_seguro
DB_HOST=localhost
DB_PORT=5432

# 📧 EMAIL (opcional pero recomendado)
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_HOST_USER=tu-email@gmail.com
EMAIL_HOST_PASSWORD=tu-app-password
EMAIL_USE_TLS=True
DEFAULT_FROM_EMAIL=tu-email@gmail.com

# 🚀 CACHÉ (opcional pero recomendado)
REDIS_URL=redis://127.0.0.1:6379/1
```

### **2. Generar Nueva SECRET_KEY**

**NUNCA uses la clave por defecto en producción:**

```bash
# En Python shell:
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

### **3. Configuración de Base de Datos**

```bash
# Crear base de datos PostgreSQL
sudo -u postgres psql
CREATE DATABASE db_sistema_colegio;
CREATE USER tu_usuario WITH PASSWORD 'tu_password_super_seguro';
GRANT ALL PRIVILEGES ON DATABASE db_sistema_colegio TO tu_usuario;
\q

# Aplicar migraciones
python manage.py migrate
```

### **4. Configuración de Archivos Estáticos**

```bash
# Recolectar archivos estáticos
python manage.py collectstatic --noinput

# Configurar servidor web (nginx/apache) para servir archivos estáticos
```

### **5. Configuración de Seguridad del Servidor**

```bash
# Firewall
sudo ufw enable
sudo ufw allow 22    # SSH
sudo ufw allow 80    # HTTP
sudo ufw allow 443   # HTTPS
sudo ufw allow 5432  # PostgreSQL (solo si es necesario)

# Configurar SSL/TLS con Let's Encrypt
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d tu-dominio.com
```

### **6. Configuración de Django**

```bash
# Crear superusuario
python manage.py createsuperuser

# Verificar configuración
python manage.py check --deploy
```

## **🚨 VERIFICACIONES DE SEGURIDAD**

### **Antes del Despliegue:**
- [ ] DEBUG = False
- [ ] SECRET_KEY cambiada
- [ ] ALLOWED_HOSTS configurado
- [ ] Base de datos configurada
- [ ] Migraciones aplicadas
- [ ] Archivos estáticos recolectados

### **Después del Despliegue:**
- [ ] HTTPS funcionando
- [ ] Login admin accesible
- [ ] Archivos estáticos servidos
- [ ] Base de datos conectando
- [ ] Logs funcionando

## **📊 MONITOREO Y MANTENIMIENTO**

### **Logs del Sistema:**
```bash
# Ver logs de Django
tail -f logs/django.log

# Ver logs del sistema
sudo journalctl -u gunicorn -f
sudo journalctl -u nginx -f
```

### **Backup de Base de Datos:**
```bash
# Backup diario
pg_dump db_sistema_colegio > backup_$(date +%Y%m%d).sql

# Restaurar si es necesario
psql db_sistema_colegio < backup_20250101.sql
```

## **🔍 SOLUCIÓN DE PROBLEMAS COMUNES**

### **Error de Conexión a Base de Datos:**
```bash
# Verificar que PostgreSQL esté corriendo
sudo systemctl status postgresql

# Verificar conexión
psql -h localhost -U tu_usuario -d db_sistema_colegio
```

### **Error de Archivos Estáticos:**
```bash
# Verificar permisos
sudo chown -R www-data:www-data staticfiles/
sudo chmod -R 755 staticfiles/

# Recolectar archivos estáticos nuevamente
python manage.py collectstatic --noinput
```

### **Error de Permisos:**
```bash
# Verificar permisos del proyecto
sudo chown -R www-data:www-data /ruta/a/tu/proyecto/
sudo chmod -R 755 /ruta/a/tu/proyecto/
```

## **📞 CONTACTO DE EMERGENCIA**

Si encuentras problemas de seguridad críticos:
1. **INMEDIATO**: Desconectar el servidor de internet
2. **URGENTE**: Revisar logs de acceso
3. **CRÍTICO**: Cambiar todas las contraseñas
4. **EMERGENCIA**: Restaurar desde backup limpio

---

**⚠️ RECUERDA: La seguridad es responsabilidad de todos. Revisa regularmente tu configuración y mantén actualizado el sistema.**