import { useNavigate } from 'react-router-dom'
import { TrendingUp, Map, Filter, BarChart3, Zap, Shield } from 'lucide-react'
import Header from '../components/layout/Header'
import Footer from '../components/layout/Footer'
import Button from '../components/common/Button'
import Card from '../components/common/Card'

/**
 * Landing Page - Theory of Mind:
 * - Hero with clear value prop = immediate understanding
 * - Social proof (stats) = credibility
 * - Feature showcase = education
 * - Strong CTAs throughout = conversion opportunities
 * - Free tier CTA = low-friction entry
 */

export default function LandingPage() {
  const navigate = useNavigate()

  const features = [
    {
      icon: Map,
      title: 'Interactive Map View',
      description: 'Visualize listings across 20 Nashville neighborhoods with our interactive map.'
    },
    {
      icon: Filter,
      title: 'Smart Filtering',
      description: 'Find exactly what you need with advanced search and filtering options.'
    },
    {
      icon: BarChart3,
      title: 'Market Analytics',
      description: 'Track price trends, days on market, and neighborhood statistics.'
    },
    {
      icon: TrendingUp,
      title: 'Deal Scores',
      description: 'Our algorithm identifies the best value properties in real-time.'
    },
    {
      icon: Zap,
      title: 'Real-Time Updates',
      description: 'New listings added daily from 400+ properties across Nashville.'
    },
    {
      icon: Shield,
      title: 'Trusted Data',
      description: 'Clean, normalized data from verified sources with 96% accuracy.'
    },
  ]

  return (
    <div className="min-h-screen flex flex-col">
      <Header />

      {/* Hero Section */}
      <section className="bg-gradient-to-br from-primary-600 to-primary-800 text-white py-20">
        <div className="container mx-auto px-4">
          <div className="max-w-3xl mx-auto text-center">
            <h1 className="text-5xl font-bold mb-6">
              Find Your Perfect Nashville Rental
            </h1>
            <p className="text-xl mb-8 text-primary-100">
              Real-time market intelligence for 20 Nashville neighborhoods.
              Discover deals before they're gone.
            </p>
            <div className="flex flex-col sm:flex-row justify-center gap-4">
              <Button
                variant="success"
                size="lg"
                onClick={() => navigate('/signup')}
              >
                Start Free Today
              </Button>
              <Button
                variant="outline"
                size="lg"
                className="bg-white/10 border-white text-white hover:bg-white/20"
                onClick={() => navigate('/dashboard')}
              >
                Browse Listings
              </Button>
            </div>
            <p className="mt-4 text-sm text-primary-200">
              No credit card required • 10 free listings daily
            </p>
          </div>
        </div>
      </section>

      {/* Stats Section */}
      <section className="py-12 bg-gray-50">
        <div className="container mx-auto px-4">
          <div className="grid grid-cols-1 md:grid-cols-4 gap-8 text-center">
            <div>
              <div className="text-4xl font-bold text-primary-600 mb-2">400+</div>
              <div className="text-gray-600">Active Listings</div>
            </div>
            <div>
              <div className="text-4xl font-bold text-primary-600 mb-2">20</div>
              <div className="text-gray-600">Neighborhoods</div>
            </div>
            <div>
              <div className="text-4xl font-bold text-primary-600 mb-2">$2,380</div>
              <div className="text-gray-600">Avg Monthly Rent</div>
            </div>
            <div>
              <div className="text-4xl font-bold text-primary-600 mb-2">91%</div>
              <div className="text-gray-600">Data Accuracy</div>
            </div>
          </div>
        </div>
      </section>

      {/* Features Section */}
      <section id="features" className="py-20">
        <div className="container mx-auto px-4">
          <div className="text-center mb-12">
            <h2 className="text-3xl font-bold text-gray-900 mb-4">
              Everything You Need to Find Your Next Home
            </h2>
            <p className="text-lg text-gray-600 max-w-2xl mx-auto">
              Powered by real-time data from across Nashville's hottest neighborhoods
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
            {features.map((feature, index) => (
              <Card key={index} hover>
                <div className="flex flex-col items-center text-center">
                  <div className="bg-primary-100 text-primary-600 p-4 rounded-lg mb-4">
                    <feature.icon className="w-8 h-8" />
                  </div>
                  <h3 className="text-xl font-semibold text-gray-900 mb-2">
                    {feature.title}
                  </h3>
                  <p className="text-gray-600">
                    {feature.description}
                  </p>
                </div>
              </Card>
            ))}
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="py-20 bg-primary-600 text-white">
        <div className="container mx-auto px-4 text-center">
          <h2 className="text-3xl font-bold mb-4">
            Ready to Find Your Perfect Rental?
          </h2>
          <p className="text-xl mb-8 text-primary-100">
            Join hundreds of Nashville renters and investors
          </p>
          <Button
            variant="success"
            size="lg"
            onClick={() => navigate('/signup')}
          >
            Get Started Free
          </Button>
        </div>
      </section>

      <Footer />
    </div>
  )
}
