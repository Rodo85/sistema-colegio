from django.db import models
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.db.models import Q

from core.models import Institucion, User
from catalogos.models import (
    TipoIdentificacion, Sexo, Nacionalidad,
    Provincia, Canton, Distrito,
    EstadoCivil, Parentesco, Escolaridad, Ocupacion, Adecuacion,
    Nivel, Especialidad, CursoLectivo,
)
from config_institucional.models import Seccion, Subgrupo, PeriodoLectivo


# ─────────────────────────  PERSONA CONTACTO  ──────────────────────────
class PersonaContacto(models.Model):
    id = models.AutoField(primary_key=True)
    institucion       = models.ForeignKey(Institucion, on_delete=models.PROTECT)
    tipo_identificacion = models.ForeignKey(TipoIdentificacion, on_delete=models.PROTECT, verbose_name="Tipo de identificación")
    identificacion    = models.CharField("Identificación", max_length=20)
    primer_apellido   = models.CharField("1° Apellido", max_length=50)

    # ← ahora permite NULL
    segundo_apellido  = models.CharField("2° Apellido", max_length=50, blank=True, null=True)

    nombres           = models.CharField("Nombre(s)",  max_length=100)

    # ← ahora permiten NULL
    celular_avisos    = models.CharField("Celular", max_length=20, blank=True, null=True)
    correo            = models.CharField("Correo", max_length=100, blank=True, null=True)
    lugar_trabajo     = models.CharField("Lugar de trabajo", max_length=100, blank=True, null=True)
    telefono_trabajo  = models.CharField("Teléfono trabajo", max_length=20, blank=True, null=True)

    # ← ahora permiten NULL
    estado_civil = models.ForeignKey(EstadoCivil, on_delete=models.PROTECT, blank=True, null=True)
    escolaridad  = models.ForeignKey(Escolaridad, on_delete=models.PROTECT, blank=True, null=True)
    ocupacion    = models.ForeignKey(Ocupacion,   on_delete=models.PROTECT, blank=True, null=True)

    class Meta:
        verbose_name = "Persona de contacto"
        verbose_name_plural = "Personas de contacto"
        ordering = ("primer_apellido", "nombres")
        constraints = [
            models.UniqueConstraint(
                fields=["institucion", "identificacion"],
                name="unique_persona_contacto_por_institucion",
            )
        ]
        permissions = [
            ("only_search_personacontacto", "Solo puede buscar personas de contacto (no ve lista completa)"),
        ]

    def clean(self):
        from django.core.exceptions import ValidationError
        
        # Validar que si es cédula, tenga exactamente 9 dígitos
        if self.tipo_identificacion and self.identificacion:
            tipo_nombre = self.tipo_identificacion.nombre.upper()
            if 'CÉDULA' in tipo_nombre or 'CEDULA' in tipo_nombre:
                if not self.identificacion.isdigit() or len(self.identificacion) != 9:
                    raise ValidationError({
                        'identificacion': 'La cédula debe tener exactamente 9 dígitos numéricos.'
                    })
        
        # Validar unicidad de identificación por institución
        if self.institucion_id and self.identificacion:
            # Buscar personas de contacto con la misma institución e identificación
            contactos_existentes = PersonaContacto.objects.filter(
                institucion_id=self.institucion_id,
                identificacion=self.identificacion.strip().upper()
            )
            
            # Excluir el contacto actual si está editando
            if self.pk:
                contactos_existentes = contactos_existentes.exclude(pk=self.pk)
            
            if contactos_existentes.exists():
                contacto_existente = contactos_existentes.first()
                raise ValidationError({
                    'identificacion': f'Ya existe una persona de contacto con la identificación {self.identificacion} en esta institución: {contacto_existente.primer_apellido} {contacto_existente.segundo_apellido or ""} {contacto_existente.nombres}.'
                })

    def save(self, *args, **kwargs):
        # Normaliza strings: recorta y a MAYÚSCULA (correo se maneja aparte)
        for campo in (
            "identificacion", "primer_apellido", "segundo_apellido",
            "nombres", "celular_avisos", "lugar_trabajo", "telefono_trabajo",
        ):
            valor = getattr(self, campo, None)
            if isinstance(valor, str):
                setattr(self, campo, valor.strip().upper())

        # Correos electrónicos en minúscula
        if self.correo:
            self.correo = self.correo.strip().lower()

        super().save(*args, **kwargs)

    def __str__(self):
        segundo = (self.segundo_apellido or "").strip()
        partes = [self.primer_apellido, segundo, self.nombres]
        return " ".join([p for p in partes if p])

# ──────────────────────────────  ESTUDIANTE  ───────────────────────────
class Estudiante(models.Model):
    PR = "PR"
    PN = "PN"
    TIPO_CHOICES = [
        (PR, "Plan regular"),
        (PN, "Plan nacional"),
    ]

    # ======== SOLO estos campos quedan NO NULOS ========
    # NOTA: institucion se maneja ahora a través de EstudianteInstitucion (tabla intermedia)
    tipo_estudiante     = models.CharField("Tipo de estudiante", max_length=2, choices=TIPO_CHOICES, default=PR)  # NOT NULL
    tipo_identificacion = models.ForeignKey(TipoIdentificacion, on_delete=models.PROTECT)             # NOT NULL
    identificacion      = models.CharField("Identificación", max_length=20)                           # NOT NULL
    primer_apellido     = models.CharField("1° Apellido", max_length=50)                              # NOT NULL
    segundo_apellido    = models.CharField("2° Apellido", max_length=50)                              # NOT NULL
    nombres             = models.CharField("Nombre(s)", max_length=100)                               # NOT NULL
    fecha_nacimiento    = models.DateField()                                                          # NOT NULL
    sexo                = models.ForeignKey(Sexo, on_delete=models.PROTECT)                           # NOT NULL
    nacionalidad        = models.ForeignKey(Nacionalidad, on_delete=models.PROTECT)                   # NOT NULL
    correo              = models.CharField("Correo electrónico", max_length=100)                      # NOT NULL

    # ======== TODOS los demás pueden ser NULOS ========
    celular           = models.CharField(max_length=20, blank=True, null=True)
    telefono_casa     = models.CharField(max_length=20, blank=True, null=True)

    provincia         = models.ForeignKey(Provincia, on_delete=models.PROTECT, blank=True, null=True)
    canton            = models.ForeignKey(Canton, on_delete=models.PROTECT, blank=True, null=True)
    distrito          = models.ForeignKey(Distrito, on_delete=models.PROTECT, blank=True, null=True)

    direccion_exacta  = models.TextField(blank=True, null=True)

    foto              = models.ImageField("Foto", upload_to='estudiantes/fotos/%Y/%m/', blank=True, null=True)
    ed_religiosa      = models.BooleanField("Recibe Ed. Religiosa", default=False)
    rige_poliza       = models.DateField("Rige Póliza", blank=True, null=True)
    vence_poliza      = models.DateField("Vence Póliza", blank=True, null=True)
    presenta_enfermedad = models.BooleanField("Presenta alguna enfermedad", null=True, blank=True)
    detalle_enfermedad  = models.CharField("Nombre de la(s) enfermedad(es)", max_length=255, blank=True, null=True)
    autoriza_derecho_imagen = models.BooleanField("Autoriza derecho de imagen", default=False)
    numero_poliza     = models.CharField("Número de póliza", max_length=50, blank=True, null=True)
    adecuacion        = models.ForeignKey(Adecuacion, on_delete=models.PROTECT, blank=True, null=True)
    medicamento_consume = models.TextField("Medicamentos que consume", blank=True, null=True)

    # ======== Campos opcionales (formulario en papel) ========
    posee_carnet_conapdis     = models.BooleanField("Posee carnet de CONAPDIS", default=False)
    posee_valvula_drenaje_lcr = models.BooleanField("Posee válvula de drenaje LCR", default=False)
    
    usa_apoyo                 = models.BooleanField("Usa algún tipo de apoyo", default=False)
    apoyo_cual                = models.CharField("¿Cuál apoyo?", max_length=255, blank=True, null=True)
    TIPO_CONDICION_CHOICES = [
        ("EA", "Espectro Autista"),
        ("SD", "Síndrome de Down"),
        ("OT", "Otro"),
    ]
    tipo_condicion_diagnosticada = models.CharField(
        "Tipo de condición diagnosticada",
        max_length=2,
        choices=TIPO_CONDICION_CHOICES,
        blank=True,
        null=True,
    )
    tipo_condicion_otro       = models.CharField("Otro (especifique condición)", max_length=255, blank=True, null=True)
    posee_control             = models.BooleanField("Posee algún tipo de control", default=False)
    control_cual              = models.CharField("¿Cuál control?", max_length=255, blank=True, null=True)
    orden_alejamiento         = models.BooleanField("Existe persona con orden de alejamiento", null=True, blank=True)
    orden_alejamiento_nombre  = models.CharField("Nombre de la persona con orden", max_length=255, blank=True, null=True)

    class Meta:
        verbose_name = "Estudiante"
        verbose_name_plural = "Estudiantes"
        ordering = ("primer_apellido", "nombres")
        constraints = [
            # Identificación única GLOBALMENTE (no por institución)
            models.UniqueConstraint(
                fields=["identificacion"],
                name="unique_estudiante_identificacion_global"
            )
        ]
        # Permisos personalizados para vistas no basadas en modelos específicos
        permissions = [
            ("access_consulta_estudiante", "Puede acceder a Consulta de Estudiante"),
            ("print_ficha_estudiante", "Puede imprimir ficha del estudiante"),
            ("print_comprobante_matricula", "Puede imprimir comprobante de matrícula"),
            ("print_pas_estudiante", "Puede imprimir PAS del estudiante"),
            ("access_reporte_pas_seccion", "Puede acceder a Reporte PAS por Sección"),
            ("access_asignacion_grupos", "Puede acceder a Asignación de Grupos"),
            ("only_search_estudiante", "Solo puede buscar estudiantes (no ve lista completa)"),
        ]

    def clean(self):
        """Validación personalizada para el modelo Estudiante"""
        super().clean()
        
        # Validar unicidad de identificación GLOBALMENTE
        if self.identificacion:
            # Buscar estudiantes con la misma identificación
            estudiantes_existentes = Estudiante.objects.filter(
                identificacion=self.identificacion.strip().upper()
            )
            
            # Excluir el estudiante actual si está editando
            if self.pk:
                estudiantes_existentes = estudiantes_existentes.exclude(pk=self.pk)
            
            if estudiantes_existentes.exists():
                estudiante_existente = estudiantes_existentes.first()
                raise ValidationError({
                    'identificacion': f'Ya existe un estudiante con la identificación {self.identificacion}: {estudiante_existente.primer_apellido} {estudiante_existente.segundo_apellido} {estudiante_existente.nombres}.'
                })

    def save(self, *args, **kwargs):
        # Normaliza strings: recorta y MAYÚSCULAS (correo se maneja aparte)
        for campo in (
            "identificacion", "primer_apellido", "segundo_apellido",
            "nombres", "celular", "telefono_casa", "direccion_exacta", "numero_poliza"
        ):
            valor = getattr(self, campo, None)
            if isinstance(valor, str):
                setattr(self, campo, valor.strip().upper())

        # Correos electrónicos en minúscula y obligatorio (no nulo).
        # Si hay identificación, construye el institucional.
        if self.identificacion:
            self.correo = f"{self.identificacion.strip()}@est.mep.go.cr".lower()
        elif isinstance(self.correo, str):
            self.correo = self.correo.strip().lower()

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

        # Eliminar foto anterior si se está cargando una nueva
        if self.pk:  # Solo si el estudiante ya existe
            try:
                # Obtener el estudiante actual de la base de datos
                estudiante_actual = Estudiante.objects.get(pk=self.pk)
                
                # Si el estudiante tenía una foto anterior y ahora tiene una nueva (diferente)
                if estudiante_actual.foto and self.foto and estudiante_actual.foto != self.foto:
                    # Eliminar el archivo físico de la foto anterior
                    import os
                    if os.path.isfile(estudiante_actual.foto.path):
                        os.remove(estudiante_actual.foto.path)
                
                # Si se está eliminando la foto (foto = None o '')
                elif estudiante_actual.foto and not self.foto:
                    # Eliminar el archivo físico de la foto anterior
                    import os
                    if os.path.isfile(estudiante_actual.foto.path):
                        os.remove(estudiante_actual.foto.path)
                        
            except Estudiante.DoesNotExist:
                pass  # El estudiante no existe aún, no hay foto anterior que eliminar
            except Exception as e:
                # Si hay algún error al eliminar la foto, registrar pero continuar
                import logging
                logger = logging.getLogger(__name__)
                logger.warning(f"Error al eliminar foto anterior del estudiante: {e}")

        super().save(*args, **kwargs)

    def __str__(self):
        # Mostrar: Primer Apellido Segundo Apellido Nombres
        segundo = (self.segundo_apellido or "").strip()
        if segundo:
            return f"{self.primer_apellido} {segundo} {self.nombres}"
        return f"{self.primer_apellido} {self.nombres}"
    
    def get_institucion_activa(self):
        """Obtiene la institución activa actual del estudiante"""
        try:
            relacion_activa = self.instituciones_estudiante.filter(estado='activo').first()
            return relacion_activa.institucion if relacion_activa else None
        except:
            return None
    
    def get_instituciones_historial(self):
        """Obtiene el historial completo de instituciones ordenado por fecha"""
        try:
            return self.instituciones_estudiante.all().order_by('-fecha_ingreso')
        except:
            return []


# ────────────────────  HISTORIAL INSTITUCIONAL  ───────────────────────────
class EstudianteInstitucion(models.Model):
    """
    Tabla intermedia que registra el historial de instituciones de un estudiante.
    Permite que un estudiante cambie de colegio sin duplicar su información personal.
    """
    ACTIVO = 'activo'
    TRASLADADO = 'trasladado'
    RETIRADO = 'retirado'
    GRADUADO = 'graduado'
    
    ESTADO_CHOICES = [
        (ACTIVO, 'Activo'),
        (TRASLADADO, 'Trasladado'),
        (RETIRADO, 'Retirado'),
        (GRADUADO, 'Graduado'),
    ]
    
    estudiante = models.ForeignKey(
        Estudiante, 
        on_delete=models.PROTECT, 
        related_name='instituciones_estudiante',
        verbose_name="Estudiante"
    )
    institucion = models.ForeignKey(
        Institucion, 
        on_delete=models.PROTECT,
        related_name='estudiantes_institucion',
        verbose_name="Institución"
    )
    estado = models.CharField("Estado", max_length=15, choices=ESTADO_CHOICES, default=ACTIVO)
    fecha_ingreso = models.DateField("Fecha de ingreso", default=timezone.now)
    fecha_salida = models.DateField("Fecha de salida", blank=True, null=True)
    observaciones = models.TextField("Observaciones", blank=True, null=True)
    
    # Auditoría
    fecha_registro = models.DateTimeField("Fecha de registro", auto_now_add=True)
    usuario_registro = models.ForeignKey(
        User, 
        on_delete=models.PROTECT, 
        blank=True, 
        null=True,
        verbose_name="Usuario que registró"
    )
    
    class Meta:
        verbose_name = "Historial institucional del estudiante"
        verbose_name_plural = "Historiales institucionales de estudiantes"
        ordering = ['-fecha_ingreso']
        constraints = [
            # Un estudiante solo puede tener UNA relación activa a la vez
            models.UniqueConstraint(
                fields=['estudiante'],
                condition=Q(estado='activo'),
                name='unique_estudiante_activo_por_vez',
            ),
        ]
    
    def clean(self):
        """Validaciones personalizadas"""
        super().clean()
        
        # Validar que fecha_salida sea posterior a fecha_ingreso
        if self.fecha_salida and self.fecha_ingreso:
            if self.fecha_salida < self.fecha_ingreso:
                raise ValidationError({
                    'fecha_salida': 'La fecha de salida debe ser posterior a la fecha de ingreso.'
                })
        
        # Si el estado es activo, no debe tener fecha de salida
        if self.estado == self.ACTIVO and self.fecha_salida:
            raise ValidationError({
                'fecha_salida': 'Un estudiante activo no puede tener fecha de salida.'
            })
    
    def __str__(self):
        return f"{self.estudiante} - {self.institucion} ({self.get_estado_display()})"


# ────────────────────────  TABLA INTERMEDIA  ───────────────────────────
class EncargadoEstudiante(models.Model):
    estudiante       = models.ForeignKey(Estudiante,      on_delete=models.CASCADE)
    persona_contacto = models.ForeignKey(PersonaContacto, on_delete=models.CASCADE)
    parentesco       = models.ForeignKey(Parentesco,      on_delete=models.PROTECT)
    convivencia      = models.BooleanField("Convive con el estudiante", blank=True)
    principal        = models.BooleanField("Es encargado principal", default=False)

    class Meta:
        verbose_name = "Encargado de estudiante"
        verbose_name_plural = "Encargados de estudiantes"
        unique_together = ("estudiante", "persona_contacto", "parentesco")
        constraints = [
            # Un solo encargado principal por estudiante
            models.UniqueConstraint(
                fields=["estudiante"],
                condition=Q(principal=True),
                name="unique_principal_por_estudiante",
            ),
        ]

    def __str__(self):
        return f"{self.persona_contacto} – {self.estudiante} ({self.parentesco})"

    def save(self, *args, **kwargs):
        # Normalizar campos de texto si los hay
        for campo in ("convivencia",):
            valor = getattr(self, campo, None)
            if isinstance(valor, str):
                setattr(self, campo, valor.strip().upper())
        super().save(*args, **kwargs)



class MatriculaAcademica(models.Model):
    ACTIVO = 'activo'
    RETIRADO = 'retirado'
    PROMOVIDO = 'promovido'
    REPITENTE = 'repitente'
    ESTADO_CHOICES = [
        (ACTIVO, 'Activo'),
        (RETIRADO, 'Retirado'),
        (PROMOVIDO, 'Promovido'),
        (REPITENTE, 'Repitente'),
    ]
    estudiante = models.ForeignKey('Estudiante', on_delete=models.PROTECT, related_name='matriculas_academicas')
    institucion = models.ForeignKey(Institucion, on_delete=models.PROTECT, verbose_name="Institución")
    nivel = models.ForeignKey(Nivel, on_delete=models.PROTECT)
    seccion = models.ForeignKey(Seccion, on_delete=models.PROTECT, null=True, blank=True, verbose_name="Sección")
    subgrupo = models.ForeignKey(Subgrupo, on_delete=models.PROTECT, null=True, blank=True, verbose_name="Subgrupo")
    curso_lectivo = models.ForeignKey('catalogos.CursoLectivo', on_delete=models.PROTECT, verbose_name="Curso Lectivo")
    fecha_asignacion = models.DateField(auto_now_add=True)
    estado = models.CharField(max_length=15, choices=ESTADO_CHOICES, default=ACTIVO)
    especialidad = models.ForeignKey('config_institucional.EspecialidadCursoLectivo', on_delete=models.PROTECT, null=True, blank=True, verbose_name="Especialidad del curso lectivo")
    
    class Meta:
        verbose_name = "Matrícula académica"
        verbose_name_plural = "Matrículas académicas"
        # Evita dos matrículas ACTIVAS en el mismo año
        constraints = [
            models.UniqueConstraint(
                fields=['estudiante', 'curso_lectivo'],
                condition=Q(estado='activo'),
                name='uniq_matricula_activa_por_anio',
            ),
        ]
        # Permiso personalizado para gestionar sección, subgrupo y estado
        permissions = [
            ("manage_seccion_subgrupo_estado", "Puede gestionar sección, subgrupo y estado de matrícula"),
            ("access_reporte_matricula", "Puede acceder al reporte de matrícula académica"),
        ]
    
    def __str__(self):
        return f"{self.estudiante} - {self.nivel} {self.seccion or ''} {self.subgrupo or ''} ({self.curso_lectivo})"

    def save(self, *args, **kwargs):
        # Asignar automáticamente la institución activa del estudiante si no está establecida
        if not self.institucion_id and self.estudiante_id:
            institucion_activa = self.estudiante.get_institucion_activa()
            if institucion_activa:
                self.institucion = institucion_activa
        
        # No alterar "estado": debe coincidir con las keys de choices ('activo', 'retirado', ...)
        super().save(*args, **kwargs)

    def clean(self):
        from django.core.exceptions import ValidationError
        
        # 1) Especialidad obligatoria solo para décimo (10)
        if self.nivel and getattr(self.nivel, 'numero', None) == 10:
            if not self.especialidad:
                raise ValidationError("La especialidad es obligatoria para décimo (10°).")
        
        # 2) Para niveles 11 y 12, verificar si hay especialidad previa de décimo
        elif self.nivel and getattr(self.nivel, 'numero', None) in [11, 12]:
            if not self.especialidad:
                # Buscar si hay matrícula de décimo con especialidad
                matricula_10 = MatriculaAcademica.objects.filter(
                    estudiante=self.estudiante,
                    nivel__numero=10,
                    estado='activo'
                ).first()
                if not matricula_10 or not matricula_10.especialidad:
                    raise ValidationError("Para 11° y 12° debe seleccionar una especialidad si no existe una asignada en décimo.")

        # 3) Validar que el estudiante tenga relación activa con la institución
        if self.estudiante and self.institucion:
            relacion_activa = EstudianteInstitucion.objects.filter(
                estudiante=self.estudiante,
                institucion=self.institucion,
                estado='activo'
            ).exists()
            
            if not relacion_activa:
                raise ValidationError(
                    f"El estudiante no tiene una relación activa con la institución {self.institucion}. "
                    f"Debe agregarlo primero al historial institucional."
                )
        
        # 4) Coherencia ECL ↔ curso lectivo e institución
        if self.especialidad:
            if self.especialidad.curso_lectivo_id != self.curso_lectivo_id:
                raise ValidationError("La especialidad seleccionada no corresponde a este curso lectivo.")

            # Validar que la especialidad pertenece a la institución de la matrícula
            if self.institucion:
                if self.especialidad.institucion_id != self.institucion_id:
                    raise ValidationError("La especialidad no pertenece a la institución de la matrícula.")

        # 5) Salvaguarda adicional (evita dos activas por año aunque cambie sección/subgrupo)
        if (self.estado == 'activo' and self.curso_lectivo_id and getattr(self.estudiante, 'pk', None)):
            existe = MatriculaAcademica.objects.filter(
                estudiante=self.estudiante,
                curso_lectivo=self.curso_lectivo,
                estado='activo'
            ).exclude(pk=self.pk).exists()
            if existe:
                raise ValidationError("Ya existe una matrícula activa para este curso lectivo.")

        super().clean()

    @classmethod
    def get_siguiente_matricula_data(cls, estudiante, curso_lectivo_actual):
        """
        Obtiene los datos para la siguiente matrícula de un estudiante
        """
        from catalogos.models import Nivel, CursoLectivo
        
        # Buscar matrícula activa en el curso lectivo actual del estudiante
        matricula_actual = cls.objects.filter(
            estudiante=estudiante,
            curso_lectivo=curso_lectivo_actual,
            estado__iexact='activo'
        ).first()
        
        if not matricula_actual:
            return None  # No hay matrícula activa, proceso manual
        
        # Obtener siguiente nivel
        nivel_actual = matricula_actual.nivel
        try:
            siguiente_nivel = Nivel.objects.get(numero=nivel_actual.numero + 1)
        except Nivel.DoesNotExist:
            return None  # No hay siguiente nivel disponible
        
        # Obtener siguiente curso lectivo (ahora es global)
        try:
            siguiente_curso = CursoLectivo.objects.get(anio=curso_lectivo_actual.anio + 1)
        except CursoLectivo.DoesNotExist:
            return None  # No hay siguiente curso lectivo disponible
        
        # Preparar datos para siguiente matrícula
        siguiente_data = {
            'nivel': siguiente_nivel,
            'curso_lectivo': siguiente_curso,
            'especialidad': None,
        }
        
        # Para niveles 10→11 y 11→12, mantener la especialidad
        if nivel_actual.numero in [10, 11]:
            siguiente_data['especialidad'] = matricula_actual.especialidad
        
        # Verificar que la especialidad siga siendo válida para el siguiente curso lectivo
        # IMPORTANTE: Buscar el EspecialidadCursoLectivo del NUEVO año
        if siguiente_data['especialidad']:
            try:
                from config_institucional.models import EspecialidadCursoLectivo
                # Buscar la especialidad del catálogo que tiene la matrícula actual
                especialidad_catalogo = siguiente_data['especialidad'].especialidad
                
                # Buscar el EspecialidadCursoLectivo del NUEVO curso lectivo que apunte a la misma especialidad
                especialidad_valida = EspecialidadCursoLectivo.objects.filter(
                    institucion=matricula_actual.institucion,
                    curso_lectivo=siguiente_curso,
                    especialidad=especialidad_catalogo,
                    activa=True
                ).first()
                
                if especialidad_valida:
                    # CRÍTICO: Reemplazar con el EspecialidadCursoLectivo del nuevo año
                    siguiente_data['especialidad'] = especialidad_valida
                else:
                    # La especialidad no está disponible en el siguiente curso, no asignarla
                    siguiente_data['especialidad'] = None
            except Exception as e:
                # Log del error para debugging
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f"Error buscando especialidad para siguiente curso: {e}")
                # Si hay error, no asignar especialidad
                siguiente_data['especialidad'] = None
        
        return siguiente_data

    @classmethod
    def get_especialidades_disponibles(cls, institucion, curso_lectivo):
        """
        Obtiene las especialidades disponibles para una institución y curso lectivo específicos.
        Solo retorna las especialidades que han sido configuradas como activas.
        """
        from config_institucional.models import EspecialidadCursoLectivo
        return (
            EspecialidadCursoLectivo.objects
            .filter(institucion=institucion, curso_lectivo=curso_lectivo, activa=True)
            .select_related('especialidad', 'especialidad__modalidad')
            .order_by('especialidad__nombre')
        )


class AsignacionGrupos(models.Model):
    """
    Modelo para registrar las asignaciones automáticas de grupos realizadas.
    Permite llevar un historial de las asignaciones masivas.
    """
    institucion = models.ForeignKey('core.Institucion', on_delete=models.CASCADE, verbose_name="Institución")
    curso_lectivo = models.ForeignKey('catalogos.CursoLectivo', on_delete=models.CASCADE, verbose_name="Curso Lectivo")
    nivel = models.ForeignKey('catalogos.Nivel', on_delete=models.CASCADE, verbose_name="Nivel", null=True, blank=True)
    
    fecha_asignacion = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de Asignación")
    usuario_asignacion = models.ForeignKey('core.User', on_delete=models.PROTECT, verbose_name="Usuario que realizó la asignación")
    
    # Estadísticas de la asignación
    total_estudiantes = models.PositiveIntegerField(verbose_name="Total de Estudiantes Asignados")
    total_mujeres = models.PositiveIntegerField(verbose_name="Total Mujeres")
    total_hombres = models.PositiveIntegerField(verbose_name="Total Hombres") 
    total_otros = models.PositiveIntegerField(verbose_name="Total Otros")
    
    secciones_utilizadas = models.PositiveIntegerField(verbose_name="Secciones Utilizadas")
    subgrupos_utilizados = models.PositiveIntegerField(verbose_name="Subgrupos Utilizados")
    
    # Detalle del algoritmo
    hermanos_agrupados = models.PositiveIntegerField(default=0, verbose_name="Hermanos Agrupados Juntos")
    algoritmo_version = models.CharField(max_length=20, default="v1.0", verbose_name="Versión del Algoritmo")
    
    observaciones = models.TextField(blank=True, verbose_name="Observaciones")
    
    class Meta:
        verbose_name = "Asignación de Grupos"
        verbose_name_plural = "Asignaciones de Grupos"
        ordering = ['-fecha_asignacion']
        
    def __str__(self):
        nivel_str = f" - {self.nivel.nombre}" if self.nivel else ""
        return f"{self.institucion.nombre} - {self.curso_lectivo.nombre}{nivel_str} ({self.fecha_asignacion.strftime('%d/%m/%Y %H:%M')})"


class PlantillaImpresionMatricula(models.Model):
    institucion = models.ForeignKey(
        "core.Institucion", 
        on_delete=models.CASCADE, 
        verbose_name="Institución",
        help_text="Institución a la que pertenece esta plantilla"
    )
    titulo = models.CharField("Título principal", max_length=200)
    logo_mep = models.ImageField("Logo MEP", upload_to="plantillas/logos_mep/", null=False, blank=False)
    encabezado = models.TextField("Encabezado superior", help_text="Puedes usar variables como {{ institucion.nombre }}")
    pie_pagina = models.TextField("Pie de página", help_text="Puedes usar variables como {{ institucion.nombre }}")

    def save(self, *args, **kwargs):
        # Verificar que no exista otra plantilla para la misma institución
        if PlantillaImpresionMatricula.objects.filter(institucion=self.institucion).exists() and not self.pk:
            raise Exception(f"Ya existe una plantilla para la institución {self.institucion.nombre}.")
        super().save(*args, **kwargs)

    class Meta:
        verbose_name = "Plantilla de impresión de matrícula"
        verbose_name_plural = "Plantillas de impresión de matrícula"
        unique_together = ['institucion']

    def __str__(self):
        return f"Plantilla - {self.institucion.nombre}"
