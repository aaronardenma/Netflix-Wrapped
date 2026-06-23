// src/api/index.js
// Barrel exports - import everything from one place

export { default as apiClient, setUnauthorizedHandler } from './apiClient';
export { authAPI, netflixAPI } from "./endpoints";

// Re-export the default client for direct usage
export { default } from './apiClient';
