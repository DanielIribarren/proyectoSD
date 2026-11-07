"""
Pruebas de sensor.py: se levanta el sensor como proceso aparte y la prueba hace de nave.
Así se prueba el sensor sin depender de nave.py.
"""
import os
import socket
import subprocess
import sys
import unittest

import cielo
from protocolo import enviar, leer_mensajes

CARPETA = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SEMILLA_PRUEBA = 11


class PruebasSensor(unittest.TestCase):

    def setUp(self):
        self.servidor = socket.socket()
        self.servidor.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.servidor.bind(('127.0.0.1', 0)) # puerto 0: el sistema elige uno libre
        self.servidor.listen()
        self.servidor.settimeout(5)
        puerto = self.servidor.getsockname()[1]
        self.sensor = subprocess.Popen([sys.executable, 'sensor.py', 'NE', '--puerto', str(puerto)],
                                       cwd=CARPETA, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    def tearDown(self):
        self.sensor.kill()
        self.sensor.wait()
        self.servidor.close()

    def aceptar(self):
        """Acepta la conexión del sensor y devuelve (socket, generador de mensajes)."""
        conn, _ = self.servidor.accept()
        conn.settimeout(5)
        return conn, leer_mensajes(conn)

    def siguiente(self, mensajes, tipo):
        """Devuelve el siguiente mensaje del tipo pedido, saltando los latidos y lo demás."""
        for mensaje in mensajes:
            if mensaje['tipo'] == tipo:
                return mensaje
        self.fail(f"El sensor cerró sin mandar {tipo}")

    def dar_bienvenida(self):
        conn, mensajes = self.aceptar()
        self.assertEqual(next(mensajes), {'tipo': 'HOLA', 'sector': 'NE'})
        enviar(conn, {'tipo': 'BIENVENIDA', 'semilla': SEMILLA_PRUEBA, 'tick_actual': 0})
        return conn, mensajes

    def test_reporta_lo_mismo_que_dice_la_semilla(self):
        conn, mensajes = self.dar_bienvenida()
        with conn:
            for numero in range(1, 6):
                enviar(conn, {'tipo': 'TICK', 'tick': numero})
                reporte = self.siguiente(mensajes, 'REPORTE')
                objetos = cielo.generar_cielo(SEMILLA_PRUEBA, numero)
                self.assertEqual(reporte['tick'], numero)
                self.assertEqual(reporte['sector'], 'NE')
                self.assertEqual(reporte['valor'], cielo.valor_sector(objetos, 'NE'))
                self.assertEqual(reporte['objetos'], cielo.objetos_en_sector(objetos, 'NE'))

    def test_manda_latidos(self):
        conn, mensajes = self.dar_bienvenida()
        with conn:
            self.assertEqual(self.siguiente(mensajes, 'LATIDO'), {'tipo': 'LATIDO', 'sector': 'NE'})
            self.assertEqual(self.siguiente(mensajes, 'LATIDO'), {'tipo': 'LATIDO', 'sector': 'NE'})

    def test_con_cobertura_reporta_tambien_el_sector_ajeno(self):
        conn, mensajes = self.dar_bienvenida()
        with conn:
            enviar(conn, {'tipo': 'COBERTURA', 'sectores': ['N']})
            enviar(conn, {'tipo': 'TICK', 'tick': 7})
            sectores = [self.siguiente(mensajes, 'REPORTE')['sector'] for _ in range(2)]
            self.assertEqual(sectores, ['NE', 'N'])

            enviar(conn, {'tipo': 'COBERTURA', 'sectores': []}) # vuelve a solo el suyo
            enviar(conn, {'tipo': 'TICK', 'tick': 8})
            enviar(conn, {'tipo': 'TICK', 'tick': 9})
            reportes = [self.siguiente(mensajes, 'REPORTE') for _ in range(2)]
            self.assertEqual([(r['tick'], r['sector']) for r in reportes], [(8, 'NE'), (9, 'NE')])

    def test_orden_apagar_termina_el_proceso(self):
        conn, _ = self.dar_bienvenida()
        with conn:
            enviar(conn, {'tipo': 'ORDEN', 'accion': 'apagar'})
            self.assertEqual(self.sensor.wait(timeout=5), 0)

    def test_si_lo_rechazan_se_apaga(self):
        conn, mensajes = self.aceptar()
        with conn:
            next(mensajes)
            enviar(conn, {'tipo': 'RECHAZO', 'motivo': 'el sector NE ya está conectado'})
            self.assertEqual(self.sensor.wait(timeout=5), 0)

    def test_si_se_corta_la_conexion_vuelve_a_conectarse(self):
        conn, _ = self.dar_bienvenida()
        conn.close()
        conn2, mensajes2 = self.aceptar()
        with conn2:
            self.assertEqual(next(mensajes2), {'tipo': 'HOLA', 'sector': 'NE'})

    def test_en_modo_alien_miente_a_veces(self):
        conn, mensajes = self.dar_bienvenida()
        with conn:
            enviar(conn, {'tipo': 'ORDEN', 'accion': 'alien'})
            mentiras = 0
            for numero in range(1, 41):
                enviar(conn, {'tipo': 'TICK', 'tick': numero})
                reporte = self.siguiente(mensajes, 'REPORTE')
                if reporte['valor'] != cielo.valor_sector(cielo.generar_cielo(SEMILLA_PRUEBA, numero), 'NE'):
                    mentiras += 1
            # Con probabilidad 0,5 en 40 ticks, que salgan menos de 5 mentiras es casi imposible
            self.assertGreater(mentiras, 5)
            self.assertLess(mentiras, 40)


if __name__ == '__main__':
    unittest.main()
