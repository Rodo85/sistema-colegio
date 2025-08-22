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
    institucion      = models.ForeignKey(
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
        unique=True,
        db_index=True 
    )
    telefono         = models.CharField("Teléfono", max_length=20, blank=True)

    class Meta:
        verbose_name = "Profesor"
        verbose_name_plural = "Docentes"
        ordering = ("usuario__last_name", "usuario__second_last_name", "usuario__first_name")

    def __str__(self):
        return self.usuario.full_name()

    def save(self, *args, **kwargs):
        for campo in ("identificacion", "telefono"):
            valor = getattr(self, campo, None)
            if isinstance(valor, str):
                setattr(self, campo, valor.strip().upper())
        super().save(*args, **kwargs)

class Clase(models.Model):
    institucion = models.ForeignKey("core.Institucion", on_delete=models.PROTECT)
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
        unique_together = ("subarea", "subgrupo", "periodo")
        ordering = (
            "subgrupo__seccion__nivel__numero",
            "subgrupo__seccion__numero",
            "subgrupo__letra",
            "subarea__nombre",
        )

    def __str__(self) -> str:
        # si subarea llega a ser None, evitamos AttributeError
        nombre_subarea = self.subarea.nombre if self.subarea else "—"
        return f"{nombre_subarea} – {self.subgrupo.codigo} – {self.profesor.usuario.full_name()}"

    def save(self, *args, **kwargs):
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
        if not self.curso_lectivo:
            raise ValidationError("Debe seleccionar un curso lectivo.")
        
        if not self.institucion:
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
        if not self.curso_lectivo:
            raise ValidationError("Debe seleccionar un curso lectivo.")
        
        if not self.institucion:
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
        if not self.curso_lectivo:
            raise ValidationError("Debe seleccionar un curso lectivo.")
        
        if not self.institucion:
            raise ValidationError("Debe seleccionar una institución.")
        
        # Validación: Los subgrupos son globales, no hay restricción por institución
        
        super().clean()

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

