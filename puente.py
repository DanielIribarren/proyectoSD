"""
Puente entre la nave y el panel web por WebSocket (puerto 8765).
Responsable: Derek (E4). Lo usan nave.py y simulador_estado.py.

El servidor WebSocket corre en su propio hilo con un bucle de asyncio. La nave nunca espera
al panel: publicar() solo deja el estado para que ese hilo lo mande, así que un navegador
lento o cerrado no frena el cierre de los ticks.

- nave -> panel: un JSON con el estado de cada tick (formato en la sección 7 del PLAN.md).
- panel -> nave: un JSON por orden, {"accion": "apagar"|"alien"|"normal", "sector": "NE"}.

Si la librería websockets no está instalada o el puerto está ocupado, se avisa por consola y
la nave sigue funcionando sin panel.
"""
import asyncio
import json
import logging
import threading

try:
    from websockets.asyncio.server import broadcast, serve
except ImportError: # la nave tiene que poder correr aunque no se haya instalado
    serve = None

HOST = '127.0.0.1'
PUERTO_PANEL = 8765
ESPERA_ARRANQUE = 2.0 # cuánto espera iniciar_puente a que el servidor quede escuchando

registro = logging.getLogger('puente')
logging.getLogger('websockets').setLevel(logging.WARNING) # sus avisos de cada conexión ensucian la consola de la nave

bucle = None # bucle de asyncio del hilo del puente; None si el puente no está corriendo
navegadores = set() # conexiones abiertas; solo se tocan desde el hilo del puente
ultimo = {'estado': None} # último estado publicado, para mandárselo a quien se conecte tarde


def iniciar_puente(al_recibir_orden, puerto=PUERTO_PANEL):
    """Levanta el WebSocket en un hilo aparte. Cada orden del panel se pasa a al_recibir_orden(dict)."""
    if serve is None:
        registro.warning("Falta la librería websockets (pip install websockets): la nave sigue sin panel")
        return False

    listo = threading.Event()
    resultado = {'ok': False}
    hilo = threading.Thread(target=correr_servidor, args=(al_recibir_orden, puerto, listo, resultado), daemon=True)
    hilo.start()
    listo.wait(ESPERA_ARRANQUE)
    return resultado['ok']


def publicar(estado):
    """Manda el estado del tick a todos los navegadores conectados."""
    if bucle is None:
        return # sin puente no hay a quién mandarle nada
    texto = json.dumps(estado, ensure_ascii=False)
    # call_soon_threadsafe no espera: la nave sigue de una vez y el envío pasa en el hilo del puente
    bucle.call_soon_threadsafe(difundir, texto)


# ---------- Todo lo de abajo corre en el hilo del puente ----------

def correr_servidor(al_recibir_orden, puerto, listo, resultado):
    """Crea el bucle de asyncio del hilo y deja el servidor escuchando para siempre."""
    global bucle
    nuevo = asyncio.new_event_loop()
    asyncio.set_event_loop(nuevo)
    try:
        nuevo.run_until_complete(escuchar(al_recibir_orden, puerto, listo, resultado, nuevo))
    except OSError as error:
        registro.warning("No se pudo abrir el panel en el puerto %d (%s): la nave sigue sin panel", puerto, error)
    finally:
        if bucle is nuevo: # si este intento falló, no se toca el puente que ya estaba andando
            bucle = None
        listo.set()


async def escuchar(al_recibir_orden, puerto, listo, resultado, nuevo):
    """Abre el servidor WebSocket y atiende navegadores hasta que se apague el proceso."""
    global bucle

    async def atender(conexion):
        await atender_navegador(conexion, al_recibir_orden)

    async with serve(atender, HOST, puerto):
        bucle = nuevo # recién ahora publicar() puede mandar cosas
        resultado['ok'] = True
        registro.info("Panel disponible en ws://%s:%d", HOST, puerto)
        listo.set()
        await asyncio.Future() # nunca se completa: el servidor queda abierto


async def atender_navegador(conexion, al_recibir_orden):
    """Le manda el último estado al navegador nuevo y pasa a la nave cada orden que llegue."""
    navegadores.add(conexion)
    registro.info("Se conectó un panel (%d abiertos)", len(navegadores))
    try:
        if ultimo['estado'] is not None:
            await conexion.send(ultimo['estado']) # para no ver la pantalla vacía hasta el próximo tick
        async for texto in conexion:
            orden = leer_orden(texto)
            if orden is not None:
                al_recibir_orden(orden)
    except Exception as error: # un navegador que se cierra feo no puede tumbar al puente
        registro.info("Panel desconectado con error: %s", error)
    finally:
        navegadores.discard(conexion)
        registro.info("Se desconectó un panel (%d abiertos)", len(navegadores))


def leer_orden(texto):
    """Pasa el texto que mandó el panel a diccionario. Devuelve None si no es una orden."""
    try:
        orden = json.loads(texto)
    except (TypeError, json.JSONDecodeError):
        registro.warning("Orden mal formada del panel, se ignora: %r", texto)
        return None
    if not isinstance(orden, dict):
        registro.warning("Orden mal formada del panel, se ignora: %r", texto)
        return None
    return orden # la nave revisa que la acción y el sector sean válidos


def difundir(texto):
    """Guarda el estado como el último y se lo manda a todos los navegadores abiertos."""
    ultimo['estado'] = texto
    # broadcast no espera a cada navegador: si uno está lento, los demás no lo notan
    broadcast(navegadores, texto)
