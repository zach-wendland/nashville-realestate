/**
 * Input Component - Theory of Mind:
 * - Large touch targets for mobile users
 * - Clear focus states for accessibility
 * - Error states with red border = immediate feedback
 * - Labels always visible = no confusion
 */

export default function Input({
  label,
  error,
  type = 'text',
  className = '',
  ...props
}) {
  return (
    <div className="w-full">
      {label && (
        <label className="block text-sm font-medium text-gray-700 mb-1">
          {label}
        </label>
      )}
      <input
        type={type}
        className={`
          w-full px-4 py-2
          border rounded-lg
          ${error ? 'border-red-500 focus:ring-red-500' : 'border-gray-300 focus:ring-primary-500'}
          focus:outline-none focus:ring-2 focus:ring-offset-0
          disabled:bg-gray-100 disabled:cursor-not-allowed
          ${className}
        `}
        {...props}
      />
      {error && (
        <p className="mt-1 text-sm text-red-600">{error}</p>
      )}
    </div>
  )
}
