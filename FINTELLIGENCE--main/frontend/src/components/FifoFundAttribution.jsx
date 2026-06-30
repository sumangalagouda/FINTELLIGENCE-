import { useState, useEffect } from 'react';
import { ChevronDown, ChevronUp, Layers, ArrowRight } from 'lucide-react';

const formatMoney = (value) => new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 0 }).format(Number(value || 0));
const formatDate = (value) => {
  if (!value) return '-';
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? String(value).slice(0, 10) : date.toISOString().slice(0, 10);
};

export default function FifoFundAttribution({ api, caseId, selectedAccountId, uniqueAccounts, onAccountSelect }) {
  const [data, setData] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [expandedOutflows, setExpandedOutflows] = useState(new Set());

  useEffect(() => {
    if (!api || !caseId || !selectedAccountId) return;
    
    let alive = true;
    setIsLoading(true);
    
    api('/intelligence/fifo-trace', {
      method: 'POST',
      body: JSON.stringify({ account_id: selectedAccountId, case_id: caseId })
    }).then(res => {
      if (alive) {
        setData(res.traced_outflows || []);
      }
    }).catch(err => {
      console.error(err);
      if (alive) setData([]);
    }).finally(() => {
      if (alive) setIsLoading(false);
    });

    return () => { alive = false; };
  }, [api, caseId, selectedAccountId]);

  const toggleExpand = (txnId) => {
    const newExpanded = new Set(expandedOutflows);
    if (newExpanded.has(txnId)) {
      newExpanded.delete(txnId);
    } else {
      newExpanded.add(txnId);
    }
    setExpandedOutflows(newExpanded);
  };

  return (
    <div className="panel" style={{ padding: '24px', background: 'white', borderRadius: '12px', border: '1px solid #e2e8f0', marginTop: '24px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
        <div>
          <span className="eyebrow" style={{ color: '#64748b', fontSize: '12px', fontWeight: 'bold', letterSpacing: '0.05em' }}>FORENSIC ACCOUNTING</span>
          <h3 style={{ margin: '4px 0 0 0', fontSize: '20px', color: '#0f172a' }}>FIFO Fund Attribution</h3>
          <p style={{ margin: '4px 0 0 0', fontSize: '14px', color: '#64748b' }}>
            Trace which specific incoming funds capitalized each outgoing transaction.
          </p>
        </div>
        
        {/* Account Selector */}
        <select 
          value={selectedAccountId || ''}
          onChange={(e) => onAccountSelect(e.target.value)}
          style={{ padding: '8px 12px', borderRadius: '8px', border: '1px solid #cbd5e1', outline: 'none', background: '#f8fafc', color: '#0f172a', fontWeight: '500', minWidth: '200px' }}
        >
          {uniqueAccounts.map(acc => (
            <option key={acc} value={acc}>{acc}</option>
          ))}
        </select>
      </div>

      {isLoading ? (
        <div style={{ padding: '32px', textAlign: 'center', color: '#64748b' }}>Running FIFO trace algorithm...</div>
      ) : !data || data.length === 0 ? (
        <div style={{ padding: '32px', textAlign: 'center', color: '#94a3b8', background: '#f8fafc', borderRadius: '8px', border: '1px dashed #e2e8f0' }}>
          No outflows available to trace for the selected account.
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
          {data.map((outflow) => {
            const isExpanded = expandedOutflows.has(outflow.outflow_txn_id);
            return (
              <div key={outflow.outflow_txn_id} style={{ border: '1px solid #e2e8f0', borderRadius: '8px', overflow: 'hidden' }}>
                <div 
                  onClick={() => toggleExpand(outflow.outflow_txn_id)}
                  style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '16px', background: isExpanded ? '#f8fafc' : 'white', cursor: 'pointer', transition: 'background 0.2s' }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
                    <div style={{ background: '#fee2e2', color: '#dc2626', padding: '8px', borderRadius: '8px' }}>
                      <ArrowRight size={20} />
                    </div>
                    <div>
                      <div style={{ fontWeight: 'bold', color: '#0f172a', fontSize: '15px' }}>
                        Outflow: {formatMoney(outflow.outflow_amount)}
                      </div>
                      <div style={{ fontSize: '13px', color: '#64748b', marginTop: '2px' }}>
                        {formatDate(outflow.outflow_date)} • {outflow.fully_traced ? <span style={{color: '#10b981'}}>Fully Traced</span> : <span style={{color: '#f59e0b'}}>Partially Traced</span>}
                      </div>
                    </div>
                  </div>
                  <div style={{ color: '#94a3b8' }}>
                    {isExpanded ? <ChevronUp size={20} /> : <ChevronDown size={20} />}
                  </div>
                </div>

                {isExpanded && (
                  <div style={{ padding: '16px', background: '#f1f5f9', borderTop: '1px solid #e2e8f0' }}>
                    <h4 style={{ margin: '0 0 12px 0', fontSize: '13px', color: '#475569', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Funded By</h4>
                    {outflow.funded_by.length === 0 ? (
                      <div style={{ fontSize: '14px', color: '#94a3b8' }}>No prior inflows found to fund this transaction. (Existing Balance)</div>
                    ) : (
                      <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                        {outflow.funded_by.map((inflow, idx) => (
                          <div key={idx} style={{ display: 'flex', justifyContent: 'space-between', padding: '12px', background: 'white', borderRadius: '6px', border: '1px solid #e2e8f0' }}>
                            <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                              <Layers size={16} color="#3b82f6" />
                              <span style={{ fontSize: '14px', color: '#334155', fontWeight: '500' }}>Inflow on {formatDate(inflow.source_date)}</span>
                            </div>
                            <span style={{ fontSize: '14px', fontWeight: 'bold', color: '#10b981' }}>
                              {formatMoney(inflow.amount_consumed)}
                            </span>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
