import '../App.css';

export default function PageHeader({ meta, selectedCaseId, setSelectedCaseId, cases }) {
  return (
    <header className="page-header">
      <div>
        <p className="eyebrow">{meta.eyebrow}</p>
        <h1>{meta.title}</h1>
      </div>
      {cases.length > 0 && !['dashboard', 'upload'].includes(meta.id) && (
        <select value={selectedCaseId} onChange={(event) => setSelectedCaseId(event.target.value)}>
          {cases.map((item) => (
            <option key={item.id} value={item.id}>
              {item.title || `Investigation ${item.id.slice(0, 8)}`}
            </option>
          ))}
        </select>
      )}
    </header>
  );
}
