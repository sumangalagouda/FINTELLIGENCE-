import { FileText } from 'lucide-react';

export default function Evidence({ evidence, selectedCase }) {
  const synthetic = selectedCase?.statements?.map((statement) => ({
    id: statement.id,
    item_type: 'statement',
    file_path: statement.filename,
    created_at: null,
  })) || [];
  const items = evidence.length ? evidence : synthetic;

  return (
    <section className="locker-grid">
      {items.map((item) => (
        <article className="locker-card" key={item.id}>
          <FileText size={24} />
          <span>{(item.item_type || 'evidence').toUpperCase()}</span>
          <strong>{item.file_path?.split(/[\\/]/).pop() || item.note_text || 'Evidence note'}</strong>
          <small>{item.created_at ? item.created_at.slice(0,10) : ''}</small>
        </article>
      ))}
      {items.length === 0 && <p className="empty-line">No evidence has been stored for this case yet.</p>}
    </section>
  );
}
