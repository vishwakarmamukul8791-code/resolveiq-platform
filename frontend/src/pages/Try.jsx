// frontend/src/pages/Try.jsx
//
// Public, no-login page for people evaluating the product without a
// shared demo account — e.g. linked directly from a LinkedIn post.

import { Link } from "react-router";
import Navbar from "../components/Navbar";
import GuestWorkspace from "../components/GuestWorkspace";
import "../styles/try-page.css";

function Try() {
  return (
    <>
      <Navbar />

      <div className="try-page-container">
        <GuestWorkspace />

        <p className="try-page-footer">
          Want full access, saved history, and admin tools?{" "}
          <Link to="/">Log in or create an account</Link>
        </p>
      </div>
    </>
  );
}

export default Try;
