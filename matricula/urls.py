from django.urls import path
from .views import (
    consulta_estudiante, get_especialidades_disponibles, 
    EspecialidadAutocomplete, SeccionAutocomplete, SubgrupoAutocomplete,
    asignacion_grupos, ejecutar_asignacion_grupos,
    exportar_listas_clase_excel,
    comprobante_matricula,
    api_secciones_por_curso_nivel, api_subgrupos_por_curso_seccion,
    buscar_estudiante_existente, agregar_estudiante_a_institucion,
)

app_name = 'matricula'

urlpatterns = [
    path('consulta-estudiante/', consulta_estudiante, name='consulta_estudiante'),
    path('comprobante-matricula/', comprobante_matricula, name='comprobante_matricula'),
    path('get-especialidades-disponibles/', get_especialidades_disponibles, name='get_especialidades_disponibles'),
    
    # Django Autocomplete Light (DAL)
    path('especialidad-autocomplete/', EspecialidadAutocomplete.as_view(), name='especialidad-autocomplete'),
    path('seccion-autocomplete/', SeccionAutocomplete.as_view(), name='seccion-autocomplete'),
    path('subgrupo-autocomplete/', SubgrupoAutocomplete.as_view(), name='subgrupo-autocomplete'),
    
    # Asignación automática de grupos
    path('asignacion-grupos/', asignacion_grupos, name='asignacion_grupos'),
    path('ejecutar-asignacion-grupos/', ejecutar_asignacion_grupos, name='ejecutar_asignacion_grupos'),
    path('exportar-listas-excel/', exportar_listas_clase_excel, name='exportar_listas_clase_excel'),
    # APIs para poblar selects
    path('api/secciones/', api_secciones_por_curso_nivel, name='api_secciones_por_curso_nivel'),
    path('api/subgrupos/', api_subgrupos_por_curso_seccion, name='api_subgrupos_por_curso_seccion'),
    
    # Buscar estudiante existente
    path('api/buscar-estudiante/', buscar_estudiante_existente, name='buscar_estudiante_existente'),
    path('api/agregar-estudiante-institucion/', agregar_estudiante_a_institucion, name='agregar_estudiante_a_institucion'),
]