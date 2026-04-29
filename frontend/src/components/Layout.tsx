import { NavLink, Outlet } from 'react-router-dom'
import { useState, useEffect } from 'react'
import { Layers, Cpu, BarChart2, Brain, Zap } from 'lucide-react'
import { cn } from '../lib/utils'
import { getLLMStatus, type LLMStatus } from '../lib/api'

const nav = [
  { to: '/jobs',   label: 'Jobs',       icon: Layers   },
  { to: '/eval',   label: 'Evaluation', icon: BarChart2 },
  { to: '/memory', label: 'Memory',     icon: Brain    },
]

function LLMChip() {
  const [status, setStatus] = useState<LLMStatus | null>(null)

  useEffect(() => {
    getLLMStatus().then(r => setStatus(r.data)).catch(() => {})
    const t = setInterval(() => {
      getLLMStatus().then(r => setStatus(r.data)).catch(() => {})
    }, 30_000)
    return () => clearInterval(t)
  }, [])

  if (!status) return null

  const isOllama   = status.provider === 'ollama'
  const dot        = status.reachable ? 'bg-apple-green' : 'bg-apple-red'
  const chipColor  = isOllama
    ? 'bg-purple-50 text-purple-700 ring-purple-200 dark:bg-purple-950/40 dark:text-purple-300 dark:ring-purple-800'
    : 'bg-blue-50 text-blue-700 ring-blue-200 dark:bg-blue-950/40 dark:text-blue-300 dark:ring-blue-800'

  return (
    <div className={cn('hidden sm:flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium ring-1 ring-inset', chipColor)}>
      <span className={cn('w-1.5 h-1.5 rounded-full shrink-0', dot, status.reachable && 'animate-pulse-soft')} />
      <Zap size={10} strokeWidth={2.5} />
      <span className="max-w-[120px] truncate">{status.model}</span>
    </div>
  )
}

export default function Layout() {
  return (
    <div className="min-h-screen flex flex-col">
      {/* ── Top bar ──────────────────────────────────────── */}
      <header className="sticky top-0 z-40 glass border-b border-apple-gray4/60 dark:border-white/8">
        <div className="max-w-5xl mx-auto px-5 h-14 flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <div className="w-7 h-7 rounded-lg bg-apple-blue flex items-center justify-center shadow-sm">
              <Cpu size={14} className="text-white" strokeWidth={2.5} />
            </div>
            <span className="font-semibold text-[15px] tracking-tight text-gray-900 dark:text-white">
              DataFlow<span className="text-apple-blue"> Agent</span>
            </span>
            <LLMChip />
          </div>

          <nav className="flex items-center gap-1">
            {nav.map(({ to, label, icon: Icon }) => (
              <NavLink
                key={to}
                to={to}
                className={({ isActive }) => cn(
                  'flex items-center gap-1.5 px-3.5 py-1.5 rounded-xl text-sm font-medium transition-all duration-150',
                  isActive
                    ? 'bg-apple-blue/10 text-apple-blue dark:bg-apple-blue/20'
                    : 'text-apple-gray1 hover:text-gray-800 hover:bg-apple-gray5 dark:hover:bg-white/8 dark:hover:text-white',
                )}
              >
                <Icon size={14} strokeWidth={2} />
                {label}
              </NavLink>
            ))}
          </nav>
        </div>
      </header>

      {/* ── Page ─────────────────────────────────────────── */}
      <main className="flex-1 max-w-5xl mx-auto w-full px-5 py-8">
        <Outlet />
      </main>

      {/* ── Footer ───────────────────────────────────────── */}
      <footer className="border-t border-apple-gray4/40 dark:border-white/5 py-4">
        <p className="text-center text-xs text-apple-gray2">
          DataFlow Agent · Multi-agent data cleaning engine
        </p>
      </footer>
    </div>
  )
}
