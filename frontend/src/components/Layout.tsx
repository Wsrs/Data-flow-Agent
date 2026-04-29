import { NavLink, Outlet } from 'react-router-dom'
import { Layers, Cpu, BarChart2, Brain } from 'lucide-react'
import { cn } from '../lib/utils'

const nav = [
  { to: '/jobs',     label: 'Jobs',       icon: Layers   },
  { to: '/eval',     label: 'Evaluation', icon: BarChart2 },
  { to: '/memory',   label: 'Memory',     icon: Brain    },
]

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
