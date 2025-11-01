import { TrendingUp, Home, Calendar, DollarSign } from 'lucide-react'
import Card from '../common/Card'

/**
 * StatsCards Component - Theory of Mind:
 * - Big numbers = confidence, data-driven
 * - Icons for quick visual scanning
 * - Trend indicators = market intelligence
 * - Grid layout = easy comparison
 */

export default function StatsCards({ stats }) {
  const cards = [
    {
      label: 'Total Listings',
      value: stats.totalListings,
      icon: Home,
      color: 'text-primary-600',
      bgColor: 'bg-primary-50',
    },
    {
      label: 'Average Price',
      value: `$${stats.avgPrice.toLocaleString()}`,
      icon: DollarSign,
      color: 'text-success-600',
      bgColor: 'bg-success-50',
    },
    {
      label: 'Avg Days on Market',
      value: stats.avgDaysOnMarket,
      icon: Calendar,
      color: 'text-warning-600',
      bgColor: 'bg-warning-50',
    },
    {
      label: 'New This Week',
      value: stats.newListingsThisWeek,
      icon: TrendingUp,
      color: 'text-primary-600',
      bgColor: 'bg-primary-50',
    },
  ]

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
      {cards.map((card, index) => (
        <Card key={index}>
          <div className="flex items-start justify-between">
            <div>
              <p className="text-sm font-medium text-gray-600 mb-1">
                {card.label}
              </p>
              <p className="text-2xl font-bold text-gray-900">
                {card.value}
              </p>
            </div>
            <div className={`${card.bgColor} ${card.color} p-3 rounded-lg`}>
              <card.icon className="w-6 h-6" />
            </div>
          </div>
        </Card>
      ))}
    </div>
  )
}
