import { Link, useNavigate } from 'react-router-dom'
import { Home, LogIn, UserPlus, BarChart3 } from 'lucide-react'
import Button from '../common/Button'

/**
 * Header Component - Theory of Mind:
 * - Logo left = standard convention, brand identity
 * - CTA buttons right = natural eye movement (left-to-right readers)
 * - Sticky header = always accessible navigation
 * - Different states for logged in/out users
 */

export default function Header({ user = null }) {
  const navigate = useNavigate()

  return (
    <header className="sticky top-0 z-40 bg-white border-b border-gray-200 shadow-sm">
      <div className="container mx-auto px-4">
        <div className="flex items-center justify-between h-16">
          {/* Logo */}
          <Link to="/" className="flex items-center space-x-2">
            <Home className="w-8 h-8 text-primary-600" />
            <span className="text-xl font-bold text-gray-900">
              Nashville Rentals
            </span>
          </Link>

          {/* Navigation */}
          <nav className="hidden md:flex items-center space-x-8">
            <Link to="/dashboard" className="text-gray-600 hover:text-gray-900">
              Browse Listings
            </Link>
            <Link to="/dashboard" className="text-gray-600 hover:text-gray-900">
              Pricing
            </Link>
            <a href="#features" className="text-gray-600 hover:text-gray-900">
              Features
            </a>
          </nav>

          {/* Auth Buttons */}
          <div className="flex items-center space-x-3">
            {user ? (
              <>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => navigate('/dashboard')}
                >
                  <BarChart3 className="w-4 h-4 mr-2" />
                  Dashboard
                </Button>
                <Button
                  variant="primary"
                  size="sm"
                >
                  Upgrade
                </Button>
              </>
            ) : (
              <>
                <Button
                  variant="secondary"
                  size="sm"
                  onClick={() => navigate('/login')}
                >
                  <LogIn className="w-4 h-4 mr-2" />
                  Login
                </Button>
                <Button
                  variant="primary"
                  size="sm"
                  onClick={() => navigate('/signup')}
                >
                  <UserPlus className="w-4 h-4 mr-2" />
                  Sign Up
                </Button>
              </>
            )}
          </div>
        </div>
      </div>
    </header>
  )
}
