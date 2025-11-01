/**
 * Mock Data Service - Theory of Mind:
 * - Realistic data with Nashville addresses = credibility
 * - Mix of prices = shows market variety
 * - Some "deal" properties = creates excitement
 * - Different property types = serves various user needs
 */

export const mockListings = [
  {
    id: 1,
    address: '1234 Broadway',
    city: 'Nashville',
    zipCode: '37203',
    neighborhood: 'Gulch',
    price: 2400,
    bedrooms: 2,
    bathrooms: 2,
    sqft: 1200,
    propertyType: 'Apartment',
    imageUrl: 'https://via.placeholder.com/400x300?text=Modern+Apartment',
    daysOnMarket: 5,
    latitude: 36.1540,
    longitude: -86.7833,
    amenities: ['Pool', 'Gym', 'Parking'],
    description: 'Modern apartment in the heart of the Gulch with stunning city views.',
    dealScore: 85, // Theory of Mind: High score = good deal = excitement
  },
  {
    id: 2,
    address: '456 Fatherland St',
    city: 'Nashville',
    zipCode: '37206',
    neighborhood: 'East Nashville',
    price: 1800,
    bedrooms: 1,
    bathrooms: 1,
    sqft: 850,
    propertyType: 'Condo',
    imageUrl: 'https://via.placeholder.com/400x300?text=Cozy+Condo',
    daysOnMarket: 12,
    latitude: 36.1728,
    longitude: -86.7489,
    amenities: ['Parking'],
    description: 'Charming condo in trendy East Nashville, walk to restaurants.',
    dealScore: 92, // Great deal!
  },
  {
    id: 3,
    address: '789 12th Ave S',
    city: 'Nashville',
    zipCode: '37204',
    neighborhood: '12 South',
    price: 2800,
    bedrooms: 3,
    bathrooms: 2.5,
    sqft: 1800,
    propertyType: 'Townhouse',
    imageUrl: 'https://via.placeholder.com/400x300?text=Spacious+Townhouse',
    daysOnMarket: 3,
    latitude: 36.1203,
    longitude: -86.7872,
    amenities: ['Patio', 'Garage', 'Pet Friendly'],
    description: 'Beautiful townhouse in 12 South, close to shops and dining.',
    dealScore: 75,
  },
  {
    id: 4,
    address: '321 Charlotte Ave',
    city: 'Nashville',
    zipCode: '37209',
    neighborhood: 'Sylvan Park',
    price: 2200,
    bedrooms: 2,
    bathrooms: 2,
    sqft: 1100,
    propertyType: 'Apartment',
    imageUrl: 'https://via.placeholder.com/400x300?text=Updated+Unit',
    daysOnMarket: 8,
    latitude: 36.1556,
    longitude: -86.8067,
    amenities: ['Pool', 'Fitness Center'],
    description: 'Newly renovated apartment in quiet Sylvan Park neighborhood.',
    dealScore: 88,
  },
  {
    id: 5,
    address: '555 Main St',
    city: 'Nashville',
    zipCode: '37201',
    neighborhood: 'Downtown',
    price: 2950,
    bedrooms: 2,
    bathrooms: 2,
    sqft: 1300,
    propertyType: 'Luxury Apartment',
    imageUrl: 'https://via.placeholder.com/400x300?text=Luxury+Living',
    daysOnMarket: 1,
    latitude: 36.1627,
    longitude: -86.7816,
    amenities: ['Concierge', 'Rooftop', 'Gym', 'Valet Parking'],
    description: 'Luxury high-rise in downtown Nashville with premium amenities.',
    dealScore: 60, // Less of a deal, but luxury = different market
  },
  {
    id: 6,
    address: '888 Woodland St',
    city: 'Nashville',
    zipCode: '37206',
    neighborhood: 'East Nashville',
    price: 1650,
    bedrooms: 1,
    bathrooms: 1,
    sqft: 750,
    propertyType: 'Studio',
    imageUrl: 'https://via.placeholder.com/400x300?text=Affordable+Studio',
    daysOnMarket: 20,
    latitude: 36.1698,
    longitude: -86.7456,
    amenities: ['On-site Laundry'],
    description: 'Affordable studio in vibrant East Nashville.',
    dealScore: 95, // Excellent value!
  },
  {
    id: 7,
    address: '222 Belmont Blvd',
    city: 'Nashville',
    zipCode: '37212',
    neighborhood: 'Midtown',
    price: 2100,
    bedrooms: 2,
    bathrooms: 1.5,
    sqft: 1050,
    propertyType: 'Duplex',
    imageUrl: 'https://via.placeholder.com/400x300?text=College+Duplex',
    daysOnMarket: 15,
    latitude: 36.1372,
    longitude: -86.7933,
    amenities: ['Yard', 'Parking'],
    description: 'Duplex near Vanderbilt and Belmont universities.',
    dealScore: 78,
  },
  {
    id: 8,
    address: '999 Germantown Ave',
    city: 'Nashville',
    zipCode: '37208',
    neighborhood: 'Germantown',
    price: 2600,
    bedrooms: 2,
    bathrooms: 2,
    sqft: 1250,
    propertyType: 'Loft',
    imageUrl: 'https://via.placeholder.com/400x300?text=Industrial+Loft',
    daysOnMarket: 7,
    latitude: 36.1733,
    longitude: -86.7903,
    amenities: ['Exposed Brick', 'High Ceilings', 'Parking'],
    description: 'Industrial loft in historic Germantown district.',
    dealScore: 82,
  },
  {
    id: 9,
    address: '111 Hillsboro Pike',
    city: 'Nashville',
    zipCode: '37215',
    neighborhood: 'Green Hills',
    price: 2500,
    bedrooms: 2,
    bathrooms: 2,
    sqft: 1150,
    propertyType: 'Apartment',
    imageUrl: 'https://via.placeholder.com/400x300?text=Green+Hills+Apt',
    daysOnMarket: 4,
    latitude: 36.1079,
    longitude: -86.8156,
    amenities: ['Pool', 'Tennis Courts', 'Gym'],
    description: 'Upscale apartment in Green Hills shopping district.',
    dealScore: 70,
  },
  {
    id: 10,
    address: '777 Murfreesboro Pike',
    city: 'Nashville',
    zipCode: '37217',
    neighborhood: 'South Nashville',
    price: 1750,
    bedrooms: 3,
    bathrooms: 2,
    sqft: 1400,
    propertyType: 'House',
    imageUrl: 'https://via.placeholder.com/400x300?text=Family+Home',
    daysOnMarket: 10,
    latitude: 36.1156,
    longitude: -86.7289,
    amenities: ['Yard', 'Garage', 'Pet Friendly'],
    description: 'Spacious family home with large yard.',
    dealScore: 90, // Great value for size!
  },
]

// Calculate market stats from mock data
export const mockStats = {
  totalListings: mockListings.length,
  avgPrice: Math.round(mockListings.reduce((sum, l) => sum + l.price, 0) / mockListings.length),
  avgDaysOnMarket: Math.round(mockListings.reduce((sum, l) => sum + l.daysOnMarket, 0) / mockListings.length),
  newListingsThisWeek: mockListings.filter(l => l.daysOnMarket <= 7).length,
}

// Price history for charts (Theory of Mind: Showing trends = professional analysis tool)
export const mockPriceHistory = [
  { month: 'Jun', avgPrice: 2150 },
  { month: 'Jul', avgPrice: 2200 },
  { month: 'Aug', avgPrice: 2280 },
  { month: 'Sep', avgPrice: 2250 },
  { month: 'Oct', avgPrice: 2320 },
  { month: 'Nov', avgPrice: 2380 },
]

// Simulate API delay for realism
export const fetchListings = (filters = {}) => {
  return new Promise((resolve) => {
    setTimeout(() => {
      let filtered = [...mockListings]

      if (filters.zipCode) {
        filtered = filtered.filter(l => l.zipCode === filters.zipCode)
      }
      if (filters.minPrice) {
        filtered = filtered.filter(l => l.price >= filters.minPrice)
      }
      if (filters.maxPrice) {
        filtered = filtered.filter(l => l.price <= filters.maxPrice)
      }
      if (filters.bedrooms) {
        filtered = filtered.filter(l => l.bedrooms === filters.bedrooms)
      }

      resolve(filtered)
    }, 500) // Simulate network delay
  })
}

export const fetchStats = () => {
  return new Promise((resolve) => {
    setTimeout(() => resolve(mockStats), 300)
  })
}

export const fetchPriceHistory = () => {
  return new Promise((resolve) => {
    setTimeout(() => resolve(mockPriceHistory), 300)
  })
}
