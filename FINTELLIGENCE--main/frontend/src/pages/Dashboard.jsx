import { useMemo } from 'react';
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
  'Failed / Reversal': ['Failed / Reversal', 'Dormant Account Revival'],
  'Large Transaction': ['Large Transaction'],
  'Layering Chain': ['Layering Chain'],
  'Pass Through': ['Pass Through'],
  'Beneficiary Burst': ['Beneficiary Burst'],
};

const formatCount = (value) => new Intl.NumberFormat('en-US').format(Number(value || 0));

function buildDetectorSeries(detectors) {
  return detectorOrder.map((name, index) => {
    const item = detectors.find((entry) => detectorAliases[name].includes(entry.name));
    const raw = Number(item?.score || 0);
    const value = item?.triggered ? Math.max(1, Math.min(4, Math.round(raw / 25) || 1)) : 0;

    return {
      name,
      value,
      fill: index % 2 === 0 ? '#f59e0b' : '#facc15',
    };
  });
}

export default function Dashboard({ overview, cases, caseDetail, selectedCase, transactions, detectors }) {
  const metrics = [
    ['Statements', overview?.total_statements || caseDetail?.statements?.length || selectedCase?.statements?.length || 0, 'Ingested'],
    ['Transactions', overview?.total_transactions || transactions.length || 0, 'Normalized'],
    ['High risk cases', overview?.high_risk_cases || cases.filter((item) => ['high', 'critical'].includes(String(item.risk_level || '').toLowerCase())).length, 'High / critical'],
    ['AML alerts', overview?.aml_alerts || detectors.filter((item) => item.triggered).length, 'Triggered detectors'],
  ];

  const detectorSeries = useMemo(() => buildDetectorSeries(detectors), [detectors]);
  const recentCases = cases.slice(0, 4);

  return (
    <section className="dashboard-page">
      <div className="dashboard-hero hoste-style">
        <p className="eyebrow">OVERVIEW / 06.2026</p>
        <h1>Command Centre</h1>
        <p className="subcopy">Live signal across statements, detectors and active investigations.</p>
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
            <span className="eyebrow">RISK HEAT MAP</span>
            <h2>Detector firings by severity</h2>
          </div>
          <div className="chart-shell">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={detectorSeries} margin={{ top: 12, right: 8, left: 0, bottom: 0 }}>
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
                  {detectorSeries.map((entry) => (
                    <Cell key={entry.name} fill={entry.fill} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </section>

        <aside className="panel active-cases-panel">
          <div className="panel-label">
            <span className="eyebrow">RECENT INVESTIGATIONS</span>
            <h2>Active cases</h2>
          </div>
          <div className="active-cases">
            {recentCases.map((item) => (
              <div className="active-case" key={item.id}>
                <div>
                  <strong>Investigation: {item.id.slice(0, 8)}</strong>
                  <div className="muted">
                    Score {Math.round(item.suspicion_score || 0)} / Conf {Math.max(50, 60 + Math.round(item.suspicion_score || 0))}%
                  </div>
                </div>
                <Badge value={item.severity} />
              </div>
            ))}
          </div>
        </aside>
      </div>
    </section>
  );
}
