# Guion del video · Aegis-Star 8-Sector

Duración objetivo: 6 a 8 minutos. Se graba la pantalla con la consola a la izquierda y el
navegador con el panel a la derecha. Se usa la semilla **19** porque en los primeros 8 ticks
aparecen todos los casos del enunciado, en este orden:

| Tick | Sectores en 1 | Decisión esperada | Qué muestra |
|------|---------------|-------------------|-------------|
| 1 | ninguno | Sin amenaza | Estado 1 del enunciado |
| 2 | O | **Alerta roja** (evasión hacia N) | Estado 4: 1 aislado |
| 3 | ninguno | Sin amenaza | |
| 4 | NO, N, NE, E, O | Tránsito seguro | Grupo que cruza el borde O–NO |
| 5 | NO, N, NE, E | Tránsito seguro | Objeto que pasa de lado |
| 6 | ninguno | Sin amenaza | |
| 7 | S, SO | Tránsito seguro | Estado 3: dos 1 seguidos |
| 8 | NO | **Alerta roja** (evasión hacia NE) | Estado 5: 1 aislado |

Antes de grabar: cerrar todo lo que use los puertos 5050, 8765 y 8080, borrar `registro.log`
y tener la terminal en la carpeta del proyecto con letra grande.


## 1. Presentación (30 s)

**Pantalla:** el enunciado o el README.

**Decir:** quiénes somos, la materia y el objetivo: una nave (servidor) y 8 sensores
(clientes), cada uno un proceso aparte, comunicados por sockets TCP. Los sensores ven
meteoritos y la nave decide con la matriz de amenazas si hay alerta roja.


## 2. Arquitectura y código (1 min 30 s)

**Pantalla:** el diagrama de la sección 5 del `PLAN.md`, después los archivos.

**Decir:**
- `nave.py` es el servidor: un hilo por sensor que solo recibe mensajes y los deja en una
  cola de prioridad, y **un solo hilo** que arma la matriz y decide. Como solo ese hilo toca
  el estado, no hay condiciones de carrera.
- `sensor.py` es el cliente de cada sector. `protocolo.py` manda JSON, un mensaje por línea,
  porque TCP puede juntar o cortar los mensajes.
- `cielo.py`: todos los procesos generan el cielo con `random.Random(f"{semilla}-{tick}")`.
  La nave reparte la semilla al conectarse, así que todos ven el mismo cielo sin hablar entre
  ellos (PRNG con semilla compartida).
- `matriz.py` tiene la regla; `tolerancia.py` los latidos, la cobertura y los aliens;
  `puente.py` manda el estado al panel por WebSocket.
- Mostrar rápido la función `sectores_en_alerta` en `matriz.py`.


## 3. Arranque (30 s)

**Pantalla:** terminal.

```
python3 iniciar.py --semilla 19
```

**Decir:** este comando lanza 9 procesos: la nave y los 8 sensores. Mostrar en la consola los
8 "Conectado sensor ..." y en el panel los 8 sensores en verde. Mencionar que cada sensor manda
un latido por segundo (la columna "Último latido" se mueve).


## 4. Ticks y decisiones (2 min)

**Pantalla:** panel, con la consola visible.

**Decir**, siguiendo la tabla de arriba:
- Tick 1: matriz en ceros, sin amenaza.
- Tick 2: solo O en 1 y sus vecinos (SO y NO) en 0. Es un 1 aislado: el meteorito viene
  directo a la nave → **alerta roja** y la nave hace una evasión de costado.
- Tick 4: NO, N, NE, E y O en 1. Están todos seguidos en el anillo (O y NO son vecinos porque
  el anillo da la vuelta), así que el objeto pasa de lado → tránsito seguro.
- Tick 7: S y SO seguidos → tránsito seguro (como el estado 3 del enunciado).
- Tick 8: solo NO → alerta roja (estado 5).
- Señalar la tabla "Últimos ticks" y que la consola dibuja la misma matriz.
- Mencionar que la nave cierra el tick cuando llegan los 8 reportes o a los 1,5 s, y que los
  reportes repetidos o tardíos se descartan (se ve en el registro si pasa).


## 5. Sensor caído y cobertura (1 min)

**Pantalla:** panel.

1. Botón **Apagar** en el sensor **E**.
2. **Decir:** el proceso del sensor se cierra. La nave deja de recibir sus latidos, lo marca
   como caído y le pide a su vecino más cercano que cubra el sector. Mostrar en la tarjeta de
   NE o SE "Cubre también: E", y en la consola "... cubre ahora E".
3. La matriz sigue teniendo dato en E porque lo reporta el vecino.
4. A los 15 s `iniciar.py` relanza el sensor E ("como si lo repararan"): vuelve a verde y el
   vecino deja de cubrirlo.


## 6. Sensor alien y cuarentena (1 min)

**Pantalla:** panel.

1. Botón **Modo alien** en el sensor **S**.
2. **Decir:** ahora el sensor miente a veces (cambia lo que ve). Como la nave conoce la semilla,
   calcula lo que el sensor debería haber visto y compara. Cada diferencia suma una falla
   (se ve el contador 1/3, 2/3). A la tercera, el sensor queda en **cuarentena**: sus reportes
   se ignoran y un vecino cubre el sector.
3. Botón **Normal** en S: la nave lo saca de cuarentena y vuelve a usar sus reportes.


## 7. Pruebas y cierre (30 s)

**Pantalla:** terminal.

```
python3 -m unittest
```

**Decir:** las pruebas cubren el protocolo (mensajes pegados y cortados), las 256
combinaciones de la matriz, el cielo determinista, la nave con sensores de prueba, la
tolerancia a fallas y el puente con el panel. Cerrar con Ctrl+C en `iniciar.py` y mostrar que
todo se apaga.


## Si algo sale mal grabando

- "Address already in use": quedó una corrida abierta. Cerrarla o esperar unos segundos.
- El panel dice "Sin conexión con la nave": la nave no está corriendo o el puerto 8765 está
  ocupado (la consola de la nave lo avisa).
- El orden de los ticks cambia si un sensor tarda en conectarse antes del primer tick: volver
  a correr `iniciar.py --semilla 19`.
