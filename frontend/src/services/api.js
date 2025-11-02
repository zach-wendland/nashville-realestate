/**
 * API Service - Real Backend Integration
 * Theory of Mind: Clean API abstraction = easy to use, maintain
 */

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

class ApiError extends Error {
  constructor(message, status, data) {
    super(message);
    this.status = status;
    this.data = data;
    this.name = 'ApiError';
  }
}

// Helper to get auth token
const getAuthToken = () => {
  return localStorage.getItem('auth_token');
};

// Helper to make authenticated requests
const fetchWithAuth = async (url, options = {}) => {
  const token = getAuthToken();

  const headers = {
    'Content-Type': 'application/json',
    ...options.headers,
  };

  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  const response = await fetch(`${API_BASE_URL}${url}`, {
    ...options,
    headers,
  });

  if (!response.ok) {
    const data = await response.json().catch(() => ({}));
    throw new ApiError(
      data.detail || 'An error occurred',
      response.status,
      data
    );
  }

  return response.json();
};

// Auth API
export const authApi = {
  register: async (email, password, fullName) => {
    const data = await fetchWithAuth('/auth/register', {
      method: 'POST',
      body: JSON.stringify({
        email,
        password,
        full_name: fullName,
      }),
    });

    // Store token
    localStorage.setItem('auth_token', data.access_token);
    return data;
  },

  login: async (email, password) => {
    const data = await fetchWithAuth('/auth/login', {
      method: 'POST',
      body: JSON.stringify({ email, password }),
    });

    // Store token
    localStorage.setItem('auth_token', data.access_token);
    return data;
  },

  logout: () => {
    localStorage.removeItem('auth_token');
  },

  getCurrentUser: async () => {
    return fetchWithAuth('/auth/me');
  },

  isAuthenticated: () => {
    return !!getAuthToken();
  },
};

// Listings API
export const listingsApi = {
  getListings: async (filters = {}) => {
    const params = new URLSearchParams();

    if (filters.zipCode) params.append('zip_code', filters.zipCode);
    if (filters.minPrice) params.append('min_price', filters.minPrice);
    if (filters.maxPrice) params.append('max_price', filters.maxPrice);
    if (filters.minBeds) params.append('min_beds', filters.minBeds);
    if (filters.maxBeds) params.append('max_beds', filters.maxBeds);
    if (filters.minBaths) params.append('min_baths', filters.minBaths);
    if (filters.sortBy) params.append('sort_by', filters.sortBy);
    if (filters.sortOrder) params.append('sort_order', filters.sortOrder);
    if (filters.page) params.append('page', filters.page);
    if (filters.pageSize) params.append('page_size', filters.pageSize);

    const queryString = params.toString();
    const url = `/listings${queryString ? `?${queryString}` : ''}`;

    return fetchWithAuth(url);
  },

  getListing: async (id) => {
    return fetchWithAuth(`/listings/${id}`);
  },

  getMarketStats: async (zipCode = null) => {
    const url = zipCode
      ? `/listings/stats/market?zip_code=${zipCode}`
      : '/listings/stats/market';
    return fetchWithAuth(url);
  },

  // Saved searches
  createSavedSearch: async (name, filters, alertFrequency = 'never') => {
    return fetchWithAuth('/listings/saved-searches', {
      method: 'POST',
      body: JSON.stringify({
        name,
        filters,
        alert_frequency: alertFrequency,
      }),
    });
  },

  getSavedSearches: async () => {
    return fetchWithAuth('/listings/saved-searches');
  },

  deleteSavedSearch: async (id) => {
    return fetchWithAuth(`/listings/saved-searches/${id}`, {
      method: 'DELETE',
    });
  },
};

// Subscriptions API
export const subscriptionsApi = {
  createSubscription: async (tier, paymentMethodId) => {
    return fetchWithAuth('/subscriptions/create', {
      method: 'POST',
      body: JSON.stringify({
        tier,
        payment_method_id: paymentMethodId,
      }),
    });
  },

  getSubscription: async () => {
    return fetchWithAuth('/subscriptions');
  },

  cancelSubscription: async () => {
    return fetchWithAuth('/subscriptions/cancel', {
      method: 'POST',
    });
  },

  reactivateSubscription: async () => {
    return fetchWithAuth('/subscriptions/reactivate', {
      method: 'POST',
    });
  },

  getPortalUrl: async () => {
    return fetchWithAuth('/subscriptions/portal-url');
  },
};

// Export error class for handling
export { ApiError };
