"""
Generación de meteoritos con la semilla compartida.
Responsable: Jesus (E2). Lo usan sensor.py y nave.py (para auditar).

Todos los procesos crean su generador con random.Random(f"{semilla}-{tick}"). Con la misma
semilla y el mismo tick salen exactamente los mismos objetos en cualquier proceso, sin que
los sensores tengan que hablar entre ellos. Por eso un vecino puede cubrir un sector caído:
sabe calcular lo que ese sector habría visto.
"""
import random

from matriz import ANILLO

# Frecuencia: cuántos objetos aparecen en un tick (a veces nada, a veces una ráfaga)
CANTIDADES = [0, 1, 2, 3]
PESOS_CANTIDAD = [35, 40, 17, 8]

# Trayectorias: cuántos sectores seguidos del anillo cruza cada tipo
TIPOS = ['directa', 'tangente', 'rasante']
PESOS_TIPO = [45, 40, 15]
SECTORES_POR_TIPO = {
    'directa': [1], # viene en línea recta hacia la nave: la ve un solo sensor
    'tangente': [2, 3], # pasa de lado: la ven varios sensores seguidos
    'rasante': [4], # pasa rozando la nave: cruza medio anillo
}

TAMANO_MIN, TAMANO_MAX = 1, 5
VELOCIDAD_MIN, VELOCIDAD_MAX = 5, 40 # km/s


def generar_objeto(azar, id_objeto):
    """Crea un objeto con trayectoria, sectores, tamaño y velocidad sacados del generador."""
    tipo = azar.choices(TIPOS, weights=PESOS_TIPO)[0]
    largo = azar.choice(SECTORES_POR_TIPO[tipo])
    origen = azar.randrange(8) # posición en ANILLO del primer sector que cruza
    sentido = azar.choice([1, -1]) # horario o antihorario

    # % 8 hace que la trayectoria pueda cruzar el borde O -> NO como cualquier otro
    sectores = [ANILLO[(origen + sentido * paso) % 8] for paso in range(largo)]
    return {
        'id': id_objeto,
        'tipo': tipo,
        'sectores': sectores,
        'tamano': azar.randint(TAMANO_MIN, TAMANO_MAX),
        'velocidad': azar.randint(VELOCIDAD_MIN, VELOCIDAD_MAX),
    }


def generar_cielo(semilla, tick):
    """Devuelve la lista de objetos del tick. Cada objeto: {id, tipo, sectores, tamano, velocidad}."""
    azar = random.Random(f"{semilla}-{tick}") # generador propio: no depende de nada más del proceso
    cantidad = azar.choices(CANTIDADES, weights=PESOS_CANTIDAD)[0]
    return [generar_objeto(azar, f"{tick}-{n + 1}") for n in range(cantidad)]


def valor_sector(objetos, sector):
    """Devuelve 1 si algún objeto pasa por ese sector, si no 0."""
    return 1 if any(sector in objeto['sectores'] for objeto in objetos) else 0


def objetos_en_sector(objetos, sector):
    """Devuelve solo los objetos que pasan por ese sector."""
    return [objeto for objeto in objetos if sector in objeto['sectores']]
