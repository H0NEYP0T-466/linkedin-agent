import { useEffect, useRef, useState } from 'react'

const BACKEND_WS = import.meta.env.VITE_BACKEND_WS ?? 'ws://localhost:8006/ws'
const BACKEND_URL = import.meta.env.VITE_BACKEND_URL ?? 'http://localhost:8006'

const BANNER = `
 ██╗     ██╗███╗   ██╗██╗  ██╗███████╗██████╗ ██╗███╗   ██╗
 ██║     ██║████╗  ██║██║ ██╔╝██╔════╝██╔══██╗██║████╗  ██║
 ██║     ██║██╔██╗ ██║█████╔╝ █████╗  ██║  ██║██║██╔██╗ ██║
 ██║     ██║██║╚██╗██║██╔═██╗ ██╔══╝  ██║  ██║██║██║╚██╗██║
 ███████╗██║██║ ╚████║██║  ██╗███████╗██████╔╝██║██║ ╚████║
 ╚══════╝╚═╝╚═╝  ╚═══╝╚═╝  ╚═╝╚══════╝╚═════╝ ╚═╝╚═╝  ╚═══╝
              A G E N T  v1.0  —  LongCat-Flash-Lite
`.trim()

type LogLine = {
  id: number
  text: string
  type: 'system' | 'log' | 'error' | 'ping'
}

type Status = {
  initialized: boolean
  repos_count: number
  pending_tasks: number
  done_tasks: number
  agent_running: boolean
}

export default function App() {
  const [lines, setLines] = useState<LogLine[]>([])
  const [status, setStatus] = useState<Status | null>(null)
  const [connected, setConnected] = useState(false)
  const [reconnecting, setReconnecting] = useState(false)
  const bottomRef = useRef<HTMLDivElement>(null)
  const counterRef = useRef(0)
  const wsRef = useRef<WebSocket | null>(null)

  const addLine = (text: string, type: LogLine['type'] = 'log') => {
    const id = ++counterRef.current
    setLines(prev => {
      const next = [...prev, { id, text, type }]
      return next.length > 1000 ? next.slice(-1000) : next
    })
  }

  const fetchStatus = async () => {
    try {
      const res = await fetch(`${BACKEND_URL}/status`)
      if (res.ok) {
        const data: Status = await res.json()
        setStatus(data)
      }
    } catch {
      // backend not ready yet
    }
  }

  useEffect(() => {
    // Print banner
    BANNER.split('\n').forEach(line => addLine(line, 'system'))
    addLine('', 'system')
    addLine('[system] Connecting to agent backend...', 'system')

    let retryTimeout: ReturnType<typeof setTimeout>

    const connect = () => {
      const ws = new WebSocket(BACKEND_WS)
      wsRef.current = ws

      ws.onopen = () => {
        setConnected(true)
        setReconnecting(false)
        addLine('[system] ✓ Connected to LinkedIn Agent backend', 'system')
        void fetchStatus()
      }

      ws.onmessage = (event: MessageEvent<string>) => {
        try {
          const data = JSON.parse(event.data) as { type: string; message?: string }
          if (data.type === 'log' && data.message) {
            addLine(data.message)
          }
          // ignore pings
        } catch {
          addLine(event.data)
        }
      }

      ws.onerror = () => {
        addLine('[system] ✗ WebSocket error', 'error')
      }

      ws.onclose = () => {
        setConnected(false)
        setReconnecting(true)
        addLine('[system] Connection lost. Reconnecting in 5s...', 'error')
        retryTimeout = setTimeout(connect, 5000)
      }
    }

    connect()

    // Poll status every 30s
    const statusInterval = setInterval(() => { void fetchStatus() }, 30000)

    return () => {
      clearTimeout(retryTimeout)
      clearInterval(statusInterval)
      wsRef.current?.close()
    }
  }, [])

  // Auto-scroll to bottom
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [lines])

  const getLineColor = (type: LogLine['type']) => {
    switch (type) {
      case 'system': return '#00aaff'
      case 'error': return '#ff4444'
      default: return '#39ff14'
    }
  }

  return (
    <div style={{
      width: '100vw',
      height: '100vh',
      background: '#000',
      display: 'flex',
      flexDirection: 'column',
      overflow: 'hidden',
    }}>
      {/* Status bar */}
      <div style={{
        display: 'flex',
        alignItems: 'center',
        gap: '20px',
        padding: '6px 16px',
        borderBottom: '1px solid #1a1a1a',
        background: '#050505',
        fontFamily: '"Courier New", monospace',
        fontSize: '11px',
        color: '#555',
        flexShrink: 0,
      }}>
        <span style={{ color: connected ? '#39ff14' : '#ff4444' }}>
          {connected ? '● ONLINE' : reconnecting ? '◌ RECONNECTING' : '● OFFLINE'}
        </span>
        {status && (
          <>
            <span>REPOS: <span style={{ color: '#39ff14' }}>{status.repos_count}</span></span>
            <span>PENDING: <span style={{ color: '#ffaa00' }}>{status.pending_tasks}</span></span>
            <span>DONE: <span style={{ color: '#39ff14' }}>{status.done_tasks}</span></span>
            <span>AGENT: <span style={{ color: status.agent_running ? '#39ff14' : '#ff4444' }}>
              {status.agent_running ? 'RUNNING' : 'STOPPED'}
            </span></span>
          </>
        )}
        <span style={{ marginLeft: 'auto' }}>LinkedIn Agent — LongCat-Flash-Lite</span>
      </div>

      {/* Terminal output */}
      <div style={{
        flex: 1,
        overflowY: 'auto',
        padding: '12px 16px',
        fontFamily: '"Courier New", Courier, monospace',
        fontSize: '13px',
        lineHeight: '1.6',
      }}>
        {lines.map(line => (
          <div
            key={line.id}
            style={{
              color: getLineColor(line.type),
              whiteSpace: 'pre-wrap',
              wordBreak: 'break-word',
              minHeight: '1.6em',
            }}
          >
            {line.text || '\u00a0'}
          </div>
        ))}

        {/* Blinking cursor */}
        <div style={{ display: 'flex', alignItems: 'center', color: '#39ff14' }}>
          <span style={{ animation: 'blink 1s step-end infinite' }}>█</span>
        </div>

        <div ref={bottomRef} />
      </div>

      <style>{`
        @keyframes blink {
          0%, 100% { opacity: 1; }
          50% { opacity: 0; }
        }
        ::-webkit-scrollbar { width: 6px; }
        ::-webkit-scrollbar-track { background: #000; }
        ::-webkit-scrollbar-thumb { background: #1a3a1a; border-radius: 3px; }
        ::-webkit-scrollbar-thumb:hover { background: #39ff14; }
      `}</style>
    </div>
  )
}

