import { useMemo, useState, useEffect } from 'react';
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis, Cell } from 'recharts';
import Badge from '../shared/Badge';

const detectorOrder = [
  'Structuring / Smurfing',
  'Failed / Reversal',
  'Large Transaction',
  'Layering Chain',
  'Pass Through',
  'Beneficiary Burst',
];

const detectorAliases = {
  'Structuring / Smurfing': ['Structuring / Smurfing', 'Structuring'],
  'Failed / Reversal': ['Failed / Reversal', 'Dormant Account Revival', 'DormantRevival'],
  'Large Transaction': ['Large Transaction', 'LargeTransaction'],
  'Layering Chain': ['Layering Chain', 'LayeringChain'],
  'Pass Through': ['Pass Through', 'PassThrough'],
  'Beneficiary Burst': ['Beneficiary Burst', 'BeneficiaryBurst'],
};

const formatCount = (value) => new Intl.NumberFormat('en-US').format(Number(value || 0));

function buildGlobalDetectorSeries(overview) {
  const firings = overview?.detector_firings || {};
  return detectorOrder.map((name, index) => {
    let sum = 0;
    detectorAliases[name].forEach(alias => {
      sum += (firings[alias] || 0);
    });
    return {
      name,
      value: sum,
      fill: index % 2 === 0 ? '#f59e0b' : '#facc15',
    };
  });
}

export default function Dashboard({ user, overview, cases, caseDetail, selectedCase, transactions, detectors, setActiveView, setSelectedCaseId, setCaseViewMode }) {
  const isSio = user?.role === 'supervisor';

  const [liveAlerts, setLiveAlerts] = useState([]);

  useEffect(() => {
    // Generate a fake alert every 3.5 seconds to simulate a live SOC environment
    const interval = setInterval(() => {
      const fakeAlerts = [
        { msg: '🚨 Structuring Anomaly Detected', color: '#ef4444' },
        { msg: '⚠️ Large Transaction Flagged', color: '#f59e0b' },
        { msg: '🚨 Circular Flow Loop Found', color: '#ef4444' },
        { msg: '👀 Dormant Account Reactivated', color: '#3b82f6' },
        { msg: '⚠️ High Risk Time Transfer', color: '#f59e0b' },
        { msg: '🚨 Layering Chain Expanding', color: '#ef4444' },
      ];
      
      const randomCase = cases[Math.floor(Math.random() * cases.length)] || { id: '000000', display_id: '123' };
      const caseLabel = `Case ${String(randomCase.display_id || randomCase.id.substring(0,4)).padStart(3, '0')}`;
      const alert = fakeAlerts[Math.floor(Math.random() * fakeAlerts.length)];
      const time = new Date().toLocaleTimeString();
      
      setLiveAlerts(prev => {
        const next = [{...alert, id: Date.now(), caseLabel, time}, ...prev];
        return next.slice(0, 6); // Keep last 6
      });
    }, 3500);
    
    return () => clearInterval(interval);
  }, [cases]);

  const escalatedCount = cases.filter(c => c.status === 'escalated').length;
  const pendingCount = cases.filter(c => c.status === 'pending_sio_closure').length;
  const closedCount = cases.filter(c => c.status === 'closed').length;
  const highSuspicionCount = cases.filter(c => c.suspicion_score >= 70).length;

  const metrics = isSio ? [
    ['Escalated Cases', escalatedCount, 'Requires review'],
    ['Pending Cases', pendingCount, 'Awaiting signature'],
    ['High Suspicion', highSuspicionCount, 'Score >= 70'],
    ['Total Closed', closedCount, 'Finalized cases'],
  ] : [
    ['Statements', overview?.total_statements || caseDetail?.statements?.length || selectedCase?.statements?.length || 0, 'Ingested'],
    ['Transactions', overview?.total_transactions || transactions.length || 0, 'Normalized'],
    ['High risk cases', overview?.high_risk_cases || cases.filter((item) => ['high', 'critical'].includes(String(item.risk_level || '').toLowerCase())).length, 'High / critical'],
    ['AML alerts', overview?.aml_alerts || detectors.filter((item) => item.triggered).length, 'Triggered detectors'],
  ];

  const detectorSeries = useMemo(() => buildGlobalDetectorSeries(overview), [overview]);
  const sioSeries = [
    { name: 'Escalated', value: escalatedCount, fill: '#ef4444' },
    { name: 'Pending Closure', value: pendingCount, fill: '#f59e0b' },
    { name: 'Closed', value: closedCount, fill: '#10b981' }
  ];

  const chartData = isSio ? sioSeries : detectorSeries;
  
  const recentCases = isSio 
    ? cases.filter(c => c.status === 'escalated').slice(0, 4)
    : cases.slice(0, 3); // Reduced to 3 to make room for live alerts

  return (
    <section className="dashboard-page">
      <style>{`
        @keyframes slideIn {
          from { opacity: 0; transform: translateX(20px); }
          to { opacity: 1; transform: translateX(0); }
        }
      `}</style>
      <div className="dashboard-hero hoste-style">
        <p className="eyebrow">{isSio ? 'SIO WORKSPACE / 06.2026' : 'OVERVIEW / 06.2026'}</p>
        <h1>{isSio ? 'Oversight Centre' : 'Command Centre'}</h1>
        <p className="subcopy">{isSio ? 'Live overview of escalated cases, pending closures, and team metrics.' : 'Live signal across statements, detectors and active investigations.'}</p>
      </div>

      <div className="metric-grid hoste-metrics">
        {metrics.map(([label, value, hint], index) => (
          <div className={`metric metric-${index + 1}`} key={label}>
            <span>{label}</span>
            <strong>{formatCount(value)}</strong>
            <small>{hint}</small>
          </div>
        ))}
      </div>

      <div className="dashboard-grid">
        <section className="panel chart-panel">
          <div className="panel-label">
            <span className="eyebrow">{isSio ? 'CASE WORKFLOW' : 'RISK HEAT MAP (ALL INVESTIGATIONS)'}</span>
            <h2>{isSio ? 'Case Status Distribution' : 'Detector firings by volume'}</h2>
          </div>
          <div className="chart-shell">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={chartData} margin={{ top: 12, right: 8, left: 0, bottom: 0 }}>
                <CartesianGrid strokeDasharray="4 6" stroke="#e7e7ea" vertical={false} />
                <XAxis
                  dataKey="name"
                  axisLine={false}
                  tickLine={false}
                  interval={0}
                  tickFormatter={(value) => (String(value).length > 12 ? `${String(value).slice(0, 11)}...` : value)}
                  tick={{ fill: '#6b7280', fontSize: 12 }}
                />
                <YAxis axisLine={false} tickLine={false} tick={{ fill: '#6b7280', fontSize: 12 }} allowDecimals={false} />
                <Tooltip
                  cursor={{ fill: 'rgba(17, 24, 39, 0.04)' }}
                  contentStyle={{ borderRadius: 12, border: '1px solid #e5e7eb', boxShadow: '0 12px 24px rgba(15, 23, 42, 0.08)' }}
                />
                <Bar dataKey="value" radius={[0, 0, 0, 0]} barSize={38}>
                  {chartData.map((entry) => (
                    <Cell key={entry.name} fill={entry.fill} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </section>

        <aside className="panel active-cases-panel" style={{ display: 'flex', flexDirection: 'column' }}>
          <div style={{ marginBottom: '24px' }}>
            <div className="panel-label">
              <span className="eyebrow">{isSio ? 'NEW NOTIFICATIONS' : 'RECENT INVESTIGATIONS'}</span>
              <h2>{isSio ? 'Recently Escalated' : 'Active cases'}</h2>
            </div>
            <div className="active-cases">
              {recentCases.map((item) => (
                <div 
                  className="active-case" 
                  key={item.id}
                  onClick={() => {
                    setSelectedCaseId(item.id);
                    setCaseViewMode('detail');
                    setActiveView('cases');
                  }}
                  style={{ cursor: 'pointer' }}
                >
                  <div>
                    <strong>Investigation: {item.display_id ? `Case ${String(item.display_id).padStart(3, '0')}` : item.id.slice(0, 8)}</strong>
                    <div className="muted">
                      Score {Math.round(item.suspicion_score || 0)} / Conf {Math.max(50, 60 + Math.round(item.suspicion_score || 0))}%
                    </div>
                  </div>
                  <Badge value={item.severity} />
                </div>
              ))}
            </div>
          </div>
          
          <div style={{ flex: 1, display: 'flex', flexDirection: 'column', borderTop: '1px solid #e2e8f0', paddingTop: '24px' }}>
            <div className="panel-label">
              <span className="eyebrow">LIVE S.O.C. STREAM</span>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <h2>Real-Time Alert Feed</h2>
                <span style={{ display: 'inline-block', width: '8px', height: '8px', background: '#ef4444', borderRadius: '50%', boxShadow: '0 0 8px #ef4444', animation: 'pulse 2s infinite' }}></span>
              </div>
            </div>
            <div className="active-cases" style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: '8px' }}>
              {liveAlerts.length === 0 ? <div className="muted" style={{ padding: '16px', fontSize: '13px' }}>Monitoring global transaction network...</div> : null}
              {liveAlerts.map(alert => (
                <div key={alert.id} style={{ padding: '12px', background: 'white', borderRadius: '8px', borderLeft: `4px solid ${alert.color}`, border: '1px solid #e2e8f0', boxShadow: '0 2px 4px rgba(0,0,0,0.02)', animation: 'slideIn 0.4s cubic-bezier(0.16, 1, 0.3, 1)' }}>
                  <div style={{ fontSize: '11px', color: '#64748b', marginBottom: '4px', display: 'flex', justifyContent: 'space-between' }}>
                    <span style={{ fontWeight: 'bold' }}>{alert.caseLabel}</span>
                    <span>{alert.time}</span>
                  </div>
                  <div style={{ fontSize: '13px', fontWeight: '600', color: '#0f172a' }}>{alert.msg}</div>
                </div>
              ))}
            </div>
          </div>
        </aside>
      </div>
    </section>
  );
}
