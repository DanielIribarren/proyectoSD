"""Pruebas de cielo.py: mismo cielo en todos los procesos y variedad suficiente."""
import json
import os
import subprocess
import sys
import unittest

from cielo import generar_cielo, objetos_en_sector, valor_sector
from matriz import ANILLO

CARPETA = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TICKS_MUESTRA = 1000


def son_seguidos(sectores):
    """True si cada sector está pegado al anterior en el anillo (en cualquier sentido)."""
    for a, b in zip(sectores, sectores[1:]):
        distancia = (ANILLO.index(b) - ANILLO.index(a)) % 8
        if distancia not in (1, 7):
            return False
    return True


class PruebasDeterminismo(unittest.TestCase):

    def test_misma_semilla_y_tick_da_lo_mismo(self):
        self.assertEqual(generar_cielo(1234, 42), generar_cielo(1234, 42))

    def test_otro_proceso_genera_el_mismo_cielo(self):
        # Como los sensores: procesos distintos, cada uno con su Python, deben ver lo mismo
        codigo = 'import json, cielo; print(json.dumps([cielo.generar_cielo(1234, t) for t in range(20)]))'
        salida = subprocess.run([sys.executable, '-c', codigo], cwd=CARPETA, capture_output=True, text=True,
                                env={**os.environ, 'PYTHONHASHSEED': 'random'}, check=True).stdout
        self.assertEqual(json.loads(salida), [generar_cielo(1234, t) for t in range(20)])

    def test_otra_semilla_da_otro_cielo(self):
        cielos_a = [generar_cielo(1, t) for t in range(30)]
        cielos_b = [generar_cielo(2, t) for t in range(30)]
        self.assertNotEqual(cielos_a, cielos_b)


class PruebasVariedad(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.cielos = [generar_cielo(99, t) for t in range(TICKS_MUESTRA)]
        cls.objetos = [objeto for cielo in cls.cielos for objeto in cielo]

    def test_hay_ticks_vacios_y_rafagas(self):
        cantidades = {len(cielo) for cielo in self.cielos}
        self.assertEqual(cantidades, {0, 1, 2, 3})

    def test_aparecen_los_tres_tipos(self):
        self.assertEqual({o['tipo'] for o in self.objetos}, {'directa', 'tangente', 'rasante'})

    def test_salen_de_los_8_sectores(self):
        self.assertEqual({o['sectores'][0] for o in self.objetos}, set(ANILLO))

    def test_cantidad_de_sectores_segun_el_tipo(self):
        largos = {'directa': {1}, 'tangente': {2, 3}, 'rasante': {4}}
        for objeto in self.objetos:
            self.assertIn(len(objeto['sectores']), largos[objeto['tipo']])

    def test_las_trayectorias_son_seguidas_en_el_anillo(self):
        for objeto in self.objetos:
            self.assertTrue(son_seguidos(objeto['sectores']), objeto)

    def test_algunas_trayectorias_cruzan_el_borde_o_no(self):
        cruzan = [o for o in self.objetos if {'O', 'NO'} <= set(o['sectores'])]
        self.assertTrue(cruzan)

    def test_tamano_y_velocidad_varian(self):
        self.assertGreater(len({o['tamano'] for o in self.objetos}), 3)
        self.assertGreater(len({o['velocidad'] for o in self.objetos}), 20)

    def test_ids_unicos_por_tick(self):
        ids = [o['id'] for o in self.objetos]
        self.assertEqual(len(ids), len(set(ids)))


class PruebasSector(unittest.TestCase):

    def test_valor_y_objetos_de_un_sector(self):
        objetos = [{'id': '1-1', 'tipo': 'tangente', 'sectores': ['NE', 'E'], 'tamano': 2, 'velocidad': 10}]
        self.assertEqual(valor_sector(objetos, 'E'), 1)
        self.assertEqual(valor_sector(objetos, 'S'), 0)
        self.assertEqual(objetos_en_sector(objetos, 'NE'), objetos)
        self.assertEqual(objetos_en_sector(objetos, 'S'), [])


if __name__ == '__main__':
    unittest.main()
