"""
URL configuration for sis_colegio project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from other_app.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.views.generic import RedirectView
from django.conf import settings
from django.conf.urls.static import static
from core import views as core_views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('catalogos/', include('catalogos.urls')),
    path('matricula/', include('matricula.urls')),
    path('ingreso/', include('ingreso_clases.urls')),
    path('config/', include('config_institucional.urls')),
    path('seleccionar-institucion/', core_views.seleccionar_institucion, name='seleccionar_institucion'),
    path('', RedirectView.as_view(pattern_name='admin:index', permanent=False)),
]

# Servir archivos estáticos adicionales solo en DEBUG (opcional)
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

# Servir archivos media siempre (WhiteNoise respaldará en producción)
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
