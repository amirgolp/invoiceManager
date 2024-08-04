import { Link } from 'react-router-dom'
import ThemeToggle from '../ThemeToggle'

const Navbar = () => (
  <nav>
    <Link to="/">Home</Link>
    <Link to="/chat">Chat</Link>
    <Link to="/profile">Profile</Link>
    <ThemeToggle />
  </nav>
)

export default Navbar
