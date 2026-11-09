import { useEffect, useRef } from 'react'
import { ScrollArea } from '@/components/ui/scroll-area'
import { cn } from '@/lib/utils'
import type { Evento } from '@/tipos'

/** Últimos eventos de la nave, el más nuevo abajo. */
export function Registro({ eventos }: { eventos: Evento[] }) {
  const fin = useRef<HTMLDivElement>(null)
  useEffect(() => {
    fin.current?.scrollIntoView({ block: 'nearest' })
  }, [eventos])

  return (
    <ScrollArea className="h-[22rem] rounded-md border bg-background p-3 font-mono text-xs">
      {eventos.length === 0 && <div className="text-muted-foreground">Sin eventos todavía.</div>}
      {eventos.map((evento, i) => (
        <div
          key={i}
          className={cn(
            'py-0.5',
            evento.nivel === 'alerta' && 'font-semibold text-destructive',
            evento.nivel === 'aviso' && 'text-foreground',
            evento.nivel === 'info' && 'text-muted-foreground',
          )}
        >
          <span className="mr-2 opacity-60">{evento.hora}</span>
          {evento.texto}
        </div>
      ))}
      <div ref={fin} />
    </ScrollArea>
  )
}
