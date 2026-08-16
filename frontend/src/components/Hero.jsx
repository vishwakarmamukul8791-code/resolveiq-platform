import "../styles/hero.css";

function Hero() {
  return (
    <section className="hero-section">

      <div className="hero-eyebrow">
        INCIDENT OPERATIONS · HYBRID RAG
      </div>

      <h1>
        Resolve incidents
        <span> with intelligence.</span>
      </h1>

      <p>
        A centralized AI platform that helps support engineers
        investigate incidents using historical resolutions,
        enterprise knowledge, and hybrid retrieval.
      </p>

      <div className="hero-points">

    <div>
      <strong>01</strong>
      <span>Hybrid Evidence Retrieval</span>
    </div>

    <div>
      <strong>02</strong>
      <span>Historical Resolution Intelligence</span>
    </div>

    <div>
      <strong>03</strong>
      <span>Grounded AI Resolution</span>
    </div>

    </div>

    </section>
  );
}

export default Hero;
