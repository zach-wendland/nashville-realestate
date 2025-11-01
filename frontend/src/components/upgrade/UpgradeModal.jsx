import { Check, X } from 'lucide-react'
import Modal from '../common/Modal'
import Button from '../common/Button'

/**
 * UpgradeModal Component - Theory of Mind:
 * - Three tiers = anchoring effect (most choose middle)
 * - "Most Popular" badge = social proof
 * - Feature comparison = clear value
 * - Green checkmarks = positive reinforcement
 */

export default function UpgradeModal({ isOpen, onClose }) {
  const plans = [
    {
      name: 'Renter Plus',
      price: 14.99,
      popular: false,
      features: [
        'Unlimited listing views',
        '30-day price history',
        'Up to 5 saved searches',
        'Email alerts',
        'No ads',
        'Mobile app access',
      ],
      notIncluded: [
        'ROI calculator',
        'API access',
        'Export to CSV',
        'Priority support',
      ],
    },
    {
      name: 'Investor Pro',
      price: 199,
      popular: true,
      features: [
        'Everything in Renter Plus',
        'Full historical data',
        'ROI calculator',
        'Rental yield analysis',
        'Neighborhood heat maps',
        'Price change tracking',
        'CMA tool',
        'Export to CSV (500/month)',
        'Priority email support',
      ],
      notIncluded: [
        'Multi-user accounts',
        'API access',
        'White-label reports',
      ],
    },
    {
      name: 'Enterprise',
      price: 499,
      popular: false,
      features: [
        'Everything in Investor Pro',
        'Multi-user accounts (5 seats)',
        'API access (5,000 calls/month)',
        'White-label reports',
        'Custom market reports',
        'Dedicated support',
        'Phone support',
      ],
      notIncluded: [],
    },
  ]

  return (
    <Modal isOpen={isOpen} onClose={onClose} size="xl" title="Choose Your Plan">
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {plans.map((plan) => (
          <div
            key={plan.name}
            className={`relative border-2 rounded-lg p-6 ${
              plan.popular
                ? 'border-primary-600 bg-primary-50'
                : 'border-gray-200 bg-white'
            }`}
          >
            {plan.popular && (
              <div className="absolute top-0 left-1/2 transform -translate-x-1/2 -translate-y-1/2">
                <span className="bg-primary-600 text-white text-xs font-bold px-3 py-1 rounded-full">
                  MOST POPULAR
                </span>
              </div>
            )}

            <div className="text-center mb-6">
              <h3 className="text-xl font-bold text-gray-900 mb-2">
                {plan.name}
              </h3>
              <div className="flex items-baseline justify-center">
                <span className="text-4xl font-bold text-gray-900">
                  ${plan.price}
                </span>
                <span className="text-gray-600 ml-2">/month</span>
              </div>
            </div>

            <ul className="space-y-3 mb-6">
              {plan.features.map((feature) => (
                <li key={feature} className="flex items-start">
                  <Check className="w-5 h-5 text-success-500 mr-2 flex-shrink-0" />
                  <span className="text-sm text-gray-700">{feature}</span>
                </li>
              ))}
              {plan.notIncluded.map((feature) => (
                <li key={feature} className="flex items-start">
                  <X className="w-5 h-5 text-gray-400 mr-2 flex-shrink-0" />
                  <span className="text-sm text-gray-400">{feature}</span>
                </li>
              ))}
            </ul>

            <Button
              variant={plan.popular ? 'primary' : 'outline'}
              className="w-full"
              size="lg"
            >
              Get Started
            </Button>
          </div>
        ))}
      </div>

      <div className="mt-6 text-center text-sm text-gray-600">
        <p>All plans include 7-day free trial. Cancel anytime.</p>
      </div>
    </Modal>
  )
}
