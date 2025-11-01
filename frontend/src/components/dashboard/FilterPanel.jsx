import { useState } from 'react'
import { Search, SlidersHorizontal } from 'lucide-react'
import Input from '../common/Input'
import Button from '../common/Button'
import Card from '../common/Card'

/**
 * FilterPanel Component - Theory of Mind:
 * - Search bar prominent = primary user action
 * - Common filters visible = no hidden features
 * - "Advanced" collapsed initially = progressive disclosure
 * - Real-time feedback = responsive feel
 */

export default function FilterPanel({ onFilterChange, disabled = false }) {
  const [filters, setFilters] = useState({
    zipCode: '',
    minPrice: '',
    maxPrice: '',
    bedrooms: '',
    propertyType: '',
  })

  const [showAdvanced, setShowAdvanced] = useState(false)

  const handleChange = (field, value) => {
    const newFilters = { ...filters, [field]: value }
    setFilters(newFilters)
    onFilterChange(newFilters)
  }

  const handleReset = () => {
    const emptyFilters = {
      zipCode: '',
      minPrice: '',
      maxPrice: '',
      bedrooms: '',
      propertyType: '',
    }
    setFilters(emptyFilters)
    onFilterChange(emptyFilters)
  }

  return (
    <Card>
      <div className="space-y-4">
        {/* Search by Zip */}
        <div>
          <div className="relative">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-5 h-5" />
            <input
              type="text"
              placeholder="Search by zip code (e.g., 37206)"
              value={filters.zipCode}
              onChange={(e) => handleChange('zipCode', e.target.value)}
              disabled={disabled}
              className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:outline-none disabled:bg-gray-100"
            />
          </div>
        </div>

        {/* Price Range */}
        <div className="grid grid-cols-2 gap-3">
          <Input
            label="Min Price"
            type="number"
            placeholder="$1,600"
            value={filters.minPrice}
            onChange={(e) => handleChange('minPrice', e.target.value)}
            disabled={disabled}
          />
          <Input
            label="Max Price"
            type="number"
            placeholder="$3,000"
            value={filters.maxPrice}
            onChange={(e) => handleChange('maxPrice', e.target.value)}
            disabled={disabled}
          />
        </div>

        {/* Bedrooms */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Bedrooms
          </label>
          <div className="grid grid-cols-5 gap-2">
            {['Any', '1', '2', '3', '4+'].map((bed) => (
              <button
                key={bed}
                onClick={() => handleChange('bedrooms', bed === 'Any' ? '' : bed)}
                disabled={disabled}
                className={`px-3 py-2 text-sm rounded-lg border transition-colors
                  ${filters.bedrooms === (bed === 'Any' ? '' : bed)
                    ? 'bg-primary-600 text-white border-primary-600'
                    : 'bg-white text-gray-700 border-gray-300 hover:border-primary-600'
                  }
                  disabled:opacity-50 disabled:cursor-not-allowed
                `}
              >
                {bed}
              </button>
            ))}
          </div>
        </div>

        {/* Advanced Filters Toggle */}
        <button
          onClick={() => setShowAdvanced(!showAdvanced)}
          className="flex items-center text-sm text-primary-600 hover:text-primary-700"
        >
          <SlidersHorizontal className="w-4 h-4 mr-2" />
          {showAdvanced ? 'Hide' : 'Show'} Advanced Filters
        </button>

        {/* Advanced Filters */}
        {showAdvanced && (
          <div className="pt-4 border-t border-gray-200 space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Property Type
              </label>
              <select
                value={filters.propertyType}
                onChange={(e) => handleChange('propertyType', e.target.value)}
                disabled={disabled}
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:outline-none disabled:bg-gray-100"
              >
                <option value="">All Types</option>
                <option value="Apartment">Apartment</option>
                <option value="House">House</option>
                <option value="Condo">Condo</option>
                <option value="Townhouse">Townhouse</option>
                <option value="Studio">Studio</option>
              </select>
            </div>

            {/* Locked Feature Hint (Theory of Mind: Show what they're missing) */}
            <div className="bg-gray-50 border border-gray-200 rounded-lg p-3">
              <p className="text-xs text-gray-600 mb-2">
                🔒 Upgrade for advanced filters:
              </p>
              <ul className="text-xs text-gray-500 space-y-1 ml-4">
                <li>• Neighborhood scores</li>
                <li>• School ratings</li>
                <li>• Walk score</li>
                <li>• Pet-friendly filter</li>
              </ul>
            </div>
          </div>
        )}

        {/* Actions */}
        <div className="flex space-x-2 pt-4 border-t border-gray-200">
          <Button
            variant="primary"
            className="flex-1"
            disabled={disabled}
            onClick={() => onFilterChange(filters)}
          >
            Apply Filters
          </Button>
          <Button
            variant="secondary"
            onClick={handleReset}
            disabled={disabled}
          >
            Reset
          </Button>
        </div>
      </div>
    </Card>
  )
}
