#app catalogos
from django.db import models

# Modelos globales
class Provincia(models.Model):
    nombre = models.CharField(max_length=50)
    def __str__(self):
        return self.nombre

class Canton(models.Model):
    provincia = models.ForeignKey(Provincia, on_delete=models.PROTECT, related_name="cantones")
    nombre = models.CharField(max_length=50)
    
    class Meta:
        verbose_name = "Cantón"
        verbose_name_plural = "Cantones"
        ordering = ("nombre",)
    
    def __str__(self):
        return f"{self.nombre} ({self.provincia.nombre})"

class Distrito(models.Model):
    canton = models.ForeignKey(Canton, on_delete=models.PROTECT, related_name="distritos")
    nombre = models.CharField(max_length=50)
    
    class Meta:
        verbose_name = "Distrito"
        verbose_name_plural = "Distritos"
        ordering = ("nombre",)
    
    def __str__(self):
        return f"{self.nombre} ({self.canton.nombre}, {self.canton.provincia.nombre})"
    
class Nivel(models.Model):
    numero = models.PositiveSmallIntegerField(unique=True)
    nombre = models.CharField("Nivel",max_length=20)

    class Meta:
        verbose_name = "Nivel"
        verbose_name_plural = "Niveles"
        ordering = ("numero",)

    def __str__(self):
        return f"{self.nombre} ({self.numero})"
    def save(self, *args, **kwargs):
        if self.nombre:
            self.nombre = self.nombre.strip().upper()
        super().save(*args, **kwargs)

class TipoIdentificacion(models.Model):
    nombre = models.CharField("Tipo de identificación", max_length=50)
    def save(self, *args, **kwargs):
        if self.nombre:
            self.nombre = self.nombre.strip().upper()
        super().save(*args, **kwargs)
    def __str__(self):
        return self.nombre

class Nacionalidad(models.Model):
    nombre = models.CharField("Nacionalidad", max_length=50, unique=True)

    class Meta:
        verbose_name = "Nacionalidad"
        verbose_name_plural = "Nacionalidades"

    def __str__(self):
        return self.nombre
    
class Adecuacion(models.Model):
    descripcion = models.CharField(max_length=100, unique=True)
    class Meta:
        verbose_name = "Adecuación curricular"
        verbose_name_plural = "Adecuaciones"

    def save(self, *args, **kwargs):
        if self.descripcion:
            self.descripcion = self.descripcion.strip().upper()
        super().save(*args, **kwargs)
    def __str__(self):
        return self.descripcion

# ────────── 0. Modalidad (tabla “padre” de Especialidad) ───────
class Modalidad(models.Model):
    nombre = models.CharField("Modalidad", max_length=100, unique=True)
    def save(self, *args, **kwargs):
        if self.nombre:
            self.nombre = self.nombre.strip().upper()
        super().save(*args, **kwargs)

    class Meta:
        verbose_name = "Modalidad"
        verbose_name_plural = "Modalidades"
        ordering = ("nombre",)

    def __str__(self):
        return self.nombre



class Especialidad(models.Model):
    modalidad = models.ForeignKey(Modalidad, on_delete=models.PROTECT)
    nombre = models.CharField(max_length=100, unique=True)
    def save(self, *args, **kwargs):
        if self.nombre:
            self.nombre = self.nombre.strip().upper()
        super().save(*args, **kwargs)

    class Meta:
        verbose_name = "Especialidad"
        verbose_name_plural = "Especialidades"
        
    def __str__(self):
        return self.nombre
    


class SubArea(models.Model):
    """
    Catálogo unificado de materias y subáreas. Si es_academica=True, representa una materia académica (Matemática, Español, etc.) y especialidad debe ser None. Si es_academica=False, representa una materia técnica y debe tener especialidad asignada.
    """
    especialidad = models.ForeignKey(
        Especialidad,
        on_delete=models.PROTECT,
        null=True, blank=True
    )
    nombre = models.CharField(max_length=100)
    es_academica = models.BooleanField(default=False)

    class Meta:
        unique_together = ("nombre", "especialidad")
        verbose_name = "Sub area"
        verbose_name_plural = "Subáreas-Materias"

    def clean(self):
        from django.core.exceptions import ValidationError
        # Validar reglas de negocio
        if self.es_academica and self.especialidad is not None:
            raise ValidationError("Una materia académica no debe tener especialidad asignada.")
        if not self.es_academica and self.especialidad is None:
            raise ValidationError("Una materia técnica debe tener especialidad asignada.")

    def save(self, *args, **kwargs):
        # Normalizar texto: mayúsculas y sin espacios de sobra
        if self.nombre:
            self.nombre = self.nombre.strip().upper()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.nombre}"

class Sexo(models.Model):
    codigo = models.CharField("Código", max_length=1, unique=True)  # F, M, X
    nombre = models.CharField(max_length=20)              # Femenino, Masculino, No binario...
    def save(self, *args, **kwargs):
        if self.codigo:
            self.codigo = self.codigo.strip().upper()
        if self.nombre:
            self.nombre = self.nombre.strip().upper()
        super().save(*args, **kwargs)

    class Meta:
        verbose_name = "Género"
        verbose_name_plural = "Géneros"
        ordering = ("nombre",)

    def __str__(self):
        return self.nombre

class EstadoCivil(models.Model):
    descripcion = models.CharField("Estado civil", max_length=30, unique=True)
    def save(self, *args, **kwargs):
        if self.descripcion:
            self.descripcion = self.descripcion.strip().upper()
        super().save(*args, **kwargs)
    class Meta:
        verbose_name = "Estado civil"
        verbose_name_plural = "Estados civiles"
        ordering = ("descripcion",)
    def __str__(self):
        return self.descripcion

class Parentesco(models.Model):
    descripcion = models.CharField("Parentesco", max_length=30, unique=True)
    def save(self, *args, **kwargs):
        if self.descripcion:
            self.descripcion = self.descripcion.strip().upper()
        super().save(*args, **kwargs)
    def __str__(self):
        return self.descripcion

class Escolaridad(models.Model):
    descripcion = models.CharField("Escolaridad", max_length=50, unique=True)
    def save(self, *args, **kwargs):
        if self.descripcion:
            self.descripcion = self.descripcion.strip().upper()
        super().save(*args, **kwargs)
    class Meta:
        verbose_name = "Escolaridad"
        verbose_name_plural = "Escolaridades"
        ordering = ("descripcion",)
    def __str__(self):
        return self.descripcion

class Ocupacion(models.Model):
    descripcion = models.CharField("Ocupación", max_length=50, unique=True)
    def save(self, *args, **kwargs):
        if self.descripcion:
            self.descripcion = self.descripcion.strip().upper()
        super().save(*args, **kwargs)
    class Meta:
        verbose_name = "Ocupación"
        verbose_name_plural = "Ocupaciones"
        ordering = ("descripcion",)
    def __str__(self):
        return self.descripcion


# ═══════════════════════════════════════════════════════════════════
#                    SECCIONES Y SUBGRUPOS GLOBALES
# ═══════════════════════════════════════════════════════════════════

class Seccion(models.Model):
    """
    Catálogo global de secciones.
    Las instituciones seleccionan de este catálogo cuáles usar por año.
    """
    nivel = models.ForeignKey(Nivel, on_delete=models.PROTECT, verbose_name="Nivel", related_name="secciones_globales")
    numero = models.PositiveSmallIntegerField(verbose_name="Número de sección")

    class Meta:
        verbose_name = "Sección"
        verbose_name_plural = "Secciones"
        unique_together = ("nivel", "numero")
        ordering = ("nivel__numero", "numero")

    def __str__(self):
        return f"{self.nivel.numero}-{self.numero}"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)


class Subgrupo(models.Model):
    """
    Catálogo global de subgrupos.
    Las instituciones seleccionan de este catálogo cuáles usar por año.
    """
    seccion = models.ForeignKey(Seccion, on_delete=models.PROTECT, related_name="subgrupos", verbose_name="Sección")
    letra = models.CharField("Letra de subgrupo", max_length=2)

    class Meta:
        verbose_name = "Subgrupo"
        verbose_name_plural = "Subgrupos"
        unique_together = ("seccion", "letra")
        ordering = ("seccion__nivel__numero", "seccion__numero", "letra")

    def __str__(self):
        return f"{self.seccion.nivel.numero}-{self.seccion.numero}{self.letra}"

    @property
    def codigo(self):
        """Mantener compatibilidad con código existente."""
        return f"{self.seccion.numero}-{self.letra}"

    def save(self, *args, **kwargs):
        if self.letra:
            self.letra = self.letra.strip().upper()
        super().save(*args, **kwargs)
