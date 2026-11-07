"""
La nave (servidor central). Recibe a los 8 sensores, marca los ticks, arma la matriz y decide.
Responsable: Daniel (E1).

Correr con:  python3 nave.py [--semilla 1234] [--puerto 5050]

Hilos de la nave:
- principal: acepta conexiones nuevas.
- uno por sensor (atender_sensor): lee los mensajes del sensor y los deja en la cola de eventos.
- marcar_ticks: cada SEGUNDOS_TICK avisa que empieza un tick nuevo.
- vigilar_latidos: cada SEGUNDOS_REVISION pide revisar qué sensores dejaron de latir.
- el del panel (puente.py): deja en la cola las órdenes que llegan del navegador.
- procesar_eventos: el ÚNICO hilo que toca el estado de la nave (tick, matriz, sensores,
  cobertura). Saca los eventos de la cola según su prioridad. Como nadie más escribe ese
  estado, no hay condiciones de carrera.
"""
import argparse
import collections
import itertools
import logging
import queue
import random
import socket
import sys
import threading
import time

import cielo
import matriz
import puente
import tolerancia
from protocolo import enviar, leer_mensajes

HOST = '127.0.0.1'
PUERTO_SENSORES = 5050
SEGUNDOS_TICK = 2.0 # cada cuánto la nave pide un escaneo
ESPERA_REPORTES = 1.5 # máximo que se espera a los reportes de un tick antes de cerrarlo
SEGUNDOS_REVISION = 1.0 # cada cuánto se revisan los latidos
EVENTOS_PANEL = 30 # cuántos eventos recientes se mandan al panel
ACCIONES_PANEL = ('apagar', 'alien', 'normal')

# Número más chico = se atiende primero
PRIORIDAD = {
    'DETECCION': 0, # reporte con valor 1: puede ser un choque
    'DESCONEXION': 1,
    'CONEXION': 1,
    'REVISION': 1,
    'ORDEN': 1,
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
eventos_panel = collections.deque(maxlen=EVENTOS_PANEL) # deque: se puede agregar desde varios hilos

# Lo que sigue solo lo toca procesar_eventos
tick = {
    'numero': 0,
    'abierto': False,
    'limite': 0.0, # hora en la que se cierra aunque falten reportes
    'esperados': set(), # sectores que tienen que reportar en este tick
    'reportes': {}, # sector -> 0 o 1
    'cielo': [], # lo que dice el PRNG para este tick; solo se usa para auditar
}
estado_sensor = {} # sector -> 'ACTIVO' | 'CAIDO' | 'CUARENTENA' (solo los que se conectaron alguna vez)
ultimo_latido = {} # sector -> time.time() del último latido
cobertura = {} # sector del sensor que cubre -> lista de sectores ajenos que reporta
fallas = {} # sector -> veces que reportó algo distinto a lo que dice el PRNG (lo actualiza tolerancia.auditar)


class RegistroPanel(logging.Handler):
    """Guarda los últimos mensajes del registro para mostrarlos en el panel."""

    def emit(self, record):
        texto = record.getMessage()
        if '\n' in texto:
            return # la matriz dibujada no va: el panel ya la dibuja
        nivel = {logging.ERROR: 'alerta', logging.WARNING: 'aviso'}.get(record.levelno, 'info')
        hora = time.strftime('%H:%M:%S', time.localtime(record.created))
        eventos_panel.append({'hora': hora, 'nivel': nivel, 'texto': texto})


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


def enviar_a(sector, mensaje):
    """Manda el mensaje al sensor de ese sector, si está conectado."""
    with sensores_lock:
        sock = sensores.get(sector)
    if sock:
        enviar(sock, mensaje)


def cortar_conexion(sector):
    """Corta la conexión de un sensor. Su hilo se da cuenta y avisa la desconexión."""
    with sensores_lock:
        sock = sensores.get(sector)
    if sock:
        try:
            sock.shutdown(socket.SHUT_RDWR) # despierta al hilo que está esperando en recv()
        except OSError:
            pass


# ---------- Hilos de los sensores ----------

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
    encolar('CONEXION', sector)

    for mensaje in mensajes:
        if mensaje['tipo'] == 'REPORTE':
            encolar('DETECCION' if mensaje.get('valor') == 1 else 'REPORTE', sector, mensaje)
        elif mensaje['tipo'] == 'LATIDO':
            encolar('LATIDO', sector)
        else:
            registro.warning("Mensaje desconocido de %s: %s", sector, mensaje['tipo'])

    # Si se salió del for, el sensor cerró la conexión o se cortó.
    # La DESCONEXION se encola dentro del lock: así, si el sensor se reconecta enseguida,
    # su CONEXION nueva queda detrás en la cola y no se procesan al revés.
    with sensores_lock:
        if sensores.get(sector) is conn:
            del sensores[sector]
        encolar('DESCONEXION', sector)
    conn.close()


# ---------- Hilos que marcan el ritmo ----------

def marcar_ticks():
    """Cada SEGUNDOS_TICK deja en la cola el aviso de que empieza un tick nuevo."""
    while True:
        time.sleep(SEGUNDOS_TICK)
        encolar('TICK', None)


def vigilar_latidos():
    """Cada SEGUNDOS_REVISION pide revisar si algún sensor dejó de latir."""
    while True:
        time.sleep(SEGUNDOS_REVISION)
        encolar('REVISION', None)


def recibir_orden_panel(orden):
    """La llama puente.py desde su hilo con cada orden del navegador. Solo la encola."""
    encolar('ORDEN', None, orden)


# ---------- Todo lo de abajo corre en el hilo procesador ----------

def sectores_activos():
    """Sectores con sensor conectado, latiendo y fuera de cuarentena."""
    return {sector for sector, estado in estado_sensor.items() if estado == 'ACTIVO'}


def reasignar_cobertura():
    """Recalcula quién cubre cada sector sin sensor activo y avisa solo a los que les cambió la lista."""
    activos = sectores_activos()
    nueva = {}
    for sector in matriz.ANILLO:
        if estado_sensor.get(sector) in (None, 'ACTIVO'):
            continue # activo, o nunca se conectó (no hay nada que reemplazar)
        cubridor = tolerancia.elegir_cubridor(sector, activos)
        if cubridor is None:
            registro.warning("Nadie puede cubrir el sector %s", sector)
        else:
            nueva.setdefault(cubridor, []).append(sector)

    for sensor in set(cobertura) | set(nueva):
        antes, ahora = cobertura.get(sensor, []), nueva.get(sensor, [])
        if antes != ahora:
            enviar_a(sensor, {'tipo': 'COBERTURA', 'sectores': ahora})
            if ahora:
                registro.info("%s cubre ahora %s", sensor, ', '.join(ahora))
            else:
                registro.info("%s deja de cubrir otros sectores", sensor)

    cobertura.clear()
    cobertura.update(nueva)


def sensor_conectado(sector):
    """Marca al sensor como activo (salvo que esté en cuarentena) y le devuelve su sector."""
    ultimo_latido[sector] = time.time() # conectarse cuenta como el primer latido
    if estado_sensor.get(sector) == 'CUARENTENA':
        registro.warning("El sensor %s volvió pero sigue en cuarentena", sector)
    else:
        estado_sensor[sector] = 'ACTIVO'
    reasignar_cobertura()


def sensor_desconectado(sector):
    """Marca al sensor como caído y reparte su sector."""
    registro.warning("Se desconectó el sensor %s", sector)
    ultimo_latido.pop(sector, None)
    if estado_sensor.get(sector) == 'ACTIVO':
        estado_sensor[sector] = 'CAIDO'
    tick['esperados'].discard(sector) # no se le espera más en este tick
    reasignar_cobertura()


def revisar_latidos():
    """Da por caídos a los sensores que pasaron el límite sin latir y les corta la conexión."""
    for sector in tolerancia.sectores_caidos(ultimo_latido, time.time()):
        if estado_sensor.get(sector) != 'ACTIVO':
            continue
        registro.warning("El sensor %s lleva más de %.0f s sin latir: se da por caído", sector, tolerancia.LIMITE_LATIDO)
        estado_sensor[sector] = 'CAIDO'
        ultimo_latido.pop(sector, None)
        cortar_conexion(sector) # puede estar colgado: se le cierra para que reconecte limpio
        reasignar_cobertura()


def atender_orden(orden):
    """Reenvía al sensor la orden que llegó del panel. 'normal' además lo saca de cuarentena."""
    accion = orden.get('accion') if isinstance(orden, dict) else None
    sector = orden.get('sector') if isinstance(orden, dict) else None
    if accion not in ACCIONES_PANEL or sector not in matriz.ANILLO:
        registro.warning("Orden inválida del panel: %s", orden)
        return

    registro.info("Orden del panel: %s al sensor %s", accion, sector)
    enviar_a(sector, {'tipo': 'ORDEN', 'accion': accion})

    if accion == 'normal' and estado_sensor.get(sector) == 'CUARENTENA':
        fallas[sector] = 0
        with sensores_lock:
            conectado = sector in sensores
        estado_sensor[sector] = 'ACTIVO' if conectado else 'CAIDO'
        registro.info("El sensor %s sale de cuarentena", sector)
        reasignar_cobertura()


def abrir_tick():
    """Empieza un tick nuevo y les pide a los sensores que escaneen."""
    activos = sectores_activos()
    if not activos:
        return # sin sensores no hay nada que escanear

    cubiertos = {sector for lista in cobertura.values() for sector in lista}
    tick['numero'] += 1
    tick['abierto'] = True
    tick['limite'] = time.time() + ESPERA_REPORTES
    tick['esperados'] = activos | cubiertos
    tick['reportes'] = {}
    tick['cielo'] = cielo.generar_cielo(semilla, tick['numero'])
    difundir({'tipo': 'TICK', 'tick': tick['numero']})


def auditar_reporte(remitente, sector, valor):
    """Compara el reporte con lo que dice el PRNG. A la tercera diferencia, el sensor va a cuarentena."""
    esperado = cielo.valor_sector(tick['cielo'], sector)
    resultado = tolerancia.auditar(remitente, valor, esperado, fallas)

    if resultado == 'SOSPECHOSO':
        registro.warning("El sensor %s reportó %s=%d y la semilla dice %d (falla %d)",
                         remitente, sector, valor, esperado, fallas.get(remitente, 0))
    elif resultado == 'CUARENTENA' and estado_sensor.get(remitente) != 'CUARENTENA':
        registro.error("Sensor %s en CUARENTENA: sus reportes no coinciden con la semilla", remitente)
        estado_sensor[remitente] = 'CUARENTENA'
        tick['reportes'].pop(sector, None) # este último reporte tampoco se usa
        reasignar_cobertura()


def recibir_reporte(remitente, mensaje):
    """Guarda el valor del reporte si es válido. Descarta los de sectores ajenos, los tardíos y los duplicados."""
    numero = mensaje.get('tick')
    sector = mensaje.get('sector')
    valor = mensaje.get('valor')

    if estado_sensor.get(remitente) == 'CUARENTENA':
        registro.info("Reporte de %s ignorado: está en cuarentena", remitente)
    elif sector != remitente and sector not in cobertura.get(remitente, []):
        registro.warning("%s mandó un reporte del sector %s, se descarta", remitente, sector)
    elif valor not in (0, 1):
        registro.warning("Reporte de %s con valor inválido (%r), se descarta", remitente, valor)
    elif not tick['abierto'] or numero != tick['numero']:
        registro.info("Reporte tardío de %s (tick %s), se descarta", sector, numero)
    elif sector in tick['reportes']:
        registro.info("Reporte duplicado de %s en el tick %s, se descarta", sector, numero)
    else:
        tick['reportes'][sector] = valor
        auditar_reporte(remitente, sector, valor)


def estado_para_panel(valores, decision, alertas, maniobra):
    """Arma el diccionario que se le manda al panel (formato en la sección 7 del PLAN.md)."""
    ahora = time.time()
    sensores_panel = {}
    for sector in matriz.ANILLO:
        latido = ultimo_latido.get(sector)
        sensores_panel[sector] = {
            'estado': estado_sensor.get(sector, 'CAIDO'),
            'cubre': cobertura.get(sector, []),
            'ultimo_latido': round(ahora - latido, 1) if latido else None, # segundos desde el último
            'fallas': fallas.get(sector, 0),
        }
    return {
        'tick': tick['numero'],
        'semilla': semilla,
        'matriz': valores,
        'decision': decision,
        'alertas': alertas,
        'maniobra': maniobra,
        'sensores': sensores_panel,
        'eventos': list(eventos_panel),
    }


def cerrar_tick():
    """Arma la matriz con los reportes que llegaron, decide, informa y avisa al panel."""
    tick['abierto'] = False
    valores = {sector: tick['reportes'].get(sector) for sector in matriz.ANILLO} # None = sin dato

    decision = matriz.decidir(valores)
    alertas = matriz.sectores_en_alerta(valores)
    maniobra = matriz.elegir_maniobra(alertas) if decision == 'ALERTA_ROJA' else None

    linea = ' '.join(f"{sector}={'?' if valor is None else valor}" for sector, valor in valores.items())
    registro.info("Tick %d  %s  -> %s", tick['numero'], linea, decision)
    texto = matriz.texto_matriz(valores)
    if texto:
        registro.info("\n%s", texto)
    if decision == 'ALERTA_ROJA':
        registro.error("ALERTA ROJA en %s. %s", ', '.join(alertas), maniobra) # nivel ERROR = alerta en el panel

    puente.publicar(estado_para_panel(valores, decision, alertas, maniobra))


def atender_evento(evento):
    """Hace lo que corresponde según el tipo de evento."""
    tipo, remitente = evento['tipo'], evento['remitente']
    if tipo == 'TICK':
        if tick['abierto']:
            cerrar_tick()
        abrir_tick()
    elif tipo in ('REPORTE', 'DETECCION'):
        recibir_reporte(remitente, evento['mensaje'])
    elif tipo == 'LATIDO':
        if remitente in ultimo_latido or estado_sensor.get(remitente) == 'ACTIVO':
            ultimo_latido[remitente] = time.time()
    elif tipo == 'CONEXION':
        sensor_conectado(remitente)
    elif tipo == 'DESCONEXION':
        sensor_desconectado(remitente)
    elif tipo == 'REVISION':
        revisar_latidos()
    elif tipo == 'ORDEN':
        atender_orden(evento['mensaje'])


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

        atender_evento(evento)

        # Si ya reportaron todos no hace falta esperar al límite
        if tick['abierto'] and (tick['esperados'] <= set(tick['reportes']) or time.time() >= tick['limite']):
            cerrar_tick()


def configurar_registro():
    """Muestra los eventos en consola, los guarda en registro.log y los guarda para el panel."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s %(message)s',
        datefmt='%H:%M:%S',
        handlers=[logging.StreamHandler(sys.stdout), logging.FileHandler('registro.log', encoding='utf-8')],
    )
    registro.addHandler(RegistroPanel())


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
    threading.Thread(target=vigilar_latidos, daemon=True).start()
    puente.iniciar_puente(recibir_orden_panel)

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
