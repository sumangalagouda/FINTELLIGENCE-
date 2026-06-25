import '../App.css';

export default function PageHeader({ user, meta, cases, caseFilter, setCaseFilter }) {
  const isSio = user?.role === 'supervisor';

  return (
    <header className="page-header">
      <div>
        <p className="eyebrow">{meta.eyebrow}</p>
        <h1>{meta.title}</h1>
      </div>
      {cases.length > 0 && isSio && !['dashboard', 'sio-dashboard', 'upload', 'escalations'].includes(meta.id) && (
        <div style={{ display: 'flex', gap: '8px' }}>
          <select value={caseFilter} onChange={(e) => {
            setCaseFilter(e.target.value);
          }}>
            <option value="all">All SIO Cases</option>
            <option value="escalated">Escalated</option>
            <option value="pending_sio_closure">Pending Closure</option>
            <option value="closed">Closed</option>
          </select>
        </div>
      )}
    </header>
  );
}
