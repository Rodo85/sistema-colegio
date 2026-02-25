"""
Formularios para el módulo de evaluación por indicadores.
"""
from django import forms
from django.forms import inlineformset_factory
from django.core.exceptions import ValidationError

from .models import ActividadEvaluacion, IndicadorActividad, PuntajeIndicador


class ActividadEvaluacionForm(forms.ModelForm):
    """Formulario para crear/editar ActividadEvaluacion."""

    class Meta:
        model = ActividadEvaluacion
        fields = [
            "titulo",
            "descripcion",
            "tipo_componente",
            "fecha_asignacion",
            "fecha_entrega",
            "estado",
        ]
        widgets = {
            "titulo": forms.TextInput(attrs={"class": "form-control", "maxlength": 200}),
            "descripcion": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "tipo_componente": forms.Select(attrs={"class": "form-control"}),
            "fecha_asignacion": forms.DateInput(attrs={"class": "form-control", "type": "date"}),
            "fecha_entrega": forms.DateInput(attrs={"class": "form-control", "type": "date"}),
            "estado": forms.Select(attrs={"class": "form-control"}),
        }

    def clean(self):
        data = super().clean()
        fa = data.get("fecha_asignacion")
        fe = data.get("fecha_entrega")
        if fa and fe and fe < fa:
            raise ValidationError("La fecha de entrega no puede ser anterior a la fecha de asignación.")
        return data


class IndicadorActividadForm(forms.ModelForm):
    """Formulario para crear/editar IndicadorActividad."""

    class Meta:
        model = IndicadorActividad
        fields = ["orden", "descripcion", "escala_min", "escala_max", "activo"]
        widgets = {
            "orden": forms.NumberInput(attrs={"class": "form-control", "min": 0}),
            "descripcion": forms.Textarea(attrs={"class": "form-control", "rows": 2}),
            "escala_min": forms.NumberInput(attrs={"class": "form-control", "step": "1", "min": "0"}),
            "escala_max": forms.NumberInput(attrs={"class": "form-control", "step": "1", "min": "0"}),
            "activo": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }

    def clean(self):
        data = super().clean()
        emin = data.get("escala_min")
        emax = data.get("escala_max")
        if emin is not None:
            if emin < 0:
                self.add_error("escala_min", "Debe ser un entero mayor o igual a 0.")
            elif emin != emin.to_integral_value():
                self.add_error("escala_min", "Debe ser un número entero (sin decimales).")
        if emax is not None:
            if emax < 0:
                self.add_error("escala_max", "Debe ser un entero mayor o igual a 0.")
            elif emax != emax.to_integral_value():
                self.add_error("escala_max", "Debe ser un número entero (sin decimales).")
        if emin is not None and emax is not None and emax < emin:
            raise ValidationError("escala_max debe ser >= escala_min.")
        return data


IndicadorActividadFormSet = inlineformset_factory(
    ActividadEvaluacion,
    IndicadorActividad,
    form=IndicadorActividadForm,
    extra=1,
    can_delete=True,
    min_num=0,
    validate_min=False,
    fields=["orden", "descripcion", "escala_min", "escala_max", "activo"],
)


class PuntajeIndicadorForm(forms.ModelForm):
    """Formulario para guardar puntaje de un estudiante en un indicador."""

    class Meta:
        model = PuntajeIndicador
        fields = ["puntaje_obtenido", "observacion"]
        widgets = {
            "puntaje_obtenido": forms.NumberInput(attrs={"class": "form-control", "step": "1", "min": "0"}),
            "observacion": forms.TextInput(attrs={"class": "form-control", "maxlength": 255}),
        }

    def __init__(self, *args, indicador=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.indicador = indicador

    def clean_puntaje_obtenido(self):
        valor = self.cleaned_data.get("puntaje_obtenido")
        if valor is not None and self.indicador:
            if valor < 0:
                raise ValidationError("Debe ser un entero mayor o igual a 0.")
            if valor != valor.to_integral_value():
                raise ValidationError("Debe ser un número entero (sin decimales).")
            if self.indicador.escala_min is not None and valor < self.indicador.escala_min:
                raise ValidationError(f"Debe ser >= {self.indicador.escala_min}.")
            if self.indicador.escala_max is not None and valor > self.indicador.escala_max:
                raise ValidationError(f"Debe ser <= {self.indicador.escala_max}.")
        return valor
