import { useNavigate } from "react-router";

import "../styles/not-found.css";


function NotFound() {

    const navigate = useNavigate();


    return (

        <div className="not-found-page">

            <div className="not-found-card">

                <span className="not-found-code">
                    404
                </span>

                <h1>
                    Page not found.
                </h1>

                <p>
                    The workspace you're looking for doesn't exist or has been moved.
                </p>

                <button
                    onClick={() => navigate("/")}
                >
                    Return to workspace
                </button>

            </div>

        </div>

    );

}

export default NotFound;