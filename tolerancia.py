"""
Tolerancia a fallas: sensores caídos, quién cubre su sector y auditoría de sensores alien.
Responsable: Juan (E3). Lo usa nave.py. No abre sockets.
"""
from matriz import ANILLO

LIMITE_LATIDO = 3.0 # segundos sin latir para dar un sensor por caído
FALLAS_PARA_CUARENTENA = 3


def sectores_caidos(ultimo_latido, ahora):
    """Devuelve los sectores que pasaron LIMITE_LATIDO sin latir. ultimo_latido = {sector: time.time()}."""
    return [sector for sector in ANILLO
            if sector in ultimo_latido and ahora - ultimo_latido[sector] > LIMITE_LATIDO]


def elegir_cubridor(sector, activos):
    """Devuelve el vecino vivo más cercano en el anillo que puede cubrir el sector, o None."""
    i = ANILLO.index(sector)
    for distancia in range(1, 5):
        horario = ANILLO[(i + distancia) % 8]
        antihorario = ANILLO[(i - distancia) % 8]
        for candidato in (horario, antihorario): # a igual distancia, primero el de sentido horario
            if candidato in activos:
                return candidato
    return None


def auditar(sector, reportado, esperado, fallas):
    """Compara lo reportado con lo esperado y suma fallas. Devuelve 'OK', 'SOSPECHOSO' o 'CUARENTENA'."""
    if reportado == esperado:
        return 'CUARENTENA' if fallas.get(sector, 0) >= FALLAS_PARA_CUARENTENA else 'OK'

    fallas[sector] = fallas.get(sector, 0) + 1 # fallas es de la nave: se modifica aquí mismo
    if fallas[sector] >= FALLAS_PARA_CUARENTENA:
        return 'CUARENTENA'
    return 'SOSPECHOSO'
