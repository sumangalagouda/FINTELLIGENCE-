import { FolderOpen, ChevronRight, CheckCircle2, Clock, AlertCircle } from 'lucide-react';
import Badge from '../shared/Badge';

function getStatusDetails(status = '') {
  const s = status.toLowerCase();
  if (s === 'closed') return { color: '#10b981', bg: '#ecfdf5', icon: CheckCircle2, label: 'CLOSED' };
  if (s.includes('pending') || s.includes('review')) return { color: '#f59e0b', bg: '#fffbeb', icon: Clock, label: status.replace(/_/g, ' ').toUpperCase() };
  if (s === 'escalated') return { color: '#ef4444', bg: '#fef2f2', icon: AlertCircle, label: 'ESCALATED' };
  return { color: '#3b82f6', bg: '#eff6ff', icon: AlertCircle, label: status.replace(/_/g, ' ').toUpperCase() };
}

export default function CaseList({ cases = [], onSelect, title }) {
  return (
    <section className="stack" style={{ padding: '24px', background: '#f8fafc', minHeight: '100%' }}>
      <style>{`
        .premium-card {
          background: white;
          border: 1px solid #e2e8f0;
          border-radius: 12px;
          padding: 20px;
          display: flex;
          flex-direction: column;
          gap: 16px;
          cursor: pointer;
          transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
          box-shadow: 0 1px 3px rgba(15, 23, 42, 0.05);
          position: relative;
          overflow: hidden;
        }
        .premium-card:hover {
          transform: translateY(-4px);
          box-shadow: 0 12px 24px rgba(15, 23, 42, 0.08);
          border-color: #cbd5e1;
        }
        .premium-card::before {
          content: '';
          position: absolute;
          top: 0; left: 0; right: 0; height: 4px;
          background: linear-gradient(to right, #3b82f6, #8b5cf6);
          opacity: 0;
          transition: opacity 0.2s;
        }
        .premium-card:hover::before {
          opacity: 1;
        }
        .card-icon-wrap {
          width: 40px; height: 40px;
          border-radius: 10px;
          background: #f1f5f9;
          display: flex;
          align-items: center;
          justify-content: center;
          color: #3b82f6;
          transition: all 0.2s;
        }
        .premium-card:hover .card-icon-wrap {
          background: #eff6ff;
          color: #2563eb;
        }
        .card-arrow {
          color: #cbd5e1;
          transition: all 0.2s;
        }
        .premium-card:hover .card-arrow {
          color: #3b82f6;
          transform: translateX(4px);
        }
      `}</style>

      {title && (
        <div style={{ marginBottom: '24px' }}>
          <h2 style={{ fontSize: '24px', fontWeight: 'bold', color: '#0f172a', margin: 0 }}>{title}</h2>
          <p style={{ color: '#64748b', margin: '4px 0 0 0', fontSize: '14px' }}>Select an investigation to view the fund flow timeline.</p>
        </div>
      )}

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(320px, 1fr))', gap: '20px' }}>
        {cases.map(c => {
          const statusDef = getStatusDetails(c.status);
          const StatusIcon = statusDef.icon;
          
          return (
            <article 
              className="premium-card" 
              key={c.id} 
              onClick={() => onSelect(c.id)}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                <div className="card-icon-wrap">
                  <FolderOpen size={20} />
                </div>
                {c.severity && <Badge value={c.severity} />}
              </div>
              
              <div>
                <h3 style={{ margin: '0 0 4px 0', fontSize: '18px', fontWeight: 'bold', color: '#0f172a' }}>
                  {c.display_id ? `Case ${String(c.display_id).padStart(3, '0')}` : `Case ${c.id.slice(0, 8)}`}
                </h3>
                <p style={{ margin: 0, fontSize: '13px', color: '#64748b', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                  {c.title || 'Ongoing Investigation'}
                </p>
              </div>

              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: 'auto', paddingTop: '8px', borderTop: '1px solid #f1f5f9' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '6px', background: statusDef.bg, padding: '4px 10px', borderRadius: '20px' }}>
                  <StatusIcon size={14} color={statusDef.color} />
                  <span style={{ fontSize: '11px', fontWeight: 'bold', color: statusDef.color, letterSpacing: '0.05em' }}>
                    {statusDef.label}
                  </span>
                </div>
                
                <ChevronRight size={20} className="card-arrow" />
              </div>
            </article>
          );
        })}
        {cases.length === 0 && (
          <div style={{ gridColumn: '1 / -1', padding: '48px', textAlign: 'center', background: 'white', borderRadius: '12px', border: '1px dashed #cbd5e1' }}>
            <FolderOpen size={48} color="#cbd5e1" style={{ margin: '0 auto 16px auto' }} />
            <p style={{ color: '#64748b', fontSize: '15px', margin: 0 }}>No cases available.</p>
          </div>
        )}
      </div>
    </section>
  );
}
