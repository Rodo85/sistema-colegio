from django.db import models

# Create your models here.
class TipoIdentificacion(models.Model):
    nombre = models.CharField("Tipo de identificación", max_length=50)

    class Meta:
        verbose_name = "Identificación"
        verbose_name_plural = "Tipo de Identificación"

    def __str__(self):
        return self.nombre

class Nacionalidad(models.Model):
    nombre = models.CharField("Nacionalidad", max_length=50)

    class Meta:
        verbose_name = "Nacionalidad"
        verbose_name_plural = "Nacionalidades"

    def __str__(self):
        return self.nombre

class Especialidad(models.Model):
    nombre = models.CharField("Especialidad", max_length=100)
    año    = models.PositiveSmallIntegerField("Año")

    class Meta:
        verbose_name = "Especialidad"
        verbose_name_plural = "Especialidades"

    def __str__(self):
        return f"{self.nombre} ({self.año})"

class Adecuacion(models.Model):
    descripcion = models.CharField("Adecuación", max_length=100)
    class Meta:
        verbose_name = "Adecuación curricular"
        verbose_name_plural = "Adecuaciones"

    def __str__(self):
        return self.descripcion


class Provincia(models.Model):
    nombre = models.CharField("Provincia", max_length=50)

    def __str__(self):
        return self.nombre

class Canton(models.Model):
    provincia = models.ForeignKey(Provincia, on_delete=models.PROTECT, verbose_name="Provincia")
    nombre    = models.CharField("Cantón", max_length=50)

    def __str__(self):
        return f"{self.nombre} ({self.provincia})"

class Distrito(models.Model):
    canton = models.ForeignKey(Canton, on_delete=models.PROTECT, verbose_name="Cantón")
    nombre = models.CharField("Distrito", max_length=50)

    def __str__(self):
        return f"{self.nombre} ({self.canton})"


# ──────────────────────────────────────────────────────────────
# 1.  ESTRUCTURA DE GRUPOS
# ──────────────────────────────────────────────────────────────
class Nivel(models.Model):
    """Ej.: 7, 8, 9, 10 …"""
    numero = models.PositiveSmallIntegerField(unique=True)
    nombre = models.CharField("Nivel",max_length=20)          # «Sétimo», «Décimo», …

    class Meta:
        verbose_name = "Nivel"
        verbose_name_plural = "Niveles"
        ordering = ("numero",)

    def __str__(self):
        return f"{self.nombre} ({self.numero})"


class Seccion(models.Model):
    """
    Ej.: 7-1, 7-2 … 9-3.
    Una Sección puede dividirse en varios Subgrupos (A,B,C…).
    """
    nivel  = models.ForeignKey(Nivel, on_delete=models.PROTECT)
    numero = models.PositiveSmallIntegerField()

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
    """
    Letra «A», «B», «C»…  Si el colegio NO usa subdivisiones,
    basta crear un único Subgrupo con letra 'Ú' (Único).
    """
    seccion = models.ForeignKey(
        Seccion,
        on_delete=models.PROTECT,
        related_name="subgrupos"
    )
    letra = models.CharField(max_length=2)            # «A», «B», «Ú»…

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


# ──────────────────────────────────────────────────────────────
# 2.  MATERIAS Y PROFESORES
# ──────────────────────────────────────────────────────────────
class Materia(models.Model):
    TIPO_ACADEMICA = "A"
    TIPO_TECNICA   = "T"
    TIPO_CHOICES = [
        (TIPO_ACADEMICA, "Académica"),
        (TIPO_TECNICA,   "Técnica"),
    ]

    nombre = models.CharField(max_length=100)
    tipo   = models.CharField(max_length=1, choices=TIPO_CHOICES)

    class Meta:
        verbose_name = "Materia"
        verbose_name_plural = "Materias"
        ordering = ("nombre",)

    def __str__(self):
        return f"{self.nombre} ({self.get_tipo_display()})"


class Profesor(models.Model):
    """
    La PK es el id automático; la identificación queda editable.
    """
    identificacion   = models.CharField("Identificación", max_length=20, unique=True)
    primer_apellido  = models.CharField(max_length=50)
    segundo_apellido = models.CharField(max_length=50, blank=True)
    nombres          = models.CharField(max_length=100)

    correo           = models.EmailField(blank=True)
    telefono         = models.CharField("Teléfono",max_length=20, blank=True)

    materias = models.ManyToManyField(
        Materia,
        through="Clase",
        related_name="profesores",
        blank=True,
    )

    class Meta:
        verbose_name = "Profesor"
        verbose_name_plural = "Docentes"
        ordering = ("primer_apellido", "segundo_apellido", "nombres")

    def __str__(self):
        return f"{self.nombres} {self.primer_apellido}"


# ──────────────────────────────────────────────────────────────
# 3.  CLASE  (Profesor × Materia × Subgrupo)
# ──────────────────────────────────────────────────────────────
class Clase(models.Model):
    """
    Representa que un PROFESOR imparte una MATERIA
    a un SUBGRUPO (p. ej. 7-1A) en un PERIODO lectivo.
    Si el colegio dicta la materia a toda la sección,
    asigne la Clase a CADA subgrupo de esa sección
    (o cree un subgrupo 'Ú' si solo hay uno).
    """
    profesor  = models.ForeignKey(Profesor, on_delete=models.CASCADE,verbose_name="Docente")
    materia   = models.ForeignKey(Materia,  on_delete=models.PROTECT)
    subgrupo  = models.ForeignKey(Subgrupo, on_delete=models.PROTECT)
    periodo   = models.CharField(max_length=20, default="Actual")

    class Meta:
        verbose_name = "Clase"
        verbose_name_plural = "Clases"
        unique_together = ("profesor", "materia", "subgrupo", "periodo")
        ordering = ("subgrupo__seccion__nivel__numero",
                    "subgrupo__seccion__numero",
                    "subgrupo__letra",
                    "materia__nombre")

    def __str__(self):
        return (f"{self.materia.nombre} – {self.subgrupo.codigo} – "
                f"{self.profesor.nombres.split()[0]}")