from django.db import models

# Modelos globales
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
    
class Nivel(models.Model):
    numero = models.PositiveSmallIntegerField(unique=True)
    nombre = models.CharField("Nivel",max_length=20)          # «Sétimo», «Décimo», …

    class Meta:
        verbose_name = "Nivel"
        verbose_name_plural = "Niveles"
        ordering = ("numero",)

    def __str__(self):
        return f"{self.nombre} ({self.numero})"

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
    
class Adecuacion(models.Model):
    descripcion = models.CharField("Adecuación", max_length=100)
    class Meta:
        verbose_name = "Adecuación curricular"
        verbose_name_plural = "Adecuaciones"

    def __str__(self):
        return self.descripcion

# ────────── 0. Modalidad (tabla “padre” de Especialidad) ───────
class Modalidad(models.Model):
    nombre = models.CharField("Modalidad", max_length=100, unique=True)

    class Meta:
        verbose_name = "Modalidad"
        verbose_name_plural = "Modalidades"
        ordering = ("nombre",)

    def __str__(self):
        return self.nombre



class Especialidad(models.Model):
    modalidad = models.ForeignKey(
        Modalidad,
        on_delete=models.PROTECT,
        verbose_name="Modalidad"
    )
    nombre    = models.CharField("Especialidad", max_length=100, unique=True)

    class Meta:
        verbose_name = "Especialidad"
        verbose_name_plural = "Especialidades"
        
    def __str__(self):
        return self.nombre
    


class SubArea(models.Model):
    especialidad = models.ForeignKey(Especialidad, on_delete=models.PROTECT)
    nombre       = models.CharField(max_length=100)
    class Meta:
        unique_together = ("especialidad", "nombre")
        verbose_name = "Sub area"          
        verbose_name_plural = "Subáreas"
    def __str__(self):
        return f"{self.especialidad} – {self.nombre}"

class Materia(models.Model):
    ACADEMICA = "A"
    TECNICA   = "T"
    tipo      = models.CharField(max_length=1, choices=[(ACADEMICA,"Académica"),(TECNICA,"Técnica")])
    nombre    = models.CharField(max_length=120)
    subarea   = models.ForeignKey(SubArea, null=True, blank=True, on_delete=models.PROTECT)
    class Meta:
        unique_together = ("nombre", "subarea", "tipo")
    def __str__(self):
        return self.nombre

"""
# clases propias por institución
class Seccion(models.Model):
    institucion     = models.ForeignKey("core.Institucion", on_delete=models.PROTECT)
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

"""

"""
class Subgrupo(models.Model):
    institucion     = models.ForeignKey("core.Institucion", on_delete=models.PROTECT)
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

"""


# ──────────────────────────────────────────────────────────────
# 2.  MATERIAS Y PROFESORES
# ──────────────────────────────────────────────────────────────
"""
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
"""


"""
class Profesor(models.Model):

    institucion = models.ForeignKey("core.Institucion", on_delete=models.PROTECT)
    usuario     = models.ForeignKey("core.User", on_delete=models.PROTECT) 
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
"""



# ──────────────────────────────────────────────────────────────
# 3.  CLASE  (Profesor × Materia × Subgrupo)
# ──────────────────────────────────────────────────────────────
"""
    Representa que un PROFESOR imparte una MATERIA
    a un SUBGRUPO (p. ej. 7-1A) en un PERIODO lectivo.
    Si el colegio dicta la materia a toda la sección,
    asigne la Clase a CADA subgrupo de esa sección
    (o cree un subgrupo 'Ú' si solo hay uno).
    """
"""
class Clase(models.Model):
    
    institucion     = models.ForeignKey("core.Institucion", on_delete=models.PROTECT)
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
"""

"""
class Clase(models.Model):
    institucion = models.ForeignKey("core.Institucion", on_delete=models.PROTECT)
    profesor    = models.ForeignKey(Profesor, on_delete=models.PROTECT)
    materia     = models.ForeignKey("catalogos.Materia", on_delete=models.PROTECT)
    subgrupo    = models.ForeignKey("catalogos.Subgrupo", on_delete=models.PROTECT)
    periodo     = models.CharField(max_length=20, default="Actual")
    class Meta:
        unique_together = ("materia","subgrupo","periodo")
"""

