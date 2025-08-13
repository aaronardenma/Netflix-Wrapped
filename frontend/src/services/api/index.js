// src/api/index.js
// Barrel exports - import everything from one place

export { default as apiClient, setAuthContext } from './apiClient';
export { authAPI, netflixAPI, dataAPI, createGenericAPI } from './endpoints';

// Re-export the default client for direct usage
export { default } from './apiClient';