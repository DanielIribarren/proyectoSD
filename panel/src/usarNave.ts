import { useCallback, useEffect, useRef, useState } from 'react'
import type { EstadoNave, Orden } from './tipos'

const PUERTO_PANEL = 8765
const SEGUNDOS_REINTENTO = 2

// Por defecto se conecta a la misma máquina; ?ws=ws://otra-ip:8765 permite cambiarlo
function direccionNave() {
  const pedida = new URLSearchParams(window.location.search).get('ws')
  return pedida ?? `ws://${window.location.hostname || '127.0.0.1'}:${PUERTO_PANEL}`
}

/** Mantiene el WebSocket con la nave: devuelve el último estado, si hay conexión y cómo mandar órdenes. */
export function usarNave() {
  const [estado, setEstado] = useState<EstadoNave | null>(null)
  const [conectado, setConectado] = useState(false)
  const socket = useRef<WebSocket | null>(null)

  useEffect(() => {
    let cerrado = false // el componente se desmontó: no reintentar más
    let reintento: number | undefined

    function abrir() {
      const ws = new WebSocket(direccionNave())
      socket.current = ws
      ws.onopen = () => setConectado(true)
      ws.onmessage = (mensaje) => {
        try {
          setEstado(JSON.parse(mensaje.data))
        } catch {
          console.warn('Estado mal formado de la nave', mensaje.data)
        }
      }
      ws.onclose = () => {
        setConectado(false)
        if (!cerrado) reintento = window.setTimeout(abrir, SEGUNDOS_REINTENTO * 1000)
      }
    }

    abrir()
    return () => {
      cerrado = true
      window.clearTimeout(reintento)
      socket.current?.close()
    }
  }, [])

  const mandarOrden = useCallback((orden: Orden) => {
    if (socket.current?.readyState === WebSocket.OPEN) socket.current.send(JSON.stringify(orden))
  }, [])

  return { estado, conectado, mandarOrden }
}
