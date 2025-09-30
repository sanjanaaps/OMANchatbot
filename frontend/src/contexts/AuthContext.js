import React, { createContext, useContext, useState, useEffect } from 'react';
import { authService } from '../services/authService';
import toast from 'react-hot-toast';

const AuthContext = createContext();

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [loginTime, setLoginTime] = useState(null);
  const [lastLogoutTime, setLastLogoutTime] = useState(null);

  useEffect(() => {
    // Load stored timestamps
    try {
      const storedLoginTime = localStorage.getItem('loginTime');
      const storedLastLogoutTime = localStorage.getItem('lastLogoutTime');
      if (storedLoginTime) {
        setLoginTime(Number(storedLoginTime));
      }
      if (storedLastLogoutTime) {
        setLastLogoutTime(Number(storedLastLogoutTime));
      }
    } catch (e) {
      // no-op if storage is unavailable
    }

    checkAuthStatus();
  }, []);

  const checkAuthStatus = async () => {
    try {
      setLoading(true);
      const response = await authService.checkAuth();
      if (response.success) {
        setUser(response.user);
        setIsAuthenticated(true);
      } else {
        setUser(null);
        setIsAuthenticated(false);
      }
    } catch (error) {
      console.error('Auth check failed:', error);
      setUser(null);
      setIsAuthenticated(false);
    } finally {
      setLoading(false);
    }
  };

  const login = async (credentials) => {
    try {
      setLoading(true);
      const response = await authService.login(credentials);
      if (response.success) {
        setUser(response.user);
        setIsAuthenticated(true);
        const now = Date.now();
        setLoginTime(now);
        try {
          localStorage.setItem('loginTime', String(now));
        } catch (e) {}
        toast.success('Login successful!');
        return { success: true };
      } else {
        toast.error(response.message || 'Login failed');
        return { success: false, message: response.message };
      }
    } catch (error) {
      console.error('Login error:', error);
      toast.error('Login failed. Please try again.');
      return { success: false, message: 'Login failed' };
    } finally {
      setLoading(false);
    }
  };

  const logout = async () => {
    try {
      const now = Date.now();
      await authService.logout();
      setUser(null);
      setIsAuthenticated(false);
      setLastLogoutTime(now);
      setLoginTime(null);
      try {
        localStorage.setItem('lastLogoutTime', String(now));
        localStorage.removeItem('loginTime');
      } catch (e) {}
      toast.success('Logged out successfully');
    } catch (error) {
      console.error('Logout error:', error);
      toast.error('Logout failed');
    }
  };

  const value = {
    user,
    loading,
    isAuthenticated,
    loginTime,
    lastLogoutTime,
    login,
    logout,
    checkAuthStatus
  };

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
};
