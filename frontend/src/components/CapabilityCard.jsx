function CapabilityCard({ number, title, description }) {
  return (
    <div className="capability-card">

      <span className="capability-number">
        {number}
      </span>

      <h3>{title}</h3>

      <p>{description}</p>

    </div>
  );
}

export default CapabilityCard;