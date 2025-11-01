/**
 * Card Component - Theory of Mind:
 * - Clean white background = trust, professionalism
 * - Subtle shadow = depth without distraction
 * - Hover effect = interactive feedback
 * - Padding scaled by size = information hierarchy
 */

export default function Card({
  children,
  className = '',
  hover = false,
  size = 'md',
  ...props
}) {
  const baseStyles = 'bg-white rounded-lg shadow-sm border border-gray-200'
  const hoverStyles = hover ? 'hover:shadow-md transition-shadow cursor-pointer' : ''

  const sizes = {
    sm: 'p-3',
    md: 'p-4',
    lg: 'p-6',
  }

  return (
    <div
      className={`${baseStyles} ${hoverStyles} ${sizes[size]} ${className}`}
      {...props}
    >
      {children}
    </div>
  )
}
