
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
          Have admin credentials? <Link to="/">Log in</Link>.{" "}
          Want to explore the full app — admin dashboard, document
          upload, analytics — yourself? There's no public sign-up, but
          you can run your own instance in a few minutes:{" "}
          <a
            href="https://github.com/vishwakarmamukul8791-code/resolveiq-platform#readme"
            target="_blank"
            rel="noopener noreferrer"
          >
            see the README
          </a>.
        </p>
      </div>
    </>
  );
}

export default Try;
