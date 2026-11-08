"""Pruebas de puente.py: el panel recibe el estado de la nave y la nave recibe las órdenes del panel."""
import json
import logging
import queue
import unittest

import puente

try:
    from websockets.sync.client import connect
except ImportError:
    connect = None

logging.disable(logging.CRITICAL)

PUERTO_PRUEBA = 8799 # distinto del 8765 para no chocar con una nave que esté corriendo
ordenes = queue.Queue() # el puente llama al_recibir_orden desde su hilo; la cola lo pasa a la prueba


def conectar():
    """Abre un WebSocket hacia el puente de prueba, como lo haría el navegador."""
    return connect(f"ws://127.0.0.1:{PUERTO_PRUEBA}", open_timeout=3)


def estado_de_prueba(tick):
    """Estado mínimo con el formato del contrato."""
    return {'tick': tick, 'decision': 'ALERTA_ROJA', 'matriz': {'N': 1}, 'alertas': ['N'], 'maniobra': 'Evasión hacia NE'}


@unittest.skipIf(connect is None, "falta la librería websockets")
class PruebasPuente(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        # El puente vive todo el proceso (hilo daemon), así que se levanta una sola vez
        if puente.bucle is None:
            assert puente.iniciar_puente(ordenes.put, puerto=PUERTO_PRUEBA)

    def test_el_panel_recibe_el_estado_publicado(self):
        with conectar() as ws:
            puente.publicar(estado_de_prueba(1))
            # Puede llegar primero el último estado de otra prueba: se busca el del tick 1
            for _ in range(3):
                recibido = json.loads(ws.recv(timeout=3))
                if recibido['tick'] == 1:
                    break
            self.assertEqual(recibido, estado_de_prueba(1))

    def test_el_que_llega_tarde_recibe_el_ultimo_estado(self):
        with conectar() as ws:
            puente.publicar(estado_de_prueba(2))
            while json.loads(ws.recv(timeout=3))['tick'] != 2:
                pass
        with conectar() as tarde:
            self.assertEqual(json.loads(tarde.recv(timeout=3))['tick'], 2)

    def test_la_nave_recibe_las_ordenes(self):
        with conectar() as ws:
            ws.send(json.dumps({'accion': 'alien', 'sector': 'NE'}))
            self.assertEqual(ordenes.get(timeout=3), {'accion': 'alien', 'sector': 'NE'})

    def test_orden_mal_formada_se_ignora(self):
        with conectar() as ws:
            ws.send('esto no es json')
            ws.send(json.dumps(['tampoco', 'un', 'dict']))
            ws.send(json.dumps({'accion': 'normal', 'sector': 'S'}))
            # Solo la tercera llega a la nave, y el puente sigue atendiendo
            self.assertEqual(ordenes.get(timeout=3), {'accion': 'normal', 'sector': 'S'})
            self.assertTrue(ordenes.empty())

    def test_publicar_sin_puente_no_falla(self):
        bucle = puente.bucle
        puente.bucle = None
        try:
            puente.publicar(estado_de_prueba(3)) # la nave sin panel no se puede caer por esto
        finally:
            puente.bucle = bucle

    def test_puerto_ocupado_no_tumba_a_la_nave(self):
        bucle = puente.bucle
        self.assertFalse(puente.iniciar_puente(ordenes.put, puerto=PUERTO_PRUEBA))
        self.assertIs(puente.bucle, bucle) # el intento fallido no deja sin bucle al puente que ya andaba


if __name__ == '__main__':
    unittest.main()
