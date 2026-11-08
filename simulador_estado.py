"""
Simulador del estado de la nave para trabajar en el panel sin levantar la nave ni los sensores.
Responsable: Derek (E4).

Correr con:  python3 simulador_estado.py [--semilla 1234]

Publica por puente.py un estado cada SEGUNDOS_TICK con el mismo formato que la nave (sección 7
del PLAN.md). La matriz sale de cielo.py y la decisión de matriz.py, así que lo que se ve es
igual a lo que vería la nave con esa semilla. Las órdenes del panel cambian el estado de los
sensores de mentira: 'apagar' lo deja CAIDO, 'alien' le suma fallas hasta la CUARENTENA y
'normal' lo vuelve a ACTIVO.
"""
import argparse
import collections
import logging
import random
import threading
import time

import cielo
import matriz
import puente
import tolerancia

SEGUNDOS_TICK = 2.0
EVENTOS_PANEL = 30

sensores = {sector: {'estado': 'ACTIVO', 'alien': False, 'fallas': 0} for sector in matriz.ANILLO}
sensores_lock = threading.Lock() # las órdenes llegan desde el hilo del puente
eventos = collections.deque(maxlen=EVENTOS_PANEL)


def anotar(nivel, texto):
    """Agrega un evento al registro que ve el panel y lo muestra en consola."""
    eventos.append({'hora': time.strftime('%H:%M:%S'), 'nivel': nivel, 'texto': texto})
    print(f"{nivel:6} {texto}")


def recibir_orden(orden):
    """Cambia el sensor de mentira según la orden que mandó el panel."""
    accion, sector = orden.get('accion'), orden.get('sector')
    if accion not in ('apagar', 'alien', 'normal') or sector not in matriz.ANILLO:
        anotar('aviso', f"Orden inválida del panel: {orden}")
        return
    with sensores_lock:
        sensor = sensores[sector]
        if accion == 'apagar':
            sensor['estado'] = 'CAIDO'
        elif accion == 'alien':
            sensor['alien'] = True
        else:
            sensor.update(estado='ACTIVO', alien=False, fallas=0)
    anotar('info', f"Orden del panel: {accion} al sensor {sector}")


def armar_estado(semilla, numero):
    """Arma un estado con el formato que publica la nave para el tick pedido."""
    objetos = cielo.generar_cielo(semilla, numero)
    with sensores_lock:
        activos = {s for s, datos in sensores.items() if datos['estado'] == 'ACTIVO'}
        cobertura = {}
        for sector, datos in sensores.items():
            if datos['estado'] != 'ACTIVO':
                cubridor = tolerancia.elegir_cubridor(sector, activos)
                if cubridor:
                    cobertura.setdefault(cubridor, []).append(sector)

        valores = {}
        for sector in matriz.ANILLO:
            datos = sensores[sector]
            cubierto = any(sector in lista for lista in cobertura.values())
            if datos['estado'] == 'ACTIVO':
                valor = cielo.valor_sector(objetos, sector)
                if datos['alien'] and random.random() < 0.5:
                    valor = 1 - valor
                    datos['fallas'] += 1
                    if datos['fallas'] >= tolerancia.FALLAS_PARA_CUARENTENA:
                        datos['estado'] = 'CUARENTENA'
                        anotar('alerta', f"Sensor {sector} en CUARENTENA")
                        valor = None
                valores[sector] = valor
            else:
                valores[sector] = cielo.valor_sector(objetos, sector) if cubierto else None

        sensores_panel = {
            sector: {
                'estado': datos['estado'],
                'cubre': cobertura.get(sector, []),
                'ultimo_latido': round(random.uniform(0.1, 0.9), 1) if datos['estado'] != 'CAIDO' else None,
                'fallas': datos['fallas'],
            }
            for sector, datos in sensores.items()
        }

    decision = matriz.decidir(valores)
    alertas = matriz.sectores_en_alerta(valores)
    maniobra = matriz.elegir_maniobra(alertas) if decision == 'ALERTA_ROJA' else None
    if decision == 'ALERTA_ROJA':
        anotar('alerta', f"ALERTA ROJA en {', '.join(alertas)}. {maniobra}")
    else:
        anotar('info', f"Tick {numero} -> {decision}")

    return {
        'tick': numero,
        'semilla': semilla,
        'matriz': valores,
        'decision': decision,
        'alertas': alertas,
        'maniobra': maniobra,
        'sensores': sensores_panel,
        'eventos': list(eventos),
    }


def main():
    parser = argparse.ArgumentParser(description='Simulador del estado de la nave para el panel')
    parser.add_argument('--semilla', type=int, default=random.randrange(1, 1_000_000))
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(message)s', datefmt='%H:%M:%S')
    if not puente.iniciar_puente(recibir_orden):
        return
    print(f"Simulador publicando con semilla {args.semilla}. Ctrl+C para salir.")

    numero = 0
    try:
        while True:
            numero += 1
            puente.publicar(armar_estado(args.semilla, numero))
            time.sleep(SEGUNDOS_TICK)
    except KeyboardInterrupt:
        print("Simulador apagado")


if __name__ == '__main__':
    main()
