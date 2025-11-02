/**
 * Auth Context - Theory of Mind:
 * - Global auth state = no prop drilling
 * - Auto-fetch user on mount = seamless experience
 * - Loading states = proper feedback
 */

import { createContext, useContext, useState, useEffect } from 'react';
import { authApi } from '../services/api';

const AuthContext = createContext(null);

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within AuthProvider');
  }
  return context;
};

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Fetch current user on mount
  useEffect(() => {
    const initAuth = async () => {
      if (authApi.isAuthenticated()) {
        try {
          const userData = await authApi.getCurrentUser();
          setUser(userData);
        } catch (err) {
          console.error('Auth init error:', err);
          authApi.logout();
        }
      }
      setLoading(false);
    };

    initAuth();
  }, []);

  const register = async (email, password, fullName) => {
    setError(null);
    try {
      const data = await authApi.register(email, password, fullName);
      setUser(data.user);
      return data;
    } catch (err) {
      setError(err.message);
      throw err;
    }
  };

  const login = async (email, password) => {
    setError(null);
    try {
      const data = await authApi.login(email, password);
      setUser(data.user);
      return data;
    } catch (err) {
      setError(err.message);
      throw err;
    }
  };

  const logout = () => {
    authApi.logout();
    setUser(null);
  };

  const refreshUser = async () => {
    try {
      const userData = await authApi.getCurrentUser();
      setUser(userData);
      return userData;
    } catch (err) {
      console.error('Error refreshing user:', err);
      throw err;
    }
  };

  const value = {
    user,
    loading,
    error,
    register,
    login,
    logout,
    refreshUser,
    isAuthenticated: !!user,
    isPremium: user?.tier !== 'free',
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};
