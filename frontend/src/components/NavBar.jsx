import { NavLink } from "react-router-dom";

export default function NavBar() {
  const items = [
    { name: "Statistics", path: "/upload" },
    // { name: "Contact", path: "/contact" },
    {name: "Login", path: "/auth"}
  ];

  const listItems = items.map((item) => (
    <li key={item.name.toLowerCase()}>
      <NavLink
        to={item.path}
        className={
             "mr-4 font-semibold text-gray-700 hover:text-red-600 transition-colors duration-200"
        }
      >
        {item.name}
      </NavLink>
    </li>
  ));

  return (
    <nav className="flex justify-between items-center p-4 bg-gray-50 shadow-md">
      <NavLink to="/" className="font-bold text-gray-900 text-xl">
        Netflix <span className="text-red-600">Wrapped</span>
      </NavLink>
      <ul className="flex space-x-4">{listItems}</ul>
    </nav>
  );
}
