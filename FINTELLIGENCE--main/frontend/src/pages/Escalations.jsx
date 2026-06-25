import { useState, useEffect } from 'react';
import { AlertCircle, FileText, CheckCircle, XCircle } from 'lucide-react';
import Badge from '../shared/Badge';

export default function Escalations({ api, setSelectedCaseId, setActiveView, setCaseViewMode }) {
  const [escalations, setEscalations] = useState([]);
  const [loading, setLoading] = useState(true);

  const fetchEscalations = async () => {
    setLoading(true);
    try {
      const data = await api('/escalations');
      setEscalations(data || []);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchEscalations();
  }, [api]);

  const pendingEscalations = escalations.filter(e => e.status === 'pending');
  const resolvedEscalations = escalations.filter(e => e.status !== 'pending');

  return (
    <section className="dashboard-grid">
      <header className="dashboard-header" style={{ gridColumn: '1 / -1' }}>
        <div>
          <h1 style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <AlertCircle className="brand-accent" size={28} />
            Escalation Queue
          </h1>
          <p className="subcopy">Review and process cases escalated by investigators</p>
        </div>
      </header>

      {/* Main List */}
      <div className="table-frame" style={{ gridColumn: '1 / -1' }}>
        <div style={{ padding: '16px 20px', borderBottom: '1px solid var(--line)', background: '#f9fafb' }}>
          <h3 style={{ margin: 0, fontSize: '15px' }}>Pending Escalations ({pendingEscalations.length})</h3>
        </div>
        <table>
          <thead>
            <tr>
              <th>Date</th>
              <th>Case ID</th>
              <th>Investigator ID</th>
              <th>Status</th>
              <th>Action</th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr><td colSpan={5} style={{ textAlign: 'center', padding: '24px' }}>Loading...</td></tr>
            ) : pendingEscalations.map((esc) => (
              <tr key={esc.id}>
                <td>{new Date(esc.created_at).toLocaleDateString()}</td>
                <td><code style={{ fontSize: '12px' }}>{esc.case_id.substring(0, 8)}</code></td>
                <td>{esc.escalated_by.substring(0, 8)}</td>
                <td><Badge value="pending" /></td>
                <td>
                  <button className="secondary-button" style={{ padding: '4px 12px', fontSize: '12px' }} onClick={() => {
                    setSelectedCaseId(esc.case_id);
                    if (setCaseViewMode) setCaseViewMode('detail');
                    setActiveView('cases');
                  }}>Review</button>
                </td>
              </tr>
            ))}
            {!loading && pendingEscalations.length === 0 && (
              <tr><td colSpan={5} style={{ textAlign: 'center', padding: '24px' }}>No pending escalations. All caught up!</td></tr>
            )}
          </tbody>
        </table>
      </div>

      <div className="table-frame" style={{ gridColumn: '1 / -1', marginTop: '24px', opacity: 0.7 }}>
        <div style={{ padding: '16px 20px', borderBottom: '1px solid var(--line)', background: '#f9fafb' }}>
          <h3 style={{ margin: 0, fontSize: '15px' }}>Resolved Escalations</h3>
        </div>
        <table>
          <thead>
            <tr>
              <th>Date Resolved</th>
              <th>Case ID</th>
              <th>Decision</th>
              <th>Notes</th>
            </tr>
          </thead>
          <tbody>
            {resolvedEscalations.map((esc) => (
              <tr key={esc.id}>
                <td>{new Date(esc.resolved_at).toLocaleDateString()}</td>
                <td><code style={{ fontSize: '12px' }}>{esc.case_id.substring(0, 8)}</code></td>
                <td>
                  <span style={{ display: 'flex', alignItems: 'center', gap: '6px', color: esc.fir_recommended ? '#047857' : '#b91c1c' }}>
                    {esc.fir_recommended ? <CheckCircle size={14} /> : <XCircle size={14} />}
                    {esc.fir_recommended ? 'FIR Recommended' : 'Case Closed'}
                  </span>
                </td>
                <td style={{ maxWidth: '300px', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }} title={esc.reviewer_notes}>
                  {esc.reviewer_notes}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
