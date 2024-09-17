import { NavLink } from "react-router-dom"

function NavItem({name, path}) {
    return (
        <li className={("nav__link link__hover-effect link__hover-effect--white")}>
            <NavLink to = {path} className="nav__link--anchor">{name}</NavLink>
        </li>
    )
}

export default NavItem