import Navbar from "../components/Navbar";
import Hero from "../components/Hero";
import LoginPanel from "../components/LoginPanel";
import PlatformStatus from "../components/PlatformStatus";
import CapabilityGrid from "../components/CapabilityGrid";

import "../styles/landing.css";

function Landing() {
    return (
        <>
            <Navbar />

            <div className="landing-container">

                <div className="landing-left">

                    <Hero />

                    <PlatformStatus />

                </div>

                <div className="landing-right">

                    <LoginPanel />

                </div>

            </div>

            <CapabilityGrid />

        </>
    );
}

export default Landing;