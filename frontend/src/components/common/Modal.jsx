import { X } from 'lucide-react'
import Button from './Button'

/**
 * Modal Component - Theory of Mind:
 * - Overlay darkens background = focus on modal content
 * - Close button top-right = expected position (UX convention)
 * - Click outside to close = intuitive escape hatch
 * - Smooth animations = polished, professional feel
 */

export default function Modal({
  isOpen,
  onClose,
  title,
  children,
  size = 'md',
  showCloseButton = true,
}) {
  if (!isOpen) return null

  const sizes = {
    sm: 'max-w-md',
    md: 'max-w-lg',
    lg: 'max-w-2xl',
    xl: 'max-w-4xl',
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50"
      onClick={onClose}
    >
      <div
        className={`relative w-full ${sizes[size]} bg-white rounded-lg shadow-xl`}
        onClick={(e) => e.stopPropagation()}
      >
        {showCloseButton && (
          <button
            onClick={onClose}
            className="absolute top-4 right-4 text-gray-400 hover:text-gray-600"
          >
            <X size={24} />
          </button>
        )}

        {title && (
          <div className="px-6 py-4 border-b border-gray-200">
            <h2 className="text-xl font-semibold text-gray-900">{title}</h2>
          </div>
        )}

        <div className="p-6">
          {children}
        </div>
      </div>
    </div>
  )
}
