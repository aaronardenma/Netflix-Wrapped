// components/Auth.jsx
import { useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { useAuth } from "../contexts/AuthContext";
import { Input } from "@/components/ui/input"

export default function Auth() {
  const { type } = useParams();
  const isLogin = type === "login";
  const [message, setMessage] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const nav = useNavigate();
  const { login, logout, getCSRFToken, loading } = useAuth();
  const backendURL = "http://127.0.0.1:8000";

  const handleSubmit = async (e) => {
    e.preventDefault();
    setSubmitting(true);
    setMessage("");

    const email = e.target.email.value;
    const password = e.target.password.value;
    
    // Get name fields only for registration
    const firstName = !isLogin ? e.target.firstName.value : undefined;
    const lastName = !isLogin ? e.target.lastName.value : undefined;

    try {
      const csrfToken = await getCSRFToken();

      if (!csrfToken) {
        setMessage("Failed to get CSRF token, please refresh.");
        return;
      }

      const endpoint = isLogin
        ? `${backendURL}/api/auth/login/`
        : `${backendURL}/api/auth/register/`;

      // Build request body based on login/register
      const requestBody = isLogin 
        ? { email, password }
        : { email, password, firstName, lastName };

      const res = await fetch(endpoint, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-CSRFToken": csrfToken,
        },
        credentials: "include",
        body: JSON.stringify(requestBody),
      });

      const data = await res.json();

      if (res.ok) {
        setMessage(data.message || "Success!");

        if (isLogin && data.user) {
          console.log("Login successful, user data:", data.user);
          await login(data.user);
          nav("/");
        } else if (!isLogin) {
          // For registration, you might want to auto-login or redirect to login
          setMessage("Account created successfully! Please log in.");
          setTimeout(() => nav("/auth/login"), 2000);
        }
      } else {
        setMessage(data.error || "Something went wrong.");
      }
    } catch (err) {
      console.error("Request failed:", err);
      setMessage("Request failed.");
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) {
    return <div style={{ maxWidth: 400, margin: "auto" }}>Loading...</div>;
  }

  return (
    <div className="flex flex-col items-center p-8 md:p-16">
      <h2 className="font-semibold mb-4">
        {isLogin ? "Nice to see you again" : "Create your Account"}
      </h2>
      <div className="border p-12">
        <form className="flex flex-col" onSubmit={handleSubmit}>
          {/* Name fields - only show for registration */}
          {!isLogin && (
            <>
              <div className="mb-4">
                <p className="mb-2 text-xs ml-2 text-gray-500">First Name</p>
                <Input
                  id="firstName"
                  name="firstName"
                  placeholder="First Name"
                  type="text"
                  required
                  disabled={submitting}
                />
              </div>
              <div className="mb-4">
                <p className="mb-2 text-xs ml-2 text-gray-500">Last Name</p>
                <Input
                  id="lastName"
                  name="lastName"
                  placeholder="Last Name"
                  type="text"
                  required
                  disabled={submitting}
                />
              </div>
            </>
          )}
          
          <div className="mb-4">
            <p className="mb-2 text-xs ml-2 text-gray-500">Email</p>
            <Input
              id="email"
              name="email"
              placeholder="Email"
              type="email"
              required
              disabled={submitting}
            />
          </div>
          
          <div className="mb-4">
            <p className="mb-2 text-xs ml-2 text-gray-500">Password</p>
            <Input
              id="password"
              name="password"
              placeholder="Password"
              type="password"
              required
              disabled={submitting}
            />
          </div>
          
          <button
            className="outline w-full text-sm rounded bg-black text-white font-semibold p-2 cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed"
            type="submit"
            disabled={submitting}
          >
            {submitting 
              ? "Please wait..." 
              : (isLogin ? "Sign in" : "Create Account")
            }
          </button>
        </form>
        
        {message && (
          <p className={`text-xs mt-4 ${message.includes('successful') ? 'text-green-600' : 'text-red-600'}`}>
            {message}
          </p>
        )}
        
        <hr className="my-4" />
        <p className="text-xs">
          {isLogin ? "Don't have an account? " : "Already have an account? "}
          <a
            className="text-[#0000EE] cursor-pointer"
            onClick={() => nav(isLogin ? "/auth/create" : "/auth/login")}
          >
            {isLogin ? "Sign up here" : "Log in here"}
          </a>
        </p>
      </div>
    </div>
  );
}