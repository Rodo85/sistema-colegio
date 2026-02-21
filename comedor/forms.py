from django import forms

from .models import ConfiguracionComedor


class ConfiguracionComedorForm(forms.ModelForm):
    intervalo_horas = forms.DecimalField(
        min_value=0.5,
        max_value=24,
        decimal_places=1,
        label="Intervalo mínimo entre registros (horas)",
        help_text=(
            "Tiempo mínimo que debe pasar entre dos registros del mismo estudiante. "
            "Ejemplo: 2.0 horas = puede registrar desayuno y almuerzo. "
            "20.0 horas = prácticamente una vez al día."
        ),
        widget=forms.NumberInput(attrs={"step": "0.5", "min": "0.5", "max": "24"}),
    )

    class Meta:
        model = ConfiguracionComedor
        exclude = ["intervalo_minutos"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            self.fields["intervalo_horas"].initial = round(self.instance.intervalo_minutos / 60, 1)
        else:
            self.fields["intervalo_horas"].initial = 20.0

    def save(self, commit=True):
        instance = super().save(commit=False)
        horas = self.cleaned_data.get("intervalo_horas") or 20
        instance.intervalo_minutos = int(float(horas) * 60)
        if commit:
            instance.save()
        return instance
