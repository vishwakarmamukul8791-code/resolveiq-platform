import Navbar from "../components/Navbar";
import Hero from "../components/Hero";
import LoginPanel from "../components/LoginPanel";
import PlatformStatus from "../components/PlatformStatus";
import DemoEntryCard from "../components/DemoEntryCard";
import LandingRagStory from "../components/LandingRagStory";

import "../styles/Landing.css";
import "../styles/demo-explorer.css";

function Landing() {
    return (
        <>
            <Navbar />

            <div className="landing-container">

                <div className="landing-left">

                    <Hero />

                    <PlatformStatus />

                    <LandingRagStory />

                </div>

                <div className="landing-right landing-right-stack">

                    <DemoEntryCard />

                    <LoginPanel />

                </div>

            </div>

        </>
    );
}

export default Landing;
