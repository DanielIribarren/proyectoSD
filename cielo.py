"""
Generación de meteoritos con la semilla compartida.
Responsable: Jesus (E2). Lo usan sensor.py y nave.py (para auditar).

Con la misma semilla y el mismo tick, cualquier proceso genera exactamente los mismos objetos.

VERSIÓN PROVISIONAL: generar_cielo devuelve un cielo vacío mientras se implementa
(tarea T2.1 del PLAN.md). No cambiar las firmas.
"""


def generar_cielo(semilla, tick):
    """Devuelve la lista de objetos del tick. Cada objeto: {id, tipo, sectores, tamano, velocidad}."""
    return [] # TODO T2.1: usar random.Random(f"{semilla}-{tick}")


def valor_sector(objetos, sector):
    """Devuelve 1 si algún objeto pasa por ese sector, si no 0."""
    return 1 if any(sector in objeto['sectores'] for objeto in objetos) else 0
