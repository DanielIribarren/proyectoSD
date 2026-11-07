"""
Tolerancia a fallas: sensores caídos, quién cubre su sector y auditoría de sensores alien.
Responsable: Juan (E3). Lo usa nave.py. No abre sockets.

VERSIÓN PROVISIONAL: las funciones devuelven valores fijos para que la nave pueda correr
mientras se implementan (tareas T3.3 y T3.4 del PLAN.md). No cambiar las firmas.
"""

LIMITE_LATIDO = 3.0 # segundos sin latir para dar un sensor por caído
FALLAS_PARA_CUARENTENA = 3


def sectores_caidos(ultimo_latido, ahora):
    """Devuelve los sectores que pasaron LIMITE_LATIDO sin latir. ultimo_latido = {sector: time.time()}."""
    return [] # TODO T3.3


def elegir_cubridor(sector, activos):
    """Devuelve el vecino vivo más cercano en el anillo que puede cubrir el sector, o None."""
    return None # TODO T3.3


def auditar(sector, reportado, esperado, fallas):
    """Compara lo reportado con lo esperado y suma fallas. Devuelve 'OK', 'SOSPECHOSO' o 'CUARENTENA'."""
    return 'OK' # TODO T3.4
