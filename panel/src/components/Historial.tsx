import { cn } from '@/lib/utils'
import { ANILLO, type EstadoNave } from '@/tipos'

const TEXTO = { ALERTA_ROJA: 'Alerta roja', TRANSITO_SEGURO: 'Tránsito seguro', SIN_AMENAZA: 'Sin amenaza' }

/** Últimos ticks recibidos: qué sectores dieron 1 y qué decidió la nave. */
export function Historial({ ticks }: { ticks: EstadoNave[] }) {
  return (
    <table className="w-full text-sm">
      <thead>
        <tr className="border-b text-left text-muted-foreground">
          <th className="py-2 font-medium">Tick</th>
          <th className="py-2 font-medium">Sectores en 1</th>
          <th className="py-2 font-medium">Decisión</th>
        </tr>
      </thead>
      <tbody className="font-mono">
        {ticks.length === 0 && (
          <tr>
            <td colSpan={3} className="py-2 text-muted-foreground">
              Sin ticks todavía.
            </td>
          </tr>
        )}
        {ticks.map((t) => {
          const enUno = ANILLO.filter((s) => t.matriz[s] === 1)
          return (
            <tr key={t.tick} className="border-b last:border-0">
              <td className="py-1.5">{t.tick}</td>
              <td className="py-1.5">{enUno.length ? enUno.join(' ') : '—'}</td>
              <td className={cn('py-1.5', t.decision === 'ALERTA_ROJA' && 'font-semibold text-destructive')}>
                {TEXTO[t.decision]}
                {t.decision === 'ALERTA_ROJA' && ` (${t.alertas.join(', ')})`}
              </td>
            </tr>
          )
        })}
      </tbody>
    </table>
  )
}
