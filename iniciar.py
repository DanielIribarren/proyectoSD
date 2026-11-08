"""
Arranca todo el sistema con un solo comando: la nave, los 8 sensores y el panel web.
Responsable: Derek (E4).

Correr con:  python3 iniciar.py [--semilla 1234] [--alien NE] [--revivir 15] [--ver-sensores] [--sin-navegador]

Cada sensor es un proceso aparte (igual que si se abrieran 9 terminales). La consola muestra
lo que dice la nave; lo de cada sensor queda en logs/sensor_<SECTOR>.log, salvo que se pida
--ver-sensores. El panel se sirve en http://127.0.0.1:8080 si ya se compiló (panel/dist).

Si un sensor se apaga (por ejemplo con el botón "Apagar" del panel), a los --revivir segundos
se vuelve a lanzar, como si lo repararan. Así se ve en la demo que la nave le devuelve su sector.
Ctrl+C apaga todo.
"""
import argparse
import functools
import http.server
import os
import random
import subprocess
import sys
import threading
import time
import webbrowser

from matriz import ANILLO

CARPETA = os.path.dirname(os.path.abspath(__file__))
CARPETA_PANEL = os.path.join(CARPETA, 'panel', 'dist')
CARPETA_LOGS = os.path.join(CARPETA, 'logs')
PUERTO_WEB = 8080
ESPERA_NAVE = 0.5 # los sensores igual reintentan si la nave tarda más
SEGUNDOS_REVISION = 1.0


def lanzar(argumentos, salida=None):
    """Arranca un script de Python del proyecto como proceso aparte."""
    # -u: sin buffer, para que los mensajes salgan en el momento y no al final
    return subprocess.Popen([sys.executable, '-u'] + argumentos, cwd=CARPETA, stdout=salida, stderr=subprocess.STDOUT)


def lanzar_sensor(sector, alien, ver_sensores):
    """Arranca el sensor de un sector. Su salida va a la consola o a su archivo en logs/."""
    argumentos = ['sensor.py', sector] + (['--alien'] if alien else [])
    if ver_sensores:
        return lanzar(argumentos)
    salida = open(os.path.join(CARPETA_LOGS, f'sensor_{sector}.log'), 'a', encoding='utf-8')
    return lanzar(argumentos, salida)


class PaginaSilenciosa(http.server.SimpleHTTPRequestHandler):
    """Sirve los archivos del panel sin imprimir una línea por cada pedido del navegador."""

    def log_message(self, formato, *args):
        pass


def servir_panel():
    """Sirve panel/dist en PUERTO_WEB desde un hilo aparte. Devuelve la dirección o None si no se puede."""
    if not os.path.isfile(os.path.join(CARPETA_PANEL, 'index.html')):
        print("iniciar: el panel no está compilado. Para verlo:  cd panel && npm install && npm run build")
        return None
    pagina = functools.partial(PaginaSilenciosa, directory=CARPETA_PANEL)
    try:
        servidor = http.server.ThreadingHTTPServer(('127.0.0.1', PUERTO_WEB), pagina)
    except OSError as error:
        print(f"iniciar: no se pudo abrir el puerto {PUERTO_WEB} para el panel ({error})")
        return None
    threading.Thread(target=servidor.serve_forever, daemon=True).start()
    return f"http://127.0.0.1:{PUERTO_WEB}"


def vigilar(nave, sensores, args):
    """Revisa los procesos: si la nave se cae se termina todo; si un sensor se apaga, se relanza después."""
    apagado_desde = {} # sector -> hora en la que se notó que su proceso terminó
    while True:
        time.sleep(SEGUNDOS_REVISION)
        if nave.poll() is not None:
            print("iniciar: la nave terminó, se apaga todo")
            return
        for sector, proceso in sensores.items():
            if proceso.poll() is None:
                continue
            if sector not in apagado_desde:
                apagado_desde[sector] = time.time()
                if args.revivir:
                    print(f"iniciar: el sensor {sector} se apagó, se relanza en {args.revivir:.0f} s")
            elif args.revivir and time.time() - apagado_desde[sector] >= args.revivir:
                print(f"iniciar: relanzo el sensor {sector} (como si lo repararan)")
                sensores[sector] = lanzar_sensor(sector, False, args.ver_sensores)
                del apagado_desde[sector]


def apagar_todo(procesos):
    """Termina los procesos que sigan vivos y espera a que cierren."""
    for proceso in procesos:
        if proceso.poll() is None:
            proceso.terminate()
    for proceso in procesos:
        try:
            proceso.wait(timeout=3)
        except subprocess.TimeoutExpired:
            proceso.kill()


def main():
    parser = argparse.ArgumentParser(description='Arranca la nave, los 8 sensores y el panel de Aegis-Star')
    parser.add_argument('--semilla', type=int, default=random.randrange(1, 1_000_000))
    parser.add_argument('--alien', nargs='*', default=[], choices=ANILLO, metavar='SECTOR',
                        help='sectores que arrancan en modo alien, por ejemplo --alien NE S')
    parser.add_argument('--revivir', type=float, default=15, help='segundos para relanzar un sensor apagado (0 = no)')
    parser.add_argument('--ver-sensores', action='store_true', help='mostrar también lo que imprime cada sensor')
    parser.add_argument('--sin-navegador', action='store_true', help='no abrir el navegador')
    args = parser.parse_args()

    os.makedirs(CARPETA_LOGS, exist_ok=True)
    print(f"iniciar: semilla {args.semilla}. Ctrl+C para apagar todo.")

    nave = lanzar(['nave.py', '--semilla', str(args.semilla)])
    time.sleep(ESPERA_NAVE)
    sensores = {sector: lanzar_sensor(sector, sector in args.alien, args.ver_sensores) for sector in ANILLO}
    print(f"iniciar: 8 sensores lanzados{'' if args.ver_sensores else ' (su salida está en logs/)'}")

    direccion = servir_panel()
    if direccion:
        print(f"iniciar: panel en {direccion}")
        if not args.sin_navegador:
            webbrowser.open(direccion)

    try:
        vigilar(nave, sensores, args)
    except KeyboardInterrupt:
        print("\niniciar: apagando")
    finally:
        apagar_todo([nave] + list(sensores.values()))


if __name__ == '__main__':
    main()
