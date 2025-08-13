import { NavLink, useNavigate } from "react-router-dom";
import { MdOutlineSsidChart } from "react-icons/md";
import { useAuth } from "../contexts/AuthContext.jsx";
import { MdOutlineLogout } from "react-icons/md";
import { CgProfile } from "react-icons/cg";


export default function NavBar() {
  const { isAuthenticated, user, loading, logout } = useAuth();
  const nav = useNavigate()
  const items = [
    { name: "Upload", path: "/upload" },
    { name: "Statistics", path: "/statistics" },
  ];
  

  const handleLogout = async () => {
    try {
      await logout();
      nav("/")
    } catch (err) {
      console.error("Logout failed:", err);
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
        {isAuthenticated && items.map((item) => (
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
          <>
            <span className="font-semibold text-red-600 mr-4">
              <span className="text-black">Welcome,{" "}</span>{user.firstName}
            </span>
            <button
              onClick={handleLogout}
              className="font-semibold text-gray-700 hover:text-red-600 transition-colors duration-200"
            >
              <MdOutlineLogout className="text-lg cursor-pointer" />
            </button>
          </>
        ) : (
          <NavLink
            to="/auth/login"
            className="mr-4 font-semibold text-gray-700 hover:text-red-600 transition-colors duration-200"
          >
            <CgProfile className="text-2xl" />

          </NavLink>
        )}
      </div>
    </nav>
  );
}
