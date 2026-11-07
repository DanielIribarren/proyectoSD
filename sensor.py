"""
Sensor de un sector. Se conecta a la nave, genera el cielo con la semilla y reporta su sector.
Responsable: Jesus (E2).

Correr con:  python3 sensor.py NE [--alien] [--puerto 5050]

Hilos del sensor:
- principal: recibe los mensajes de la nave (TICK, COBERTURA, ORDEN) y responde.
- latir: manda un LATIDO cada SEGUNDOS_LATIDO para que la nave sepa que sigue vivo.
"""
import argparse
import random
import socket
import threading
import time

import cielo
from matriz import ANILLO
from protocolo import enviar, leer_mensajes

HOST = '127.0.0.1'
PUERTO_NAVE = 5050
SEGUNDOS_LATIDO = 1.0
SEGUNDOS_REINTENTO = 2.0 # si la nave no está, se vuelve a intentar cada 2 s
PROBABILIDAD_MENTIRA = 0.5 # en modo alien, cuántas veces cambia lo que ve

modo = {'alien': False} # lo cambia la ORDEN de la nave; dura aunque el sensor se reconecte


def latir(sock, sector, detener):
    """Manda un LATIDO cada SEGUNDOS_LATIDO hasta que se corte la conexión o se pida parar."""
    while not detener.is_set():
        if not enviar(sock, {'tipo': 'LATIDO', 'sector': sector}):
            return
        detener.wait(SEGUNDOS_LATIDO) # como sleep, pero se despierta apenas se pide parar


def reportar(sock, sector, cubre, semilla, numero):
    """Manda un REPORTE por su sector y otro por cada sector que esté cubriendo."""
    objetos = cielo.generar_cielo(semilla, numero)
    for actual in [sector] + cubre:
        vistos = cielo.objetos_en_sector(objetos, actual)
        valor = 1 if vistos else 0
        if modo['alien'] and random.random() < PROBABILIDAD_MENTIRA:
            valor = 1 - valor # el alien cambia lo que ve el sensor

        enviar(sock, {'tipo': 'REPORTE', 'tick': numero, 'sector': actual, 'valor': valor, 'objetos': vistos})
        if valor:
            detalle = ', '.join(f"{o['tipo']} {'-'.join(o['sectores'])} ({o['velocidad']} km/s)" for o in vistos)
            print(f"[{sector}] tick {numero}: detección en {actual}: {detalle or 'nada (alien)'}")


def conectar(sector, puerto):
    """Intenta conectarse a la nave hasta lograrlo."""
    while True:
        try:
            return socket.create_connection((HOST, puerto))
        except OSError:
            print(f"[{sector}] La nave no responde, reintento en {SEGUNDOS_REINTENTO:.0f} s")
            time.sleep(SEGUNDOS_REINTENTO)


def sesion(sector, puerto):
    """Una conexión completa con la nave. Devuelve True si hay que reconectar, False si hay que apagarse."""
    sock = conectar(sector, puerto)
    detener = threading.Event()
    with sock:
        enviar(sock, {'tipo': 'HOLA', 'sector': sector})
        mensajes = leer_mensajes(sock)
        respuesta = next(mensajes, None)
        if respuesta is None:
            return True
        if respuesta['tipo'] == 'RECHAZO':
            print(f"[{sector}] La nave me rechazó: {respuesta['motivo']}")
            return False

        semilla = respuesta['semilla']
        cubre = [] # sectores ajenos que la nave me pidió reportar
        print(f"[{sector}] Conectado a la nave. Semilla {semilla}")
        threading.Thread(target=latir, args=(sock, sector, detener), daemon=True).start()

        try:
            for mensaje in mensajes:
                if mensaje['tipo'] == 'TICK':
                    reportar(sock, sector, cubre, semilla, mensaje['tick'])
                elif mensaje['tipo'] == 'COBERTURA':
                    cubre = [s for s in mensaje['sectores'] if s in ANILLO and s != sector]
                    print(f"[{sector}] Ahora cubro también: {', '.join(cubre) or 'nada'}")
                elif mensaje['tipo'] == 'ORDEN':
                    if mensaje['accion'] == 'apagar':
                        print(f"[{sector}] La nave pidió apagarme")
                        return False
                    modo['alien'] = mensaje['accion'] == 'alien'
                    print(f"[{sector}] Modo {'ALIEN' if modo['alien'] else 'normal'}")
        finally:
            detener.set()

    print(f"[{sector}] Se perdió la conexión con la nave")
    return True


def main():
    parser = argparse.ArgumentParser(description='Sensor de un sector de Aegis-Star')
    parser.add_argument('sector', choices=ANILLO)
    parser.add_argument('--alien', action='store_true', help='arranca reportando valores falsos a veces')
    parser.add_argument('--puerto', type=int, default=PUERTO_NAVE)
    args = parser.parse_args()
    modo['alien'] = args.alien

    try:
        while sesion(args.sector, args.puerto):
            time.sleep(SEGUNDOS_REINTENTO)
    except KeyboardInterrupt:
        pass
    print(f"[{args.sector}] Sensor apagado")


if __name__ == '__main__':
    main()
