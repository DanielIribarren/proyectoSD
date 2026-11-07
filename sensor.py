"""
Sensor de un sector. Se conecta a la nave, genera el cielo con la semilla y reporta su sector.
Responsable: Jesus (E2).

Correr con:  python3 sensor.py NE [--alien]

PENDIENTE: tareas T2.2 a T2.6 del PLAN.md.
"""

HOST = '127.0.0.1'
PUERTO_NAVE = 5050
SEGUNDOS_LATIDO = 1.0
SEGUNDOS_REINTENTO = 2.0 # si la nave no está, se vuelve a intentar cada 2 s
