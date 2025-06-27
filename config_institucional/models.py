# config_institucional/models.py
from django.db import models
from core.models import Institucion
from catalogos.models import Nivel, SubArea

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

class SubAreaInstitucion(models.Model):
    institucion = models.ForeignKey(
        Institucion,
        on_delete=models.CASCADE,
        verbose_name="Institución"
    )
    subarea     = models.ForeignKey(
        SubArea,
        on_delete=models.PROTECT,
        verbose_name="Subárea"
    )

    class Meta:
        verbose_name = "Subárea por institución"
        verbose_name_plural = "Subáreas por institución"
        unique_together = ("institucion", "subarea")
        ordering = ("subarea__especialidad__modalidad__nombre", "subarea__nombre")

    def __str__(self):
        return f"{self.institucion} → {self.subarea}"

class Seccion(models.Model):
    institucion = models.ForeignKey(
        Institucion,
        on_delete=models.PROTECT,
        verbose_name="Institución"
    )
    nivel  = models.ForeignKey(
        Nivel,
        on_delete=models.PROTECT,
        verbose_name="Nivel"
    )
    numero = models.PositiveSmallIntegerField(verbose_name="Número de sección")

    class Meta:
        verbose_name = "Sección"
        verbose_name_plural = "Secciones"
        unique_together = ("nivel", "numero")
        ordering = ("nivel__numero", "numero")

    @property
    def codigo(self):
        return f"{self.nivel.numero}-{self.numero}"

    def __str__(self):
        return self.codigo

class Subgrupo(models.Model):
    institucion = models.ForeignKey(
        Institucion,
        on_delete=models.PROTECT,
        verbose_name="Institución"
    )
    seccion = models.ForeignKey(
        Seccion,
        on_delete=models.PROTECT,
        related_name="subgrupos",
        verbose_name="Sección"
    )
    letra = models.CharField("Letra de subgrupo", max_length=2)

    class Meta:
        verbose_name = "Subgrupo"
        verbose_name_plural = "Subgrupos"
        unique_together = ("seccion", "letra")
        ordering = ("seccion__nivel__numero", "seccion__numero", "letra")

    @property
    def codigo(self):
        return f"{self.seccion.codigo}{self.letra}"

    def __str__(self):
        return self.codigo

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
    identificacion   = models.CharField("Identificación", max_length=20, unique=True)
    primer_apellido  = models.CharField("Primer apellido", max_length=50)
    segundo_apellido = models.CharField("Segundo apellido", max_length=50, blank=True)
    nombres          = models.CharField("Nombres", max_length=100)
    correo           = models.EmailField("Correo", blank=True)
    telefono         = models.CharField("Teléfono", max_length=20, blank=True)

    class Meta:
        verbose_name = "Profesor"
        verbose_name_plural = "Profesores"
        ordering = ("primer_apellido", "segundo_apellido", "nombres")

    def __str__(self):
        return f"{self.nombres} {self.primer_apellido}"

class Clase(models.Model):
    institucion = models.ForeignKey(
        Institucion,
        on_delete=models.PROTECT,
        verbose_name="Institución"
    )
    profesor    = models.ForeignKey(
        Profesor,
        on_delete=models.PROTECT,
        verbose_name="Profesor"
    )
    materia     = models.ForeignKey(
        "catalogos.Materia",
        on_delete=models.PROTECT,
        verbose_name="Materia"
    )
    subgrupo    = models.ForeignKey(
        "config_institucional.Subgrupo",
        on_delete=models.PROTECT,
        verbose_name="Subgrupo"
    )
    periodo     = models.CharField("Periodo lectivo", max_length=20, default="Actual")

    class Meta:
        verbose_name = "Clase"
        verbose_name_plural = "Clases"
        unique_together = ("materia", "subgrupo", "periodo")
        ordering = (
            "subgrupo__seccion__nivel__numero",
            "subgrupo__seccion__numero",
            "subgrupo__letra",
            "materia__nombre",
        )

    def __str__(self):
        return f"{self.materia.nombre} – {self.subgrupo.codigo} – {self.profesor.nombres.split()[0]}"
