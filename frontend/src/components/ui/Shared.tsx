import type { ReactNode } from 'react'
import type { LucideIcon } from 'lucide-react'
import { cn } from '../../lib/utils'

interface StatCardProps {
  label: string
  value: number | string
  icon: LucideIcon
  className?: string
}

export function StatCard({ label, value, icon: Icon, className }: StatCardProps) {
  return (
    <div
      className={cn(
        'rounded-2xl border border-gray-100 bg-white p-6 shadow-sm',
        className,
      )}
    >
      <div className="flex items-start justify-between">
        <p className="text-sm text-gray-500">{label}</p>
        <Icon className="h-5 w-5 text-brand" strokeWidth={1.75} />
      </div>
      <p className="mt-4 text-4xl font-semibold tracking-tight text-gray-900">{value}</p>
    </div>
  )
}

interface EmptyStateProps {
  icon: ReactNode
  title: string
  description: string
  action?: ReactNode
}

export function EmptyState({ icon, title, description, action }: EmptyStateProps) {
  return (
    <div className="flex flex-col items-center justify-center rounded-2xl border-2 border-dashed border-gray-200 bg-white/60 px-8 py-20 text-center">
      <div className="mb-6 flex h-16 w-16 items-center justify-center rounded-2xl bg-brand-light">
        {icon}
      </div>
      <h3 className="text-lg font-semibold text-gray-900">{title}</h3>
      <p className="mt-2 max-w-md text-sm text-gray-500">{description}</p>
      {action && <div className="mt-8">{action}</div>}
    </div>
  )
}

interface ModalProps {
  open: boolean
  title: string
  onClose: () => void
  children: ReactNode
  panelClassName?: string
}

export function Modal({ open, title, onClose, children, panelClassName }: ModalProps) {
  if (!open) return null
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <div className="absolute inset-0 bg-black/40" onClick={onClose} />
      <div
        className={cn(
          'relative w-full max-w-md rounded-2xl bg-white p-6 shadow-xl',
          panelClassName,
        )}
      >
        <h2 className="text-lg font-semibold text-gray-900">{title}</h2>
        <div className="mt-4">{children}</div>
      </div>
    </div>
  )
}

export function LoadingOverlay({ message }: { message: string }) {
  return (
    <div className="fixed inset-0 z-50 flex flex-col items-center justify-center bg-white/80 backdrop-blur-sm">
      <div className="h-10 w-10 animate-spin rounded-full border-4 border-brand border-t-transparent" />
      <p className="mt-4 max-w-sm text-center text-sm text-gray-600">{message}</p>
    </div>
  )
}
