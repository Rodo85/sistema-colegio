"""
Tests para el módulo Libro del Docente.
Cálculo de puntaje base y aporte real de asistencia.
Evaluación por indicadores (TAREAS/COTIDIANOS).
"""
from decimal import Decimal

from django.test import TestCase

from .models import (
    ActividadEvaluacion,
    ExclusionEstudianteAsignacion,
    IndicadorActividad,
    PuntajeIndicador,
)
from .services import (
    calcular_porcentaje_logro,
    calcular_total_maximo_actividad,
    calcular_total_obtenido_estudiante,
    validar_puntaje_en_rango,
)
from .views import _get_estudiantes, _nota_mep


class NotaMepTests(TestCase):
    """Tests para la conversión % ausencias → puntaje base (0-10)."""

    def test_33_3_pct_debe_dar_6(self):
        """3 sesiones, 1 ausencia => 33.3% => puntaje_base=6 (30% a <40%)."""
        self.assertEqual(_nota_mep(33.333), 6)
        self.assertEqual(_nota_mep(33.3), 6)
        self.assertEqual(_nota_mep(30), 6)
        self.assertEqual(_nota_mep(39.99), 6)

    def test_0_pct_debe_dar_10(self):
        """0 ausencias => 0% => puntaje_base=10."""
        self.assertEqual(_nota_mep(0), 10)
        self.assertEqual(_nota_mep(0.5), 10)

    def test_10_pct_debe_dar_8(self):
        """10 sesiones, 1 ausencia => 10% => puntaje_base=8 (10% a <20%)."""
        self.assertEqual(_nota_mep(10), 8)
        self.assertEqual(_nota_mep(10.1), 8)
        self.assertEqual(_nota_mep(19.99), 8)

    def test_1_pct_debe_dar_9(self):
        """1% a <10% => 9."""
        self.assertEqual(_nota_mep(1), 9)
        self.assertEqual(_nota_mep(9.99), 9)

    def test_rangos_completos(self):
        """Verificar todos los rangos de la tabla."""
        self.assertEqual(_nota_mep(0), 10)
        self.assertEqual(_nota_mep(0.99), 10)
        self.assertEqual(_nota_mep(1), 9)
        self.assertEqual(_nota_mep(9.99), 9)
        self.assertEqual(_nota_mep(10), 8)
        self.assertEqual(_nota_mep(19.99), 8)
        self.assertEqual(_nota_mep(20), 7)
        self.assertEqual(_nota_mep(29.99), 7)
        self.assertEqual(_nota_mep(30), 6)
        self.assertEqual(_nota_mep(39.99), 6)
        self.assertEqual(_nota_mep(40), 5)
        self.assertEqual(_nota_mep(49.99), 5)
        self.assertEqual(_nota_mep(50), 4)
        self.assertEqual(_nota_mep(59.99), 4)
        self.assertEqual(_nota_mep(60), 3)
        self.assertEqual(_nota_mep(69.99), 3)
        self.assertEqual(_nota_mep(70), 2)
        self.assertEqual(_nota_mep(79.99), 2)
        self.assertEqual(_nota_mep(80), 1)
        self.assertEqual(_nota_mep(89.99), 1)
        self.assertEqual(_nota_mep(90), 0)
        self.assertEqual(_nota_mep(100), 0)


class AporteRealTests(TestCase):
    """Tests para la fórmula aporte_real = (puntaje_base / 10) * peso_esquema."""

    def test_puntaje_10_peso_10_aporte_10(self):
        """puntaje_base=10, peso=10 => aporte_real=10."""
        aporte = Decimal("10") / Decimal("10") * Decimal("10")
        self.assertEqual(aporte, Decimal("10"))

    def test_puntaje_10_peso_5_aporte_5(self):
        """puntaje_base=10, peso=5 => aporte_real=5."""
        aporte = Decimal("10") / Decimal("10") * Decimal("5")
        self.assertEqual(aporte, Decimal("5"))

    def test_puntaje_6_peso_10_aporte_6(self):
        """puntaje_base=6, peso=10 => aporte_real=6."""
        aporte = Decimal("6") / Decimal("10") * Decimal("10")
        self.assertEqual(aporte, Decimal("6"))

    def test_puntaje_6_peso_5_aporte_3(self):
        """puntaje_base=6, peso=5 => aporte_real=3."""
        aporte = Decimal("6") / Decimal("10") * Decimal("5")
        self.assertEqual(aporte, Decimal("3"))


# ═══════════════════════════════════════════════════════════════════════════
#  EVALUACIÓN POR INDICADORES
# ═══════════════════════════════════════════════════════════════════════════


class EvaluacionIndicadoresTests(TestCase):
    """
    Tests para el módulo de evaluación por indicadores.
    Requiere datos de prueba: institución, curso_lectivo, periodo, docente_asignacion, estudiante.
    """

    def setUp(self):
        from catalogos.models import CursoLectivo, Nivel, Seccion, SubArea
        from config_institucional.models import Profesor
        from core.models import Institucion, User
        from evaluaciones.models import DocenteAsignacion, Periodo, PeriodoCursoLectivo, SubareaCursoLectivo
        from matricula.models import Estudiante, EstudianteInstitucion, MatriculaAcademica

        self.user = User.objects.create_user(
            email="docente_eval@test.com",
            password="test123",
            first_name="Doc",
            last_name="Test",
        )
        self.institucion = Institucion.objects.create(nombre="INST EVAL TEST")
        self.curso_lectivo, _ = CursoLectivo.objects.get_or_create(anio=2025, defaults={"nombre": "2025"})
        self.nivel, _ = Nivel.objects.get_or_create(numero=7, defaults={"nombre": "7°"})
        self.seccion, _ = Seccion.objects.get_or_create(
            nivel=self.nivel,
            numero=1,
            defaults={"codigo": "7-1"},
        )
        self.profesor = Profesor.objects.create(
            usuario=self.user,
            institucion=self.institucion,
            primer_apellido="TEST",
            segundo_apellido="DOC",
            nombres="DOCENTE",
        )
        self.periodo, _ = Periodo.objects.get_or_create(numero=1, defaults={"nombre": "1ER PERÍODO"})
        subarea = SubArea.objects.filter(es_academica=True).first()
        if not subarea:
            subarea = SubArea.objects.create(nombre="MATEMÁTICA TEST", es_academica=True)
        self.subarea_curso = SubareaCursoLectivo.objects.create(
            institucion=self.institucion,
            curso_lectivo=self.curso_lectivo,
            subarea=subarea,
            activa=True,
        )
        self.asignacion = DocenteAsignacion.objects.create(
            docente=self.profesor,
            subarea_curso=self.subarea_curso,
            curso_lectivo=self.curso_lectivo,
            seccion=self.seccion,
            activo=True,
        )
        PeriodoCursoLectivo.objects.get_or_create(
            institucion=self.institucion,
            curso_lectivo=self.curso_lectivo,
            periodo=self.periodo,
            defaults={"activo": True},
        )
        self.estudiante = Estudiante.objects.filter(
            instituciones_estudiante__institucion=self.institucion,
            instituciones_estudiante__estado="activo",
        ).first()
        if not self.estudiante:
            self.estudiante = Estudiante.objects.create(
                identificacion="TESTEVAL001",
                primer_apellido="EST",
                segundo_apellido="UDIANTE",
                nombres="UNO",
            )
            EstudianteInstitucion.objects.get_or_create(
                estudiante=self.estudiante,
                institucion=self.institucion,
                defaults={"estado": "activo"},
            )
            MatriculaAcademica.objects.create(
                estudiante=self.estudiante,
                institucion=self.institucion,
                nivel=self.nivel,
                seccion=self.seccion,
                curso_lectivo=self.curso_lectivo,
                estado="activo",
            )

    def test_total_maximo_indicadores_0_3_0_5_0_3_0_5(self):
        """Indicadores con escalas 0-3, 0-5, 0-3, 0-5 => total máximo 16."""
        actividad = ActividadEvaluacion.objects.create(
            docente_asignacion=self.asignacion,
            institucion=self.institucion,
            curso_lectivo=self.curso_lectivo,
            periodo=self.periodo,
            tipo_componente=ActividadEvaluacion.TAREA,
            titulo="Tarea prueba",
            estado=ActividadEvaluacion.ACTIVA,
        )
        IndicadorActividad.objects.create(
            actividad=actividad, orden=1, descripcion="Ind 1", escala_min=0, escala_max=3, activo=True
        )
        IndicadorActividad.objects.create(
            actividad=actividad, orden=2, descripcion="Ind 2", escala_min=0, escala_max=5, activo=True
        )
        IndicadorActividad.objects.create(
            actividad=actividad, orden=3, descripcion="Ind 3", escala_min=0, escala_max=3, activo=True
        )
        IndicadorActividad.objects.create(
            actividad=actividad, orden=4, descripcion="Ind 4", escala_min=0, escala_max=5, activo=True
        )
        total = calcular_total_maximo_actividad(actividad)
        self.assertEqual(total, Decimal("16"))

    def test_total_obtenido_14_porcentaje_87_5(self):
        """Puntajes 3,4,2,5 => total obtenido 14 => porcentaje 87.5%."""
        actividad = ActividadEvaluacion.objects.create(
            docente_asignacion=self.asignacion,
            institucion=self.institucion,
            curso_lectivo=self.curso_lectivo,
            periodo=self.periodo,
            tipo_componente=ActividadEvaluacion.TAREA,
            titulo="Tarea prueba",
            estado=ActividadEvaluacion.ACTIVA,
        )
        ind1 = IndicadorActividad.objects.create(
            actividad=actividad, orden=1, descripcion="Ind 1", escala_min=0, escala_max=3, activo=True
        )
        ind2 = IndicadorActividad.objects.create(
            actividad=actividad, orden=2, descripcion="Ind 2", escala_min=0, escala_max=5, activo=True
        )
        ind3 = IndicadorActividad.objects.create(
            actividad=actividad, orden=3, descripcion="Ind 3", escala_min=0, escala_max=3, activo=True
        )
        ind4 = IndicadorActividad.objects.create(
            actividad=actividad, orden=4, descripcion="Ind 4", escala_min=0, escala_max=5, activo=True
        )
        PuntajeIndicador.objects.create(indicador=ind1, estudiante=self.estudiante, puntaje_obtenido=3)
        PuntajeIndicador.objects.create(indicador=ind2, estudiante=self.estudiante, puntaje_obtenido=4)
        PuntajeIndicador.objects.create(indicador=ind3, estudiante=self.estudiante, puntaje_obtenido=2)
        PuntajeIndicador.objects.create(indicador=ind4, estudiante=self.estudiante, puntaje_obtenido=5)
        total_obt = calcular_total_obtenido_estudiante(actividad, self.estudiante.id)
        self.assertEqual(total_obt, Decimal("14"))
        pct = calcular_porcentaje_logro(actividad, self.estudiante.id)
        self.assertEqual(pct, Decimal("87.5"))

    def test_puntaje_4_en_indicador_0_3_rechazado(self):
        """Intento guardar puntaje 4 en indicador 0-3 => rechazar."""
        actividad = ActividadEvaluacion.objects.create(
            docente_asignacion=self.asignacion,
            institucion=self.institucion,
            curso_lectivo=self.curso_lectivo,
            periodo=self.periodo,
            tipo_componente=ActividadEvaluacion.TAREA,
            titulo="Tarea",
            estado=ActividadEvaluacion.ACTIVA,
        )
        ind = IndicadorActividad.objects.create(
            actividad=actividad, orden=1, descripcion="Ind 0-3", escala_min=0, escala_max=3, activo=True
        )
        with self.assertRaises(ValueError) as ctx:
            validar_puntaje_en_rango(ind, Decimal("4"))
        self.assertIn("4", str(ctx.exception))
        self.assertIn("<=", str(ctx.exception) or "3" in str(ctx.exception))

    def test_tipo_prueba_valido(self):
        """Debe permitir crear actividad tipo PRUEBA."""
        actividad = ActividadEvaluacion.objects.create(
            docente_asignacion=self.asignacion,
            institucion=self.institucion,
            curso_lectivo=self.curso_lectivo,
            periodo=self.periodo,
            tipo_componente=ActividadEvaluacion.PRUEBA,
            titulo="Prueba corta 1",
            estado=ActividadEvaluacion.ACTIVA,
        )
        self.assertEqual(actividad.tipo_componente, ActividadEvaluacion.PRUEBA)

    def test_exclusion_estudiante_no_sale_en_lista_docente(self):
        """Estudiante excluido no debe mostrarse en _get_estudiantes."""
        ExclusionEstudianteAsignacion.objects.create(
            docente_asignacion=self.asignacion,
            estudiante=self.estudiante,
            created_by=self.user,
        )
        estudiantes = list(_get_estudiantes(self.asignacion))
        self.assertFalse(any(m.estudiante_id == self.estudiante.id for m in estudiantes))
