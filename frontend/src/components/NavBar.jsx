import NavItem from "./NavItem"
import { NavLink } from "react-router-dom"


function NavBar() {

    const navBarItems = [
        {name: "Home", path: "/"},
        {name: "Statistics", path: "/statistics"},
        {name: "Contact", path: "/contact"},];

    const listItems = navBarItems.map(item => <NavItem name={item.name} key={item.name.toLowerCase()}
                                                        path={item.path} />)

    return (
        <nav>
            <NavLink to="/" className={("logo--text nav__link")}>Netflix <span style={{ fontStyle: 'normal', fontWeight: '400' }}>Wrapped</span></NavLink>
            
                <ul className="nav__link--list">
                    {listItems}
                </ul>
        </nav>
    )
}

export default NavBar