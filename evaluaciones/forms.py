from django import forms

from catalogos.models import CursoLectivo, SubArea
from config_institucional.models import Profesor

from .models import DocenteAsignacion, EsquemaEval, PeriodoCursoLectivo, SubareaCursoLectivo


class SubareaCursoLectivoForm(forms.ModelForm):
    class Meta:
        model = SubareaCursoLectivo
        fields = ("subarea", "eval_scheme", "activa")
        widgets = {
            "subarea": forms.Select(attrs={"class": "form-control"}),
            "eval_scheme": forms.Select(attrs={"class": "form-control"}),
        }

    def __init__(self, *args, institucion=None, curso_lectivo=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["eval_scheme"].queryset = EsquemaEval.objects.filter(activo=True).order_by("tipo", "nombre")
        self.fields["eval_scheme"].empty_label = "— Sin esquema —"
        self.fields["subarea"].queryset = SubArea.objects.all().order_by("nombre")


class DocenteAsignacionForm(forms.ModelForm):
    class Meta:
        model = DocenteAsignacion
        fields = ("docente", "subarea_curso", "curso_lectivo", "seccion", "subgrupo", "activo")
        widgets = {
            "docente": forms.Select(attrs={"class": "form-control"}),
            "subarea_curso": forms.Select(attrs={"class": "form-control"}),
            "curso_lectivo": forms.Select(attrs={"class": "form-control"}),
            "seccion": forms.Select(attrs={"class": "form-control"}),
            "subgrupo": forms.Select(attrs={"class": "form-control"}),
        }

    def __init__(self, *args, institucion=None, curso_lectivo=None, **kwargs):
        super().__init__(*args, **kwargs)
        if institucion:
            self.fields["docente"].queryset = Profesor.objects.filter(
                institucion=institucion
            ).select_related("usuario").order_by("usuario__last_name")
            qs_scl = SubareaCursoLectivo.objects.filter(
                institucion=institucion, activa=True
            ).select_related("subarea", "curso_lectivo")
            if curso_lectivo:
                qs_scl = qs_scl.filter(curso_lectivo=curso_lectivo)
            self.fields["subarea_curso"].queryset = qs_scl.order_by("subarea__nombre")
        if curso_lectivo:
            self.fields["curso_lectivo"].initial = curso_lectivo
            self.fields["curso_lectivo"].queryset = CursoLectivo.objects.filter(pk=curso_lectivo.pk)


class PeriodoCursoLectivoForm(forms.ModelForm):
    class Meta:
        model = PeriodoCursoLectivo
        fields = ("periodo", "fecha_inicio", "fecha_fin", "activo")
        widgets = {
            "periodo": forms.Select(attrs={"class": "form-control"}),
            "fecha_inicio": forms.DateInput(attrs={"type": "date", "class": "form-control"}),
            "fecha_fin": forms.DateInput(attrs={"type": "date", "class": "form-control"}),
        }
