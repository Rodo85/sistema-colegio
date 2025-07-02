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
        "config_institucional.Subgrupo",
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


