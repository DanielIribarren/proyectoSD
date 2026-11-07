"""Pruebas de nave.py: se levanta la nave como proceso aparte y se le conectan sensores de prueba."""
import os
import re
import socket
import subprocess
import sys
import threading
import time
import unittest

from protocolo import enviar, leer_mensajes

CARPETA = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PUERTO_PRUEBA = 5099 # distinto del 5050 para no chocar con una nave que esté corriendo
SEMILLA_PRUEBA = 7


def conectar(sector):
    """Abre un socket hacia la nave de prueba, manda HOLA y devuelve (socket, generador de mensajes)."""
    sock = socket.create_connection(('127.0.0.1', PUERTO_PRUEBA))
    sock.settimeout(5) # si la nave no contesta, la prueba falla en vez de quedarse colgada
    enviar(sock, {'tipo': 'HOLA', 'sector': sector})
    return sock, leer_mensajes(sock)


def esperar_tipo(mensajes, tipo):
    """Devuelve el primer mensaje del tipo pedido, saltando los demás."""
    for mensaje in mensajes:
        if mensaje['tipo'] == tipo:
            return mensaje
    raise AssertionError(f"La conexión se cerró sin recibir {tipo}")


class PruebasNave(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.nave = subprocess.Popen(
            [sys.executable, 'nave.py', '--puerto', str(PUERTO_PRUEBA), '--semilla', str(SEMILLA_PRUEBA)],
            cwd=CARPETA, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
        )
        # Un hilo va guardando lo que la nave imprime para poder buscarlo después
        cls.salida = []
        threading.Thread(target=lambda: cls.salida.extend(cls.nave.stdout), daemon=True).start()

        for _ in range(50): # espera hasta 5 s a que la nave abra el puerto
            try:
                socket.create_connection(('127.0.0.1', PUERTO_PRUEBA)).close()
                return
            except ConnectionRefusedError:
                time.sleep(0.1)
        raise RuntimeError("La nave no arrancó")

    @classmethod
    def tearDownClass(cls):
        cls.nave.terminate()
        cls.nave.wait()

    def esperar_linea(self, patron, segundos=5):
        """Espera a que la nave imprima una línea que cumpla el patrón."""
        limite = time.time() + segundos
        while time.time() < limite:
            for linea in list(self.salida):
                if re.search(patron, linea):
                    return linea
            time.sleep(0.05)
        self.fail(f"La nave no imprimió nada con {patron!r}. Salida:\n{''.join(self.salida)}")

    def test_bienvenida_trae_la_semilla(self):
        sock, mensajes = conectar('N')
        with sock:
            bienvenida = next(mensajes)
        self.assertEqual(bienvenida['tipo'], 'BIENVENIDA')
        self.assertEqual(bienvenida['semilla'], SEMILLA_PRUEBA)

    def test_sector_repetido_se_rechaza(self):
        primero, mensajes1 = conectar('NE')
        with primero:
            self.assertEqual(next(mensajes1)['tipo'], 'BIENVENIDA')
            segundo, mensajes2 = conectar('NE')
            with segundo:
                self.assertEqual(next(mensajes2)['tipo'], 'RECHAZO')

    def test_sector_invalido_se_rechaza(self):
        sock, mensajes = conectar('X')
        with sock:
            self.assertEqual(next(mensajes)['tipo'], 'RECHAZO')

    def test_reporte_entra_en_la_matriz_y_se_descartan_duplicados(self):
        sock_s, mensajes_s = conectar('S')
        sock_so, mensajes_so = conectar('SO')
        with sock_s, sock_so:
            # Se espera un tick que empiece con los dos ya conectados, así la nave espera a ambos
            objetivo = max(esperar_tipo(mensajes_s, 'TICK')['tick'], esperar_tipo(mensajes_so, 'TICK')['tick']) + 1
            while esperar_tipo(mensajes_s, 'TICK')['tick'] < objetivo:
                pass
            while esperar_tipo(mensajes_so, 'TICK')['tick'] < objetivo:
                pass

            reporte = {'tipo': 'REPORTE', 'tick': objetivo, 'sector': 'S', 'valor': 1, 'objetos': []}
            enviar(sock_s, reporte)
            enviar(sock_s, reporte) # repetido: el tick sigue abierto porque falta SO
            enviar(sock_s, {**reporte, 'sector': 'E'}) # S no puede reportar por E
            self.esperar_linea(rf"Reporte duplicado de S en el tick {objetivo}")
            self.esperar_linea(r"S mandó un reporte del sector E")

            enviar(sock_so, {**reporte, 'sector': 'SO', 'valor': 0})
            self.esperar_linea(rf"Tick {objetivo} .* S=1 SO=0 ")
        self.esperar_linea(r"Se desconectó el sensor S")

    def test_tick_se_cierra_aunque_el_sensor_no_reporte(self):
        sock, mensajes = conectar('O')
        with sock:
            numero = esperar_tipo(mensajes, 'TICK')['tick']
            self.esperar_linea(rf"Tick {numero} .* O=\? ")


if __name__ == '__main__':
    unittest.main()
