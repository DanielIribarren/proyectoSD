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
| `panel/` | Panel web | Derek |
| `pruebas/` | Pruebas con `unittest` | Cada uno las suyas |

Los archivos que dicen "VERSIÓN PROVISIONAL" devuelven valores fijos para que los demás
puedan avanzar. Su responsable los reemplaza sin cambiar las firmas.


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
