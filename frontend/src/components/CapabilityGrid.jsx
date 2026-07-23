import CapabilityCard from "./CapabilityCard";
import "../styles/capability.css";

function CapabilityGrid() {
  return (
    <section className="capability-section">

      <div className="capability-header">
        <span>CORE CAPABILITIES</span>

        <h2>Built for incident resolution.</h2>
      </div>

      <div className="capability-grid">

        <CapabilityCard
          number="01"
          title="AI Retrieval"
          description="Find relevant historical incidents using semantic vector search."
        />

        <CapabilityCard
          number="02"
          title="Knowledge Repository"
          description="Centralize enterprise documents and operational knowledge."
        />

        <CapabilityCard
          number="03"
          title="Smart Resolution"
          description="Generate grounded AI responses using retrieved context."
        />

      </div>

    </section>
  );
}

export default CapabilityGrid;