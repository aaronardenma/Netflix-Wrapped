// components/Auth.jsx
import { useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { Input } from "@/components/ui/input";
import { useDispatch, useSelector } from "react-redux";
import { authExpired, loginUser, registerUser, selectAuthLoading } from "@/store/authSlice";
import { authAPI } from "@/services/api";

function getErrorMessage(error) {
  const detail = error?.response?.data?.error || error;
  if (Array.isArray(detail)) {
    return detail.join(" ");
  }
  return typeof detail === "string" ? detail : "Request failed.";
}

export default function Auth() {
  const { type, uid, token } = useParams();
  const isLogin = type === "login";
  const isForgotPassword = type === "forgot-password";
  const isResetPassword = Boolean(uid && token);
  const isRegister = !isLogin && !isForgotPassword && !isResetPassword;
  const [message, setMessage] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const nav = useNavigate();
  const dispatch = useDispatch();
  const loading = useSelector(selectAuthLoading);
  const formDisabled = submitting;

  const handleSubmit = async (e) => {
    e.preventDefault();
    setSubmitting(true);
    setMessage("");

    const email = e.target.email?.value;
    const password = e.target.password?.value;
    const confirmPassword = e.target.confirmPassword?.value;

    // Get name fields only for registration
    const firstName = isRegister ? e.target.firstName.value : undefined;
    const lastName = isRegister ? e.target.lastName.value : undefined;

    try {
      if (isForgotPassword) {
        await authAPI.requestPasswordReset(email);
        setMessage("If an account exists for that email, a reset link has been sent.");
      } else if (isResetPassword) {
        if (password !== confirmPassword) {
          setMessage("Passwords do not match.");
          return;
        }
        await authAPI.confirmPasswordReset({ uid, token, password });
        dispatch(authExpired());
        setMessage("Password reset successful. You can now sign in.");
        setTimeout(() => nav("/auth/login"), 1200);
      } else if (isLogin) {
        await dispatch(loginUser({ email, password })).unwrap();
        nav("/");
      } else {
        await dispatch(
          registerUser({ email, password, firstName, lastName })
        ).unwrap();
        setMessage("Account created successfully.");
        nav("/");
      }
    } catch (err) {
      console.error("Request failed:", err);
      setMessage(getErrorMessage(err));
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="flex flex-col items-center p-8 md:p-16">
      <h2 className="font-semibold text-lg mb-4">
        {isForgotPassword
          ? "Reset your password"
          : isResetPassword
          ? "Choose a new password"
          : isLogin
          ? "Nice to see you again"
          : "Create your Account"}
      </h2>
      {loading && (
        <p className="mb-3 text-xs text-gray-500">
          Checking your session...
        </p>
      )}
      <div className="border p-12">
        <form className="flex flex-col" onSubmit={handleSubmit}>
          {/* Name fields - only show for registration */}
          {isRegister && (
            <>
              <div className="mb-4">
                <p className="mb-2 text-xs ml-2 text-gray-500">First Name</p>
                <Input
                  id="firstName"
                  name="firstName"
                  placeholder="First Name"
                  type="text"
                  required
                  disabled={formDisabled}
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
                  disabled={formDisabled}
                />
              </div>
            </>
          )}

          {!isResetPassword && (
            <div className="mb-4">
              <p className="mb-2 text-xs ml-2 text-gray-500">Email</p>
              <Input
                id="email"
                name="email"
                placeholder="Email"
                type="email"
                required
                disabled={formDisabled}
              />
            </div>
          )}

          {!isForgotPassword && (
            <div className="mb-4">
              <p className="mb-2 text-xs ml-2 text-gray-500">Password</p>
              <Input
                id="password"
                name="password"
                placeholder="Password"
                type="password"
                required
                disabled={formDisabled}
              />
            </div>
          )}

          {isResetPassword && (
            <div className="mb-4">
              <p className="mb-2 text-xs ml-2 text-gray-500">Confirm Password</p>
              <Input
                id="confirmPassword"
                name="confirmPassword"
                placeholder="Confirm Password"
                type="password"
                required
                disabled={formDisabled}
              />
            </div>
          )}

          <button
            className="outline w-full text-sm rounded bg-black text-white font-semibold p-2 cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed"
            type="submit"
            disabled={submitting}
          >
            {submitting
              ? "Please wait..."
              : isForgotPassword
              ? "Send reset link"
              : isResetPassword
              ? "Reset password"
              : isLogin
              ? "Sign in"
              : "Create Account"}
          </button>

          {isLogin && (
            <button
              className="mt-3 text-xs text-[#0000EE] cursor-pointer self-center underline underline-offset-2"
              type="button"
              onClick={() => nav("/auth/forgot-password")}
            >
              Forgot your password?
            </button>
          )}
        </form>

        {message && (
          <p
            className={`text-xs mt-4 ${
              message.includes("successful") ? "text-green-600" : "text-red-600"
            }`}
          >
            {message}
          </p>
        )}

        <hr className="my-4" />
        <p className="text-xs">
          {isLogin ? "Don't have an account? " : "Remember your password? "}
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
