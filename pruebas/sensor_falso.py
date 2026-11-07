"""
Sensor falso para probar la nave mientras sensor.py no está listo.
Responde cada TICK con un valor al azar y manda un latido por segundo. No usa la semilla:
cuando tolerancia.auditar esté implementado, la nave lo va a mandar a cuarentena (es lo esperado).

Correr con:  python3 pruebas/sensor_falso.py N
"""
import os
import random
import socket
import sys
import threading
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__)))) # para importar protocolo.py
from protocolo import enviar, leer_mensajes

HOST = '127.0.0.1'
PUERTO_NAVE = 5050
PROBABILIDAD_DETECCION = 0.2


def latir(sock, sector):
    """Manda un LATIDO por segundo hasta que se corte la conexión."""
    while enviar(sock, {'tipo': 'LATIDO', 'sector': sector}):
        time.sleep(1)


def main():
    sector = sys.argv[1] if len(sys.argv) > 1 else 'N'
    with socket.create_connection((HOST, PUERTO_NAVE)) as sock:
        enviar(sock, {'tipo': 'HOLA', 'sector': sector})
        threading.Thread(target=latir, args=(sock, sector), daemon=True).start()
        for mensaje in leer_mensajes(sock):
            print(f"[{sector}] recibí {mensaje}")
            if mensaje['tipo'] == 'RECHAZO':
                break
            if mensaje['tipo'] == 'ORDEN' and mensaje['accion'] == 'apagar':
                break
            if mensaje['tipo'] == 'TICK':
                valor = 1 if random.random() < PROBABILIDAD_DETECCION else 0
                enviar(sock, {'tipo': 'REPORTE', 'tick': mensaje['tick'], 'sector': sector, 'valor': valor, 'objetos': []})


if __name__ == '__main__':
    main()
