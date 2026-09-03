import type { ButtonHTMLAttributes, ReactNode } from 'react'
import { cn } from '../../lib/utils'

type Variant = 'primary' | 'secondary' | 'ghost'

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant
  children: ReactNode
}

const variants: Record<Variant, string> = {
  primary:
    'bg-brand text-white hover:bg-brand-dark shadow-sm disabled:opacity-50 disabled:cursor-not-allowed',
  secondary:
    'bg-white text-gray-800 border border-gray-200 hover:bg-gray-50 disabled:opacity-50',
  ghost: 'bg-transparent text-gray-600 hover:bg-gray-100',
}

export function Button({
  variant = 'primary',
  className,
  children,
  ...props
}: ButtonProps) {
  return (
    <button
      className={cn(
        'inline-flex items-center justify-center gap-2 rounded-xl px-5 py-2.5 text-sm font-medium transition-colors',
        variants[variant],
        className,
      )}
      {...props}
    >
      {children}
    </button>
  )
}
