import { useState, useEffect } from 'react'
import Header from '../components/layout/Header'
import Footer from '../components/layout/Footer'
import FilterPanel from '../components/dashboard/FilterPanel'
import ListingCard from '../components/listings/ListingCard'
import StatsCards from '../components/dashboard/StatsCards'
import PriceChart from '../components/dashboard/PriceChart'
import UpgradeModal from '../components/upgrade/UpgradeModal'
import { fetchListings, fetchStats, fetchPriceHistory } from '../services/mockData'

/**
 * Dashboard Page - Theory of Mind:
 * - Free tier shows 10 listings = immediate value
 * - Cards 11-20 blurred = FOMO (fear of missing out)
 * - Stats visible = credibility
 * - Charts visible but limited = teaser of premium features
 * - Easy upgrade path throughout
 */

export default function Dashboard() {
  const [listings, setListings] = useState([])
  const [stats, setStats] = useState(null)
  const [priceHistory, setPriceHistory] = useState([])
  const [loading, setLoading] = useState(true)
  const [filters, setFilters] = useState({})
  const [showUpgradeModal, setShowUpgradeModal] = useState(false)

  // Free tier limitation
  const FREE_TIER_LIMIT = 10

  useEffect(() => {
    loadData()
  }, [filters])

  const loadData = async () => {
    setLoading(true)
    try {
      const [listingsData, statsData, priceData] = await Promise.all([
        fetchListings(filters),
        fetchStats(),
        fetchPriceHistory()
      ])
      setListings(listingsData)
      setStats(statsData)
      setPriceHistory(priceData)
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
            {/* Price Chart */}
            {priceHistory.length > 0 && (
              <PriceChart data={priceHistory} title="6-Month Price Trends" />
            )}

            {/* Listings Grid */}
            <div>
              <div className="flex justify-between items-center mb-4">
                <h2 className="text-2xl font-bold text-gray-900">
                  Available Rentals
                </h2>
                <p className="text-sm text-gray-600">
                  Showing {Math.min(listings.length, FREE_TIER_LIMIT)} of {listings.length} listings
                </p>
              </div>

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
                  {listings.map((listing, index) => (
                    <ListingCard
                      key={listing.id}
                      listing={listing}
                      isBlurred={index >= FREE_TIER_LIMIT}
                      onUpgrade={() => setShowUpgradeModal(true)}
                    />
                  ))}
                </div>
              )}

              {/* Upgrade CTA after free listings */}
              {listings.length > FREE_TIER_LIMIT && (
                <div className="mt-8 bg-gradient-to-r from-primary-600 to-primary-800 rounded-lg p-8 text-center text-white">
                  <h3 className="text-2xl font-bold mb-2">
                    {listings.length - FREE_TIER_LIMIT} More Listings Available
                  </h3>
                  <p className="mb-6 text-primary-100">
                    Upgrade to see all {listings.length} listings and unlock premium features
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
