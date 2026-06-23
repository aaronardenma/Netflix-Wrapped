import { BrowserRouter, Navigate, Routes, Route } from "react-router-dom";
import NavBar from "./components/NavBar";
import Home from "./pages/Home";
import NewRecap from "./pages/NewRecap";
import Statistics from "./pages/Statistics";
import Auth from "./pages/Auth";
import Profile from "./pages/Profile";
import { useEffect } from "react";
import { useDispatch, useSelector } from "react-redux";
import { bootstrapAuth, selectAuth } from "./store/authSlice";

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
const queryClient = new QueryClient();
const SESSION_UPLOAD_KEY = "netflixWrapped:lastAnonymousUpload";

function App() {
  const dispatch = useDispatch();
  const { isAuthenticated } = useSelector(selectAuth);

  useEffect(() => {
    dispatch(bootstrapAuth());
  }, [dispatch]);

  useEffect(() => {
    if (!isAuthenticated) return;

    sessionStorage.removeItem(SESSION_UPLOAD_KEY);
    queryClient.removeQueries({
      predicate: (query) =>
        query.queryKey[0] === "processingStatus" ||
        (query.queryKey[0] === "graphs" && Boolean(query.queryKey[3])),
    });
  }, [isAuthenticated]);

  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <NavBar />
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/create" element={<NewRecap />} />
          <Route path="/recap" element={<Statistics />} />
          <Route path="/upload" element={<Navigate to="/create" replace />} />
          <Route path="/new-recap" element={<Navigate to="/create" replace />} />
          <Route path="/statistics" element={<Navigate to="/recap" replace />} />
          <Route path="/auth/forgot-password" element={<Navigate to="/auth/login" replace />} />
          <Route path="/auth/reset-password/:uid/:token" element={<Navigate to="/auth/login" replace />} />
          <Route path="/auth/:type" element={<Auth />} />
          <Route path="/profile" element={<Profile />} />
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  );
}

export default App;
