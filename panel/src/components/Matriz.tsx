import { useRef } from 'react'
import { cn } from '@/lib/utils'
import type { EstadoNave, Sector } from '@/tipos'

// Igual que FILAS en matriz.py: la nave (null) en el centro
const FILAS: (Sector | null)[][] = [
  ['NO', 'N', 'NE'],
  ['O', null, 'E'],
  ['SO', 'S', 'SE'],
]

/** Matriz 3x3 del tick: rojo = 1 aislado (alerta), gris oscuro = 1 en tránsito, ? = sin dato. */
export function Matriz({ estado }: { estado: EstadoNave | null }) {
  // Se guarda la matriz del tick anterior para resaltar las casillas que cambiaron.
  // Solo se actualiza cuando cambia el número de tick, no en cada render.
  const actual = useRef<EstadoNave | null>(null)
  const anterior = useRef<EstadoNave['matriz'] | null>(null)
  if (estado && estado.tick !== actual.current?.tick) {
    anterior.current = actual.current?.matriz ?? null
    actual.current = estado
  }
  const previa = anterior.current

  return (
    <div className="grid grid-cols-3 gap-2 font-mono">
      {FILAS.flat().map((sector, i) => {
        if (sector === null) {
          return (
            <div key={i} className="flex aspect-square flex-col items-center justify-center rounded-lg border-2 border-dashed text-muted-foreground">
              <span className="text-xs">nave</span>
              <span className="text-2xl">x</span>
            </div>
          )
        }
        const valor = estado?.matriz[sector] ?? null
        const enAlerta = estado?.alertas.includes(sector) ?? false
        const cambio = previa !== null && previa[sector] !== valor
        return (
          <div
            key={sector}
            className={cn(
              'flex aspect-square flex-col items-center justify-center rounded-lg border',
              valor === 1 && !enAlerta && 'bg-neutral-800 text-white',
              enAlerta && 'border-destructive bg-destructive text-white',
              valor === null && 'bg-muted text-muted-foreground',
              cambio && 'ring-2 ring-neutral-400 ring-offset-2',
            )}
          >
            <span className="text-xs opacity-75">{sector}</span>
            <span className="text-3xl font-semibold">{valor === null ? '?' : valor}</span>
          </div>
        )
      })}
    </div>
  )
}
