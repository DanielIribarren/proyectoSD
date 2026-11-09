# Aegis-Star 8-Sector — Plan de trabajo

Proyecto de Sistemas Distribuidos (UNIMET). Una nave (servidor) rodeada de 8 sensores
(clientes) conectados por sockets. Los sensores ven meteoritos y le avisan a la nave. La nave
arma una matriz 3x3 con lo que le llega y decide si hay que dar alerta roja o no.

Equipo: Daniel, Jesus, Juan, Derek.
Entregables: código (nave + sensores) y un video corriendo el sistema.


## 1. Lo que pide el enunciado, en corto

| # | Pide | Dónde lo resolvemos |
|---|------|---------------------|
| 1 | Protocolo propio sobre sockets | `protocolo.py`: mensajes JSON, uno por línea |
| 2 | PRNG con semilla compartida | La nave reparte la semilla; cada sensor genera el mismo "cielo" y reporta solo su sector |
| 3 | Condiciones de carrera, duplicados y prioridad | Un solo hilo toca la matriz; descarte por `(tick, sector)`; `PriorityQueue` |
| 4 | Heartbeats y reconfiguración de cobertura | Latido cada 1 s; si un sensor se calla 3 s, un vecino cubre su sector |
| 5 | Sensores controlados por aliens / que fallan | Modo alien: la nave lo detecta comparando contra el PRNG y lo pone en cuarentena |


## 2. La regla de la matriz

```
[ NO  N  NE ]
[ O   x  E  ]      x = la nave (siempre vacía)
[ SO  S  SE ]
```

Las 8 casillas forman un **anillo** alrededor de la nave. Dos sensores son vecinos si están
pegados en ese anillo:

```
NO - N - NE - E - SE - S - SO - O - (vuelve a NO)
```

- Un **1 aislado** (sus dos vecinos del anillo en 0) = el objeto viene directo a la nave → **ALERTA ROJA**.
- **Dos o más 1 seguidos** = el objeto pasa de lado (tangente) → **tránsito seguro**.
- Si en la misma matriz hay un grupo de 1 seguidos y además un 1 aislado, gana el aislado: hay alerta.

| Caso | Sectores en 1 | Resultado |
|------|---------------|-----------|
| Estado 1 | ninguno | Sin amenaza |
| Estado 2 | N | Alerta roja |
| Estado 3 | NE, E | Seguro (están pegados) |
| Estado 4 | O | Alerta roja |
| Estado 5 | NO | Alerta roja |
| Figura pág. 3 | N, E | Alerta roja (entre N y E está NE en 0) |
| Borde | O, NO | Seguro (el anillo da la vuelta) |

**Ojo con el dibujo del enunciado:** en las figuras de las páginas 2 y 3 el Este está a la
izquierda y el Oeste a la derecha; en la matriz están al revés. Tomamos **la matriz como la
que manda**. Hay que confirmarlo con el profesor (ver sección 13).


## 3. Rúbrica y cómo la cubrimos

| Criterio | Pts | Para el máximo hay que... | Cómo lo cubrimos | Épica |
|----------|-----|---------------------------|------------------|-------|
| Ejecución y video | 25 | Correr con sockets sin fallas; video claro | Lanzador de 9 procesos, panel + consola, guion | E4 |
| Código nave y sensores | 25 | Roles separados, limpio, modular, documentado | Un archivo por responsabilidad, docstrings, README | E1, E2 |
| Paso de mensajes y matriz | 20 | Matriz dinámica sin pérdida, sin carreras ni deadlocks | Mensajes por línea, un hilo procesador, tiempos límite | E1 |
| Clasificación y decisiones | 15 | 100 % de aciertos, incluidos bordes y ráfagas | Regla del anillo + prueba de las 256 combinaciones | E3 |
| Generación aleatoria | 15 | Trayectorias, origen y frecuencia variados | Todo sale del PRNG; semilla nueva por corrida | E2 |


## 4. ¿Hace falta base de datos?

**No.** El enunciado y la rúbrica no la piden, y el sistema vive mientras corre: el estado
(sensores, matriz del tick, contadores) está en memoria en la nave. Una base de datos sería un
proceso más que levantar y que puede fallar en el video, sin sumar puntos.

Lo único que guardamos es un **archivo de registro** (`registro.log`) con los eventos de cada
corrida, por si hay que revisar qué pasó después de grabar. Eso lo escribe la nave con
`logging`, que viene con Python.


## 5. Arquitectura y stack

```
            ┌──────────── navegador (panel) ────────────┐
            │ React + Vite + TypeScript + shadcn/ui     │
            └───────────────▲───────────────────────────┘
                            │ WebSocket :8765 (estado por tick / órdenes)
   ┌────────────────────────┴─────────────────────────┐
   │ nave.py  (servidor TCP :5050)                    │
   │  - 1 hilo por sensor que recibe mensajes         │
   │  - cola de prioridad con los eventos             │
   │  - 1 hilo procesador: arma la matriz y decide    │
   │  - hilo de latidos: detecta sensores caídos      │
   └──▲─────▲─────▲─────▲─────▲─────▲─────▲─────▲─────┘
      │     │     │     │     │     │     │     │   TCP (JSON por línea)
     NO     N    NE     E    SE     S    SO     O   ← sensor.py x8 (procesos aparte)
```

| Parte | Tecnología |
|-------|------------|
| Nave y sensores | Python 3.12, solo librería estándar: `socket`, `threading`, `queue`, `random`, `json`, `logging` |
| Puente al panel | `websockets` (única librería de Python a instalar) |
| Panel | Vite + React + TypeScript + Tailwind + shadcn/ui |
| Pruebas | `unittest` |
| Lanzador | `subprocess` |
| Código compartido | Repositorio en GitHub, una rama por épica |


## 6. Protocolo de mensajes (contrato entre E1 y E2)

Cada mensaje es un JSON en **una línea** que termina en `\n`. TCP no respeta los límites de
los mensajes (dos `send` pueden llegar pegados en un `recv`), así que el receptor junta lo que
llega en un buffer y corta por `\n`.

| Tipo | Quién → quién | Campos | Para qué |
|------|---------------|--------|----------|
| `HOLA` | sensor → nave | `sector` | Registrarse |
| `BIENVENIDA` | nave → sensor | `semilla`, `tick_actual` | Le pasa la semilla compartida |
| `RECHAZO` | nave → sensor | `motivo` | Sector repetido o inválido |
| `TICK` | nave → todos | `tick` | "Escaneen el tick 42" (la nave marca el ritmo) |
| `REPORTE` | sensor → nave | `tick`, `sector`, `valor` (0/1), `objetos` | Lo que vio, aunque sea 0. Si cubre otro sector manda un `REPORTE` por cada sector |
| `LATIDO` | sensor → nave | `sector` | "Sigo vivo", cada 1 s, en su propio hilo |
| `COBERTURA` | nave → sensor | `sectores` | Lista de sectores extra que debe reportar (vacía = solo el suyo) |
| `ORDEN` | nave → sensor | `accion`: `apagar` / `alien` / `normal` | Para provocar fallas en la demo |

Ejemplo:

```
{"tipo": "REPORTE", "tick": 42, "sector": "NE", "valor": 1, "objetos": [{"id": "42-1", "tipo": "directa", "sectores": ["NE"], "tamano": 3, "velocidad": 18}]}
```

La nave cierra el tick cuando llegan los 8 reportes o a los 1,5 s, lo que pase primero. Nunca
espera para siempre.


## 7. Contratos entre módulos

Esto es lo que permite que cada uno trabaje por su lado. **Nadie cambia una firma sin avisar
al grupo.** Mientras el módulo de otro no esté listo, se usa una versión falsa (stub) que
devuelve valores fijos con la misma firma.

Los sectores siempre se escriben así: `'NO', 'N', 'NE', 'E', 'SE', 'S', 'SO', 'O'`.

**`protocolo.py`** (E1) — lo usan la nave y los sensores
```python
def enviar(sock, mensaje):          # mensaje es un dict; lo manda como JSON + '\n'
def leer_mensajes(sock):            # generador: devuelve un dict por cada línea que llega
```

**`cielo.py`** (E2) — lo usan los sensores y la nave (para auditar)
```python
def generar_cielo(semilla, tick):   # lista de objetos del tick, igual en todos los procesos
def valor_sector(objetos, sector):  # 1 si algún objeto pasa por ese sector, si no 0
```
Cada objeto: `{"id": "42-1", "tipo": "directa"|"tangente"|"rasante", "sectores": [...], "tamano": 1-5, "velocidad": km/s}`

**`matriz.py`** (E3) — lo usa la nave
```python
ANILLO = ['NO', 'N', 'NE', 'E', 'SE', 'S', 'SO', 'O']
def sectores_en_alerta(valores):    # valores = {sector: 0|1|None}; devuelve los sectores con 1 aislado
def decidir(valores):               # 'ALERTA_ROJA' | 'TRANSITO_SEGURO' | 'SIN_AMENAZA'
def elegir_maniobra(alertas):       # texto: "Evasión hacia S" o "Escudos activados"
def texto_matriz(valores):          # la matriz 3x3 lista para imprimir en consola
```

**`tolerancia.py`** (E3) — lo usa la nave
```python
LIMITE_LATIDO = 3.0
def sectores_caidos(ultimo_latido, ahora):    # ultimo_latido = {sector: time.time()}
def elegir_cubridor(sector, activos):         # vecino vivo más cercano en el anillo, o None
def auditar(sector, reportado, esperado, fallas):  # 'OK' | 'SOSPECHOSO' | 'CUARENTENA' (3 fallas)
```
`fallas` es un diccionario `{sector: cantidad}` que guarda la nave; `auditar` le suma 1 a
`fallas[sector]` cuando `reportado != esperado` y decide según el total.

**`puente.py`** (E4) — lo usa la nave
```python
def iniciar_puente(al_recibir_orden):  # levanta el WebSocket en :8765; llama al_recibir_orden(dict)
def publicar(estado):                  # manda el estado a todos los navegadores conectados
```

**Estado que la nave publica en cada tick** (contrato E1 → E4)
```json
{
  "tick": 42,
  "semilla": 91827,
  "matriz": {"NO": 0, "N": 1, "NE": 0, "E": 0, "SE": 0, "S": 0, "SO": 0, "O": null},
  "decision": "ALERTA_ROJA",
  "alertas": ["N"],
  "maniobra": "Evasión hacia S",
  "sensores": {
    "N":  {"estado": "ACTIVO", "cubre": [], "ultimo_latido": 0.4, "fallas": 0},
    "O":  {"estado": "CAIDO",  "cubre": [], "ultimo_latido": 5.2, "fallas": 0}
  },
  "eventos": [{"hora": "14:03:22", "nivel": "alerta", "texto": "Alerta roja en N"}]
}
```
`null` en la matriz = sector sin dato en ese tick. Estados de sensor: `ACTIVO`, `CAIDO`, `CUARENTENA`
(un sector que nunca se conectó aparece como `CAIDO` con `ultimo_latido: null`). `maniobra` es `null`
si no hay alerta. Niveles de evento: `info`, `aviso`, `alerta`.

**Orden que manda el panel** (contrato E4 → E1): `{"accion": "apagar"|"alien"|"normal", "sector": "NE"}`


## 8. Épicas por persona

Cada persona es dueña de sus archivos. Así casi no hay conflictos al unir ramas.

| Épica | Responsable | Archivos que toca | Rama |
|-------|-------------|-------------------|------|
| E1 Nave (servidor) e integración | **Daniel** | `protocolo.py`, `nave.py`, `pruebas/test_protocolo.py` | `e1-nave` |
| E2 Sensores y generación aleatoria | **Jesus** | `cielo.py`, `sensor.py`, `pruebas/test_cielo.py` | `e2-sensores` |
| E3 Decisión y tolerancia a fallas | **Juan** | `matriz.py`, `tolerancia.py`, `pruebas/test_matriz.py`, `pruebas/test_tolerancia.py`, `pruebas/test_integracion.py` | `e3-decision` |
| E4 Panel, lanzador y demo | **Derek** | `puente.py`, `simulador_estado.py`, `panel/`, `iniciar.py`, `README.md`, guion del video | `e4-panel` |

### E1 — Nave (servidor) e integración · Daniel

La nave recibe, ordena y reparte. No decide nada por sí misma: le pregunta a `matriz.py` y a
`tolerancia.py`.

**HU-01 Registrar sensores.** Como nave quiero que cada sensor se registre con su sector para saber quién cubre qué parte del espacio.
- [ ] Escucha en `127.0.0.1:5050`, un hilo por sensor.
- [ ] Sector repetido o inválido → `RECHAZO` y se cierra.
- [ ] Al registrarse le manda `BIENVENIDA` con la semilla.

**HU-02 Mensajes completos.** Como nave y como sensor queremos recibir mensajes enteros aunque TCP los junte o los corte.
- [ ] Mensajes JSON por línea, leídos con buffer.
- [ ] Un mensaje mal formado se anota y se ignora.

**HU-03 Ticks y matriz por tick.** Como nave quiero marcar el ritmo y juntar los reportes de cada tick para armar la matriz sin perder datos.
- [ ] Manda `TICK` a todos cada `SEGUNDOS_TICK`.
- [ ] Los hilos de los sensores solo dejan eventos en la cola; un único hilo arma la matriz.
- [ ] Cierra el tick con 8 reportes o a los 1,5 s; los que faltan quedan en `None`.

**HU-04 Sin duplicados y con prioridad.** Como nave quiero descartar repetidos y atender primero lo grave.
- [ ] Clave `(tick, sector)`: vale el primero; los repetidos y los de ticks cerrados se descartan y se anotan.
- [ ] `PriorityQueue`: reporte con detección (valor 1) > sensor caído > tick y reporte vacío > latido. La alerta roja se decide al cerrar el tick, en el mismo hilo, sin pasar por la cola.

**HU-05 Conectar las piezas.** Como equipo queremos que la nave use los módulos de los demás.
- [ ] Llama a `matriz.decidir` y `elegir_maniobra` al cerrar cada tick e imprime `texto_matriz`.
- [ ] Llama a `tolerancia.sectores_caidos` cada segundo y manda `COBERTURA` según `elegir_cubridor`.
- [ ] Llama a `tolerancia.auditar` con `cielo.valor_sector` como valor esperado.
- [ ] Llama a `puente.publicar(estado)` al cerrar cada tick y reenvía las órdenes del panel como `ORDEN`.
- [ ] Escribe `registro.log`.

| Tarea | Descripción | Depende de |
|-------|-------------|------------|
| T1.1 | `protocolo.py` + `test_protocolo.py` (mensajes pegados y cortados) | — **primera de todo el proyecto** |
| T1.2 | Servidor con hilos, registro, `BIENVENIDA`/`RECHAZO` | T1.1 |
| T1.3 | Hilo de ticks + cola de prioridad + hilo procesador | T1.2 |
| T1.4 | Cierre de tick, duplicados, reportes tardíos | T1.3 |
| T1.5 | Conectar `matriz.py` (con stub hasta que Juan entregue) | T1.4 |
| T1.6 | Conectar `tolerancia.py`: latidos, `COBERTURA`, auditoría | T1.5 |
| T1.7 | Conectar `puente.py`: publicar estado, recibir órdenes | T1.5 |
| T1.8 | `registro.log` con `logging` | T1.3 |

### E2 — Sensores y generación aleatoria · Jesus

**HU-06 Cielo aleatorio con semilla compartida.** Como sensor quiero generar el mismo cielo que mis compañeros a partir de la semilla para que el entorno sea distribuido y determinista.
- [ ] `random.Random(f"{semilla}-{tick}")`: misma semilla y tick → mismos objetos en cualquier proceso.
- [ ] Trayectorias `directa` (1 sector), `tangente` (2–3 seguidos) y `rasante` (4 seguidos: pasa rozando la nave). Cualquiera puede cruzar el borde O–NO.
- [ ] Frecuencia variable: ticks vacíos, normales y ráfagas.
- [ ] Varían origen, tamaño y velocidad.

**HU-07 Reportar.** Como sensor quiero registrarme, recibir la semilla y mandar un `REPORTE` por cada `TICK`, aunque no vea nada.
- [ ] `python3 sensor.py NE` se conecta y manda `HOLA`.
- [ ] Un `REPORTE` por tick por cada sector que cubre.
- [ ] Si la nave no está, reintenta cada 2 s sin caerse.

**HU-08 Latidos y cobertura (lado sensor).** Como sensor quiero avisar que sigo vivo y cubrir sectores ajenos cuando la nave me lo pide.
- [ ] Hilo aparte que manda `LATIDO` cada 1 s.
- [ ] Con `COBERTURA` agrega esos sectores a sus reportes; con lista vacía vuelve a solo el suyo.

**HU-09 Modo alien y apagado.** Como sensor quiero poder fallar a propósito para probar la tolerancia de la nave.
- [ ] `ORDEN alien` (o `--alien` al arrancar): a veces invierte el valor que reporta.
- [ ] `ORDEN apagar`: deja de latir y cierra el socket. `ORDEN normal`: vuelve a reportar bien.

| Tarea | Descripción | Depende de |
|-------|-------------|------------|
| T2.1 | `cielo.py` + `test_cielo.py` (determinismo, variedad, rasantes) | — |
| T2.2 | `sensor.py`: conexión, `HOLA`, reintentos | T1.1 |
| T2.3 | Responder `TICK` con `REPORTE` | T2.1, T2.2 |
| T2.4 | Hilo de latidos | T2.2 |
| T2.5 | `COBERTURA` | T2.3 |
| T2.6 | `ORDEN` (alien / apagar / normal) | T2.3 |

Para probar sin la nave de Daniel: un servidor mínimo de 20 líneas que mande `BIENVENIDA` y `TICK`.

### E3 — Decisión y tolerancia a fallas · Juan

Todo es lógica pura: **ningún archivo de esta épica abre sockets**. Se prueba sola y se le
entrega a Daniel.

**HU-10 Clasificar la matriz.** Como operador quiero que la nave diga ALERTA ROJA si hay un 1 aislado y TRÁNSITO SEGURO si los 1 están seguidos.
- [ ] Los 5 estados del enunciado + la figura de N y E dan lo esperado.
- [ ] O y NO cuentan como vecinos.
- [ ] Un sector en `None` se trata como 0 (preferimos una falsa alarma a no ver un choque).
- [ ] Prueba de las 256 combinaciones contra la definición.

**HU-11 Maniobra.** Como operador quiero saber qué hace la nave ante la alerta.
- [ ] Una alerta → evasión de costado, dos casillas más allá en el anillo (N → E, SO → NO). Ir hacia el lado opuesto dejaría a la nave en la misma línea del objeto.
- [ ] Dos o más alertas a la vez → escudos.

**HU-12 Detectar sensores caídos y elegir quién cubre.** Como nave quiero saber qué sensor dejó de latir y qué vecino toma su sector.
- [ ] `sectores_caidos`: los que pasan `LIMITE_LATIDO` sin latir.
- [ ] `elegir_cubridor`: vecino vivo más cercano (primero sentido horario, luego antihorario); `None` si no hay.

**HU-13 Auditar sensores (aliens).** Como nave quiero detectar al sensor que miente.
- [ ] Cada diferencia entre lo reportado y lo esperado suma una falla; 3 → `CUARENTENA`.

**HU-14 Prueba de integración.** Como equipo queremos una prueba que levante todo y verifique que funciona junto.
- [ ] Arranca la nave y los 8 sensores con `subprocess`, corre 5 ticks con semilla fija y compara las decisiones con las esperadas.

| Tarea | Descripción | Depende de |
|-------|-------------|------------|
| T3.1 | `matriz.py`: `sectores_en_alerta`, `decidir` + pruebas | — |
| T3.2 | `texto_matriz`, `elegir_maniobra` + pruebas | T3.1 |
| T3.3 | `tolerancia.py`: `sectores_caidos`, `elegir_cubridor` + pruebas | — |
| T3.4 | `auditar` + pruebas | — |
| T3.5 | `test_integracion.py` | T1.5, T2.3 |

### E4 — Panel, lanzador y demo · Derek

**HU-15 Puente WebSocket.** Como panel quiero recibir el estado de la nave en vivo y mandarle órdenes.
- [x] `puente.py` corre en un hilo aparte, puerto 8765, y no bloquea a la nave.
- [x] `simulador_estado.py` publica estados falsos con el formato del contrato, para trabajar sin la nave.

**HU-16 Panel.** Como operador quiero ver la matriz, los sensores, la decisión y los eventos.
- [x] Matriz 3x3 con la nave al centro; la casilla en alerta en rojo, `null` como `?`.
- [x] Una tarjeta por sensor: estado, a quién cubre, último latido, fallas.
- [x] Banner de decisión y maniobra; registro de eventos con scroll.
- [x] Si se corta el WebSocket, muestra "Sin conexión con la nave" y reintenta.

**HU-17 Provocar fallas.** Como profesor quiero ver qué pasa cuando un sensor se cae o lo toman los aliens.
- [x] Botones "Apagar", "Modo alien" y "Normal" en cada tarjeta.

**HU-18 Arranque y demo.** Como profesor quiero levantar todo con un comando y ver un video claro.
- [x] `python3 iniciar.py [--semilla 1234]` abre la nave y los 8 sensores.
- [x] README con instalación y pasos.
- [x] Guion del video: arranque → ticks normales → alerta roja → tránsito seguro → borde O/NO → sensor caído y cobertura → sensor alien y cuarentena.

| Tarea | Descripción | Depende de |
|-------|-------------|------------|
| T4.1 | `puente.py` + `simulador_estado.py` | — |
| T4.2 | Proyecto Vite + shadcn, layout del panel | — |
| T4.3 | Matriz, tarjetas, banner y eventos conectados al simulador | T4.1, T4.2 |
| T4.4 | Botones de órdenes | T4.3 |
| T4.5 | `iniciar.py` | T1.2, T2.2 |
| T4.6 | README y guion del video | T4.5 |
| T4.7 | Grabar y editar el video | Todo |


## 9. Orden de trabajo e hitos

| Hito | Qué se cumple | Quién |
|------|---------------|-------|
| H0 | Repo creado, contratos aceptados, stubs subidos, `protocolo.py` listo (T1.1) | Daniel, todos revisan |
| H1 | Cada épica funciona sola con sus pruebas (E2 con nave falsa, E4 con simulador) | Todos en paralelo |
| H2 | Nave + 8 sensores hablando por consola con la decisión de `matriz.py` | Daniel + Jesus + Juan |
| H3 | Latidos, cobertura y aliens funcionando; `test_integracion.py` en verde | Daniel + Jesus + Juan |
| H4 | Panel conectado a la nave real, `iniciar.py` | Derek + Daniel |
| H5 | Video grabado y entregado en Moodle | Derek, todos revisan |

Después de H0 nadie espera a nadie hasta H2.


## 10. Forma de trabajo

- Un repo en GitHub, rama `main` protegida. Cada uno trabaja en su rama y abre un PR.
- Cada PR lo revisa otra persona del equipo y debe pasar `python3 -m unittest discover pruebas`.
- Si alguien necesita cambiar un contrato (sección 7), lo avisa en el grupo antes de tocarlo.
- Cada historia se cierra cuando todos sus `[ ]` están marcados y probados.


## 11. Cómo escribimos el código

Que se lea como lo que hacemos en clase (ver `distribuidos-27-09-26-servidor.py`):

- Nombres en español y directos: `sensores`, `matriz`, `tick`, `semilla`, `sector`, `vecinos`, `cola_eventos`.
- Constantes arriba en mayúscula: `HOST`, `PUERTO_SENSORES`, `SEGUNDOS_TICK`, `LIMITE_LATIDO`.
- Docstring de **una línea** por función que diga qué hace. Nada de bloques `Args/Returns`.
- Comentarios solo donde la razón no es obvia (por qué hay un lock, por qué `list()` al recorrer).
- Sin clases donde alcanza una función. Funciones cortas.
- Nada de emojis, banners ni separadores decorativos en la consola.

```python
ANILLO = ['NO', 'N', 'NE', 'E', 'SE', 'S', 'SO', 'O'] # orden alrededor de la nave


def sectores_en_alerta(valores):
    """Devuelve los sectores que tienen un 1 y sus dos vecinos del anillo en 0."""
    alertas = []
    for i, sector in enumerate(ANILLO):
        anterior = ANILLO[i - 1]          # con i = 0 da ANILLO[-1], o sea O: el anillo da la vuelta
        siguiente = ANILLO[(i + 1) % 8]
        if valores[sector] == 1 and not valores[anterior] and not valores[siguiente]:
            alertas.append(sector)
    return alertas
```


## 12. Cómo hacemos el panel para que no parezca generado

- shadcn con su tema por defecto (`neutral`). Sin degradados, sin brillos, sin emojis.
- Componentes: `Card`, `Badge`, `Table`, `Button`, `ScrollArea`, `Alert`. Nada más.
- Un solo color de acento: rojo, solo para la alerta. Verde y gris para el estado de los sensores.
- Fuente monoespaciada solo para la matriz y el registro.
- Textos cortos y técnicos: "Sensor NE · activo · último latido 0,4 s".
- Sin animaciones de adorno; solo resaltar la casilla que cambió.


## 13. Pendientes

1. **Preguntar al profesor** si E y O van como en la matriz (E a la derecha) o como en el dibujo.
2. **Fecha de entrega** en Moodle, para ponerle fecha a los hitos.
3. Duración del tick: 2 s (constante `SEGUNDOS_TICK`, se puede cambiar).
