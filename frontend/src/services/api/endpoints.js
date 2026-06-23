// api/endpoints.js
import apiClient from "./apiClient";

// User/Auth related endpoints
export const authAPI = {
  // Authentication endpoints
  register: (userData) => apiClient.post("/api/auth/register/", userData),
  login: (credentials) => apiClient.post("/api/auth/login/", credentials),
  logout: () => apiClient.post("/api/auth/logout/"),
  me: () => apiClient.get("/api/auth/me/"),
  // Email-based password reset is intentionally disabled until an email
  // provider is configured for account recovery.
  // requestPasswordReset: (email) =>
  //   apiClient.post("/api/auth/password-reset/request/", { email }),
  // confirmPasswordReset: ({ uid, token, password }) =>
  //   apiClient.post("/api/auth/password-reset/confirm/", {
  //     uid,
  //     token,
  //     password,
  //   }),
  changePassword: ({ currentPassword, newPassword }) =>
    apiClient.post("/api/auth/password/change/", {
      currentPassword,
      newPassword,
    }),
  wipeAccountData: ({ currentPassword }) =>
    apiClient.post("/api/auth/account/wipe-data/", { currentPassword }),
  deleteAccount: ({ currentPassword }) =>
    apiClient.post("/api/auth/account/delete/", { currentPassword }),

  // JWT Token endpoints (if needed for manual token management)
  getToken: (credentials) => apiClient.post("/api/auth/token/", credentials),
  refreshToken: (refreshToken) =>
    apiClient.post("/api/auth/token/refresh/", { refresh: refreshToken }),
  verifyToken: (token) => apiClient.post("/api/auth/token/verify/", { token }),

  // CSRF token
  getCSRF: () => apiClient.get("/api/csrf/"),
};

// Netflix data processing endpoints
export const netflixAPI = {
  // Quick CSV upload and processing
  quickExtractCSV: (file) => {
    const formData = new FormData();
    const files = Array.isArray(file) ? file : [file];
    files.forEach((currentFile) => {
      formData.append("files", currentFile);
    });

    return apiClient.post("/api/csv/quick-extract/", formData, {
      headers: {
        "Content-Type": "multipart/form-data",
      },
    });
  },

  // Get processed data for specific profile/year
  getData: (profileName, year, jobId = null) => {
    const requestData = {
      user: profileName,
      year: year,
    };
    if (jobId) {
      requestData.job_id = jobId;
    }
    return apiClient.post("/api/get-data/", requestData);
  },

  // Check processing status
  getProcessingStatus: (jobId) =>
    apiClient.get(`/api/processing-status/${jobId}/`),

  // Get all stored data (profile/year combinations)
  getStoredData: () => apiClient.get("/api/stored-data/"),

  // Get specific stored data
  getStoredDataByProfile: (profileName, year) =>
    apiClient.post("/api/get-stored-data/", {
      profile_name: profileName,
      year: year,
    }),

  compareYears: ({ profileName, yearA, yearB, jobId = null }) => {
    const requestData = {
      profile_name: profileName,
      year_a: yearA,
      year_b: yearB,
    };
    if (jobId) {
      requestData.job_id = jobId;
    }
    return apiClient.post("/api/compare-years/", requestData);
  },

  getRecommendations: (profileName, refresh = false) =>
    apiClient.post("/api/recommendations/", {
      profile_name: profileName,
      refresh,
    }),
};

export default apiClient;
