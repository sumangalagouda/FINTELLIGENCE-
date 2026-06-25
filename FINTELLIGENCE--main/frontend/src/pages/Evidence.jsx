import { useState } from 'react';
import { FileText, Download, Trash2, Folder } from 'lucide-react';

export default function Evidence({ cases = [], evidence, selectedCase, api, setEvidence, selectedCaseId, setSelectedCaseId }) {
  const items = evidence || [];

  const handleDownload = async (item) => {
    if (!api) return;
    try {
      const blob = await api(`/evidence/${item.id}/download`);

      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;

      const filename = item.file_path ? item.file_path.split(/[\\/]/).pop() : 'download';
      a.download = filename;

      document.body.appendChild(a);
      a.click();

      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch (err) {
      console.error('Download failed:', err);
      alert('Failed to download the file.');
    }
  };

  const handleDelete = async (item) => {
    if (!api || !setEvidence) return;
    if (!window.confirm('Are you sure you want to delete this evidence?')) return;
    try {
      await api(`/evidence/${item.id}`, { method: 'DELETE' });
      setEvidence(prev => prev.filter(e => e.id !== item.id));
    } catch (err) {
      console.error(err);
    }
  };

  return (
    <section className="stack">
      <div style={{ marginBottom: '16px' }}>
        <h2 style={{ fontSize: '20px', fontWeight: 'bold', color: '#0f172a', margin: 0 }}>
          Evidence Locker
        </h2>
        <p style={{ color: '#64748b', margin: '4px 0 0 0', fontSize: '14px' }}>
          {selectedCase?.display_id ? `Case ${String(selectedCase.display_id).padStart(3, '0')}` : `Case ${selectedCaseId?.slice(0, 8)}`}
        </p>
      </div>

      <div className="locker-grid" style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))', gap: '16px' }}>
        {items.map((item) => (
          <article className="locker-card" key={item.id} style={{ border: '1px solid #d1d5db', borderRadius: '8px', padding: '16px', display: 'flex', flexDirection: 'column', gap: '8px', background: 'white' }}>
            <FileText size={24} style={{ color: '#3b82f6' }} />
            <span style={{ fontSize: '12px', fontWeight: 'bold', color: '#64748b' }}>{(item.item_type || 'evidence').toUpperCase()}</span>
            <strong style={{ whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{item.file_path?.split(/[\\/]/).pop() || item.note_text || 'Evidence note'}</strong>
            <small style={{ color: '#94a3b8' }}>{item.created_at ? item.created_at.slice(0, 10) : ''}</small>

            <div style={{ display: 'flex', gap: '8px', marginTop: '12px' }}>
              <button onClick={() => handleDownload(item)} style={{ padding: '6px 12px', border: '1px solid #e2e8f0', borderRadius: '4px', background: 'white', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '4px', color: '#334155' }}>
                <Download size={14} /> Download
              </button>
              <button onClick={() => handleDelete(item)} style={{ padding: '6px 12px', border: '1px solid #fca5a5', borderRadius: '4px', background: '#fef2f2', color: '#dc2626', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '4px' }}>
                <Trash2 size={14} /> Delete
              </button>
            </div>
          </article>
        ))}
        {items.length === 0 && (
          <div style={{ gridColumn: '1 / -1', padding: '48px', textAlign: 'center', background: 'white', borderRadius: '12px', border: '1px dashed #cbd5e1' }}>
            <FileText size={48} color="#cbd5e1" style={{ margin: '0 auto 16px auto' }} />
            <p style={{ color: '#64748b', fontSize: '15px', margin: 0 }}>No evidence has been stored for this case yet.</p>
          </div>
        )}
      </div>
    </section>
  );
}
