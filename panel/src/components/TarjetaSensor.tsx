import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardFooter, CardHeader, CardTitle } from '@/components/ui/card'
import type { Accion, Sector, Sensor } from '@/tipos'

const FALLAS_PARA_CUARENTENA = 3 // igual que tolerancia.py

const INSIGNIA = {
  ACTIVO: { texto: 'activo', variante: 'ok' },
  CAIDO: { texto: 'caído', variante: 'secondary' },
  CUARENTENA: { texto: 'cuarentena', variante: 'default' },
} as const

function segundos(valor: number) {
  return valor.toLocaleString('es-VE', { minimumFractionDigits: 1, maximumFractionDigits: 1 })
}

interface Props {
  sector: Sector
  sensor: Sensor | undefined
  conectado: boolean
  alOrdenar: (accion: Accion) => void
}

/** Estado de un sensor y los botones para provocarle fallas. */
export function TarjetaSensor({ sector, sensor, conectado, alOrdenar }: Props) {
  const estado = sensor?.estado ?? 'CAIDO'
  const insignia = INSIGNIA[estado]
  return (
    <Card className="gap-3 py-4" data-sector={sector}>
      <CardHeader className="px-4">
        <CardTitle className="font-mono">Sensor {sector}</CardTitle>
        <Badge variant={insignia.variante}>{insignia.texto}</Badge>
      </CardHeader>
      <CardContent className="space-y-1 px-4 text-sm text-muted-foreground">
        <div>
          Último latido:{' '}
          <span className="font-mono text-foreground">
            {sensor?.ultimo_latido == null ? '—' : `${segundos(sensor.ultimo_latido)} s`}
          </span>
        </div>
        <div>
          Cubre también:{' '}
          <span className="font-mono text-foreground">{sensor?.cubre.length ? sensor.cubre.join(', ') : '—'}</span>
        </div>
        <div>
          Fallas:{' '}
          <span className="font-mono text-foreground">
            {sensor?.fallas ?? 0}/{FALLAS_PARA_CUARENTENA}
          </span>
        </div>
      </CardContent>
      <CardFooter className="flex-wrap px-4">
        <Button size="sm" variant="outline" disabled={!conectado || estado === 'CAIDO'} onClick={() => alOrdenar('apagar')}>
          Apagar
        </Button>
        <Button size="sm" variant="outline" disabled={!conectado || estado !== 'ACTIVO'} onClick={() => alOrdenar('alien')}>
          Modo alien
        </Button>
        <Button size="sm" variant="outline" disabled={!conectado} onClick={() => alOrdenar('normal')}>
          Normal
        </Button>
      </CardFooter>
    </Card>
  )
}
