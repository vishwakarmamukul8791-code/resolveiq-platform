import { Link } from "react-router-dom";
function Navbar(){
  return(
    <nav>
  <Link to="/">Home</Link>
  <Link to="/Admin">Admin</Link>
  <Link to="/Support">Support</Link>
</nav>
  )
}
export default Navbar;
