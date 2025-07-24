# matricula/management/commands/cargar_datos_prueba.py
from django.core.management.base import BaseCommand
from catalogos.models import (
    Sexo, Nacionalidad, TipoIdentificacion, EstadoCivil, 
    Parentesco, Escolaridad, Ocupacion
)

class Command(BaseCommand):
    help = "Carga datos básicos de prueba para el sistema"

    def handle(self, *args, **options):
        self.stdout.write("Cargando datos básicos de prueba...")
        
        # Sexos
        sexos_data = [
            {"codigo": "F", "nombre": "Femenino"},
            {"codigo": "M", "nombre": "Masculino"},
            {"codigo": "X", "nombre": "No binario"},
        ]
        
        for sexo_data in sexos_data:
            sexo, created = Sexo.objects.get_or_create(
                codigo=sexo_data["codigo"],
                defaults={"nombre": sexo_data["nombre"]}
            )
            if created:
                self.stdout.write(f"  ✓ Sexo creado: {sexo.nombre}")
        
        # Nacionalidades
        nacionalidades_data = [
            "Costarricense",
            "Nicaragüense", 
            "Colombiana",
            "Venezolana",
            "Estadounidense",
            "Canadiense",
            "Española",
            "Mexicana",
            "Panameña",
            "Salvadoreña",
            "Hondureña",
            "Guatemalteca",
            "Argentina",
            "Chilena",
            "Peruana",
            "Ecuatoriana",
            "Boliviana",
            "Paraguaya",
            "Uruguaya",
            "Brasileña",
        ]
        
        for nombre in nacionalidades_data:
            nacionalidad, created = Nacionalidad.objects.get_or_create(nombre=nombre)
            if created:
                self.stdout.write(f"  ✓ Nacionalidad creada: {nacionalidad.nombre}")
        
        # Tipos de identificación
        tipos_id_data = [
            "Cédula de Identidad",
            "DIMEX",
            "Pasaporte",
            "Carné de Menor",
            "Cédula de Residencia",
        ]
        
        for nombre in tipos_id_data:
            tipo_id, created = TipoIdentificacion.objects.get_or_create(nombre=nombre)
            if created:
                self.stdout.write(f"  ✓ Tipo de identificación creado: {tipo_id.nombre}")
        
        # Estados civiles
        estados_civiles_data = [
            "Soltero(a)",
            "Casado(a)",
            "Divorciado(a)",
            "Viudo(a)",
            "Unión Libre",
        ]
        
        for estado in estados_civiles_data:
            estado_civil, created = EstadoCivil.objects.get_or_create(estado=estado)
            if created:
                self.stdout.write(f"  ✓ Estado civil creado: {estado_civil.estado}")
        
        # Parentescos
        parentescos_data = [
            "Padre",
            "Madre",
            "Tutor Legal",
            "Abuelo(a)",
            "Tío(a)",
            "Hermano(a)",
            "Otro Familiar",
        ]
        
        for parentezco in parentescos_data:
            parentesco, created = Parentesco.objects.get_or_create(parentezco=parentezco)
            if created:
                self.stdout.write(f"  ✓ Parentesco creado: {parentesco.parentezco}")
        
        # Escolaridades
        escolaridades_data = [
            "Sin estudios",
            "Primaria incompleta",
            "Primaria completa",
            "Secundaria incompleta", 
            "Secundaria completa",
            "Técnico medio",
            "Bachillerato universitario",
            "Licenciatura",
            "Maestría",
            "Doctorado",
        ]
        
        for descripcion in escolaridades_data:
            escolaridad, created = Escolaridad.objects.get_or_create(descripcion=descripcion)
            if created:
                self.stdout.write(f"  ✓ Escolaridad creada: {escolaridad.descripcion}")
        
        # Ocupaciones
        ocupaciones_data = [
            "Ama de casa",
            "Estudiante",
            "Empleado(a) público",
            "Empleado(a) privado",
            "Empresario(a)",
            "Profesional independiente",
            "Trabajador(a) por cuenta propia",
            "Jubilado(a)",
            "Desempleado(a)",
            "Otro",
        ]
        
        for descripcion in ocupaciones_data:
            ocupacion, created = Ocupacion.objects.get_or_create(descripcion=descripcion)
            if created:
                self.stdout.write(f"  ✓ Ocupación creada: {ocupacion.descripcion}")
        
        self.stdout.write(
            self.style.SUCCESS(
                f"\n✓ Datos básicos cargados exitosamente!\n"
                f"  - {Sexo.objects.count()} sexos\n"
                f"  - {Nacionalidad.objects.count()} nacionalidades\n"
                f"  - {TipoIdentificacion.objects.count()} tipos de identificación\n"
                f"  - {EstadoCivil.objects.count()} estados civiles\n"
                f"  - {Parentesco.objects.count()} parentescos\n"
                f"  - {Escolaridad.objects.count()} escolaridades\n"
                f"  - {Ocupacion.objects.count()} ocupaciones"
            )
        ) 