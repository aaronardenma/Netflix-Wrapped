// api/apiClient.js
import axios from 'axios';
import { getCookie } from '../../utils/cookies';

// Create axios instance
const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000',
  withCredentials: true, // Always send cookies
  timeout: 60000,
});

let unauthorizedHandler = null;

export const setUnauthorizedHandler = (handler) => {
  unauthorizedHandler = handler;
};

// Request interceptor - adds CSRF token to all requests
apiClient.interceptors.request.use(
  (config) => {
    // Get CSRF token from cookies and add to headers
    const csrfToken = getCookie('csrftoken');
    if (csrfToken) {
      config.headers['X-CSRFToken'] = csrfToken;
    }
    
    console.log(`Making ${config.method?.toUpperCase()} request to: ${config.url}`);
    return config;
  },
  (error) => {
    console.error('Request interceptor error:', error);
    return Promise.reject(error);
  }
);

// Response interceptor - handles authentication errors globally
apiClient.interceptors.response.use(
  (response) => {
    // Any status code in 2xx range triggers this function
    response.ok = response.status >= 200 && response.status < 300;
    return response;
  },
  (error) => {
    console.error('API Error:', error.response?.status, error.response?.data);
    
    // Handle authentication errors
    const isAuthEndpoint = error.config?.url?.includes('/api/auth/login/')
      || error.config?.url?.includes('/api/auth/register/');

    if (!isAuthEndpoint && (error.response?.status === 401 || error.response?.status === 403)) {
      console.log('Authentication error detected, logging out user...');
      
      if (unauthorizedHandler) {
        unauthorizedHandler();
      }
      
      // Don't re-throw auth errors since they're handled globally
      return Promise.reject(new Error('Authentication expired'));
    }
    
    // For all other errors, just pass them through
    return Promise.reject(error);
  }
);

export default apiClient;
