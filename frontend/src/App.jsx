import { BrowserRouter, Routes, Route } from "react-router-dom";
import NavBar from "./components/NavBar";
import Home from "./pages/Home";
import Upload from "./pages/Upload";
import Contact from "./pages/Contact";
import Statistics from "./pages/Statistics";
import Auth from "./pages/Auth";
import Profiles from "./components/Profiles";
import { useEffect } from "react";
import { AuthProvider } from "./contexts/AuthContext.jsx";
import { useQuery } from "@tanstack/react-query";

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
const queryClient = new QueryClient();
const backendURL = "http://127.0.0.1:8000";

function App() {
  useEffect(() => {
    fetch(`${backendURL}/api/csrf/`, {
      credentials: "include",
    });
  }, []);

  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <AuthProvider>
          <NavBar />
          <Routes>
            <Route path="/" element={<Home />} />
            <Route path="/upload" element={<Upload />} />
            <Route path="/statistics" element={<Statistics />} />
            <Route path="/auth/:type" element={<Auth />} />
            <Route path="/contact" element={<Contact />} />
            <Route path="/profiles" element={<Profiles />} />
          </Routes>
        </AuthProvider>
      </BrowserRouter>
    </QueryClientProvider>
  );
}

export default App;
