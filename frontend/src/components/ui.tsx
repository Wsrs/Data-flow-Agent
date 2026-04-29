import { cn } from '../lib/utils'
import { type ReactNode } from 'react'

interface CardProps {
  children: ReactNode
  className?: string
  onClick?: () => void
  hover?: boolean
}

export function Card({ children, className, onClick, hover }: CardProps) {
  return (
    <div
      onClick={onClick}
      className={cn(
        'glass rounded-2xl shadow-sm',
        hover && 'cursor-pointer transition-all duration-200 hover:shadow-md hover:-translate-y-0.5 active:translate-y-0',
        className,
      )}
    >
      {children}
    </div>
  )
}

interface SectionHeaderProps {
  title: string
  subtitle?: string
  action?: ReactNode
}

export function SectionHeader({ title, subtitle, action }: SectionHeaderProps) {
  return (
    <div className="flex items-end justify-between mb-5">
      <div>
        <h2 className="text-xl font-semibold tracking-tight text-gray-900 dark:text-white">
          {title}
        </h2>
        {subtitle && <p className="mt-0.5 text-sm text-apple-gray1">{subtitle}</p>}
      </div>
      {action}
    </div>
  )
}

interface BadgeProps {
  label: string
  className?: string
}

export function Badge({ label, className }: BadgeProps) {
  return (
    <span className={cn('inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ring-1 ring-inset', className)}>
      {label}
    </span>
  )
}

interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'danger' | 'ghost'
  size?: 'sm' | 'md'
  loading?: boolean
}

export function Button({ variant = 'primary', size = 'md', loading, children, className, disabled, ...props }: ButtonProps) {
  const base = 'inline-flex items-center justify-center gap-1.5 rounded-xl font-medium transition-all duration-150 focus:outline-none focus-visible:ring-2 focus-visible:ring-apple-blue focus-visible:ring-offset-2 disabled:opacity-50 disabled:pointer-events-none active:scale-95'
  const variants = {
    primary:   'bg-apple-blue text-white hover:bg-blue-600 shadow-sm',
    secondary: 'bg-apple-gray5 text-gray-900 hover:bg-apple-gray4 dark:bg-white/10 dark:text-white dark:hover:bg-white/15',
    danger:    'bg-apple-red text-white hover:bg-red-600 shadow-sm',
    ghost:     'text-apple-blue hover:bg-apple-blue/8',
  }
  const sizes = { sm: 'px-3 py-1.5 text-sm', md: 'px-4 py-2 text-sm' }
  return (
    <button
      className={cn(base, variants[variant], sizes[size], className)}
      disabled={disabled || loading}
      {...props}
    >
      {loading && <span className="w-3.5 h-3.5 border-2 border-current border-t-transparent rounded-full animate-spin" />}
      {children}
    </button>
  )
}

interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  label?: string
  hint?: string
}

export function Input({ label, hint, className, ...props }: InputProps) {
  return (
    <div>
      {label && <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">{label}</label>}
      <input
        className={cn(
          'w-full rounded-xl border border-apple-gray4 bg-white/80 px-3.5 py-2.5 text-sm text-gray-900 placeholder:text-apple-gray2 shadow-sm outline-none transition-all',
          'focus:border-apple-blue focus:ring-2 focus:ring-apple-blue/20',
          'dark:bg-white/5 dark:border-white/10 dark:text-white',
          className,
        )}
        {...props}
      />
      {hint && <p className="mt-1 text-xs text-apple-gray1">{hint}</p>}
    </div>
  )
}

interface SelectProps extends React.SelectHTMLAttributes<HTMLSelectElement> {
  label?: string
  options: { value: string; label: string }[]
}

export function Select({ label, options, className, ...props }: SelectProps) {
  return (
    <div>
      {label && <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">{label}</label>}
      <select
        className={cn(
          'w-full rounded-xl border border-apple-gray4 bg-white/80 px-3.5 py-2.5 text-sm text-gray-900 shadow-sm outline-none transition-all appearance-none cursor-pointer',
          'focus:border-apple-blue focus:ring-2 focus:ring-apple-blue/20',
          'dark:bg-white/5 dark:border-white/10 dark:text-white',
          className,
        )}
        {...props}
      >
        {options.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
      </select>
    </div>
  )
}

export function Spinner({ size = 20 }: { size?: number }) {
  return (
    <span
      style={{ width: size, height: size }}
      className="inline-block border-2 border-apple-gray3 border-t-apple-blue rounded-full animate-spin"
    />
  )
}

export function EmptyState({ icon, title, subtitle }: { icon: ReactNode; title: string; subtitle?: string }) {
  return (
    <div className="flex flex-col items-center justify-center py-16 text-center">
      <div className="mb-4 text-apple-gray3">{icon}</div>
      <p className="text-base font-medium text-gray-500 dark:text-gray-400">{title}</p>
      {subtitle && <p className="mt-1 text-sm text-apple-gray1">{subtitle}</p>}
    </div>
  )
}
