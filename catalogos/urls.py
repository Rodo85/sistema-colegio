# catalogos/urls.py

from django.urls import path
from . import views

app_name = 'catalogos'  # ¡Esta línea es crucial!

urlpatterns = [
    path('api/cantones/<int:provincia_id>/',
         views.api_cantones,
         name='api_cantones'),
    path('api/distritos/<int:canton_id>/',
         views.api_distritos,
         name='api_distritos'),
]