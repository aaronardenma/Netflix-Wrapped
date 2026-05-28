import { BrowserRouter, Routes, Route } from "react-router-dom";
import NavBar from "./components/NavBar";
import Home from "./pages/Home";
import Upload from "./pages/Upload";
import Contact from "./pages/Contact";
import Statistics from "./pages/Statistics";
import Auth from "./pages/Auth";
import Profile from "./pages/Profile";
import Profiles from "./components/Profiles";
import { useEffect } from "react";
import { useDispatch } from "react-redux";
import { bootstrapAuth } from "./store/authSlice";

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
const queryClient = new QueryClient();

function App() {
  const dispatch = useDispatch();

  useEffect(() => {
    dispatch(bootstrapAuth());
  }, [dispatch]);

  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <NavBar />
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/upload" element={<Upload />} />
          <Route path="/statistics" element={<Statistics />} />
          <Route path="/auth/reset-password/:uid/:token" element={<Auth />} />
          <Route path="/auth/:type" element={<Auth />} />
          <Route path="/profile" element={<Profile />} />
          <Route path="/contact" element={<Contact />} />
          <Route path="/profiles" element={<Profiles />} />
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  );
}

export default App;
