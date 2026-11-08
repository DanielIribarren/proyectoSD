// Formato del estado que publica la nave en cada tick (sección 7 del PLAN.md)

export const ANILLO = ['NO', 'N', 'NE', 'E', 'SE', 'S', 'SO', 'O'] as const
export type Sector = (typeof ANILLO)[number]

export type Decision = 'ALERTA_ROJA' | 'TRANSITO_SEGURO' | 'SIN_AMENAZA'
export type EstadoSensor = 'ACTIVO' | 'CAIDO' | 'CUARENTENA'
export type Accion = 'apagar' | 'alien' | 'normal'

export interface Sensor {
  estado: EstadoSensor
  cubre: Sector[]
  ultimo_latido: number | null
  fallas: number
}

export interface Evento {
  hora: string
  nivel: 'info' | 'aviso' | 'alerta'
  texto: string
}

export interface EstadoNave {
  tick: number
  semilla: number
  matriz: Record<Sector, 0 | 1 | null>
  decision: Decision
  alertas: Sector[]
  maniobra: string | null
  sensores: Record<Sector, Sensor>
  eventos: Evento[]
}

export interface Orden {
  accion: Accion
  sector: Sector
}
