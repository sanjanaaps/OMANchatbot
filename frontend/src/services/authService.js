import api from './api';

export const authService = {
  async login(credentials) {
    try {
      const formData = new URLSearchParams();
      formData.append('username', credentials.username);
      formData.append('password', credentials.password);

      const response = await api.post('/api/auth/login', formData, {
        headers: {
          'Content-Type': 'application/x-www-form-urlencoded',
        },
      });

      return {
        success: true,
        user: response.data.user || { username: credentials.username },
        message: response.data.message
      };
    } catch (error) {
      console.error('Login error:', error);
      return {
        success: false,
        message: error.response?.data?.message || 'Login failed'
      };
    }
  },

  async logout() {
    try {
      await api.post('/api/auth/logout');
      return { success: true };
    } catch (error) {
      console.error('Logout error:', error);
      return { success: false };
    }
  },

  async checkAuth() {
    try {
      const response = await api.get('/api/dashboard');
      return {
        success: true,
        user: response.data.user || { username: 'User' }
      };
    } catch (error) {
      return {
        success: false,
        message: 'Not authenticated'
      };
    }
  }
};
