// contexts/AuthContext.jsx
import React, { createContext, useContext, useState, useEffect } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { getCookie } from "../utils/cookies";
import { useNavigate } from "react-router-dom";
import { setAuthContext } from "../services/api/apiClient";
import { authAPI } from "@/services/api";

const AuthContext = createContext();

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
};

export const AuthProvider = ({ children }) => {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [csrfToken, setCsrfToken] = useState(null);
  const queryClient = useQueryClient();
  const nav = useNavigate();

  // Handle logout/token expiry - called by axios interceptor
  const handleAuthError = () => {
    console.log('Handling auth error: clearing user state and redirecting...');
    setUser(null);
    setIsAuthenticated(false);
    queryClient.removeQueries(["me"]);
    queryClient.clear();
    nav("/");
  };

  // Fetch CSRF token
  const fetchCSRFToken = async () => {
    try {
      // Use regular fetch for CSRF endpoint (before auth is established)
      await authAPI.getCSRF()
      
      const token = getCookie("csrftoken");
      console.log("CSRF token fetched:", token);
      setCsrfToken(token);
      return token;
    } catch (error) {
      console.error("Failed to fetch CSRF token:", error);
      return null;
    }
  };

  // Check authentication status
  const checkAuthStatus = async () => {
    try {
      const response = await authAPI.me();
      
      if (response.status === 200) {
        const userData = response.data;
        setUser(userData);
        setIsAuthenticated(true);
        queryClient.setQueryData(["me"], userData);
        return true;
      }
    } catch (error) {
      console.error("Auth check failed:", error);
      // Don't handle auth errors here - interceptor handles them
      if (error.message !== 'Authentication expired') {
        setIsAuthenticated(false);
        setUser(null);
      }
      return false;
    }
  };

  // Initialize auth context reference for axios interceptor
  useEffect(() => {
    setAuthContext({
      handleAuthError,
      isAuthenticated,
      user
    });
  }, [isAuthenticated, user]);

  // Initialize on mount
  useEffect(() => {
    const initialize = async () => {
      setLoading(true);

      // Get or fetch CSRF token
      let token = getCookie("csrftoken");
      if (!token) {
        token = await fetchCSRFToken();
      } else {
        setCsrfToken(token);
      }

      // Check if user is authenticated
      if (token) {
        await checkAuthStatus();
      } else {
        setIsAuthenticated(false);
        setUser(null);
      }

      setLoading(false);
    };

    initialize();
  }, []);

  // Periodic auth check (optional - runs every 10 minutes)
  useEffect(() => {
    if (!isAuthenticated) return;

    const interval = setInterval(async () => {
      console.log('Performing periodic auth check...');
      await checkAuthStatus();
    }, 10 * 60 * 1000); // Check every 10 minutes

    return () => clearInterval(interval);
  }, [isAuthenticated]);

  const login = async () => {
    setLoading(true);
    try {
      const response = await authAPI.me();
      
      if (response.status === 200) {
        const userData = response.data;
        setUser(userData);
        setIsAuthenticated(true);
        queryClient.setQueryData(["me"], userData);
      }
    } catch (error) {
      console.error("Login rehydrate failed", error);
      // Auth errors handled by interceptor
    } finally {
      setLoading(false);
    }
  };

  const logout = async () => {
    try {
      await authAPI.logout();
      console.log('Logout successful');
    } catch (error) {
      console.error("Logout error:", error);
    } finally {
      // Always clear state regardless of API response
      handleAuthError();
    }
  };

  // Helper function to get fresh CSRF token if needed
  const getCSRFToken = async () => {
    if (csrfToken) return csrfToken;
    return await fetchCSRFToken();
  };

  const value = {
    isAuthenticated,
    user,
    loading,
    csrfToken,
    login,
    logout,
    getCSRFToken,
    checkAuthStatus,
    handleAuthError, // Expose for testing
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};