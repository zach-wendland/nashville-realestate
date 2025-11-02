import { useState, useEffect } from 'react'
import { useAuth } from '../context/AuthContext'
import { listingsApi } from '../services/api'
import Header from '../components/layout/Header'
import Footer from '../components/layout/Footer'
import FilterPanel from '../components/dashboard/FilterPanel'
import ListingCard from '../components/listings/ListingCard'
import StatsCards from '../components/dashboard/StatsCards'
import UpgradeModal from '../components/upgrade/UpgradeModal'

/**
 * Dashboard Page - Theory of Mind:
 * - Shows accessible listings based on tier
 * - Displays upgrade message when limit reached
 * - Stats visible = credibility
 * - Easy upgrade path throughout
 */

export default function Dashboard() {
  const { user, refreshUser } = useAuth()
  const [listings, setListings] = useState([])
  const [total, setTotal] = useState(0)
  const [accessible, setAccessible] = useState(0)
  const [upgradeMessage, setUpgradeMessage] = useState('')
  const [stats, setStats] = useState(null)
  const [loading, setLoading] = useState(true)
  const [filters, setFilters] = useState({})
  const [showUpgradeModal, setShowUpgradeModal] = useState(false)

  useEffect(() => {
    loadData()
  }, [filters])

  const loadData = async () => {
    setLoading(true)
    try {
      // Fetch listings
      const listingsData = await listingsApi.getListings(filters)
      setListings(listingsData.listings)
      setTotal(listingsData.total)
      setAccessible(listingsData.accessible)
      setUpgradeMessage(listingsData.upgrade_message || '')

      // Fetch market stats (premium users only)
      if (user?.tier !== 'free') {
        const statsData = await listingsApi.getMarketStats()
        setStats(statsData)
      }

      // Refresh user to get updated daily_views_remaining
      await refreshUser()
    } catch (error) {
      console.error('Error loading data:', error)
    } finally {
      setLoading(false)
    }
  }

  const handleFilterChange = (newFilters) => {
    setFilters(newFilters)
  }

  return (
    <div className="min-h-screen flex flex-col bg-gray-50">
      <Header user={{ email: 'free-user@example.com' }} />

      <main className="flex-1 container mx-auto px-4 py-8">
        {/* Stats */}
        {stats && (
          <div className="mb-8">
            <StatsCards stats={stats} />
          </div>
        )}

        {/* Main Content */}
        <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
          {/* Filters Sidebar */}
          <aside className="lg:col-span-1">
            <FilterPanel onFilterChange={handleFilterChange} />
          </aside>

          {/* Listings & Charts */}
          <div className="lg:col-span-3 space-y-6">
            {/* Listings Grid */}
            <div>
              <div className="flex justify-between items-center mb-4">
                <h2 className="text-2xl font-bold text-gray-900">
                  Available Rentals
                </h2>
                <div className="text-right">
                  <p className="text-sm text-gray-600">
                    Showing {listings.length} of {total} total listings
                  </p>
                  {user?.daily_views_remaining !== undefined && (
                    <p className="text-xs text-gray-500">
                      {user.daily_views_remaining} views remaining today
                    </p>
                  )}
                </div>
              </div>

              {upgradeMessage && (
                <div className="bg-yellow-50 border border-yellow-200 text-yellow-800 px-4 py-3 rounded-lg mb-6">
                  <p className="font-medium">{upgradeMessage}</p>
                  <button
                    onClick={() => setShowUpgradeModal(true)}
                    className="text-sm underline hover:text-yellow-900"
                  >
                    View upgrade options
                  </button>
                </div>
              )}

              {loading ? (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  {[...Array(6)].map((_, i) => (
                    <div key={i} className="bg-white rounded-lg h-96 animate-pulse" />
                  ))}
                </div>
              ) : listings.length === 0 ? (
                <div className="text-center py-12">
                  <p className="text-gray-600">No listings found. Try adjusting your filters.</p>
                </div>
              ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  {listings.map((listing) => (
                    <ListingCard
                      key={listing.id}
                      listing={listing}
                      isBlurred={false}
                      onUpgrade={() => setShowUpgradeModal(true)}
                    />
                  ))}
                </div>
              )}

              {/* Upgrade CTA when there are more listings available */}
              {total > listings.length && (
                <div className="mt-8 bg-gradient-to-r from-primary-600 to-primary-800 rounded-lg p-8 text-center text-white">
                  <h3 className="text-2xl font-bold mb-2">
                    {total - listings.length} More Listings Available
                  </h3>
                  <p className="mb-6 text-primary-100">
                    Upgrade to see all {total} listings and unlock premium features
                  </p>
                  <button
                    onClick={() => setShowUpgradeModal(true)}
                    className="bg-white text-primary-600 px-8 py-3 rounded-lg font-semibold hover:bg-gray-100 transition-colors"
                  >
                    View Pricing
                  </button>
                </div>
              )}
            </div>
          </div>
        </div>
      </main>

      <Footer />

      {/* Upgrade Modal */}
      <UpgradeModal
        isOpen={showUpgradeModal}
        onClose={() => setShowUpgradeModal(false)}
      />
    </div>
  )
}
