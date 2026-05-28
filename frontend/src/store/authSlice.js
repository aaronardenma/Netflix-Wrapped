import { createAsyncThunk, createSlice } from "@reduxjs/toolkit";
import { authAPI } from "@/services/api";
import { getCookie } from "@/utils/cookies";

const initialState = {
  user: null,
  isAuthenticated: false,
  loading: true,
  csrfToken: null,
  error: null,
};

export const fetchCSRFToken = createAsyncThunk(
  "auth/fetchCSRFToken",
  async (_, { rejectWithValue }) => {
    try {
      await authAPI.getCSRF();
      return getCookie("csrftoken");
    } catch (error) {
      return rejectWithValue(error.message || "Failed to get CSRF token");
    }
  }
);

export const bootstrapAuth = createAsyncThunk(
  "auth/bootstrap",
  async (_, { dispatch, rejectWithValue }) => {
    try {
      let csrfToken = getCookie("csrftoken");
      if (!csrfToken) {
        csrfToken = await dispatch(fetchCSRFToken()).unwrap();
      }

      const response = await authAPI.me();
      return {
        csrfToken,
        user: response.data,
      };
    } catch (error) {
      return rejectWithValue(error.message || "Not authenticated");
    }
  }
);

export const loginUser = createAsyncThunk(
  "auth/login",
  async ({ email, password }, { dispatch, rejectWithValue }) => {
    try {
      if (!getCookie("csrftoken")) {
        await dispatch(fetchCSRFToken()).unwrap();
      }

      await authAPI.login({ email, password });
      const response = await authAPI.me();
      return response.data;
    } catch (error) {
      return rejectWithValue(
        error.response?.data?.error || error.message || "Login failed"
      );
    }
  }
);

export const registerUser = createAsyncThunk(
  "auth/register",
  async (userData, { dispatch, rejectWithValue }) => {
    try {
      if (!getCookie("csrftoken")) {
        await dispatch(fetchCSRFToken()).unwrap();
      }

      const response = await authAPI.register(userData);
      return response.data.user;
    } catch (error) {
      return rejectWithValue(
        error.response?.data?.error || error.message || "Registration failed"
      );
    }
  }
);

export const logoutUser = createAsyncThunk(
  "auth/logout",
  async (_, { rejectWithValue }) => {
    try {
      await authAPI.logout();
    } catch (error) {
      return rejectWithValue(error.message || "Logout failed");
    }
  }
);

const authSlice = createSlice({
  name: "auth",
  initialState,
  reducers: {
    authExpired(state) {
      state.user = null;
      state.isAuthenticated = false;
      state.loading = false;
      state.error = null;
    },
  },
  extraReducers: (builder) => {
    builder
      .addCase(fetchCSRFToken.fulfilled, (state, action) => {
        state.csrfToken = action.payload;
      })
      .addCase(fetchCSRFToken.rejected, (state, action) => {
        state.csrfToken = null;
        state.error = action.payload;
      })
      .addCase(bootstrapAuth.pending, (state) => {
        state.loading = true;
      })
      .addCase(bootstrapAuth.fulfilled, (state, action) => {
        state.loading = false;
        state.user = action.payload.user;
        state.csrfToken = action.payload.csrfToken;
        state.isAuthenticated = true;
        state.error = null;
      })
      .addCase(bootstrapAuth.rejected, (state) => {
        state.loading = false;
        state.user = null;
        state.isAuthenticated = false;
      })
      .addCase(loginUser.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(loginUser.fulfilled, (state, action) => {
        state.loading = false;
        state.user = action.payload;
        state.isAuthenticated = true;
        state.error = null;
      })
      .addCase(loginUser.rejected, (state, action) => {
        state.loading = false;
        state.user = null;
        state.isAuthenticated = false;
        state.error = action.payload;
      })
      .addCase(registerUser.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(registerUser.fulfilled, (state, action) => {
        state.loading = false;
        state.user = action.payload;
        state.isAuthenticated = true;
        state.error = null;
      })
      .addCase(registerUser.rejected, (state, action) => {
        state.loading = false;
        state.error = action.payload;
      })
      .addCase(logoutUser.fulfilled, (state) => {
        state.user = null;
        state.isAuthenticated = false;
        state.loading = false;
        state.error = null;
      })
      .addCase(logoutUser.rejected, (state) => {
        state.user = null;
        state.isAuthenticated = false;
        state.loading = false;
      });
  },
});

export const { authExpired } = authSlice.actions;

export const selectAuth = (state) => state.auth;
export const selectIsAuthenticated = (state) => state.auth.isAuthenticated;
export const selectUser = (state) => state.auth.user;
export const selectAuthLoading = (state) => state.auth.loading;

export default authSlice.reducer;
