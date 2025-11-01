import { MapPin, Bed, Bath, Maximize, TrendingUp } from 'lucide-react'
import Card from '../common/Card'
import Button from '../common/Button'

/**
 * ListingCard Component - Theory of Mind:
 * - Image first = visual appeal (humans process images faster)
 * - Deal score badge = immediate value indicator
 * - Price prominent = primary decision factor
 * - Key stats (bed/bath/sqft) = quick comparison
 * - Blurred state for paywall = FOMO effect
 */

export default function ListingCard({ listing, isBlurred = false, onUpgrade }) {
  const formatPrice = (price) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 0,
    }).format(price)
  }

  const getDealScoreColor = (score) => {
    if (score >= 90) return 'bg-success-500'
    if (score >= 75) return 'bg-primary-500'
    return 'bg-gray-400'
  }

  return (
    <Card hover className="relative overflow-hidden">
      {/* Blur overlay for free tier limitation */}
      {isBlurred && (
        <div className="absolute inset-0 z-10 bg-white/90 backdrop-blur-sm flex items-center justify-center">
          <div className="text-center">
            <p className="text-lg font-semibold text-gray-900 mb-3">
              Upgrade to see more listings
            </p>
            <Button variant="primary" onClick={onUpgrade}>
              View Pricing
            </Button>
          </div>
        </div>
      )}

      {/* Image */}
      <div className="relative h-48 bg-gray-200 rounded-t-lg overflow-hidden">
        <img
          src={listing.imageUrl}
          alt={listing.address}
          className="w-full h-full object-cover"
        />
        {/* Deal Score Badge */}
        {listing.dealScore && listing.dealScore >= 85 && (
          <div className={`absolute top-2 right-2 ${getDealScoreColor(listing.dealScore)} text-white px-2 py-1 rounded-lg text-xs font-bold flex items-center`}>
            <TrendingUp className="w-3 h-3 mr-1" />
            Great Deal!
          </div>
        )}
        {/* Days on Market */}
        <div className="absolute bottom-2 left-2 bg-black/70 text-white px-2 py-1 rounded text-xs">
          {listing.daysOnMarket} days on market
        </div>
      </div>

      {/* Content */}
      <div className="p-4">
        {/* Price */}
        <div className="flex items-baseline justify-between mb-2">
          <span className="text-2xl font-bold text-gray-900">
            {formatPrice(listing.price)}
          </span>
          <span className="text-sm text-gray-500">/month</span>
        </div>

        {/* Address */}
        <div className="flex items-start mb-3">
          <MapPin className="w-4 h-4 text-gray-400 mr-1 mt-1 flex-shrink-0" />
          <div>
            <p className="text-sm font-medium text-gray-900">{listing.address}</p>
            <p className="text-xs text-gray-500">{listing.neighborhood}, {listing.zipCode}</p>
          </div>
        </div>

        {/* Stats */}
        <div className="flex items-center space-x-4 text-sm text-gray-600 mb-3">
          <div className="flex items-center">
            <Bed className="w-4 h-4 mr-1" />
            {listing.bedrooms} bd
          </div>
          <div className="flex items-center">
            <Bath className="w-4 h-4 mr-1" />
            {listing.bathrooms} ba
          </div>
          <div className="flex items-center">
            <Maximize className="w-4 h-4 mr-1" />
            {listing.sqft} sqft
          </div>
        </div>

        {/* Property Type */}
        <div className="flex items-center justify-between">
          <span className="text-xs bg-gray-100 text-gray-700 px-2 py-1 rounded">
            {listing.propertyType}
          </span>
          <span className={`text-xs font-semibold ${listing.dealScore >= 85 ? 'text-success-600' : 'text-gray-600'}`}>
            Deal Score: {listing.dealScore}
          </span>
        </div>
      </div>
    </Card>
  )
}
