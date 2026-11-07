"""
Matriz de amenazas: arma la matriz 3x3 y decide si hay alerta roja.
Responsable: Juan (E3). Lo usa nave.py. No abre sockets.

Las 8 casillas alrededor de la nave forman un anillo. Dos sectores son vecinos si están
pegados en ese anillo, incluido el borde donde da la vuelta (O y NO).

- Un 1 aislado (sus dos vecinos en 0): el objeto viene directo a la nave -> ALERTA ROJA.
- Dos o más 1 seguidos: el objeto pasa de lado -> TRANSITO SEGURO.
"""

ANILLO = ['NO', 'N', 'NE', 'E', 'SE', 'S', 'SO', 'O'] # orden alrededor de la nave, en sentido horario

# Cómo se ve la matriz: la nave (x) en el centro
FILAS = [
    ['NO', 'N', 'NE'],
    ['O', None, 'E'],
    ['SO', 'S', 'SE'],
]


def vecinos(sector):
    """Devuelve los dos vecinos del sector en el anillo: (anterior, siguiente)."""
    i = ANILLO.index(sector)
    return ANILLO[i - 1], ANILLO[(i + 1) % 8] # con i = 0, ANILLO[-1] es O: el anillo da la vuelta


def sectores_en_alerta(valores):
    """Devuelve los sectores que tienen un 1 y sus dos vecinos del anillo en 0. valores = {sector: 0|1|None}."""
    alertas = []
    for sector in ANILLO:
        anterior, siguiente = vecinos(sector)
        # None (sector sin dato) cuenta como 0: preferimos una falsa alarma a no ver un choque
        if valores.get(sector) == 1 and not valores.get(anterior) and not valores.get(siguiente):
            alertas.append(sector)
    return alertas


def decidir(valores):
    """Devuelve 'ALERTA_ROJA', 'TRANSITO_SEGURO' o 'SIN_AMENAZA'."""
    if sectores_en_alerta(valores):
        return 'ALERTA_ROJA' # basta un 1 aislado, aunque en otro lado haya un tránsito
    if any(valores.get(sector) == 1 for sector in ANILLO):
        return 'TRANSITO_SEGURO'
    return 'SIN_AMENAZA'


def elegir_maniobra(alertas):
    """Devuelve el texto de la maniobra: evasión de costado si hay una amenaza, escudos si hay varias."""
    if not alertas:
        return 'Sin maniobra'
    if len(alertas) > 1:
        return f"Escudos activados ({len(alertas)} amenazas: {', '.join(alertas)})"

    # El objeto viene en línea recta hacia el centro. Ir hacia el lado opuesto deja a la nave
    # en la misma línea; moverse de costado (dos casillas más allá en el anillo) sí la saca.
    i = ANILLO.index(alertas[0])
    return f"Evasión hacia {ANILLO[(i + 2) % 8]}"


def texto_matriz(valores):
    """Devuelve la matriz 3x3 como texto, igual que en el enunciado. None se muestra como '?'."""
    lineas = []
    for fila in FILAS:
        nombres = ' '.join(f"{sector or 'x':<2}" for sector in fila)
        celdas = ' '.join('x' if sector is None else ('?' if valores.get(sector) is None else str(valores[sector]))
                          for sector in fila)
        lineas.append(f"[ {nombres} ]   [ {celdas} ]")
    return '\n'.join(lineas)
