# catalogos/forms.py
import datetime
from django import forms
from .models import Especialidad

class EspecialidadForm(forms.ModelForm):
    class Meta:
        model = Especialidad
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        current_year = datetime.date.today().year
        # ej. 2025 → 2030  (ajuste el rango a su gusto)
        YEARS = [(y, y) for y in range(current_year, current_year + 3)]

        # Cambiamos el widget del campo 'año' a un Select
        self.fields["año"].widget = forms.Select(choices=YEARS)
        self.fields["año"].initial = current_year
