"""
Matriz de amenazas: arma la matriz 3x3 y decide si hay alerta roja.
Responsable: Juan (E3). Lo usa nave.py. No abre sockets.

VERSIÓN PROVISIONAL: las funciones devuelven valores fijos para que la nave pueda correr
mientras se implementan (tareas T3.1 y T3.2 del PLAN.md). No cambiar las firmas.
"""

ANILLO = ['NO', 'N', 'NE', 'E', 'SE', 'S', 'SO', 'O'] # orden alrededor de la nave


def sectores_en_alerta(valores):
    """Devuelve los sectores que tienen un 1 y sus dos vecinos del anillo en 0. valores = {sector: 0|1|None}."""
    return [] # TODO T3.1


def decidir(valores):
    """Devuelve 'ALERTA_ROJA', 'TRANSITO_SEGURO' o 'SIN_AMENAZA'."""
    return 'SIN_AMENAZA' # TODO T3.1


def elegir_maniobra(alertas):
    """Devuelve el texto de la maniobra: evasión hacia el sector opuesto o escudos si hay varias alertas."""
    return 'Sin maniobra' # TODO T3.2


def texto_matriz(valores):
    """Devuelve la matriz 3x3 como texto para imprimir en consola (None se muestra como '?')."""
    return '' # TODO T3.2
