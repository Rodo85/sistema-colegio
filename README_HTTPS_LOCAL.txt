# Cómo usar HTTPS local en Django (Windows)

1. Instala mkcert y genera los certificados (ya hecho):
   - Certificado: miapp.local+3.pem
   - Llave: miapp.local+3-key.pem

2. Asegúrate de tener django-extensions instalado y en INSTALLED_APPS.

3. Lanza el servidor de Django con HTTPS:

   python manage.py runserver_plus --cert-file miapp.local+3.pem --key-file miapp.local+3-key.pem

4. Accede a https://localhost:8000/ o https://miapp.local:8000/
   - Si el navegador pide aceptar el certificado, hazlo (solo en local).

5. Si quieres cambiar el nombre de los archivos, actualiza la ruta en settings.py.

6. (Opcional, recomendado) Para usar https://miapp.local:8000/ agrega esta línea a tu archivo hosts de Windows:

   127.0.0.1   miapp.local

   El archivo hosts está en: C:\Windows\System32\drivers\etc\hosts
   (Ábrelo como administrador para poder guardar los cambios)

¡Listo! Tu entorno de desarrollo ahora es seguro y sin advertencias de autocompletado.