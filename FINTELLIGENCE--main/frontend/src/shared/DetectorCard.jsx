import { useState } from 'react';
import Badge from './Badge';
import { ChevronDown, ChevronUp, AlertTriangle, Hash, Calendar, DollarSign, FileText } from 'lucide-react';

export default function DetectorCard({ item }) {
  const [isExpanded, setIsExpanded] = useState(false);

  // Filter out massive arrays from metadata like cycle or chain
  const renderableMetadata = item.metadata 
    ? Object.entries(item.metadata).filter(([k]) => k !== 'cycle' && k !== 'chain' && k !== 'anomalies')
    : [];

  return (
    <article 
      className="detector-card" 
      onClick={() => setIsExpanded(!isExpanded)}
      style={{ 
        cursor: 'pointer', 
        display: 'flex', 
        flexDirection: 'column', 
        gap: '16px',
        background: isExpanded ? '#ffffff' : '#fafafa',
        border: isExpanded ? '1px solid #cbd5e1' : '1px solid transparent',
        boxShadow: isExpanded ? '0 10px 25px -5px rgba(0, 0, 0, 0.05), 0 8px 10px -6px rgba(0, 0, 0, 0.01)' : 'none',
        transition: 'all 0.2s ease-in-out'
      }}
    >
      <div style={{ display: 'flex', justifyContent: 'space-between', width: '100%', alignItems: 'flex-start' }}>
        <div style={{ flex: 1 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            {item.severity === 'high' || item.severity === 'critical' ? (
              <AlertTriangle size={18} color="#ef4444" />
            ) : null}
            <strong style={{ fontSize: '1.1rem', color: '#0f172a' }}>{item.name}</strong>
            {isExpanded ? <ChevronUp size={18} color="#94a3b8" /> : <ChevronDown size={18} color="#94a3b8" />}
          </div>
          <p style={{ color: '#475569', marginTop: '6px', fontSize: '0.95rem', lineHeight: '1.4' }}>
            {item.reason || 'Potential suspicious activity detected.'}
          </p>
        </div>
        <div className="score-stack" style={{ textAlign: 'right', marginLeft: '16px' }}>
          <Badge value={item.severity || 'medium'} />
          <span style={{ display: 'block', marginTop: '6px', fontSize: '0.85rem', fontWeight: '600', color: '#64748b' }}>
            SCORE: <span style={{ color: '#0f172a', fontSize: '1rem' }}>{Math.round(item.score || 0)}</span>
          </span>
        </div>
      </div>
      
      {isExpanded && (
        <div className="detector-evidence" style={{ borderTop: '1px solid #e2e8f0', paddingTop: '20px', fontSize: '14px', animation: 'fadeIn 0.3s ease-in-out' }}>
          {renderableMetadata.length > 0 && (
            <div style={{ marginBottom: '24px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginBottom: '12px' }}>
                <Hash size={16} color="#6366f1" />
                <span style={{ fontSize: '0.8rem', fontWeight: '700', letterSpacing: '0.05em', color: '#475569', textTransform: 'uppercase' }}>
                  Detection Metadata
                </span>
              </div>
              
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(160px, 1fr))', gap: '12px' }}>
                {renderableMetadata.map(([k, v]) => (
                  <div key={k} style={{ 
                    background: '#f8fafc', 
                    border: '1px solid #e2e8f0', 
                    borderRadius: '8px', 
                    padding: '12px 16px',
                    borderLeft: '3px solid #6366f1'
                  }}>
                    <div style={{ fontSize: '0.75rem', textTransform: 'uppercase', color: '#64748b', fontWeight: '600', letterSpacing: '0.05em', marginBottom: '4px' }}>
                      {k.replace(/_/g, ' ')}
                    </div>
                    <div style={{ fontSize: '1rem', color: '#0f172a', fontWeight: '600', wordBreak: 'break-word' }}>
                      {typeof v === 'number' ? (v % 1 !== 0 ? v.toFixed(2) : v) : String(v)}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {item.transactions_involved && item.transactions_involved.length > 0 && (
            <div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginBottom: '12px' }}>
                <FileText size={16} color="#ef4444" />
                <span style={{ fontSize: '0.8rem', fontWeight: '700', letterSpacing: '0.05em', color: '#475569', textTransform: 'uppercase' }}>
                  Flagged Transactions ({item.transactions_involved.length})
                </span>
              </div>
              
              <div style={{ 
                maxHeight: '240px', 
                overflowY: 'auto', 
                border: '1px solid #e2e8f0', 
                borderRadius: '8px',
                boxShadow: 'inset 0 2px 4px 0 rgba(0, 0, 0, 0.02)'
              }}>
                <table style={{ width: '100%', fontSize: '0.85rem', borderCollapse: 'collapse' }}>
                  <thead style={{ background: '#f1f5f9', position: 'sticky', top: 0, zIndex: 1 }}>
                    <tr>
                      <th style={{ padding: '10px 16px', borderBottom: '1px solid #e2e8f0', color: '#475569', fontWeight: '600', textAlign: 'left' }}>
                        <div style={{display: 'flex', alignItems: 'center', gap: '4px'}}><Calendar size={14}/> Date/ID</div>
                      </th>
                      <th style={{ padding: '10px 16px', borderBottom: '1px solid #e2e8f0', color: '#475569', fontWeight: '600', textAlign: 'left' }}>
                        <div style={{display: 'flex', alignItems: 'center', gap: '4px'}}><DollarSign size={14}/> Amount</div>
                      </th>
                      <th style={{ padding: '10px 16px', borderBottom: '1px solid #e2e8f0', color: '#475569', fontWeight: '600', textAlign: 'left' }}>
                        Description
                      </th>
                    </tr>
                  </thead>
                  <tbody>
                    {item.transactions_involved.map((tx, idx) => {
                      // Handle case where tx is just an ID (string/number) rather than an object
                      const isObj = typeof tx === 'object' && tx !== null;
                      const dateOrId = isObj ? (tx.date || tx.Date || tx.id) : tx;
                      const amount = isObj ? (tx.amount || tx.Amount || '-') : '-';
                      const desc = isObj ? (tx.description || tx.Description || '-') : 'Transaction ID reference';

                      return (
                        <tr key={idx} style={{ borderBottom: '1px solid #e2e8f0', background: '#ffffff', transition: 'background 0.15s ease' }} className="table-row-hover">
                          <td style={{ padding: '10px 16px', whiteSpace: 'nowrap', color: '#0f172a', fontWeight: '500' }}>
                            {dateOrId}
                          </td>
                          <td style={{ padding: '10px 16px', whiteSpace: 'nowrap', color: '#ef4444', fontWeight: '700' }}>
                            {amount !== '-' && !String(amount).startsWith('$') && !String(amount).startsWith('₹') ? `$${amount}` : amount}
                          </td>
                          <td style={{ padding: '10px 16px', color: '#475569' }}>{desc}</td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </div>
          )}
          
          {(!item.transactions_involved || item.transactions_involved.length === 0) && (!renderableMetadata || renderableMetadata.length === 0) && (
            <div style={{ background: '#f8fafc', border: '1px dashed #cbd5e1', borderRadius: '8px', padding: '24px', textAlign: 'center' }}>
              <p style={{ margin: 0, color: '#64748b', fontSize: '0.9rem' }}>No detailed evidence payload provided by this detector.</p>
            </div>
          )}
        </div>
      )}
      
      <style>{`
        .table-row-hover:hover {
          background-color: #f8fafc !important;
        }
        @keyframes fadeIn {
          from { opacity: 0; transform: translateY(-4px); }
          to { opacity: 1; transform: translateY(0); }
        }
      `}</style>
    </article>
  );
}
