"""
Pruebas de la nave ante fallas: latidos, cobertura, cuarentena y órdenes del panel.
Se llama directo a las funciones del hilo procesador. Las funciones de tolerancia.py y
puente.py se reemplazan con mock para probar la nave aunque Juan y Derek no hayan terminado.
"""
import socket
import time
import unittest
from unittest import mock

import nave
from protocolo import leer_mensajes


class PruebasFallas(unittest.TestCase):

    def setUp(self):
        # Cada prueba arranca con la nave vacía
        nave.sensores.clear()
        nave.estado_sensor.clear()
        nave.ultimo_latido.clear()
        nave.cobertura.clear()
        nave.fallas.clear()
        nave.tick.update(numero=0, abierto=False, limite=0.0, esperados=set(), reportes={}, cielo=[])
        self.del_sensor = {} # sector -> el otro extremo del socket, lo que "recibe" el sensor

    def tearDown(self):
        for sock in list(nave.sensores.values()) + list(self.del_sensor.values()):
            sock.close()

    def conectar(self, sector):
        """Conecta un sensor de mentira y procesa su CONEXION."""
        lado_nave, lado_sensor = socket.socketpair()
        lado_sensor.settimeout(1)
        nave.sensores[sector] = lado_nave
        self.del_sensor[sector] = lado_sensor
        nave.atender_evento({'tipo': 'CONEXION', 'remitente': sector, 'mensaje': None})

    def recibido(self, sector):
        """Devuelve el siguiente mensaje que la nave le mandó a ese sensor."""
        return next(leer_mensajes(self.del_sensor[sector]))

    @mock.patch('tolerancia.elegir_cubridor', return_value='NE')
    @mock.patch('tolerancia.sectores_caidos', return_value=['N'])
    def test_sensor_sin_latidos_queda_caido_y_un_vecino_lo_cubre(self, _caidos, _cubridor):
        self.conectar('N')
        self.conectar('NE')
        nave.atender_evento({'tipo': 'REVISION', 'remitente': None, 'mensaje': None})

        self.assertEqual(nave.estado_sensor['N'], 'CAIDO')
        self.assertEqual(nave.cobertura, {'NE': ['N']})
        self.assertEqual(self.recibido('NE'), {'tipo': 'COBERTURA', 'sectores': ['N']})
        self.assertEqual(self.del_sensor['N'].recv(10), b'') # la nave le cortó la conexión

    @mock.patch('tolerancia.elegir_cubridor', return_value='NE')
    def test_cuando_el_sensor_vuelve_el_vecino_suelta_el_sector(self, _cubridor):
        self.conectar('N')
        self.conectar('NE')
        nave.atender_evento({'tipo': 'DESCONEXION', 'remitente': 'N', 'mensaje': None})
        self.assertEqual(self.recibido('NE')['sectores'], ['N'])

        self.conectar('N')
        self.assertEqual(nave.cobertura, {})
        self.assertEqual(self.recibido('NE'), {'tipo': 'COBERTURA', 'sectores': []})

    def test_reporte_de_un_sector_cubierto_se_acepta(self):
        self.conectar('NE')
        nave.cobertura['NE'] = ['N']
        nave.tick.update(numero=5, abierto=True)
        nave.recibir_reporte('NE', {'tick': 5, 'sector': 'N', 'valor': 1})
        self.assertEqual(nave.tick['reportes'], {'N': 1})

    @mock.patch('tolerancia.elegir_cubridor', return_value='E')
    @mock.patch('tolerancia.auditar', return_value='CUARENTENA')
    def test_sensor_que_miente_va_a_cuarentena(self, _auditar, _cubridor):
        self.conectar('NE')
        self.conectar('E')
        nave.tick.update(numero=3, abierto=True)

        nave.recibir_reporte('NE', {'tick': 3, 'sector': 'NE', 'valor': 1})
        self.assertEqual(nave.estado_sensor['NE'], 'CUARENTENA')
        self.assertEqual(nave.tick['reportes'], {}) # el reporte que lo delató no se usa
        self.assertEqual(nave.cobertura, {'E': ['NE']})

        nave.tick['numero'] = 4
        nave.recibir_reporte('NE', {'tick': 4, 'sector': 'NE', 'valor': 1})
        self.assertEqual(nave.tick['reportes'], {}) # en cuarentena no se le cree nada

    def test_orden_del_panel_llega_al_sensor_y_normal_quita_la_cuarentena(self):
        self.conectar('SO')
        nave.estado_sensor['SO'] = 'CUARENTENA'
        nave.fallas['SO'] = 3

        nave.atender_evento({'tipo': 'ORDEN', 'remitente': None, 'mensaje': {'accion': 'normal', 'sector': 'SO'}})
        self.assertEqual(self.recibido('SO'), {'tipo': 'ORDEN', 'accion': 'normal'})
        self.assertEqual(nave.estado_sensor['SO'], 'ACTIVO')
        self.assertEqual(nave.fallas['SO'], 0)

    def test_orden_invalida_se_ignora(self):
        self.conectar('SO')
        nave.atender_orden({'accion': 'explotar', 'sector': 'SO'})
        with self.assertRaises(socket.timeout):
            self.del_sensor['SO'].recv(10)

    @mock.patch('puente.publicar')
    def test_al_cerrar_el_tick_se_publica_el_estado(self, publicar):
        self.conectar('N')
        nave.tick.update(numero=8, abierto=True, reportes={'N': 1})
        nave.cerrar_tick()

        estado = publicar.call_args.args[0]
        self.assertEqual(estado['tick'], 8)
        self.assertEqual(estado['matriz']['N'], 1)
        self.assertIsNone(estado['matriz']['S']) # sin dato
        self.assertEqual(estado['sensores']['N']['estado'], 'ACTIVO')
        self.assertEqual(set(estado), {'tick', 'semilla', 'matriz', 'decision', 'alertas', 'maniobra', 'sensores', 'eventos'})

    def test_el_tick_espera_tambien_a_los_sectores_cubiertos(self):
        self.conectar('NE')
        nave.cobertura['NE'] = ['N']
        nave.abrir_tick()
        self.assertEqual(nave.tick['esperados'], {'NE', 'N'})
        self.assertEqual(self.recibido('NE'), {'tipo': 'TICK', 'tick': 1})


if __name__ == '__main__':
    unittest.main()
