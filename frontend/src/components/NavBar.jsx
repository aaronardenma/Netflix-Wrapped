import { NavLink } from "react-router-dom";
import { MdOutlineSsidChart } from "react-icons/md";
import { useAuth } from '../contexts/AuthContext.jsx';

export default function NavBar() {
  const { isAuthenticated, user, loading, logout } = useAuth();

  const items = [
    { name: "Statistics", path: "/upload" },
  ];

  const handleLogout = async () => {
    try {
      await logout();
      // optionally, you can navigate to home or login page here
    } catch (err) {
      console.error('Logout failed:', err);
    }
  };

  return (
    <nav className="flex justify-between items-end p-4 bg-gray-50 shadow-md">
      <div>
        <NavLink to="/" className="font-bold text-gray-900 text-md flex items-center">
          <MdOutlineSsidChart className="text-4xl mr-2" />
          <div className="flex flex-col">
            <p>Netflix </p>
            <span className="text-red-600">Wrapped</span>
          </div>
        </NavLink>
      </div>
      <div className="flex items-center">
        {items.map((item) => (
          <NavLink
            key={item.name.toLowerCase()}
            to={item.path}
            className="mr-4 font-semibold text-gray-700 hover:text-red-600 transition-colors duration-200"
          >
            {item.name}
          </NavLink>
        ))}

        {loading ? (
          <span className="font-semibold text-gray-500">Loading...</span>
        ) : isAuthenticated && user ? (
          <>
            <span className="font-semibold text-green-600 mr-4">Welcome, {user.firstName}</span>
            <button
              onClick={handleLogout}
              className="font-semibold text-gray-700 hover:text-red-600 transition-colors duration-200"
            >
              Logout
            </button>
          </>
        ) : (
          <NavLink
            to="/auth/login"
            className="mr-4 font-semibold text-gray-700 hover:text-red-600 transition-colors duration-200"
          >
            Login
          </NavLink>
        )}
      </div>
    </nav>
  );
}
