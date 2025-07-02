#app catalogos
from django.db import models

# Modelos globales
class Provincia(models.Model):
    nombre = models.CharField(max_length=50)
    def __str__(self):
        return self.nombre

class Canton(models.Model):
    provincia = models.ForeignKey(Provincia, on_delete=models.PROTECT,
                                  related_name="cantones")
    nombre     = models.CharField(max_length=50)
    def __str__(self):
        return f"{self.nombre} ({self.provincia})"

class Distrito(models.Model):
    canton = models.ForeignKey(Canton, on_delete=models.PROTECT,
                               related_name="distritos")
    nombre = models.CharField(max_length=50)
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
        return f"{self.nombre}"

class Sexo(models.Model):
    codigo = models.CharField("Código", max_length=1, unique=True)  # F, M, X
    nombre = models.CharField("Nombre", max_length=50)              # Femenino, Masculino, No binario...

    class Meta:
        verbose_name = "Sexo"
        verbose_name_plural = "Sexos"
        ordering = ("nombre",)

    def __str__(self):
        return self.nombre

class EstadoCivil(models.Model):
    estado = models.CharField("Estado civil", max_length=30, unique=True)
    class Meta:
        verbose_name = "Estado civil"
        verbose_name_plural = "Estados civiles"
        ordering = ("estado",)
    def __str__(self):
        return self.estado

class Parentesco(models.Model):
    parentezco = models.CharField("Parentesco", max_length=30, unique=True)
    class Meta:
        verbose_name = "Parentesco"
        verbose_name_plural = "Parentescos"
        ordering = ("parentezco",)
    def __str__(self):
        return self.parentezco

class Escolaridad(models.Model):
    descripcion = models.CharField("Escolaridad", max_length=50, unique=True)
    class Meta:
        verbose_name = "Escolaridad"
        verbose_name_plural = "Escolaridades"
        ordering = ("descripcion",)
    def __str__(self):
        return self.descripcion

class Ocupacion(models.Model):
    descripcion = models.CharField("Ocupación", max_length=50, unique=True)
    class Meta:
        verbose_name = "Ocupación"
        verbose_name_plural = "Ocupaciones"
        ordering = ("descripcion",)
    def __str__(self):
        return self.descripcion
