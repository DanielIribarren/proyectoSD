import { useEffect, useState } from 'react'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { BannerDecision } from '@/components/BannerDecision'
import { Historial } from '@/components/Historial'
import { Matriz } from '@/components/Matriz'
import { Registro } from '@/components/Registro'
import { TarjetaSensor } from '@/components/TarjetaSensor'
import { ANILLO, type EstadoNave } from '@/tipos'
import { usarNave } from '@/usarNave'

const TICKS_HISTORIAL = 8

export default function App() {
  const { estado, conectado, mandarOrden } = usarNave()
  const [historial, setHistorial] = useState<EstadoNave[]>([])

  // Guarda los últimos ticks; si la nave se reinicia (tick más chico), empieza de cero
  useEffect(() => {
    if (!estado) return
    setHistorial((antes) => {
      if (antes[0]?.tick === estado.tick) return antes
      const siguen = antes[0] && estado.tick > antes[0].tick ? antes : []
      return [estado, ...siguen].slice(0, TICKS_HISTORIAL)
    })
  }, [estado])

  const activos = estado ? ANILLO.filter((s) => estado.sensores[s]?.estado === 'ACTIVO').length : 0

  return (
    <div className="mx-auto max-w-7xl space-y-4 p-6">
      <header className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-xl font-semibold">Aegis-Star · Centro de mando</h1>
          <p className="text-sm text-muted-foreground">Nave y 8 sensores conectados por sockets</p>
        </div>
        <div className="flex items-center gap-2 font-mono text-sm">
          <Badge variant={conectado ? 'ok' : 'secondary'}>{conectado ? 'conectado' : 'sin conexión'}</Badge>
          {estado && (
            <>
              <Badge variant="outline">tick {estado.tick}</Badge>
              <Badge variant="outline">semilla {estado.semilla}</Badge>
              <Badge variant="outline">{activos}/8 sensores activos</Badge>
            </>
          )}
        </div>
      </header>

      <BannerDecision estado={estado} conectado={conectado} />

      <div className="grid gap-4 lg:grid-cols-[minmax(0,22rem)_minmax(0,1fr)_minmax(0,1fr)]">
        <Card>
          <CardHeader>
            <div className="space-y-1.5">
              <CardTitle>Matriz de amenazas</CardTitle>
              <CardDescription>1 aislado = alerta roja · 1 seguidos = tránsito</CardDescription>
            </div>
          </CardHeader>
          <CardContent>
            <Matriz estado={conectado ? estado : null} />
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Últimos ticks</CardTitle>
          </CardHeader>
          <CardContent>
            <Historial ticks={historial} />
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Registro de la nave</CardTitle>
          </CardHeader>
          <CardContent>
            <Registro eventos={estado?.eventos ?? []} />
          </CardContent>
        </Card>
      </div>

      <section className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {ANILLO.map((sector) => (
          <TarjetaSensor
            key={sector}
            sector={sector}
            sensor={estado?.sensores[sector]}
            conectado={conectado}
            alOrdenar={(accion) => mandarOrden({ accion, sector })}
          />
        ))}
      </section>
    </div>
  )
}
