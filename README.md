# Aegis-Star 8-Sector

Proyecto de Sistemas Distribuidos (UNIMET). Una nave (servidor) y 8 sensores (clientes)
conectados por sockets. Los sensores detectan meteoritos y la nave decide con la matriz de
amenazas si hay alerta roja.

Equipo: Daniel Iribarren, Jesus, Juan, Derek.

El plan completo, las historias de usuario y quién hace qué están en [PLAN.md](PLAN.md).


## Archivos

| Archivo | Qué hace | Responsable |
|---------|----------|-------------|
| `protocolo.py` | Enviar y recibir mensajes JSON por línea | Daniel |
| `nave.py` | Servidor central | Daniel |
| `cielo.py` | Genera los meteoritos con la semilla compartida | Jesus |
| `sensor.py` | Cliente de cada sector | Jesus |
| `matriz.py` | Regla de alerta de la matriz 3x3 | Juan |
| `tolerancia.py` | Sensores caídos, cobertura y aliens | Juan |
| `puente.py` | WebSocket hacia el panel | Derek |
| `simulador_estado.py` | Estados falsos para probar el panel sin la nave | Derek |
| `iniciar.py` | Arranca la nave, los 8 sensores y el panel con un comando | Derek |
| `panel/` | Panel web (Vite + React + TypeScript + Tailwind) | Derek |
| `GUION_VIDEO.md` | Guion del video de la demo | Derek |
| `pruebas/` | Pruebas con `unittest` | Cada uno las suyas |

Los archivos que dicen "VERSIÓN PROVISIONAL" devuelven valores fijos para que los demás
puedan avanzar. Su responsable los reemplaza sin cambiar las firmas.


## Instalación (una sola vez)

Hace falta Python 3.12 o más nuevo y Node 20 o más nuevo (Node solo para compilar el panel).

```
pip install -r requirements.txt
cd panel
npm install
npm run build
cd ..
```

`requirements.txt` solo trae `websockets`. Si no está instalada, la nave corre igual pero sin panel.


## Cómo correr el sistema

Todo de una vez (nave + 8 sensores + panel en el navegador):

```
python3 iniciar.py
```

Abre http://127.0.0.1:8080 con el panel. La consola muestra lo que hace la nave; lo de cada
sensor queda en `logs/sensor_<SECTOR>.log`. Ctrl+C apaga todo.

Opciones:

| Opción | Para qué |
|--------|----------|
| `--semilla 19` | Repetir siempre el mismo cielo (la del video es 19) |
| `--alien NE S` | Arrancar esos sensores en modo alien |
| `--revivir 15` | Segundos para relanzar un sensor que se apagó (0 = no se relanza) |
| `--ver-sensores` | Mostrar en la consola también lo que imprime cada sensor |
| `--sin-navegador` | No abrir el navegador |

A mano, en 9 terminales, también funciona:

```
python3 nave.py --semilla 19
python3 sensor.py NO
python3 sensor.py N
...                      (uno por sector: NO N NE E SE S SO O)
```

### Panel

- **Matriz de amenazas**: rojo = 1 aislado (alerta roja), gris oscuro = 1 que es parte de un
  grupo seguido (tránsito), `?` = sector sin dato en ese tick. Las casillas que cambiaron
  respecto al tick anterior se marcan con un borde.
- **Últimos ticks**: qué sectores dieron 1 y qué decidió la nave.
- **Registro de la nave**: los mismos eventos que salen en consola y en `registro.log`.
- **Tarjetas de sensores**: estado, último latido, a quién cubre y fallas. Los botones
  *Apagar*, *Modo alien* y *Normal* mandan una `ORDEN` al sensor a través de la nave.

Para trabajar en el panel sin levantar la nave:

```
python3 simulador_estado.py        # publica estados falsos en ws://127.0.0.1:8765
cd panel && npm run dev            # http://localhost:5173 con recarga en caliente
```


## Cómo correr las pruebas

Desde la carpeta del proyecto:

```
python3 -m unittest -v
```


## Cómo trabajamos con git

1. Cada uno trabaja en su rama: `e1-nave`, `e2-sensores`, `e3-decision`, `e4-panel`.

   ```
   git checkout main
   git pull
   git checkout -b e2-sensores
   ```

2. Antes de subir, correr las pruebas. Tienen que pasar todas.
3. Subir la rama y abrir un Pull Request hacia `main`. Lo revisa otra persona del equipo.
4. Si hay que cambiar una firma de la sección 7 del PLAN.md, se avisa en el grupo antes.
