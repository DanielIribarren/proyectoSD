import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import type { EstadoNave } from '@/tipos'

const TITULOS = {
  ALERTA_ROJA: 'ALERTA ROJA · colisión inminente',
  TRANSITO_SEGURO: 'Tránsito seguro',
  SIN_AMENAZA: 'Sin amenazas',
}

/** Decisión del último tick y la maniobra que tomó la nave. */
export function BannerDecision({ estado, conectado }: { estado: EstadoNave | null; conectado: boolean }) {
  if (!conectado) {
    return (
      <Alert>
        <AlertTitle>Sin conexión con la nave</AlertTitle>
        <AlertDescription>Reintentando cada 2 s. Revisa que la nave esté corriendo (python3 iniciar.py).</AlertDescription>
      </Alert>
    )
  }
  if (!estado) {
    return (
      <Alert>
        <AlertTitle>Conectado</AlertTitle>
        <AlertDescription>Esperando el primer tick de la nave.</AlertDescription>
      </Alert>
    )
  }

  const alerta = estado.decision === 'ALERTA_ROJA'
  let detalle = 'Ningún sensor detectó objetos en este tick.'
  if (alerta) detalle = `Objeto directo en ${estado.alertas.join(', ')}. ${estado.maniobra ?? ''}`
  else if (estado.decision === 'TRANSITO_SEGURO') detalle = 'Los objetos detectados pasan de lado: sensores seguidos en 1.'

  return (
    <Alert variant={alerta ? 'destructive' : 'default'}>
      <AlertTitle className="text-base">{TITULOS[estado.decision]}</AlertTitle>
      <AlertDescription>
        Tick {estado.tick} · {detalle}
      </AlertDescription>
    </Alert>
  )
}
