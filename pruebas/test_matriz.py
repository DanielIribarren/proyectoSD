"""Pruebas de matriz.py: casos del enunciado, bordes del anillo y las 256 combinaciones posibles."""
import itertools
import unittest

from matriz import ANILLO, decidir, elegir_maniobra, sectores_en_alerta, texto_matriz


def matriz_con(*sectores_en_1):
    """Arma una matriz con 1 en los sectores dados y 0 en el resto."""
    return {sector: (1 if sector in sectores_en_1 else 0) for sector in ANILLO}


def grupos_de_unos(valores):
    """Otra forma de ver la regla, para comparar: separa el anillo en grupos de 1 seguidos y devuelve sus tamaños."""
    lista = [valores[sector] for sector in ANILLO]
    if all(lista):
        return [8]
    inicio = lista.index(0) # se empieza a recorrer desde un 0 para no partir un grupo que da la vuelta
    girada = lista[inicio:] + lista[:inicio]
    return [len(list(grupo)) for valor, grupo in itertools.groupby(girada) if valor == 1]


class PruebasEnunciado(unittest.TestCase):
    """Los 5 estados de la página 4 y la figura de la página 3."""

    def test_estado_1_sin_amenazas(self):
        self.assertEqual(decidir(matriz_con()), 'SIN_AMENAZA')

    def test_estado_2_objeto_desde_n(self):
        self.assertEqual(decidir(matriz_con('N')), 'ALERTA_ROJA')

    def test_estado_3_columna_este(self):
        self.assertEqual(decidir(matriz_con('NE', 'E')), 'TRANSITO_SEGURO')

    def test_estado_4_objeto_desde_o(self):
        self.assertEqual(decidir(matriz_con('O')), 'ALERTA_ROJA')

    def test_estado_5_objeto_desde_no(self):
        self.assertEqual(decidir(matriz_con('NO')), 'ALERTA_ROJA')

    def test_figura_n_y_e_no_son_vecinos(self):
        self.assertEqual(sectores_en_alerta(matriz_con('N', 'E')), ['N', 'E'])

    def test_columna_este_completa(self):
        self.assertEqual(decidir(matriz_con('NE', 'E', 'SE')), 'TRANSITO_SEGURO')


class PruebasBordes(unittest.TestCase):
    """Casos límite que pide la rúbrica."""

    def test_o_y_no_son_vecinos_porque_el_anillo_da_la_vuelta(self):
        self.assertEqual(decidir(matriz_con('O', 'NO')), 'TRANSITO_SEGURO')

    def test_grupo_que_da_la_vuelta_por_el_borde(self):
        self.assertEqual(decidir(matriz_con('SO', 'O', 'NO', 'N')), 'TRANSITO_SEGURO')

    def test_transito_y_amenaza_a_la_vez_gana_la_alerta(self):
        valores = matriz_con('NE', 'E', 'SO')
        self.assertEqual(decidir(valores), 'ALERTA_ROJA')
        self.assertEqual(sectores_en_alerta(valores), ['SO'])

    def test_todo_el_anillo_en_1(self):
        self.assertEqual(decidir(matriz_con(*ANILLO)), 'TRANSITO_SEGURO')

    def test_alternados_son_todos_amenazas(self):
        self.assertEqual(sectores_en_alerta(matriz_con('NO', 'NE', 'SE', 'SO')), ['NO', 'NE', 'SE', 'SO'])

    def test_sector_sin_dato_cuenta_como_0(self):
        valores = matriz_con('N')
        valores['NE'] = None
        self.assertEqual(decidir(valores), 'ALERTA_ROJA')

    def test_sector_sin_dato_no_da_alerta_solo(self):
        valores = matriz_con()
        valores['S'] = None
        self.assertEqual(decidir(valores), 'SIN_AMENAZA')


class PruebasTodasLasCombinaciones(unittest.TestCase):

    def test_las_256_combinaciones(self):
        for bits in itertools.product([0, 1], repeat=8):
            valores = dict(zip(ANILLO, bits))
            grupos = grupos_de_unos(valores)
            if 1 in grupos:
                esperado = 'ALERTA_ROJA'
            elif grupos:
                esperado = 'TRANSITO_SEGURO'
            else:
                esperado = 'SIN_AMENAZA'
            with self.subTest(matriz=bits):
                self.assertEqual(decidir(valores), esperado)
                self.assertEqual(len(sectores_en_alerta(valores)), grupos.count(1))


class PruebasManiobraYTexto(unittest.TestCase):

    def test_una_amenaza_evade_de_costado(self):
        self.assertEqual(elegir_maniobra(['N']), 'Evasión hacia E')
        self.assertEqual(elegir_maniobra(['SO']), 'Evasión hacia NO') # da la vuelta al anillo

    def test_varias_amenazas_activan_escudos(self):
        self.assertTrue(elegir_maniobra(['N', 'S']).startswith('Escudos activados'))

    def test_texto_como_el_enunciado(self):
        valores = matriz_con('N')
        valores['SE'] = None
        self.assertEqual(texto_matriz(valores), '\n'.join([
            '[ NO N  NE ]   [ 0 1 0 ]',
            '[ O  x  E  ]   [ 0 x 0 ]',
            '[ SO S  SE ]   [ 0 0 ? ]',
        ]))


if __name__ == '__main__':
    unittest.main()
