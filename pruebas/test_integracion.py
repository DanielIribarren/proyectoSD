"""Prueba de integración: levanta la nave y los 8 sensores como procesos y compara las decisiones."""
import os
import re
import subprocess
import sys
import threading
import time
import unittest

import cielo
import matriz

CARPETA = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PUERTO_PRUEBA = 5098
SEMILLA_PRUEBA = 19
TICKS_A_COMPROBAR = 5
SEGUNDOS_MAXIMOS = 40

LINEA_TICK = re.compile(r"Tick (\d+)\s+((?:\w+=[01?]\s*)+)->\s+(\w+)")


def esperado(numero):
    """Calcula la matriz y la decisión que le corresponden al tick según la semilla, sin usar sockets."""
    objetos = cielo.generar_cielo(SEMILLA_PRUEBA, numero)
    valores = {sector: cielo.valor_sector(objetos, sector) for sector in matriz.ANILLO}
    return valores, matriz.decidir(valores)


def leer_tick(linea):
    """Devuelve (numero, valores, decision) de una línea de la nave, o None si no es de un tick."""
    encontrada = LINEA_TICK.search(linea)
    if not encontrada:
        return None
    pares = [par.split('=') for par in encontrada.group(2).split()]
    valores = {sector: None if valor == '?' else int(valor) for sector, valor in pares}
    return int(encontrada.group(1)), valores, encontrada.group(3)


class PruebaIntegracion(unittest.TestCase):

    def lanzar(self, argumentos, **opciones):
        """Arranca un script del proyecto como proceso aparte y lo apaga al terminar la prueba."""
        proceso = subprocess.Popen([sys.executable, '-u'] + argumentos, cwd=CARPETA,
                                   stderr=subprocess.STDOUT, **opciones)
        self.addCleanup(self.apagar, proceso)
        return proceso

    @staticmethod
    def apagar(proceso):
        """Termina el proceso y cierra su salida."""
        proceso.terminate()
        try:
            proceso.wait(timeout=3)
        except subprocess.TimeoutExpired:
            proceso.kill()
            proceso.wait()
        if proceso.stdout:
            proceso.stdout.close()

    def test_cinco_ticks_coinciden_con_el_cielo(self):
        nave = self.lanzar(['nave.py', '--puerto', str(PUERTO_PRUEBA), '--semilla', str(SEMILLA_PRUEBA)],
                           stdout=subprocess.PIPE, text=True)
        salida = []
        threading.Thread(target=lambda: salida.extend(nave.stdout), daemon=True).start()
        time.sleep(0.5)
        for sector in matriz.ANILLO:
            self.lanzar(['sensor.py', sector, '--puerto', str(PUERTO_PRUEBA)], stdout=subprocess.DEVNULL)

        completos = []
        limite = time.time() + SEGUNDOS_MAXIMOS
        while len(completos) < TICKS_A_COMPROBAR and time.time() < limite:
            time.sleep(0.5)
            completos = [t for t in map(leer_tick, list(salida))
                         if t and None not in t[1].values()][:TICKS_A_COMPROBAR]
        self.assertEqual(len(completos), TICKS_A_COMPROBAR,
                         f"Solo salieron {len(completos)} ticks completos. Salida:\n{''.join(salida)}")

        for numero, valores, decision in completos:
            valores_esperados, decision_esperada = esperado(numero)
            with self.subTest(tick=numero):
                self.assertEqual(valores, valores_esperados)
                self.assertEqual(decision, decision_esperada)

        self.assertTrue(any('ALERTA ROJA' in linea for linea in salida), "No se vio ninguna alerta roja")


if __name__ == '__main__':
    unittest.main()