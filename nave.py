"""
La nave (servidor central). Recibe a los 8 sensores, marca los ticks, arma la matriz y decide.
Responsable: Daniel (E1).

Correr con:  python3 nave.py [--semilla 1234] [--puerto 5050]

Hilos de la nave:
- principal: acepta conexiones nuevas.
- uno por sensor (atender_sensor): lee los mensajes del sensor y los deja en la cola de eventos.
- marcar_ticks: cada SEGUNDOS_TICK avisa que empieza un tick nuevo.
- procesar_eventos: el ÚNICO hilo que toca los datos del tick. Saca los eventos de la cola
  según su prioridad. Como nadie más escribe esos datos, no hay condiciones de carrera.

PENDIENTE: T1.6 (latidos, cobertura, auditoría) y T1.7 (panel), ver PLAN.md.
"""
import argparse
import itertools
import logging
import queue
import random
import socket
import sys
import threading
import time

import matriz
from protocolo import enviar, leer_mensajes

HOST = '127.0.0.1'
PUERTO_SENSORES = 5050
SEGUNDOS_TICK = 2.0 # cada cuánto la nave pide un escaneo
ESPERA_REPORTES = 1.5 # máximo que se espera a los reportes de un tick antes de cerrarlo

# Número más chico = se atiende primero
PRIORIDAD = {
    'DETECCION': 0, # reporte con valor 1: puede ser un choque
    'DESCONEXION': 1,
    'TICK': 2,
    'REPORTE': 2, # reporte con valor 0
    'LATIDO': 3,
}

registro = logging.getLogger('nave')

semilla = None # se elige al arrancar y se reparte a los sensores en la BIENVENIDA

sensores = {} # sector -> socket
sensores_lock = threading.Lock() # lo usan los hilos de cada sensor y el procesador a la vez

cola_eventos = queue.PriorityQueue()
turno = itertools.count() # desempata eventos con la misma prioridad: sale primero el que llegó antes

# Lo que sigue solo lo toca procesar_eventos
tick = {
    'numero': 0,
    'abierto': False,
    'limite': 0.0, # hora en la que se cierra aunque falten reportes
    'esperados': set(), # sectores que tienen que reportar en este tick
    'reportes': {}, # sector -> 0 o 1
}
ultimo_latido = {} # sector -> time.time() del último latido (lo usará T1.6)


def encolar(tipo, remitente, mensaje=None):
    """Deja un evento en la cola con la prioridad que le corresponde a su tipo."""
    evento = {'tipo': tipo, 'remitente': remitente, 'mensaje': mensaje}
    cola_eventos.put((PRIORIDAD[tipo], next(turno), evento))


def difundir(mensaje):
    """Manda el mensaje a todos los sensores conectados."""
    with sensores_lock:
        destinos = list(sensores.values())
    # Se envía fuera del lock para que un sensor lento no frene los registros de los demás
    for sock in destinos:
        enviar(sock, mensaje)


def registrar(conn, hola):
    """Anota al sensor según su HOLA. Devuelve su sector, o None si se rechaza."""
    sector = hola.get('sector') if hola and hola['tipo'] == 'HOLA' else None

    # Revisar y anotar dentro del mismo lock: si dos sensores dicen "NE" a la vez, solo entra uno
    with sensores_lock:
        if sector not in matriz.ANILLO:
            motivo = f"sector inválido: {sector}"
        elif sector in sensores:
            motivo = f"el sector {sector} ya está conectado"
        else:
            sensores[sector] = conn
            motivo = None

    if motivo:
        enviar(conn, {'tipo': 'RECHAZO', 'motivo': motivo})
        registro.warning("Rechazado: %s", motivo)
        return None

    enviar(conn, {'tipo': 'BIENVENIDA', 'semilla': semilla, 'tick_actual': tick['numero']})
    return sector


def atender_sensor(conn, addr):
    """Corre en un hilo por sensor: lo registra y pasa sus mensajes a la cola de eventos."""
    # Un solo generador para toda la conexión: si el HOLA llega pegado a otro mensaje, no se pierde
    mensajes = leer_mensajes(conn)
    sector = registrar(conn, next(mensajes, None))
    if sector is None:
        conn.close()
        return

    registro.info("Conectado sensor %s (%s:%s)", sector, addr[0], addr[1])
    encolar('LATIDO', sector) # conectarse cuenta como el primer latido

    for mensaje in mensajes:
        if mensaje['tipo'] == 'REPORTE':
            encolar('DETECCION' if mensaje.get('valor') == 1 else 'REPORTE', sector, mensaje)
        elif mensaje['tipo'] == 'LATIDO':
            encolar('LATIDO', sector)
        else:
            registro.warning("Mensaje desconocido de %s: %s", sector, mensaje['tipo'])

    # Si se salió del for, el sensor cerró la conexión o se cortó
    with sensores_lock:
        if sensores.get(sector) is conn:
            del sensores[sector]
    conn.close()
    encolar('DESCONEXION', sector)


def marcar_ticks():
    """Cada SEGUNDOS_TICK deja en la cola el aviso de que empieza un tick nuevo."""
    while True:
        time.sleep(SEGUNDOS_TICK)
        encolar('TICK', None)


def abrir_tick():
    """Empieza un tick nuevo y les pide a los sensores que escaneen."""
    with sensores_lock:
        conectados = set(sensores)
    if not conectados:
        return # sin sensores no hay nada que escanear

    tick['numero'] += 1
    tick['abierto'] = True
    tick['limite'] = time.time() + ESPERA_REPORTES
    tick['esperados'] = conectados
    tick['reportes'] = {}
    difundir({'tipo': 'TICK', 'tick': tick['numero']})


def recibir_reporte(remitente, mensaje):
    """Guarda el valor del reporte si es válido. Descarta los de otro sector, los tardíos y los duplicados."""
    numero = mensaje.get('tick')
    sector = mensaje.get('sector')
    valor = mensaje.get('valor')

    if sector != remitente: # T1.6: aceptar también los sectores que este sensor esté cubriendo
        registro.warning("%s mandó un reporte del sector %s, se descarta", remitente, sector)
    elif valor not in (0, 1):
        registro.warning("Reporte de %s con valor inválido (%r), se descarta", remitente, valor)
    elif not tick['abierto'] or numero != tick['numero']:
        registro.info("Reporte tardío de %s (tick %s), se descarta", sector, numero)
    elif sector in tick['reportes']:
        registro.info("Reporte duplicado de %s en el tick %s, se descarta", sector, numero)
    else:
        tick['reportes'][sector] = valor


def cerrar_tick():
    """Arma la matriz con los reportes que llegaron, decide e informa."""
    tick['abierto'] = False
    valores = {sector: tick['reportes'].get(sector) for sector in matriz.ANILLO} # None = sin dato

    decision = matriz.decidir(valores)
    linea = ' '.join(f"{sector}={'?' if valor is None else valor}" for sector, valor in valores.items())
    registro.info("Tick %d  %s  -> %s", tick['numero'], linea, decision)

    texto = matriz.texto_matriz(valores)
    if texto:
        registro.info("\n%s", texto)

    if decision == 'ALERTA_ROJA':
        alertas = matriz.sectores_en_alerta(valores)
        registro.warning("ALERTA ROJA en %s. %s", ', '.join(alertas), matriz.elegir_maniobra(alertas))


def procesar_eventos():
    """Saca los eventos de la cola por prioridad y cierra cada tick a tiempo."""
    while True:
        espera = None # sin tick abierto se espera lo que haga falta
        if tick['abierto']:
            espera = max(0, tick['limite'] - time.time())

        try:
            _, _, evento = cola_eventos.get(timeout=espera)
        except queue.Empty:
            cerrar_tick() # se cumplió el límite y faltaron reportes
            continue

        tipo, remitente = evento['tipo'], evento['remitente']
        if tipo == 'TICK':
            if tick['abierto']:
                cerrar_tick()
            abrir_tick()
        elif tipo in ('REPORTE', 'DETECCION'):
            recibir_reporte(remitente, evento['mensaje'])
        elif tipo == 'LATIDO':
            ultimo_latido[remitente] = time.time()
        elif tipo == 'DESCONEXION':
            registro.warning("Se desconectó el sensor %s", remitente)
            ultimo_latido.pop(remitente, None)
            tick['esperados'].discard(remitente) # no se le espera más en este tick

        # Si ya reportaron todos no hace falta esperar al límite
        if tick['abierto'] and (tick['esperados'] <= set(tick['reportes']) or time.time() >= tick['limite']):
            cerrar_tick()


def configurar_registro():
    """Muestra los eventos en consola y los guarda en registro.log."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s %(message)s',
        datefmt='%H:%M:%S',
        handlers=[logging.StreamHandler(sys.stdout), logging.FileHandler('registro.log', encoding='utf-8')],
    )


def main():
    global semilla
    parser = argparse.ArgumentParser(description='Nave: servidor central de Aegis-Star')
    parser.add_argument('--semilla', type=int, help='semilla fija (sirve para repetir una corrida)')
    parser.add_argument('--puerto', type=int, default=PUERTO_SENSORES)
    args = parser.parse_args()

    semilla = args.semilla if args.semilla is not None else random.randrange(1, 1_000_000)
    configurar_registro()

    threading.Thread(target=procesar_eventos, daemon=True).start()
    threading.Thread(target=marcar_ticks, daemon=True).start()

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1) # evita "Address already in use" al reiniciar
        s.bind((HOST, args.puerto))
        s.listen()
        registro.info("Nave escuchando en %s:%d con semilla %d", HOST, args.puerto, semilla)

        try:
            while True:
                conn, addr = s.accept()
                threading.Thread(target=atender_sensor, args=(conn, addr), daemon=True).start()
        except KeyboardInterrupt:
            registro.info("Nave apagada")


if __name__ == '__main__':
    main()
