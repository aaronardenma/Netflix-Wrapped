// contexts/AuthContext.jsx
import React, { createContext, useContext, useState, useEffect } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { getCookie } from "../utils/cookies";

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
  const backendURL = "http://127.0.0.1:8000";

  // Fetch CSRF token
  const fetchCSRFToken = async () => {
    try {
      await fetch(`${backendURL}/api/csrf/`, { credentials: "include" });
      const token = getCookie("csrftoken");
      console.log("CSRF token for checkAuthStatus:", token);
      setCsrfToken(token);
      return token;
    } catch (error) {
      console.error("Failed to fetch CSRF token:", error);
      return null;
    }
  };

  // Check authentication status
  const checkAuthStatus = async (token) => {
    try {
      const res = await fetch(`${backendURL}/api/auth/me/`, {
        credentials: "include", // send cookies
        headers: {
          "X-CSRFToken": token || "", // pass the CSRF token
        },
      });

      if (res.ok) {
        const userData = await res.json();
        setUser(userData);
        setIsAuthenticated(true);
        queryClient.setQueryData(["me"], userData);
      } else {
        setIsAuthenticated(false);
        setUser(null);
      }
    } catch (error) {
      console.error("Auth check failed:", error);
      setIsAuthenticated(false);
      setUser(null);
    }
  };

  // Initialize on mount
  useEffect(() => {
    const initialize = async () => {
      setLoading(true);

      let token = getCookie("csrftoken"); // get CSRF from cookies first

      if (!token) {
        token = await fetchCSRFToken(); // fetch CSRF token if missing
      } else {
        setCsrfToken(token);
      }

      if (token) {
        await checkAuthStatus(token); // call checkAuthStatus with token
      } else {
        setIsAuthenticated(false);
        setUser(null);
      }

      setLoading(false);
    };

    initialize();
  }, []);

  const login = async (userData) => {
    setUser(userData);
    setIsAuthenticated(true);
    queryClient.setQueryData(["me"], userData);
    await queryClient.invalidateQueries(["me"]);
  };

  const logout = async () => {
    try {
      const res = await fetch("http://127.0.0.1:8000/api/auth/logout/", {
        method: "POST",
        credentials: "include", // important to send cookies
        headers: {
          "Content-Type": "application/json",
          "X-CSRFToken": csrfToken || "", // Include CSRF token if needed
        },
      });

      if (!res.ok) {
        const errorData = await res.json();
        throw new Error(errorData.error || "Logout failed");
      }

      setUser(null);
      setIsAuthenticated(false);
      queryClient.removeQueries(["me"]);
      queryClient.clear();
    } catch (error) {
      console.error("Logout error:", error);
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
    checkAuthStatus: () => checkAuthStatus(csrfToken),
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};
