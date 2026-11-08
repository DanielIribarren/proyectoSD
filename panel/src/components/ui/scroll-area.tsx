import * as React from 'react'
import { cn } from '@/lib/utils'

// Versión simple de ScrollArea: un div con scroll propio
function ScrollArea({ className, ...props }: React.ComponentProps<'div'>) {
  return <div className={cn('relative overflow-y-auto', className)} {...props} />
}

export { ScrollArea }
