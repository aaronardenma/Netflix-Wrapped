// api/apiClient.js
import axios from 'axios';
import { getCookie } from '../../utils/cookies';

// Create axios instance
const apiClient = axios.create({
  baseURL: 'http://127.0.0.1:8000',
  withCredentials: true, // Always send cookies
  timeout: 10000, // 10 second timeout
});

// Store auth context reference (will be set from AuthProvider)
let authContextRef = null;

// Function to set auth context reference
export const setAuthContext = (authContext) => {
  authContextRef = authContext;
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
    return response;
  },
  (error) => {
    console.error('API Error:', error.response?.status, error.response?.data);
    
    // Handle authentication errors
    if (error.response?.status === 401 || error.response?.status === 403) {
      console.log('Authentication error detected, logging out user...');
      
      // Call the auth context's logout function
      if (authContextRef && authContextRef.handleAuthError) {
        authContextRef.handleAuthError();
      }
      
      // Don't re-throw auth errors since they're handled globally
      return Promise.reject(new Error('Authentication expired'));
    }
    
    // For all other errors, just pass them through
    return Promise.reject(error);
  }
);

export default apiClient;