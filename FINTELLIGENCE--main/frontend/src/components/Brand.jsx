import '../App.css';

export default function Brand({ compact = false }) {
  return (
    <div className={compact ? 'brand compact' : 'brand'}>
      <span className="brand-mark">F</span>
      <strong>FINTELLIGENCE</strong>
      {!compact && <small>FORENSIC INTEL / V1.0</small>}
    </div>
  );
}
