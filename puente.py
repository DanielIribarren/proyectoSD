"""
Puente entre la nave y el panel web por WebSocket (puerto 8765).
Responsable: Derek (E4). Lo usa nave.py.

VERSIÓN PROVISIONAL: no levanta nada todavía, para que la nave pueda correr sin el panel
(tarea T4.1 del PLAN.md). No cambiar las firmas.
"""

PUERTO_PANEL = 8765


def iniciar_puente(al_recibir_orden):
    """Levanta el WebSocket en un hilo aparte. Cada orden del panel se pasa a al_recibir_orden(dict)."""
    pass # TODO T4.1


def publicar(estado):
    """Manda el estado del tick a todos los navegadores conectados."""
    pass # TODO T4.1
