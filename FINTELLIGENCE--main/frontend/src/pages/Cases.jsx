import { useState } from 'react';
import PanelTitle from '../shared/PanelTitle';
import Badge from '../shared/Badge';
import { FileText } from 'lucide-react';

export default function Cases({ cases, selectedCaseId, setSelectedCaseId, caseDetail, detectors, api }) {
  const [note, setNote] = useState('');
  const [message, setMessage] = useState('');

  const addNote = async () => {
    if (!note.trim() || !selectedCaseId) return;
    await api(`/evidence/${selectedCaseId}/upload`, {
      method: 'POST',
      body: (() => {
        const form = new FormData();
        form.append('item_type', 'note');
        form.append('note_text', note);
        return form;
      })(),
    });
    setNote('');
    setMessage('Investigator note added to evidence locker.');
  };

  return (
    <section className="stack">
      <div className="table-frame">
        <table>
          <thead>
            <tr>
              <th>Title</th>
              <th>Severity</th>
              <th>Suspicion</th>
              <th>Status</th>
              <th>Created</th>
            </tr>
          </thead>
          <tbody>
            {cases.map((item) => (
              <tr
                className={item.id === selectedCaseId ? 'selected-row' : ''}
                key={item.id}
                onClick={() => setSelectedCaseId(item.id)}
              >
                <td>Investigation: {item.id.slice(0, 8)}</td>
                <td><Badge value={item.severity} /></td>
                <td>{item.suspicion_score || caseDetail?.suspicion_score || '-'}</td>
                <td>{item.status}</td>
                <td>{caseDetail?.created_at ? caseDetail.created_at.slice(0,10) : '-'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {caseDetail && (
        <div className="panel">
          <div className="case-detail-head">
            <div>
              <p className="eyebrow">CASE / {caseDetail.id.slice(0, 8)}</p>
              <h2>Investigation: {caseDetail.id.slice(0, 8)}</h2>
              <p>{caseDetail.statements?.[0]?.filename || 'No statement attached yet'}</p>
            </div>
            <Badge value={caseDetail.severity} />
          </div>
          <div className="metric-grid four">
            <div className="metric"><span>Suspicion</span><strong>{caseDetail.suspicion_score || 0}</strong></div>
            <div className="metric"><span>Risk</span><strong>{caseDetail.risk_level || 'low'}</strong></div>
            <div className="metric"><span>Statements</span><strong>{caseDetail.statements?.length || 0}</strong></div>
            <div className="metric"><span>Triggered</span><strong>{detectors.filter((item) => item.triggered).length}</strong></div>
          </div>
          <p className="summary-copy">
            This investigation workspace consolidates statement evidence, transaction patterns, detector output, and fund-flow context for analyst review.
          </p>
        </div>
      )}
      <div className="panel">
        <PanelTitle icon={FileText} title="Investigator notes" />
        <div className="note-row">
          <input value={note} onChange={(event) => setNote(event.target.value)} placeholder="Add a note..." />
          <button className="dark-button" onClick={addNote} type="button">Add</button>
        </div>
        {message && <p className="muted">{message}</p>}
      </div>
    </section>
  );
}
