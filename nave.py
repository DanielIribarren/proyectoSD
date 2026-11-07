"""
La nave (servidor central). Recibe a los 8 sensores, marca los ticks, arma la matriz y decide.
Responsable: Daniel (E1).

Correr con:  python3 nave.py [--semilla 1234]

PENDIENTE: tareas T1.2 a T1.8 del PLAN.md.
"""

HOST = '127.0.0.1'
PUERTO_SENSORES = 5050
SEGUNDOS_TICK = 2.0 # cada cuánto la nave pide un escaneo
ESPERA_REPORTES = 1.5 # máximo que se espera a los reportes de un tick antes de cerrarlo
