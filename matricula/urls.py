from django.urls import path
from .views import consulta_estudiante, get_especialidades_disponibles, EspecialidadAutocomplete, SeccionAutocomplete, SubgrupoAutocomplete

urlpatterns = [
    path('consulta-estudiante/', consulta_estudiante, name='consulta_estudiante'),
    path('get-especialidades-disponibles/', get_especialidades_disponibles, name='get_especialidades_disponibles'),
    
    # Django Autocomplete Light (DAL)
    path('especialidad-autocomplete/', EspecialidadAutocomplete.as_view(), name='especialidad-autocomplete'),
    path('seccion-autocomplete/', SeccionAutocomplete.as_view(), name='seccion-autocomplete'),
    path('subgrupo-autocomplete/', SubgrupoAutocomplete.as_view(), name='subgrupo-autocomplete'),
]