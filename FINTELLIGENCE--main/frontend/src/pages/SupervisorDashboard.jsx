import { useState, useEffect } from 'react';
import { Shield, Activity, Users, AlertTriangle, ArrowUpRight } from 'lucide-react';
import Badge from '../shared/Badge';

export default function SupervisorDashboard({ api }) {
  const [metrics, setMetrics] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let alive = true;
    api('/governance/accountability-dashboard')
      .then(data => {
        if (alive) {
          setMetrics(data || []);
          setLoading(false);
        }
      })
      .catch(err => {
        console.error(err);
        if (alive) setLoading(false);
      });
    return () => { alive = false; };
  }, [api]);

  return (
    <section className="dashboard-grid">
      <header className="dashboard-header" style={{ gridColumn: '1 / -1' }}>
        <div>
          <h1 style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <Shield className="brand-accent" size={28} />
            Command Centre: Reviewer & Supervisor
          </h1>
          <p className="subcopy">Oversight and Accountability Metrics for Investigation Teams</p>
        </div>
      </header>

      <div className="metric-grid" style={{ gridColumn: '1 / -1' }}>
        <div className="metric-card">
          <Activity className="muted" />
          <p>Total Investigators</p>
          <h2>{metrics.length}</h2>
        </div>
        <div className="metric-card">
          <Users className="muted" />
          <p>Active Cases</p>
          <h2>{metrics.reduce((acc, m) => acc + (m.total_assigned - m.cases_closed), 0)}</h2>
        </div>
        <div className="metric-card" style={{ borderColor: 'var(--danger-border)', background: '#fef2f2' }}>
          <AlertTriangle color="var(--danger)" />
          <p>Pending Escalations</p>
          <h2>{metrics.reduce((acc, m) => acc + m.cases_escalated, 0)}</h2>
        </div>
      </div>

      <div className="table-frame" style={{ gridColumn: '1 / -1' }}>
        <div style={{ padding: '16px 20px', borderBottom: '1px solid var(--line)', background: '#f9fafb' }}>
          <h3 style={{ margin: 0, fontSize: '15px' }}>Investigator Accountability</h3>
        </div>
        <table>
          <thead>
            <tr>
              <th>Investigator</th>
              <th>Assigned</th>
              <th>Closed</th>
              <th>Escalated</th>
              <th>AI Overrides</th>
              <th>Risk Score</th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr><td colSpan={6} style={{ textAlign: 'center', padding: '24px' }}>Loading metrics...</td></tr>
            ) : metrics.map((inv) => (
              <tr key={inv.user_id}>
                <td>
                  <strong>{inv.name}</strong>
                  <div className="muted" style={{ fontSize: '12px' }}>{inv.email}</div>
                </td>
                <td>{inv.total_assigned}</td>
                <td>{inv.cases_closed}</td>
                <td>{inv.cases_escalated}</td>
                <td>
                  <span style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                    {inv.ai_override_events}
                    {inv.ai_override_events > 0 && <ArrowUpRight size={14} color="var(--danger)" />}
                  </span>
                </td>
                <td>
                  <Badge value={inv.investigator_risk_score > 30 ? 'high' : inv.investigator_risk_score > 10 ? 'medium' : 'low'} />
                </td>
              </tr>
            ))}
            {!loading && metrics.length === 0 && (
              <tr><td colSpan={6} style={{ textAlign: 'center', padding: '24px' }}>No investigator metrics available.</td></tr>
            )}
          </tbody>
        </table>
      </div>
    </section>
  );
}
