"""
Protocolo entre la nave y los sensores.
Responsable: Daniel (E1). Lo usan nave.py y sensor.py.

Cada mensaje es un diccionario que viaja como JSON en una sola línea terminada en '\n'.
Se hace así porque TCP no respeta los límites de los mensajes: dos sendall() pueden llegar
juntos en un solo recv(), o un mensaje puede llegar partido en dos recv().
"""
import json
import logging

TAMANO_BUFFER = 4096 # bytes que se piden en cada recv()

registro = logging.getLogger('protocolo')


def enviar(sock, mensaje):
    """Manda un diccionario como una línea JSON. Devuelve False si el otro lado ya no responde."""
    linea = json.dumps(mensaje, ensure_ascii=False) + '\n'
    try:
        sock.sendall(linea.encode('utf-8'))
        return True
    except OSError:
        return False


def convertir_linea(linea):
    """Pasa una línea en bytes a diccionario. Devuelve None si no es un mensaje válido."""
    try:
        mensaje = json.loads(linea.decode('utf-8'))
    except (UnicodeDecodeError, json.JSONDecodeError):
        registro.warning("Mensaje mal formado, se ignora: %r", linea)
        return None

    if not isinstance(mensaje, dict) or 'tipo' not in mensaje:
        registro.warning("Mensaje sin 'tipo', se ignora: %r", linea)
        return None
    return mensaje


def leer_mensajes(sock):
    """Generador: devuelve un diccionario por cada línea que llega. Termina cuando se cierra la conexión."""
    buffer = b''
    while True:
        try:
            datos = sock.recv(TAMANO_BUFFER)
        except OSError:
            return # conexión rota, se trata igual que un cierre
        if not datos:
            return # el otro lado cerró la conexión

        buffer += datos
        # Puede haber 0, 1 o varias líneas completas en el buffer. Lo que queda después
        # del último '\n' es un mensaje a medias y se guarda para el próximo recv().
        # Se corta en bytes y no en texto para no partir una letra con tilde a la mitad.
        while b'\n' in buffer:
            linea, buffer = buffer.split(b'\n', 1)
            if not linea.strip():
                continue
            mensaje = convertir_linea(linea)
            if mensaje is not None:
                yield mensaje
