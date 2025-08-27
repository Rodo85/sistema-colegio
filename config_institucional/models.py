# config_institucional/models.py
from django.db import models
from core.models import Institucion
from catalogos.models import Nivel, SubArea, Seccion, Subgrupo, CursoLectivo
from django.core.exceptions import ValidationError
import datetime

class NivelInstitucion(models.Model):
    institucion = models.ForeignKey(
        Institucion,
        on_delete=models.CASCADE,
        verbose_name="Institución"
    )
    nivel       = models.ForeignKey(
        Nivel,
        on_delete=models.PROTECT,
        verbose_name="Nivel"
    )

    class Meta:
        verbose_name = "Nivel por institución"
        verbose_name_plural = "Niveles por institución"
        unique_together = ("institucion", "nivel")
        ordering = ("nivel__numero",)

    def __str__(self):
        return f"{self.institucion} → {self.nivel}"

# CursoLectivo ahora está en catalogos.models


# docentes/models.py
class Profesor(models.Model):
    institucion = models.ForeignKey(
        Institucion,
        on_delete=models.PROTECT,
        verbose_name="Institución"
    )
    usuario          = models.ForeignKey(
        "core.User",
        on_delete=models.PROTECT,
        verbose_name="Usuario"
    )
    identificacion = models.CharField(
        "Identificación",
        max_length=20,
        db_index=True
    )
    telefono         = models.CharField("Teléfono", max_length=20, blank=True)

    class Meta:
        verbose_name = "Profesor"
        verbose_name_plural = "Docentes"
        ordering = ("usuario__last_name", "usuario__second_last_name", "usuario__first_name")
        # Un profesor puede trabajar en múltiples instituciones, pero con identificación única por institución
        unique_together = ("institucion", "identificacion")

    def __str__(self):
        return f"{self.usuario.full_name()} - {self.institucion}"

    def save(self, *args, **kwargs):
        for campo in ("identificacion", "telefono"):
            valor = getattr(self, campo, None)
            if isinstance(valor, str):
                setattr(self, campo, valor.strip().upper())
        super().save(*args, **kwargs)

class Clase(models.Model):
    institucion = models.ForeignKey("core.Institucion", on_delete=models.PROTECT)
    curso_lectivo = models.ForeignKey("catalogos.CursoLectivo", on_delete=models.PROTECT, verbose_name="Curso Lectivo")
    profesor = models.ForeignKey(
        "config_institucional.Profesor",
        on_delete=models.PROTECT,
        verbose_name="Profesor",
    )

    # mientras migra datos dejamos null/blank; después quite esas opciones
    subarea = models.ForeignKey(
        "catalogos.SubArea",
        on_delete=models.PROTECT,
        null=True, blank=True,
        verbose_name="Subárea",
    )

    subgrupo = models.ForeignKey(
        "catalogos.Subgrupo",
        on_delete=models.PROTECT,
    )

    periodo = models.CharField("Periodo lectivo", max_length=20, default="Actual")

    class Meta:
        verbose_name = "Clase"
        verbose_name_plural = "Clases"
        # Unicidad scoped por institución para evitar colisiones entre tenants
        unique_together = ("institucion", "curso_lectivo", "subarea", "subgrupo", "periodo")
        ordering = (
            "subgrupo__seccion__nivel__numero",
            "subgrupo__seccion__numero",
            "subgrupo__letra",
            "subarea__nombre",
        )

    def __str__(self) -> str:
        # si subarea llega a ser None, evitamos AttributeError
        nombre_subarea = self.subarea.nombre if self.subarea else "—"
        return f"{self.institucion} - {nombre_subarea} – {self.subgrupo.codigo} – {self.profesor.usuario.full_name()} ({self.curso_lectivo})"

    def clean(self):
        from django.core.exceptions import ValidationError
        
        # Validar que el profesor pertenezca a la misma institución
        if self.profesor_id and self.institucion_id:
            if self.profesor.institucion_id != self.institucion_id:
                raise ValidationError("El profesor debe pertenecer a la misma institución.")
        
        # Validar que el subgrupo esté habilitado para esta institución en este curso lectivo
        if self.subgrupo_id and self.institucion_id and self.curso_lectivo_id:
            from .models import SubgrupoCursoLectivo
            subgrupo_habilitado = SubgrupoCursoLectivo.objects.filter(
                institucion=self.institucion,
                curso_lectivo=self.curso_lectivo,
                subgrupo=self.subgrupo,
                activa=True
            ).exists()
            if not subgrupo_habilitado:
                raise ValidationError("Este subgrupo no está habilitado para esta institución en este curso lectivo.")
        
        # Validar que la subárea esté habilitada para esta institución (si aplica)
        if self.subarea_id and self.institucion_id:
            from catalogos.models import SubAreaInstitucion
            subarea_habilitada = SubAreaInstitucion.objects.filter(
                institucion=self.institucion,
                subarea=self.subarea,
                activa=True
            ).exists()
            if not subarea_habilitada:
                raise ValidationError("Esta subárea no está habilitada para esta institución.")
        
        super().clean()

    def save(self, *args, **kwargs):
        self.full_clean()
        for campo in ("periodo",):
            valor = getattr(self, campo, None)
            if isinstance(valor, str):
                setattr(self, campo, valor.strip().upper())
        super().save(*args, **kwargs)

class PeriodoLectivo(models.Model):
    institucion = models.ForeignKey('core.Institucion', on_delete=models.CASCADE)
    curso_lectivo = models.ForeignKey(CursoLectivo, on_delete=models.CASCADE, verbose_name="Curso Lectivo")
    nombre = models.CharField(max_length=30, verbose_name="Nombre del período")  # Ej: "1er Periodo", "Trimestre 2"
    fecha_inicio = models.DateField(verbose_name="Fecha de inicio")
    fecha_fin = models.DateField(verbose_name="Fecha de fin")

    class Meta:
        unique_together = ("institucion", "curso_lectivo", "nombre")
        ordering = ("curso_lectivo__anio", "fecha_inicio")
        verbose_name = "Período Lectivo"
        verbose_name_plural = "Períodos Lectivos"

    def __str__(self):
        return f"{self.institucion} - {self.curso_lectivo} - {self.nombre}"

    def clean(self):
        # Normalizar nombre
        if self.nombre:
            self.nombre = self.nombre.strip().upper()
        
        # Validar que fecha_fin sea posterior a fecha_inicio
        if self.fecha_inicio and self.fecha_fin:
            if self.fecha_fin <= self.fecha_inicio:
                from django.core.exceptions import ValidationError
                raise ValidationError("La fecha de fin debe ser posterior a la fecha de inicio.")
        
        super().clean()

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)


class EspecialidadCursoLectivo(models.Model):
    """
    Tabla intermedia para vincular Especialidades con Cursos Lectivos por institución.
    Permite que cada institución configure qué especialidades estarán disponibles
    para cada curso lectivo específico.
    """
    institucion = models.ForeignKey('core.Institucion', on_delete=models.CASCADE, verbose_name="Institución")
    curso_lectivo = models.ForeignKey(CursoLectivo, on_delete=models.CASCADE, verbose_name="Curso Lectivo")
    especialidad = models.ForeignKey('catalogos.Especialidad', on_delete=models.PROTECT, verbose_name="Especialidad")
    activa = models.BooleanField(default=True, verbose_name="Especialidad activa para este curso")

    class Meta:
        verbose_name = "Especialidad por curso lectivo"
        verbose_name_plural = "Especialidades por curso lectivo"
        unique_together = ("institucion", "curso_lectivo", "especialidad")
        ordering = ("curso_lectivo__anio", "especialidad__nombre")

    def __str__(self):
        return f"{self.especialidad.nombre}"

    def clean(self):
        from django.core.exceptions import ValidationError
        
        # Validación: El curso lectivo es global, no pertenece a una institución específica
        # Solo validamos que la institución y curso lectivo estén seleccionados
        if not self.curso_lectivo_id:
            raise ValidationError("Debe seleccionar un curso lectivo.")
        
        if not self.institucion_id:
            raise ValidationError("Debe seleccionar una institución.")
        
        super().clean()

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)


class SeccionCursoLectivo(models.Model):
    """
    Tabla intermedia para vincular Secciones con Cursos Lectivos por institución.
    Permite que cada institución configure qué secciones estarán disponibles
    para cada curso lectivo específico.
    """
    institucion = models.ForeignKey('core.Institucion', on_delete=models.CASCADE, verbose_name="Institución")
    curso_lectivo = models.ForeignKey(CursoLectivo, on_delete=models.CASCADE, verbose_name="Curso Lectivo")
    seccion = models.ForeignKey(Seccion, on_delete=models.PROTECT, verbose_name="Sección")
    activa = models.BooleanField(default=True, verbose_name="Sección activa para este curso")

    class Meta:
        unique_together = ("institucion", "curso_lectivo", "seccion")
        ordering = ("curso_lectivo__anio", "seccion__nivel__numero", "seccion__numero")
        verbose_name = "Sección por Curso Lectivo"
        verbose_name_plural = "Secciones por Curso Lectivo"

    def __str__(self):
        return f"Sección {self.seccion.numero}"

    def clean(self):
        from django.core.exceptions import ValidationError
        
        # Validación: El curso lectivo es global, no pertenece a una institución específica
        # Solo validamos que la institución y curso lectivo estén seleccionados
        if not self.curso_lectivo_id:
            raise ValidationError("Debe seleccionar un curso lectivo.")
        
        if not self.institucion_id:
            raise ValidationError("Debe seleccionar una institución.")
        
        # Validación: Las secciones son globales, no hay restricción por institución
        
        super().clean()

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)


class SubgrupoCursoLectivo(models.Model):
    """
    Tabla intermedia para vincular Subgrupos con Cursos Lectivos por institución.
    Permite que cada institución configure qué subgrupos estarán disponibles
    para cada curso lectivo específico.
    """
    institucion = models.ForeignKey('core.Institucion', on_delete=models.CASCADE, verbose_name="Institución")
    curso_lectivo = models.ForeignKey(CursoLectivo, on_delete=models.CASCADE, verbose_name="Curso Lectivo")
    subgrupo = models.ForeignKey(Subgrupo, on_delete=models.PROTECT, verbose_name="Subgrupo")
    activa = models.BooleanField(default=True, verbose_name="Subgrupo activo para este curso")

    # Nueva relación opcional para niveles con especialidad (10, 11, 12)
    especialidad_curso = models.ForeignKey(
        'config_institucional.EspecialidadCursoLectivo',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        verbose_name="Especialidad (solo 10°, 11°, 12°)"
    )

    class Meta:
        unique_together = ("institucion", "curso_lectivo", "subgrupo")
        ordering = ("curso_lectivo__anio", "subgrupo__seccion__nivel__numero", "subgrupo__letra")
        verbose_name = "Subgrupo por Curso Lectivo"
        verbose_name_plural = "Subgrupos por Curso Lectivo"

    def __str__(self):
        return f"{self.subgrupo.letra}"

    def clean(self):
        from django.core.exceptions import ValidationError
        
        # Validación: El curso lectivo es global, no pertenece a una institución específica
        # Solo validamos que la institución y curso lectivo estén seleccionados
        if not self.curso_lectivo_id:
            raise ValidationError("Debe seleccionar un curso lectivo.")
        
        if not self.institucion_id:
            raise ValidationError("Debe seleccionar una institución.")
        
        # Validaciones de especialidad ligada a niveles 10-12
        try:
            nivel_numero = self.subgrupo.seccion.nivel.numero if self.subgrupo_id else None
        except Exception:
            nivel_numero = None

        # Si el nivel es 10, 11 o 12, la especialidad es obligatoria
        if nivel_numero in [10, 11, 12]:
            if not self.especialidad_curso_id:
                raise ValidationError("Para subgrupos de 10°, 11° o 12° debe asignar una especialidad (ECL).")
        else:
            # Para otros niveles, no debe haber especialidad
            if self.especialidad_curso_id:
                raise ValidationError("Solo niveles 10°, 11° o 12° pueden tener especialidad asignada.")

        # Coherencia: si hay especialidad, debe pertenecer a la misma institución y curso lectivo
        if self.especialidad_curso_id:
            if self.especialidad_curso.institucion_id != self.institucion_id:
                raise ValidationError("La especialidad seleccionada no pertenece a esta institución.")
            if self.especialidad_curso.curso_lectivo_id != self.curso_lectivo_id:
                raise ValidationError("La especialidad seleccionada no corresponde a este curso lectivo.")

        super().clean()

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

