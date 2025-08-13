// api/endpoints.js
import apiClient from './apiClient';

// User/Auth related endpoints
export const authAPI = {
  // Authentication endpoints
  register: (userData) => apiClient.post('/api/auth/register/', userData),
  login: (credentials) => apiClient.post('/api/auth/login/', credentials),
  logout: () => apiClient.post('/api/auth/logout/'),
  me: () => apiClient.get('/api/auth/me/'),
  
  // JWT Token endpoints (if needed for manual token management)
  getToken: (credentials) => apiClient.post('/api/auth/token/', credentials),
  refreshToken: (refreshToken) => apiClient.post('/api/auth/token/refresh/', { refresh: refreshToken }),
  verifyToken: (token) => apiClient.post('/api/auth/token/verify/', { token }),
  
  // CSRF token
  getCSRF: () => apiClient.get('/api/csrf/'),
};

// Netflix data processing endpoints
export const netflixAPI = {
  // Quick CSV upload and processing
  quickExtractCSV: (file) => {
    const formData = new FormData();
    formData.append('file', file);
    
    return apiClient.post('/api/csv/quick-extract/', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
  },

  // Priority processing for specific profile/year
  priorityProcess: (data) => apiClient.post('/api/priority-process/', data),

  // Get processed data for specific profile/year
  getData: (profileName, year, jobId = null) => {
    const requestData = {
      user: profileName,
      year: year,
    };
    if (jobId) {
      requestData.job_id = jobId;
    }
    return apiClient.post('/api/get-data/', requestData);
  },

  // Check processing status
  getProcessingStatus: (jobId) => apiClient.get(`/api/processing-status/${jobId}/`),

  // Get all stored data (profile/year combinations)
  getStoredData: () => apiClient.get('/api/stored-data/'),

  // Get specific stored data
  getStoredDataByProfile: (profileName, year) => 
    apiClient.post('/api/get-stored-data/', {
      profile_name: profileName,
      year: year,
    }),
};

// Simplified data API for common operations
export const dataAPI = {
  // Upload and process Netflix CSV
  uploadNetflixCSV: netflixAPI.quickExtractCSV,
  
  // Get viewing statistics for a profile/year
  getViewingStats: netflixAPI.getData,
  
  // Get all available profile/year combinations
  getAvailableData: netflixAPI.getStoredData,
  
  // Check if processing is complete
  checkProcessingStatus: netflixAPI.getProcessingStatus,
};

// Generic CRUD helpers (if you have other endpoints)
export const createGenericAPI = (endpoint) => ({
  list: (params) => apiClient.get(endpoint, { params }),
  get: (id) => apiClient.get(`${endpoint}${id}/`),
  create: (data) => apiClient.post(endpoint, data),
  update: (id, data) => apiClient.put(`${endpoint}${id}/`, data),
  patch: (id, data) => apiClient.patch(`${endpoint}${id}/`, data),
  delete: (id) => apiClient.delete(`${endpoint}${id}/`),
});

export default apiClient;