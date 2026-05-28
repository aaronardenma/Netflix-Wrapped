import { NavLink, useNavigate } from "react-router-dom";
import { MdOutlineSsidChart } from "react-icons/md";
import { MdOutlineLogout } from "react-icons/md";
import { MdOutlineManageAccounts } from "react-icons/md";
import { CgProfile } from "react-icons/cg";
import { ChevronDown } from "lucide-react";
import { useDispatch, useSelector } from "react-redux";
import { logoutUser, selectAuth } from "@/store/authSlice";


export default function NavBar() {
  const { isAuthenticated, user, loading } = useSelector(selectAuth);
  const dispatch = useDispatch();
  const nav = useNavigate()
  const items = [
    { name: "Generate", path: "/upload" },
    { name: "Statistics", path: "/statistics" },
  ];
  

  const handleLogout = async () => {
    try {
      await dispatch(logoutUser()).unwrap();
      nav("/")
    } catch (err) {
      console.error("Logout failed:", err);
      nav("/")
    }
  };

  return (
    <nav className="flex justify-between items-end p-4 bg-gray-50 shadow-md">
      <div>
        <NavLink
          to="/"
          className="font-bold text-gray-900 text-md flex items-center"
        >
          <MdOutlineSsidChart className="text-4xl mr-2" />
          <div className="flex flex-col">
            <p>Netflix </p>
            <span className="text-red-600">Wrapped</span>
          </div>
        </NavLink>
      </div>
      <div className="flex items-center space-x-4">
        {items.map((item) => (
          <NavLink
            key={item.name.toLowerCase()}
            to={{ pathname: item.path, search: "" }} // clear search params
            className="text-center font-semibold text-gray-700 hover:text-red-600 transition-colors duration-200"
          >
            {item.name}
          </NavLink>
        ))}
        </div>
      <div className="flex items-center">
        {loading ? (
          <span className="font-semibold text-gray-500">Loading...</span>
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
                className="inline-flex items-center gap-1"
              >
                <span>
                  <span className="text-black">Welcome, </span>
                  {user.firstName}
                </span>
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
                  className="flex w-full items-center gap-2 px-3 py-2 text-left text-sm font-medium text-neutral-700 hover:bg-neutral-100 hover:text-red-600"
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
