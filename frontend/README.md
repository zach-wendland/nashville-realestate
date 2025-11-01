# Nashville Rentals - Frontend

Free-tier React frontend for the Nashville Real Estate Intelligence Platform. Designed to showcase value and drive conversions to paid tiers through strategic feature limitations and upgrade prompts.

## Theory of Mind - Design Principles

### User Psychology
- **Curiosity Phase**: Impressive landing page with real market stats
- **Value Discovery**: 10 free listings show immediate utility
- **Frustration Point**: Blurred listings #11-20 create FOMO
- **Conversion Trigger**: Upgrade modals at strategic points

### Design Decisions
- **Blue color scheme**: Trust and professionalism (real estate context)
- **Card-based layout**: Easy scanning for comparison shoppers
- **Big numbers**: Data-driven confidence building
- **Deal scores**: Gamification + urgency

## Features

### Free Tier
✅ View 10 listings per day
✅ Basic search/filter (zip, price, beds)
✅ Map view
✅ Simple stats
✅ 7-day price history

### Premium Locked (Visible but Disabled)
🔒 Unlimited listings
🔒 Advanced filters
🔒 30-day price history
🔒 ROI calculator
🔒 Price alerts
🔒 CSV export

## Tech Stack

- **React 18** - UI library
- **Vite** - Fast build tool
- **React Router 6** - Routing
- **Tailwind CSS** - Styling
- **Recharts** - Data visualization
- **React-Leaflet** - Maps
- **Lucide React** - Icons

## Project Structure

```
src/
├── components/
│   ├── common/          # Reusable UI (Button, Card, Input, Modal)
│   ├── layout/          # Layout (Header, Footer)
│   ├── dashboard/       # Dashboard-specific components
│   ├── listings/        # Listing cards and details
│   └── upgrade/         # Upgrade modals and pricing
├── pages/
│   ├── LandingPage.jsx  # Marketing homepage
│   ├── Dashboard.jsx    # Main app (listings grid)
│   ├── Login.jsx        # Authentication
│   └── Signup.jsx       # User registration
├── services/
│   └── mockData.js      # Mock API (10 sample listings)
├── App.jsx              # Route configuration
└── main.jsx             # App entry point
```

## Setup

### Install Dependencies
```bash
npm install
```

### Run Development Server
```bash
npm run dev
```

Opens at http://localhost:3000

### Build for Production
```bash
npm run build
```

### Preview Production Build
```bash
npm run preview
```

### Run Tests
```bash
npm test
```

## Mock Data

Currently uses 10 hardcoded Nashville listings with realistic data:
- Mix of neighborhoods (Gulch, East Nashville, 12 South, etc.)
- Price range: $1,650 - $2,950/month
- Various property types (apartments, condos, townhouses)
- "Deal scores" to highlight value

**Future**: Replace with real API calls to Python backend.

## Components Overview

### Common Components
- **Button**: Primary/secondary/outline variants
- **Card**: Content containers with hover effects
- **Input**: Form inputs with labels and error states
- **Modal**: Overlay dialogs (used for upgrades)

### Dashboard Components
- **FilterPanel**: Search and filter interface
- **ListingCard**: Property display with blurring for free tier
- **StatsCards**: Market statistics grid
- **PriceChart**: Price trend visualization (Recharts)

### Upgrade Components
- **UpgradeModal**: Pricing table with 3 tiers ($14.99, $199, $499)

## Conversion Strategy

### Free Tier Limitations
1. **10 listing cap**: Show value, then create urgency
2. **Blurred cards**: FOMO for listings #11-20
3. **Locked features**: Visible but disabled advanced filters
4. **Chart teasers**: Show 6-month trends, promote 30-day history

### Upgrade Prompts
- After 10 listings (inline CTA)
- Click on blurred listing (modal)
- Filter panel (locked features hint)
- Charts (upgrade note)

### Pricing Tiers
1. **Renter Plus** ($14.99/mo) - Unlimited viewing
2. **Investor Pro** ($199/mo) - Analytics & ROI tools (MOST POPULAR)
3. **Enterprise** ($499/mo) - Multi-user + API

## Next Steps

### Backend Integration
- Replace mockData.js with real API calls
- Implement authentication (JWT tokens)
- Add payment processing (Stripe)
- Rate limiting for free tier

### Additional Features
- User dashboard (saved searches, alerts)
- Email notifications
- Mobile app (React Native)
- A/B testing framework

## Performance

- **First Load**: ~2s (with bundle splitting)
- **Time to Interactive**: ~3s
- **Lighthouse Score**: 90+ (target)

## Browser Support

- Chrome/Edge (last 2 versions)
- Firefox (last 2 versions)
- Safari 14+
- Mobile browsers (iOS Safari, Chrome Mobile)

## License

Proprietary - Nashville Rentals SaaS Platform
