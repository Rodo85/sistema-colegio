from django.urls import path
from . import views

app_name = 'config_institucional'

urlpatterns = [
    # Vista para gestionar secciones por curso lectivo de forma masiva
    path('gestionar-secciones-curso-lectivo/', 
         views.gestionar_secciones_curso_lectivo, 
         name='gestionar_secciones_curso_lectivo'),
    
    # Vista AJAX para actualizar secciones por curso lectivo
    path('actualizar-secciones-curso-lectivo/', 
         views.actualizar_secciones_curso_lectivo, 
         name='actualizar_secciones_curso_lectivo'),
    
    # Vista para gestionar especialidades por curso lectivo de forma masiva
    path('gestionar-especialidades-curso-lectivo/', 
         views.gestionar_especialidades_curso_lectivo, 
         name='gestionar_especialidades_curso_lectivo'),
    
    # Vista AJAX para actualizar especialidades por curso lectivo
    path('actualizar-especialidades-curso-lectivo/', 
         views.actualizar_especialidades_curso_lectivo, 
         name='actualizar_especialidades_curso_lectivo'),
    
    # Vista para gestionar subgrupos por curso lectivo de forma masiva
    path('gestionar-subgrupos-curso-lectivo/', 
         views.gestionar_subgrupos_curso_lectivo, 
         name='gestionar_subgrupos_curso_lectivo'),
    
    # Vista AJAX para actualizar subgrupos por curso lectivo
    path('actualizar-subgrupos-curso-lectivo/', 
         views.actualizar_subgrupos_curso_lectivo, 
         name='actualizar_subgrupos_curso_lectivo'),
]
