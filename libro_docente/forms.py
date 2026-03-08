"""
Formularios para el módulo de evaluación por indicadores.
"""
import re

from django import forms
from django.forms import inlineformset_factory
from django.core.exceptions import ValidationError

from catalogos.models import Especialidad, SubArea, TipoIdentificacion
from config_institucional.models import SeccionCursoLectivo, SubgrupoCursoLectivo
from evaluaciones.models import CentroTrabajo, DocenteAsignacion, EsquemaEval
from .models import ActividadEvaluacion, IndicadorActividad, PuntajeIndicador


class ActividadEvaluacionForm(forms.ModelForm):
    """Formulario para crear/editar ActividadEvaluacion."""

    class Meta:
        model = ActividadEvaluacion
        fields = [
            "titulo",
            "descripcion",
            "tipo_componente",
            "alcance_estudiantes",
            "puntaje_total",
            "porcentaje_actividad",
            "fecha_asignacion",
            "fecha_entrega",
            "estado",
        ]
        widgets = {
            "titulo": forms.TextInput(attrs={"class": "form-control", "maxlength": 200}),
            "descripcion": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "tipo_componente": forms.Select(attrs={"class": "form-control"}),
            "alcance_estudiantes": forms.Select(attrs={"class": "form-control"}),
            "puntaje_total": forms.NumberInput(attrs={"class": "form-control", "step": "1", "min": "0"}),
            "porcentaje_actividad": forms.NumberInput(attrs={"class": "form-control", "step": "1", "min": "0", "max": "100"}),
            "fecha_asignacion": forms.DateInput(attrs={"class": "form-control", "type": "date"}),
            "fecha_entrega": forms.DateInput(attrs={"class": "form-control", "type": "date"}),
            "estado": forms.Select(attrs={"class": "form-control"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        tipo = (
            self.data.get("tipo_componente")
            or self.initial.get("tipo_componente")
            or getattr(self.instance, "tipo_componente", None)
        )
        if tipo in (ActividadEvaluacion.TAREA, ActividadEvaluacion.COTIDIANO):
            self.fields["alcance_estudiantes"].choices = ActividadEvaluacion.ALCANCE_CHOICES
        else:
            self.fields["alcance_estudiantes"].choices = [
                (ActividadEvaluacion.ALCANCE_TODOS, "Asignar a todos")
            ]

    def clean(self):
        data = super().clean()
        fa = data.get("fecha_asignacion")
        fe = data.get("fecha_entrega")
        if fa and fe and fe < fa:
            raise ValidationError("La fecha de entrega no puede ser anterior a la fecha de asignación.")
        tipo = data.get("tipo_componente") or getattr(self.instance, "tipo_componente", None)
        if tipo in (ActividadEvaluacion.PRUEBA, ActividadEvaluacion.PROYECTO):
            pt = data.get("puntaje_total")
            pa = data.get("porcentaje_actividad")
            if pt is None or pt <= 0:
                self.add_error("puntaje_total", "Indique valor en puntos mayor a 0.")
            elif pt != pt.to_integral_value():
                self.add_error("puntaje_total", "Debe ser entero (sin decimales).")
            if pa is None or pa <= 0:
                self.add_error("porcentaje_actividad", "Indique valor en porcentaje mayor a 0.")
            elif pa != pa.to_integral_value():
                self.add_error("porcentaje_actividad", "Debe ser entero (sin decimales).")
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

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        min_permitido = 0
        if self.instance and self.instance.actividad_id:
            if self.instance.actividad.tipo_componente == ActividadEvaluacion.COTIDIANO:
                min_permitido = 1
        self.fields["escala_min"].widget.attrs["min"] = str(min_permitido)
        if not self.instance.pk and min_permitido == 1 and self.initial.get("escala_min") in (None, "", 0, "0"):
            self.initial["escala_min"] = 1

    def clean(self):
        data = super().clean()
        emin = data.get("escala_min")
        emax = data.get("escala_max")
        min_permitido = 0
        if self.instance and self.instance.actividad_id:
            if self.instance.actividad.tipo_componente == ActividadEvaluacion.COTIDIANO:
                min_permitido = 1
        if emin is not None:
            if emin < min_permitido:
                self.add_error("escala_min", f"Debe ser un entero mayor o igual a {min_permitido}.")
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
    extra=0,
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


class AsignacionOnboardingForm(forms.Form):
    CATEGORIA_ACADEMICA = "ACADEMICA"

    categoria = forms.ChoiceField(
        choices=(),
        label="Categoría",
        widget=forms.Select(attrs={"class": "form-control"}),
    )
    subarea = forms.ModelChoiceField(
        queryset=SubArea.objects.none(),
        label="Materia",
        widget=forms.Select(attrs={"class": "form-control"}),
    )
    eval_scheme = forms.ModelChoiceField(
        queryset=EsquemaEval.objects.none(),
        label="Esquema de evaluación",
        widget=forms.Select(attrs={"class": "form-control"}),
    )
    centro_trabajo = forms.ModelChoiceField(
        queryset=CentroTrabajo.objects.none(),
        required=False,
        label="Centro de trabajo",
        widget=forms.Select(attrs={"class": "form-control"}),
    )
    seccion = forms.ModelChoiceField(
        queryset=SeccionCursoLectivo.objects.none(),
        required=False,
        label="Grupo (Sección)",
        widget=forms.Select(attrs={"class": "form-control"}),
    )
    subgrupo = forms.ModelChoiceField(
        queryset=SubgrupoCursoLectivo.objects.none(),
        required=False,
        label="Subgrupo",
        widget=forms.Select(attrs={"class": "form-control"}),
    )
    nombre_corto = forms.CharField(
        required=False,
        max_length=20,
        label="Nombre corto (horario)",
        widget=forms.TextInput(
            attrs={"class": "form-control", "placeholder": "Ej: MAT, ESP, PROG"}
        ),
        help_text="Opcional. Si se define, se usa en el horario en lugar de siglas automáticas.",
    )

    def __init__(self, *args, institucion=None, curso_lectivo=None, profesor=None, asignacion=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.institucion = institucion
        self.curso_lectivo = curso_lectivo
        self.profesor = profesor
        self.asignacion = asignacion

        categorias = [(self.CATEGORIA_ACADEMICA, "Académica")]
        categorias += [
            (f"ESP_{esp.id}", esp.nombre)
            for esp in Especialidad.objects.order_by("nombre")
        ]
        self.fields["categoria"].choices = categorias

        if institucion and curso_lectivo:
            self.fields["subarea"].queryset = (
                SubArea.objects.all()
                .order_by("nombre")
            )
            self.fields["eval_scheme"].queryset = (
                EsquemaEval.objects.filter(activo=True)
                .prefetch_related("componentes_esquema__componente")
                .order_by("tipo", "nombre")
            )
            self.fields["seccion"].queryset = (
                SeccionCursoLectivo.objects.filter(
                    institucion=institucion,
                    curso_lectivo=curso_lectivo,
                    activa=True,
                )
                .select_related("seccion__nivel")
                .order_by("seccion__nivel__numero", "seccion__numero")
            )
            self.fields["subgrupo"].queryset = (
                SubgrupoCursoLectivo.objects.filter(
                    institucion=institucion,
                    curso_lectivo=curso_lectivo,
                    activa=True,
                )
                .select_related("subgrupo__seccion__nivel")
                .order_by("subgrupo__seccion__nivel__numero", "subgrupo__seccion__numero", "subgrupo__letra")
            )
            self.fields["centro_trabajo"].queryset = (
                CentroTrabajo.objects.filter(
                    docente=profesor,
                    institucion=institucion,
                    activo=True,
                ).order_by("nombre")
            )

        categoria_sel = self.data.get("categoria") or self.initial.get("categoria")
        if not categoria_sel:
            self.initial["categoria"] = self.CATEGORIA_ACADEMICA

        self.fields["seccion"].label_from_instance = self._label_seccion
        self.fields["subgrupo"].label_from_instance = self._label_subgrupo
        self.fields["eval_scheme"].label_from_instance = self._label_esquema

        seccion_sel = self.data.get("seccion") or self.initial.get("seccion")
        if seccion_sel:
            try:
                seccion_cl_id = int(seccion_sel)
                seccion_catalogo_id = (
                    self.fields["seccion"].queryset
                    .filter(pk=seccion_cl_id)
                    .values_list("seccion_id", flat=True)
                    .first()
                )
                if seccion_catalogo_id:
                    self.fields["subgrupo"].queryset = self.fields["subgrupo"].queryset.filter(
                        subgrupo__seccion_id=seccion_catalogo_id
                    )
            except (TypeError, ValueError):
                pass

        if asignacion and not self.is_bound:
            subarea_obj = getattr(getattr(asignacion, "subarea_curso", None), "subarea", None)
            if subarea_obj:
                if subarea_obj.es_academica:
                    self.initial.setdefault("categoria", self.CATEGORIA_ACADEMICA)
                elif subarea_obj.especialidad_id:
                    self.initial.setdefault("categoria", f"ESP_{subarea_obj.especialidad_id}")
                self.initial.setdefault("subarea", subarea_obj.id)
            esquema = asignacion.eval_scheme_snapshot or getattr(asignacion.subarea_curso, "eval_scheme", None)
            if esquema:
                self.initial.setdefault("eval_scheme", esquema.id)
            if asignacion.centro_trabajo_id:
                self.initial.setdefault("centro_trabajo", asignacion.centro_trabajo_id)
            if asignacion.seccion_id:
                sec_cl = self.fields["seccion"].queryset.filter(seccion_id=asignacion.seccion_id).first()
                if sec_cl:
                    self.initial.setdefault("seccion", sec_cl.id)
            if asignacion.subgrupo_id:
                sgr_cl = self.fields["subgrupo"].queryset.filter(subgrupo_id=asignacion.subgrupo_id).first()
                if sgr_cl:
                    self.initial.setdefault("subgrupo", sgr_cl.id)
            self.initial.setdefault("nombre_corto", (asignacion.nombre_corto or ""))

    @staticmethod
    def _label_seccion(seccion_cl):
        s = seccion_cl.seccion
        return f"{s.nivel.numero}-{s.numero}"

    @staticmethod
    def _label_subgrupo(subgrupo_cl):
        s = subgrupo_cl.subgrupo.seccion
        return f"{s.nivel.numero}-{s.numero}{subgrupo_cl.subgrupo.letra}"

    @staticmethod
    def _label_esquema(esquema):
        comps = list(getattr(esquema, "componentes_esquema", []).all()) if hasattr(esquema, "componentes_esquema") else []
        if not comps:
            return f"{esquema.nombre} (sin componentes)"
        parts = [f"{c.componente.codigo}={int(c.porcentaje) if c.porcentaje == int(c.porcentaje) else c.porcentaje}" for c in comps]
        return f"{esquema.nombre} — " + ", ".join(parts)

    def clean(self):
        cleaned = super().clean()
        categoria = cleaned.get("categoria")
        subarea = cleaned.get("subarea")
        sec_cl = cleaned.get("seccion")
        sgr_cl = cleaned.get("subgrupo")
        centro = cleaned.get("centro_trabajo")
        if not subarea:
            return cleaned
        if categoria == self.CATEGORIA_ACADEMICA and not subarea.es_academica:
            self.add_error("subarea", "La materia seleccionada no pertenece a la categoría Académica.")
        if categoria and categoria.startswith("ESP_"):
            try:
                esp_id = int(categoria.split("_", 1)[1])
            except (TypeError, ValueError):
                self.add_error("categoria", "La categoría seleccionada no es válida.")
                return cleaned
            if subarea.es_academica or subarea.especialidad_id != esp_id:
                self.add_error("subarea", "La materia seleccionada no corresponde a la especialidad elegida.")

        es_academica = subarea.es_academica
        if sec_cl and self.institucion and self.curso_lectivo:
            if sec_cl.institucion_id != self.institucion.id or sec_cl.curso_lectivo_id != self.curso_lectivo.id:
                self.add_error("seccion", "La sección seleccionada no pertenece al catálogo institucional activo.")
        if sgr_cl and self.institucion and self.curso_lectivo:
            if sgr_cl.institucion_id != self.institucion.id or sgr_cl.curso_lectivo_id != self.curso_lectivo.id:
                self.add_error("subgrupo", "El subgrupo seleccionado no pertenece al catálogo institucional activo.")

        if es_academica:
            if not sec_cl:
                self.add_error("seccion", "Debes seleccionar un grupo (sección) para esta materia.")
            if sgr_cl:
                self.add_error("subgrupo", "Esta materia académica no debe llevar subgrupo.")
        else:
            if not sgr_cl:
                self.add_error("subgrupo", "Debes seleccionar un subgrupo para esta materia técnica.")
            # Sección puede venir seleccionada solo para filtrar visualmente subgrupos.
            # Si viene, validamos coherencia con el subgrupo elegido y luego la ignoramos.
            if sec_cl and sgr_cl and sec_cl.seccion_id != sgr_cl.subgrupo.seccion_id:
                self.add_error("subgrupo", "El subgrupo elegido no pertenece al grupo seleccionado.")
            cleaned["seccion"] = None

        if self.institucion and getattr(self.institucion, "es_institucion_general", False):
            if not centro:
                self.add_error("centro_trabajo", "Debes seleccionar un centro de trabajo.")
        else:
            cleaned["centro_trabajo"] = None

        if self.profesor and subarea and self.curso_lectivo:
            dup = DocenteAsignacion.objects.filter(
                docente=self.profesor,
                subarea_curso__subarea=subarea,
                curso_lectivo=self.curso_lectivo,
            )
            if self.asignacion and self.asignacion.pk:
                dup = dup.exclude(pk=self.asignacion.pk)
            if self.institucion and getattr(self.institucion, "es_institucion_general", False):
                dup = dup.filter(centro_trabajo=centro)
            if sgr_cl:
                dup = dup.filter(subgrupo=sgr_cl.subgrupo)
            elif sec_cl:
                dup = dup.filter(seccion=sec_cl.seccion, subgrupo__isnull=True)
            if dup.exists():
                raise ValidationError("Ya tenés esta asignación creada.")
        return cleaned


class AsignacionEditForm(forms.Form):
    eval_scheme = forms.ModelChoiceField(
        queryset=EsquemaEval.objects.none(),
        label="Esquema de evaluación",
        widget=forms.Select(attrs={"class": "form-control"}),
    )
    nombre_corto = forms.CharField(
        required=False,
        max_length=20,
        label="Nombre corto (horario)",
        widget=forms.TextInput(
            attrs={"class": "form-control", "placeholder": "Ej: MAT, ESP, PROG"}
        ),
        help_text="Opcional. Si se define, se usa en el horario en lugar de siglas automáticas.",
    )

    def __init__(self, *args, asignacion=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.asignacion = asignacion
        self.fields["eval_scheme"].queryset = (
            EsquemaEval.objects.filter(activo=True)
            .prefetch_related("componentes_esquema__componente")
            .order_by("tipo", "nombre")
        )
        self.fields["eval_scheme"].label_from_instance = AsignacionOnboardingForm._label_esquema
        if asignacion and not self.is_bound:
            esquema = asignacion.eval_scheme_snapshot or getattr(asignacion.subarea_curso, "eval_scheme", None)
            if esquema:
                self.initial["eval_scheme"] = esquema.id
            self.initial["nombre_corto"] = (asignacion.nombre_corto or "")

class EstudianteCargaManualForm(forms.Form):
    tipo_identificacion = forms.ModelChoiceField(
        queryset=TipoIdentificacion.objects.order_by("nombre"),
        label="Tipo de identificación",
        widget=forms.Select(attrs={"class": "form-control"}),
    )
    identificacion = forms.CharField(
        label="Identificación",
        max_length=20,
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )
    primer_apellido = forms.CharField(
        label="Primer apellido",
        max_length=50,
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )
    segundo_apellido = forms.CharField(
        label="Segundo apellido",
        max_length=50,
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )
    nombres = forms.CharField(
        label="Nombre(s)",
        max_length=100,
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )

    def clean_identificacion(self):
        raw = (self.cleaned_data.get("identificacion") or "").strip().upper()
        return re.sub(r"[\s-]+", "", raw)

    def clean(self):
        cleaned = super().clean()
        tipo = cleaned.get("tipo_identificacion")
        identificacion = cleaned.get("identificacion") or ""
        tipo_nombre = (getattr(tipo, "nombre", "") or "").upper()
        if ("CÉDULA" in tipo_nombre or "CEDULA" in tipo_nombre) and identificacion:
            if not identificacion.isdigit() or len(identificacion) != 9:
                self.add_error(
                    "identificacion",
                    "Si es cédula de identidad debe tener exactamente 9 dígitos (ejemplo: 112280841).",
                )
        return cleaned
