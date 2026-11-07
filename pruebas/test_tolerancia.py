"""Pruebas de tolerancia.py: sensores caídos, elección de quién cubre y auditoría."""
import unittest

from tolerancia import LIMITE_LATIDO, auditar, elegir_cubridor, sectores_caidos


class PruebasCaidos(unittest.TestCase):

    def test_solo_cae_el_que_pasa_el_limite(self):
        ultimo_latido = {'N': 100.0, 'E': 100.0 - LIMITE_LATIDO - 0.1, 'S': 99.0}
        self.assertEqual(sectores_caidos(ultimo_latido, 100.0), ['E'])

    def test_sin_latidos_no_hay_caidos(self):
        self.assertEqual(sectores_caidos({}, 100.0), [])


class PruebasCubridor(unittest.TestCase):

    def test_prefiere_el_vecino_horario(self):
        self.assertEqual(elegir_cubridor('N', {'NO', 'NE'}), 'NE')

    def test_si_el_horario_no_esta_usa_el_antihorario(self):
        self.assertEqual(elegir_cubridor('N', {'NO', 'S'}), 'NO')

    def test_da_la_vuelta_por_el_borde(self):
        self.assertEqual(elegir_cubridor('O', {'NO', 'S'}), 'NO')

    def test_si_los_vecinos_cayeron_busca_mas_lejos(self):
        self.assertEqual(elegir_cubridor('N', {'E'}), 'E')

    def test_sin_sensores_vivos_devuelve_none(self):
        self.assertIsNone(elegir_cubridor('N', set()))


class PruebasAuditoria(unittest.TestCase):

    def test_reporte_correcto_es_ok(self):
        fallas = {}
        self.assertEqual(auditar('NE', 1, 1, fallas), 'OK')
        self.assertEqual(fallas, {})

    def test_tres_mentiras_llevan_a_cuarentena(self):
        fallas = {}
        self.assertEqual(auditar('NE', 1, 0, fallas), 'SOSPECHOSO')
        self.assertEqual(auditar('NE', 0, 0, fallas), 'OK') # un reporte bueno no borra las fallas
        self.assertEqual(auditar('NE', 0, 1, fallas), 'SOSPECHOSO')
        self.assertEqual(auditar('NE', 1, 0, fallas), 'CUARENTENA')
        self.assertEqual(fallas['NE'], 3)

    def test_las_fallas_son_de_cada_sector(self):
        fallas = {'E': 2}
        self.assertEqual(auditar('NE', 1, 0, fallas), 'SOSPECHOSO')
        self.assertEqual(fallas, {'E': 2, 'NE': 1})


if __name__ == '__main__':
    unittest.main()
