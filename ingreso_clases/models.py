from django.db import models
from core.models import Institucion


class RegistroIngreso(models.Model):
    institucion = models.ForeignKey(Institucion, on_delete=models.PROTECT, verbose_name="Institución")
    identificacion = models.CharField("Identificación estudiante", max_length=20, db_index=True)
    fecha_hora = models.DateTimeField(auto_now_add=True)
    es_entrada = models.BooleanField(default=True)
    observacion = models.CharField(max_length=255, blank=True)

    class Meta:
        verbose_name = "Registro de ingreso/salida"
        verbose_name_plural = "Registros de ingreso/salida"
        ordering = ("-fecha_hora",)
        constraints = [
            models.UniqueConstraint(
                fields=["institucion", "identificacion", "fecha_hora"],
                name="unique_registro_ingreso_por_institucion"
            )
        ]

    def __str__(self):
        return f"{self.institucion} - {self.identificacion} - {'ENTRA' if self.es_entrada else 'SALE'} - {self.fecha_hora:%Y-%m-%d %H:%M}"

    def save(self, *args, **kwargs):
        # Normalizar campos de texto
        for campo in ("observacion",):
            valor = getattr(self, campo, None)
            if isinstance(valor, str):
                setattr(self, campo, valor.strip().upper())
        super().save(*args, **kwargs)
















