from django.db import models


class RegistroIngreso(models.Model):
    identificacion = models.CharField("Identificación estudiante", max_length=20, db_index=True)
    fecha_hora = models.DateTimeField(auto_now_add=True)
    es_entrada = models.BooleanField(default=True)
    observacion = models.CharField(max_length=255, blank=True)

    class Meta:
        verbose_name = "Registro de ingreso/salida"
        verbose_name_plural = "Registros de ingreso/salida"
        ordering = ("-fecha_hora",)

    def __str__(self):
        return f"{self.identificacion} - {'ENTRA' if self.es_entrada else 'SALE'} - {self.fecha_hora:%Y-%m-%d %H:%M}"







