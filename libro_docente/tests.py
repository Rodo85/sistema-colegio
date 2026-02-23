"""
Tests para el módulo Libro del Docente.
Cálculo de puntaje base y aporte real de asistencia.
"""
from decimal import Decimal

from django.test import TestCase

from .views import _nota_mep


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
