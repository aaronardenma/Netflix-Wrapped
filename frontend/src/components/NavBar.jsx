import { NavLink, useLocation, useNavigate } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { MdOutlineSsidChart } from "react-icons/md";
import { MdOutlineLogout } from "react-icons/md";
import { MdOutlineManageAccounts } from "react-icons/md";
import { CgProfile } from "react-icons/cg";
import { ChartNoAxesCombined, ChevronDown, Plus } from "lucide-react";
import { useDispatch, useSelector } from "react-redux";
import { logoutUser, selectAuth } from "@/store/authSlice";
import { netflixAPI } from "@/services/api";

const SESSION_UPLOAD_KEY = "netflixWrapped:lastAnonymousUpload";

export default function NavBar() {
  const { isAuthenticated, user, loading } = useSelector(selectAuth);
  const dispatch = useDispatch();
  const nav = useNavigate();
  const location = useLocation();
  const { data: storedData } = useQuery({
    queryKey: ["storedData"],
    queryFn: async () => {
      const response = await netflixAPI.getStoredData();
      return response.data;
    },
    enabled: !loading && isAuthenticated,
  });

  let hasAnonymousRecap = false;
  try {
    const session = JSON.parse(
      (location.pathname && sessionStorage.getItem(SESSION_UPLOAD_KEY)) || "null",
    );
    const hasProfiles = Object.keys(session?.profileYears || {}).length > 0;
    const isExpired = session?.expiresAt
      ? new Date(session.expiresAt).getTime() <= Date.now()
      : false;
    hasAnonymousRecap = hasProfiles && !isExpired;
  } catch {
    hasAnonymousRecap = false;
  }

  const hasSavedData =
    isAuthenticated && Object.keys(storedData || {}).length > 0;
  const hasResults = hasSavedData || hasAnonymousRecap;

  const handleLogout = async () => {
    try {
      await dispatch(logoutUser()).unwrap();
      nav("/");
    } catch (err) {
      console.error("Logout failed:", err);
      nav("/");
    }
  };

  return (
    <nav className="grid grid-cols-[1fr_auto_1fr] items-center gap-3 bg-gray-50 px-4 py-3 shadow-md sm:px-6">
      <div className="min-w-0">
        <NavLink
          to="/"
          className="flex w-fit items-center font-bold text-gray-900"
        >
          <MdOutlineSsidChart className="mr-2 shrink-0 text-4xl" />
          <div className="hidden flex-col leading-tight sm:flex">
            <p>Netflix</p>
            <span className="text-red-600">Wrapped</span>
          </div>
        </NavLink>
      </div>
      <div className="flex items-center gap-2">
        <NavLink
          to={{ pathname: "/create", search: "" }}
          className={({ isActive }) =>
            `inline-flex h-10 items-center gap-2 border px-3 text-sm font-bold transition-colors sm:px-4 ${
              isActive
                ? "border-red-600 bg-red-600 text-white"
                : "border-neutral-900 bg-neutral-900 text-white hover:border-red-600 hover:bg-red-600 transition duration-300"
            }`
          }
        >
          <Plus className="h-4 w-4" aria-hidden="true" />
          <span className="hidden sm:inline">New Recap</span>
          <span className="sm:hidden">New</span>
        </NavLink>
        {hasResults && (
          <NavLink
            to={{ pathname: "/recap", search: "" }}
            aria-label="View results"
            title="View results"
            className={({ isActive }) =>
              `inline-flex h-10 w-10 items-center justify-center border transition-colors ${
                isActive
                  ? "border-red-600 bg-red-600 text-white"
                  : "border-neutral-300 bg-white text-neutral-700 hover:border-red-600 hover:text-red-600"
              }`
            }
          >
            <ChartNoAxesCombined className="h-5 w-5" aria-hidden="true" />
          </NavLink>
        )}
      </div>
      <div className="flex min-w-0 items-center justify-end">
        {loading ? (
          <span className="hidden font-semibold text-gray-500 sm:inline">
            Loading...
          </span>
        ) : isAuthenticated && user ? (
          <div className="flex items-center gap-3">
            <NavLink
              to="/profile"
              className="mr-1 font-semibold text-gray-700 hover:text-red-600 transition-colors duration-200"
              title="Profile"
            >
              {!isAuthenticated && !user && <CgProfile className="text-2xl" />}
            </NavLink>
            <div className="relative group flex items-center font-semibold text-red-600 transition-colors duration-200">
              <button
                type="button"
                className="inline-flex items-center gap-1 cursor-pointer"
              >
                <span className="hidden md:inline">
                  <span className="text-black">Welcome, </span>
                  {user.firstName}
                </span>
                <CgProfile className="text-2xl md:hidden" />
                <ChevronDown className="h-3 w-3 text-neutral-700" />
              </button>
              <div className="invisible absolute right-0 top-full z-20 mt-2 min-w-44 border border-neutral-200 bg-white p-2 opacity-0 shadow-lg transition-all duration-150 group-hover:visible group-hover:opacity-100">
                <NavLink
                  to="/profile"
                  className="flex items-center gap-2 px-3 py-2 text-sm font-medium text-neutral-700 hover:bg-neutral-100 hover:text-red-600"
                >
                  <MdOutlineManageAccounts className="text-lg" />
                  Account
                </NavLink>
                <button
                  onClick={handleLogout}
                  className="flex w-full cursor-pointer items-center gap-2 px-3 py-2 text-left text-sm font-medium text-neutral-700 hover:bg-neutral-100 hover:text-red-600"
                >
                  <MdOutlineLogout className="text-lg" />
                  Logout
                </button>
              </div>
            </div>
          </div>
        ) : (
          <NavLink
            to="/auth/login"
            className="mr-4 font-semibold text-gray-700 hover:text-red-600 transition-colors duration-200"
            title="Sign in"
          >
            <CgProfile className="text-2xl" />
          </NavLink>
        )}
      </div>
    </nav>
  );
}
