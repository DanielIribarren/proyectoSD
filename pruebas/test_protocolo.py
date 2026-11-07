"""Pruebas de protocolo.py: mensajes pegados, cortados y mal formados."""
import logging
import socket
import unittest

from protocolo import enviar, leer_mensajes

logging.disable(logging.CRITICAL) # los avisos de mensajes mal formados ensucian la salida de las pruebas


class SocketFalso:
    """Imita un socket: cada recv() devuelve el siguiente pedazo de la lista, como si llegara así por la red."""

    def __init__(self, pedazos):
        self.pedazos = list(pedazos)

    def recv(self, tamano):
        if not self.pedazos:
            return b'' # igual que un socket cuando el otro lado cierra
        return self.pedazos.pop(0)


class PruebasProtocolo(unittest.TestCase):

    def test_un_mensaje(self):
        sock = SocketFalso([b'{"tipo": "HOLA", "sector": "N"}\n'])
        self.assertEqual(list(leer_mensajes(sock)), [{"tipo": "HOLA", "sector": "N"}])

    def test_dos_mensajes_pegados_en_un_recv(self):
        sock = SocketFalso([b'{"tipo": "LATIDO", "sector": "N"}\n{"tipo": "LATIDO", "sector": "E"}\n'])
        sectores = [m["sector"] for m in leer_mensajes(sock)]
        self.assertEqual(sectores, ["N", "E"])

    def test_mensaje_cortado_en_varios_recv(self):
        sock = SocketFalso([b'{"tipo": "REP', b'ORTE", "tick": 4', b'2, "valor": 1}\n'])
        self.assertEqual(list(leer_mensajes(sock)), [{"tipo": "REPORTE", "tick": 42, "valor": 1}])

    def test_letra_con_tilde_partida_entre_dos_recv(self):
        texto = '{"tipo": "RECHAZO", "motivo": "sector inválido"}\n'.encode('utf-8')
        corte = texto.index('á'.encode('utf-8')) + 1 # cae justo en la mitad de los 2 bytes de la 'á'
        sock = SocketFalso([texto[:corte], texto[corte:]])
        self.assertEqual(list(leer_mensajes(sock))[0]["motivo"], "sector inválido")

    def test_mensaje_mal_formado_se_ignora(self):
        sock = SocketFalso([b'esto no es json\n{"sin": "tipo"}\n{"tipo": "TICK", "tick": 1}\n'])
        self.assertEqual(list(leer_mensajes(sock)), [{"tipo": "TICK", "tick": 1}])

    def test_mensaje_a_medias_al_cerrar_se_descarta(self):
        sock = SocketFalso([b'{"tipo": "TICK", "tick": 1}\n{"tipo": "TI'])
        self.assertEqual(list(leer_mensajes(sock)), [{"tipo": "TICK", "tick": 1}])

    def test_ida_y_vuelta_por_sockets_reales(self):
        a, b = socket.socketpair()
        with a, b:
            self.assertTrue(enviar(a, {"tipo": "HOLA", "sector": "NE"}))
            self.assertTrue(enviar(a, {"tipo": "LATIDO", "sector": "NE"}))
            a.shutdown(socket.SHUT_WR) # avisa que no se manda nada más, así el generador termina
            tipos = [m["tipo"] for m in leer_mensajes(b)]
        self.assertEqual(tipos, ["HOLA", "LATIDO"])

    def test_enviar_a_socket_cerrado_devuelve_false(self):
        a, b = socket.socketpair()
        b.close()
        a.close()
        self.assertFalse(enviar(a, {"tipo": "LATIDO", "sector": "N"}))


if __name__ == '__main__':
    unittest.main()
