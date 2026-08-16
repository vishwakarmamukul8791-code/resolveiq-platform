import "../styles/demo-explorer.css";

const STEPS = [
  ["01", "Hybrid retrieval", "BM25 and semantic search retrieve complementary incident evidence."],
  ["02", "Rank and validate", "Reciprocal Rank Fusion combines rankings before optional reranking."],
  ["03", "Confidence gate", "Weak or out-of-domain evidence is rejected before it reaches the LLM."],
  ["04", "Grounded resolution", "Gemini answers only from accepted context and returns source citations."],
];

function LandingRagStory() {
  return (
    <section className="landing-rag-story" aria-label="ResolveIQ RAG workflow">
      <div className="landing-rag-story-heading">
        <div>
          <span className="demo-eyebrow">HOW RESOLVEIQ ANSWERS</span>
          <h2>Retrieval first. Generation only when evidence is strong.</h2>
        </div>
        <span className="landing-rag-story-badge">GROUNDED BY DESIGN</span>
      </div>

      <div className="landing-rag-story-grid">
        {STEPS.map(([number, title, description]) => (
          <article key={number} className="landing-rag-story-step">
            <span>{number}</span>
            <div>
              <strong>{title}</strong>
              <p>{description}</p>
            </div>
          </article>
        ))}
      </div>

      <div className="landing-rag-proof" aria-label="Retrieval evaluation snapshot">
        <div><strong>90.5%</strong><span>Hybrid Hit@1</span></div>
        <div><strong>100%</strong><span>Hybrid Hit@5</span></div>
        <div><strong>384</strong><span>Embedding dimensions</span></div>
        <div><strong>Safe abstention</strong><span>Weak evidence stops before generation</span></div>
      </div>
    </section>
  );
}

export default LandingRagStory;
