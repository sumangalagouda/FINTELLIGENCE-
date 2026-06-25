import { useState, useMemo, useEffect } from 'react';
import Badge from '../shared/Badge';
import CaseList from '../components/CaseList';
import { FileText, Download, Sparkles, UploadCloud, Clock, Search, ShieldAlert, BadgeInfo, AlertTriangle, PlayCircle, Briefcase, Target, Users, MoreHorizontal, ArrowUpRight, CheckCircle2, Key } from 'lucide-react';
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis, Cell } from 'recharts';
import '../App.css'; // Make sure styling fits

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

export default function Cases({ 
  user,
  cases, 
  selectedCaseId, 
  setSelectedCaseId, 
  caseDetail, 
  detectors,
  api,
  viewMode,
  setViewMode,
  refreshCases,
  setCaseDetail
}) {
  const [note, setNote] = useState('');
  const [message, setMessage] = useState('');
  const [investigatorNotes, setInvestigatorNotes] = useState([]);
  const [showEscalateModal, setShowEscalateModal] = useState(false);
  const [escalateReason, setEscalateReason] = useState('');
  const [escalateEvidenceFile, setEscalateEvidenceFile] = useState(null);
  const [escalateSignaturePassword, setEscalateSignaturePassword] = useState('');

  const [showSIOActionModal, setShowSIOActionModal] = useState(null); // 'close' or 'fir'
  const [sioSignaturePassword, setSioSignaturePassword] = useState('');
  const [firMockDetails, setFirMockDetails] = useState('');

  const isSIO = user?.role === 'supervisor' || localStorage.getItem('sio_view') === 'true';
  
  const [showCloseModal, setShowCloseModal] = useState(false);
  const [closingReason, setClosingReason] = useState('');
  const [signaturePassword, setSignaturePassword] = useState('');
  const [closeEvidenceFile, setCloseEvidenceFile] = useState(null);

  // Fetch actual investigator notes
  const fetchNotes = async () => {
    if (!selectedCaseId) return;
    try {
      const data = await api(`/governance/notes/${selectedCaseId}`);
      setInvestigatorNotes(data || []);
    } catch (err) {
      console.error(err);
    }
  };

  useEffect(() => {
    if (viewMode === 'detail' && selectedCaseId) {
      fetchNotes();
    }
  }, [viewMode, selectedCaseId]);

  const addNote = async () => {
    if (!note.trim() || !selectedCaseId) return;
    try {
      await api(`/governance/notes/${selectedCaseId}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ note_text: note }),
      });
      setNote('');
      setMessage('Investigator note added successfully.');
      fetchNotes(); // refresh notes
      setTimeout(() => setMessage(''), 3000);
    } catch (err) {
      console.error(err);
    }
  };

  const changeStatus = async (newStatus) => {
    if (!selectedCaseId) return;
    
    if (newStatus === 'closed') {
      setShowCloseModal(true);
      return;
    }
    
    try {
      await api(`/cases/${selectedCaseId}/status`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ status: newStatus })
      });
      if (refreshCases) refreshCases(); 
      if (setCaseDetail) setCaseDetail(prev => ({ ...prev, status: newStatus }));
    } catch (err) {
      console.error(err);
      alert(err.message || 'Error updating status');
    }
  };

  const closeCaseWithSignature = async () => {
    if (!selectedCaseId || !closingReason.trim() || !signaturePassword.trim()) {
      alert("Both closing reason and digital signature are required.");
      return;
    }
    try {
      const form = new FormData();
      form.append('status', 'closed');
      form.append('closing_reason', closingReason);
      form.append('signature_password', signaturePassword);
      if (closeEvidenceFile) {
        form.append('evidence_file', closeEvidenceFile);
      }

      await api(`/cases/${selectedCaseId}/status`, {
        method: 'PATCH',
        body: form
      });
      setShowCloseModal(false);
      setClosingReason('');
      setSignaturePassword('');
      setCloseEvidenceFile(null);
      if (refreshCases) refreshCases(); 
      if (setCaseDetail) setCaseDetail(prev => ({ ...prev, status: 'closed' }));
    } catch (err) {
      console.error(err);
      alert(err.message || "Invalid digital signature or error closing case.");
    }
  };

  const escalateCase = async () => {
    if (!selectedCaseId || !escalateReason.trim()) return;
    if (!escalateSignaturePassword.trim()) {
      alert("Digital signature is required to escalate the case.");
      return;
    }
    try {
      const form = new FormData();
      form.append('reason', escalateReason);
      form.append('signature_password', escalateSignaturePassword);
      if (escalateEvidenceFile) {
        form.append('evidence_file', escalateEvidenceFile);
      }
      await api(`/cases/${selectedCaseId}/escalate`, {
        method: 'POST',
        body: form
      });
      setShowEscalateModal(false);
      setEscalateReason('');
      setEscalateEvidenceFile(null);
      setEscalateSignaturePassword('');
      if (refreshCases) refreshCases(); 
      if (setCaseDetail) setCaseDetail(prev => ({ ...prev, status: 'escalated' }));
    } catch (err) {
      console.error(err);
      alert('Error escalating case: ' + err.message);
    }
  };

  const downloadReport = async () => {
    if (!selectedCaseId) return;
    try {
      const response = await fetch(`/api/reports/generate/${selectedCaseId}`, {
        headers: { 'Authorization': `Bearer ${localStorage.getItem('fintelligence_token')}` }
      });
      if (!response.ok) throw new Error('Failed to download report');
      const blob = await response.blob();
      const objectUrl = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = objectUrl;
      link.download = `FINTELLIGENCE_Report_${selectedCaseId.slice(0, 8)}.pdf`;
      link.click();
      URL.revokeObjectURL(objectUrl);
    } catch (e) {
      console.error(e);
      alert('Error generating report: ' + e.message);
    }
  };

  const handleSIOAction = async () => {
    if (!selectedCaseId || !sioSignaturePassword) {
      alert("Please enter your Digital Signature.");
      return;
    }
    
    try {
      if (showSIOActionModal === 'close') {
        if (!closingReason.trim()) {
          alert("Closing reason is required.");
          return;
        }
        const response = await api(`/cases/${selectedCaseId}/status`, {
          method: 'PATCH',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ status: 'closed', closing_reason: closingReason, signature_password: sioSignaturePassword })
        });
        if (response.error) throw new Error(response.error);
        if (refreshCases) refreshCases();
        if (setCaseDetail) setCaseDetail(prev => ({ ...prev, status: 'closed' }));
        alert('Case closed successfully.');
      } else if (showSIOActionModal === 'fir') {
        // Generating FIR
        const response = await fetch(`/api/reports/fir-draft/${selectedCaseId}`, {
          method: 'POST',
          headers: { 
            'Authorization': `Bearer ${localStorage.getItem('fintelligence_token')}`,
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({ signature_password: sioSignaturePassword, mock_details: firMockDetails })
        });
        
        if (!response.ok) {
           const err = await response.json();
           throw new Error(err.error || 'Failed to generate FIR');
        }
        
        const blob = await response.blob();
        const objectUrl = URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = objectUrl;
        link.download = `FIR_Copy_${selectedCaseId.slice(0, 8)}.pdf`;
        link.click();
        URL.revokeObjectURL(objectUrl);
      }
      setShowSIOActionModal(null);
      setSioSignaturePassword('');
      setFirMockDetails('');
      setClosingReason('');
    } catch (err) {
      console.error(err);
      alert('Error performing action: ' + err.message);
    }
  };

  const confidence = Math.max(50, 60 + Math.round(caseDetail?.suspicion_score || 0));
  const evidenceScore = Math.max(40, 50 + Math.round((caseDetail?.suspicion_score || 0) * 0.5));

  const formatCurrency = (val) => new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR' }).format(val || 0);

  const detectorSeries = useMemo(() => buildDetectorSeries(detectors), [detectors]);

  return (
    <section className="stack">
      {viewMode === 'list' ? (
        <CaseList 
          cases={cases} 
          title="All Cases" 
          onSelect={(id) => { 
            setSelectedCaseId(id); 
            setViewMode('detail'); 
          }} 
        />
      ) : (
        caseDetail && (
        <div className="case-summary-view">
          <div style={{ marginBottom: '16px' }}>
             <button className="link-button" onClick={() => setViewMode('list')} style={{ border: 'none', background: 'transparent', color: 'var(--accent)', fontWeight: 'bold', display: 'flex', alignItems: 'center', gap: '8px' }}>&larr; Back to all cases</button>
          </div>
          <header className="case-summary-header">
            <div className="case-title-block">
              <span className="eyebrow">CASE - {String(caseDetail.display_id || '').padStart(8, '0')}</span>
              <h1>{caseDetail.title || `Investigation: ${caseDetail.id.slice(0, 8)}`}</h1>
              <div className="case-meta-row muted">
                <span>{caseDetail.statements?.[0]?.filename || 'No statement'}</span>
                {caseDetail.statement_period && caseDetail.statement_period !== 'Unknown' && (
                  <>
                    <span className="separator">&bull;</span>
                    <span>{caseDetail.statement_period}</span>
                  </>
                )}
              </div>
            </div>
            <div className="case-actions">
              {!isSIO ? (
                <>
                  <select 
                    value={caseDetail.status || 'open'} 
                    onChange={(e) => changeStatus(e.target.value)}
                    className="secondary-button" 
                    style={{ padding: '8px', borderRadius: '4px', border: '1px solid #d1d5db', background: 'white' }}
                  >
                    <option value="open">Open</option>
                    <option value="closed">Closed</option>
                    <option value="under_review">Under Review</option>
                    <option value="escalated" disabled>Escalated</option>
                  </select>
                  <button className="secondary-button" onClick={() => setShowEscalateModal(true)} style={{ color: '#dc2626', borderColor: '#fca5a5' }}>
                    ESCALATE
                  </button>
                </>
              ) : (
                <>
                  <button 
                    className="secondary-button" 
                    onClick={() => setShowSIOActionModal('close')} 
                    style={{ color: caseDetail.status === 'closed' ? '#9ca3af' : '#dc2626', borderColor: caseDetail.status === 'closed' ? '#e5e7eb' : '#fca5a5', cursor: caseDetail.status === 'closed' ? 'not-allowed' : 'pointer' }}
                    disabled={caseDetail.status === 'closed'}
                  >
                    <Key size={16} /> {caseDetail.status === 'closed' ? 'Case Closed' : 'Close Case'}
                  </button>
                  <button className="dark-button" onClick={() => setShowSIOActionModal('fir')} style={{ background: '#4f46e5' }}>
                    <FileText size={16} /> Take Action (FIR)
                  </button>
                </>
              )}
              <button className="secondary-button"><Sparkles size={16}/> AI SUMMARY</button>
              <button className="dark-button" onClick={downloadReport}><Download size={16}/> GENERATE REPORT</button>
            </div>
          </header>

          {showEscalateModal && (
            <div className="modal-overlay" style={{ position: 'fixed', top: 0, left: 0, right: 0, bottom: 0, background: 'rgba(15, 23, 42, 0.6)', backdropFilter: 'blur(4px)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1000 }}>
              <div className="modal-content" style={{ background: 'white', padding: '32px', borderRadius: '16px', width: '480px', boxShadow: '0 25px 50px -12px rgba(0, 0, 0, 0.25)' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '8px' }}>
                  <div style={{ background: '#fee2e2', padding: '10px', borderRadius: '12px', color: '#dc2626' }}>
                    <ShieldAlert size={24} />
                  </div>
                  <h3 style={{ margin: 0, fontSize: '22px', fontWeight: '700', color: '#0f172a' }}>Escalate Case</h3>
                </div>
                
                <p style={{ margin: '0 0 20px 0', fontSize: '15px', color: '#64748b', lineHeight: '1.5' }}>
                  Please provide a reason for escalating this case to the Supervisory Investigating Officer (SIO) and optionally attach evidence.
                </p>

                <textarea 
                  value={escalateReason}
                  onChange={(e) => setEscalateReason(e.target.value)}
                  style={{ width: '100%', height: '120px', padding: '12px 16px', border: '1px solid #cbd5e1', borderRadius: '8px', fontSize: '15px', resize: 'vertical', outline: 'none', transition: 'border-color 0.2s' }}
                  placeholder="Detailed reason for escalation..."
                  onFocus={(e) => e.target.style.borderColor = '#3b82f6'}
                  onBlur={(e) => e.target.style.borderColor = '#cbd5e1'}
                />
                
                <div style={{ marginTop: '16px' }}>
                  <label style={{ display: 'block', fontSize: '14px', fontWeight: '600', color: '#475569', marginBottom: '8px' }}>Supporting Evidence (Optional)</label>
                  <input 
                    type="file" 
                    onChange={(e) => setEscalateEvidenceFile(e.target.files[0])}
                    style={{ width: '100%', padding: '8px', border: '1px dashed #cbd5e1', borderRadius: '8px', background: '#f8fafc', color: '#64748b' }}
                  />
                </div>

                <div style={{ marginTop: '20px', position: 'relative' }}>
                  <div style={{ position: 'absolute', left: '12px', top: '12px', color: '#94a3b8' }}>
                    <Key size={18} />
                  </div>
                  <input 
                    type="password" 
                    value={escalateSignaturePassword}
                    onChange={(e) => setEscalateSignaturePassword(e.target.value)}
                    placeholder="Digital Signature PIN (e.g. 1234)"
                    style={{ width: '100%', padding: '10px 10px 10px 40px', border: '1px solid #cbd5e1', borderRadius: '8px', fontSize: '15px', outline: 'none', transition: 'border-color 0.2s' }}
                    onFocus={(e) => e.target.style.borderColor = '#3b82f6'}
                    onBlur={(e) => e.target.style.borderColor = '#cbd5e1'}
                  />
                </div>
                
                <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '12px', marginTop: '24px' }}>
                  <button onClick={() => setShowEscalateModal(false)} style={{ padding: '10px 20px', background: 'transparent', border: '1px solid #cbd5e1', borderRadius: '8px', color: '#475569', fontWeight: '600', cursor: 'pointer', transition: 'all 0.2s' }} onMouseOver={(e) => e.target.style.background = '#f1f5f9'} onMouseOut={(e) => e.target.style.background = 'transparent'}>CANCEL</button>
                  <button onClick={escalateCase} style={{ padding: '10px 20px', background: '#dc2626', border: 'none', borderRadius: '8px', color: 'white', fontWeight: '600', cursor: 'pointer', boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1)' }}>
                    SUBMIT ESCALATION
                  </button>
                </div>
              </div>
            </div>
          )}

          {showSIOActionModal && (
            <div className="modal-overlay" style={{ position: 'fixed', top: 0, left: 0, right: 0, bottom: 0, background: 'rgba(15, 23, 42, 0.6)', backdropFilter: 'blur(4px)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1000 }}>
              <div className="modal-content" style={{ background: 'white', padding: '32px', borderRadius: '16px', width: '480px', boxShadow: '0 25px 50px -12px rgba(0, 0, 0, 0.25)' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '8px' }}>
                  <div style={{ background: showSIOActionModal === 'close' ? '#fee2e2' : '#e0e7ff', padding: '10px', borderRadius: '12px', color: showSIOActionModal === 'close' ? '#ef4444' : '#4f46e5' }}>
                    {showSIOActionModal === 'close' ? <CheckCircle2 size={24} /> : <FileText size={24} />}
                  </div>
                  <h3 style={{ margin: 0, fontSize: '22px', fontWeight: '700', color: '#0f172a' }}>{showSIOActionModal === 'close' ? 'Close Case' : 'Take Action (Generate FIR)'}</h3>
                </div>
                
                <p style={{ margin: '0 0 20px 0', fontSize: '15px', color: '#64748b', lineHeight: '1.5' }}>
                  {showSIOActionModal === 'close' 
                    ? 'Please provide your final closing remarks and digital signature to archive this case.' 
                    : 'Provide SIO directives and your digital signature to authorize the FIR generation.'}
                </p>

                {showSIOActionModal === 'fir' ? (
                  <textarea 
                    value={firMockDetails}
                    onChange={(e) => setFirMockDetails(e.target.value)}
                    style={{ width: '100%', height: '120px', padding: '12px 16px', border: '1px solid #cbd5e1', borderRadius: '8px', fontSize: '15px', resize: 'vertical', outline: 'none', transition: 'border-color 0.2s' }}
                    placeholder="Provide detailed reasoning for FIR generation..."
                    onFocus={(e) => e.target.style.borderColor = '#3b82f6'}
                    onBlur={(e) => e.target.style.borderColor = '#cbd5e1'}
                  />
                ) : (
                  <textarea 
                    value={closingReason}
                    onChange={(e) => setClosingReason(e.target.value)}
                    style={{ width: '100%', height: '120px', padding: '12px 16px', border: '1px solid #cbd5e1', borderRadius: '8px', fontSize: '15px', resize: 'vertical', outline: 'none', transition: 'border-color 0.2s' }}
                    placeholder="Closing Remarks / Reasoning..."
                    onFocus={(e) => e.target.style.borderColor = '#3b82f6'}
                    onBlur={(e) => e.target.style.borderColor = '#cbd5e1'}
                  />
                )}
                
                <div style={{ marginTop: '16px', position: 'relative' }}>
                  <div style={{ position: 'absolute', left: '12px', top: '12px', color: '#94a3b8' }}>
                    <Key size={18} />
                  </div>
                  <input 
                    type="password" 
                    value={sioSignaturePassword}
                    onChange={(e) => setSioSignaturePassword(e.target.value)}
                    placeholder="Digital Signature PIN (e.g. 1234)"
                    style={{ width: '100%', padding: '10px 10px 10px 40px', border: '1px solid #cbd5e1', borderRadius: '8px', fontSize: '15px', outline: 'none', transition: 'border-color 0.2s' }}
                    onFocus={(e) => e.target.style.borderColor = '#3b82f6'}
                    onBlur={(e) => e.target.style.borderColor = '#cbd5e1'}
                  />
                </div>
                
                <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '12px', marginTop: '24px' }}>
                  <button onClick={() => setShowSIOActionModal(null)} style={{ padding: '10px 20px', background: 'transparent', border: '1px solid #cbd5e1', borderRadius: '8px', color: '#475569', fontWeight: '600', cursor: 'pointer', transition: 'all 0.2s' }} onMouseOver={(e) => e.target.style.background = '#f1f5f9'} onMouseOut={(e) => e.target.style.background = 'transparent'}>CANCEL</button>
                  <button onClick={handleSIOAction} style={{ padding: '10px 20px', background: showSIOActionModal === 'close' ? '#ef4444' : '#4f46e5', border: 'none', borderRadius: '8px', color: 'white', fontWeight: '600', cursor: 'pointer', boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1)' }}>
                    {showSIOActionModal === 'close' ? 'CONFIRM CLOSE' : 'GENERATE FIR'}
                  </button>
                </div>
              </div>
            </div>
          )}
          
          {showCloseModal && (
            <div className="modal-overlay" style={{ position: 'fixed', top: 0, left: 0, right: 0, bottom: 0, background: 'rgba(15, 23, 42, 0.6)', backdropFilter: 'blur(4px)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1000 }}>
              <div className="modal-content" style={{ background: 'white', padding: '32px', borderRadius: '16px', width: '480px', boxShadow: '0 25px 50px -12px rgba(0, 0, 0, 0.25)' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '8px' }}>
                  <div style={{ background: '#fee2e2', padding: '10px', borderRadius: '12px', color: '#ef4444' }}>
                    <CheckCircle2 size={24} />
                  </div>
                  <h3 style={{ margin: 0, fontSize: '22px', fontWeight: '700', color: '#0f172a' }}>Close Case</h3>
                </div>
                
                <p style={{ margin: '0 0 20px 0', fontSize: '15px', color: '#64748b', lineHeight: '1.5' }}>
                  Provide closing remarks, an optional file, and your digital signature.
                </p>

                <textarea 
                  value={closingReason}
                  onChange={(e) => setClosingReason(e.target.value)}
                  style={{ width: '100%', height: '120px', padding: '12px 16px', border: '1px solid #cbd5e1', borderRadius: '8px', fontSize: '15px', resize: 'vertical', outline: 'none', transition: 'border-color 0.2s' }}
                  placeholder="Closing Remarks / Evidence reasoning..."
                  onFocus={(e) => e.target.style.borderColor = '#3b82f6'}
                  onBlur={(e) => e.target.style.borderColor = '#cbd5e1'}
                />

                <div style={{ marginTop: '16px', padding: '16px', border: '1px dashed #cbd5e1', borderRadius: '8px', background: '#f8fafc' }}>
                  <label style={{ display: 'flex', alignItems: 'center', gap: '8px', color: '#475569', fontSize: '14px', fontWeight: '500', marginBottom: '8px' }}>
                    <UploadCloud size={16} /> Attach Final Report (Optional)
                  </label>
                  <input 
                    type="file" 
                    onChange={(e) => setCloseEvidenceFile(e.target.files[0])}
                    style={{ width: '100%', fontSize: '14px', color: '#64748b' }}
                  />
                </div>

                <div style={{ marginTop: '16px', position: 'relative' }}>
                  <div style={{ position: 'absolute', left: '12px', top: '12px', color: '#94a3b8' }}>
                    <Key size={18} />
                  </div>
                  <input 
                    type="password"
                    value={signaturePassword}
                    onChange={(e) => setSignaturePassword(e.target.value)}
                    style={{ width: '100%', padding: '10px 10px 10px 40px', border: '1px solid #cbd5e1', borderRadius: '8px', fontSize: '15px', outline: 'none', transition: 'border-color 0.2s' }}
                    placeholder="Digital Signature (Password)"
                    onFocus={(e) => e.target.style.borderColor = '#3b82f6'}
                    onBlur={(e) => e.target.style.borderColor = '#cbd5e1'}
                  />
                </div>

                <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '12px', marginTop: '24px' }}>
                  <button onClick={() => setShowCloseModal(false)} style={{ padding: '10px 20px', background: 'transparent', border: '1px solid #cbd5e1', borderRadius: '8px', color: '#475569', fontWeight: '600', cursor: 'pointer', transition: 'all 0.2s' }} onMouseOver={(e) => e.target.style.background = '#f1f5f9'} onMouseOut={(e) => e.target.style.background = 'transparent'}>CANCEL</button>
                  <button onClick={closeCaseWithSignature} style={{ padding: '10px 20px', background: '#ef4444', border: 'none', borderRadius: '8px', color: 'white', fontWeight: '600', cursor: 'pointer', boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1)' }}>CONFIRM CLOSURE</button>
                </div>
              </div>
            </div>
          )}

          {/* Extracted Metadata (Added as requested) */}
          <div className="extracted-metadata-bar">
            <div className="meta-item">
              <span className="meta-label">Account Holder</span>
              <span className="meta-value">{caseDetail.account_holder || 'Unknown'}</span>
            </div>
            <div className="meta-item">
              <span className="meta-label">Account Number</span>
              <span className="meta-value">{caseDetail.account_number || 'Unknown'}</span>
            </div>
            <div className="meta-item">
              <span className="meta-label">Bank & Branch</span>
              <span className="meta-value">{caseDetail.bank_name || 'Unknown'}</span>
            </div>
            <div className="meta-item">
              <span className="meta-label">Total Debits</span>
              <span className="meta-value error-text">{formatCurrency(caseDetail.total_debited)}</span>
            </div>
            <div className="meta-item">
              <span className="meta-label">Total Credits</span>
              <span className="meta-value success-text">{formatCurrency(caseDetail.total_credited)}</span>
            </div>
          </div>

          <div className="metric-grid four case-summary-metrics">
            <div className="metric">
              <span>SEVERITY</span>
              <div className="metric-badge"><Badge value={caseDetail.severity || 'low'} /></div>
            </div>
            <div className="metric">
              <span>SUSPICION</span>
              <strong>{caseDetail.suspicion_score || 0}</strong>
            </div>
            <div className="metric">
              <span>CONFIDENCE</span>
              <strong>{confidence}%</strong>
            </div>
            <div className="metric">
              <span>EVIDENCE</span>
              <strong>{evidenceScore}%</strong>
            </div>
          </div>

          <div className="panel ai-summary-panel">
            <h3 className="panel-title">AI INVESTIGATION SUMMARY</h3>
            <div className="ai-summary-content">
              <h4>**CASE OVERVIEW**</h4>
              <p>This investigation concerns {caseDetail.bank_name} Account {caseDetail.account_number} held by {caseDetail.account_holder}, covering the period {caseDetail.statement_period}. The account demonstrates suspicious activity with multiple transactions totaling significant volumes across banking channels. The account exhibits a suspicion score of {caseDetail.suspicion_score || 0}/100 with {confidence}% confidence, triggering {detectors.filter(d=>d.triggered).length} distinct financial crime detection algorithms.</p>
              
              <h4>**RECOMMENDED NEXT STEPS**</h4>
              <p>Immediately review the flagged transactions and connected accounts pending investigation. Request Suspicious Transaction Reports (STRs) and obtain complete KYC documentation. Conduct enhanced due diligence on the account holder including employment verification and cross-reference against law enforcement databases.</p>
            </div>
          </div>

          <section className="panel chart-panel" style={{ marginTop: '0', height: '320px' }}>
            <div className="panel-label">
              <span className="eyebrow">RISK HEAT MAP (THIS CASE)</span>
              <h2 style={{ fontSize: '18px', margin: '4px 0 0 0' }}>Detector firings by severity</h2>
            </div>
            <div className="chart-shell" style={{ height: '240px', marginTop: '16px' }}>
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
                  <YAxis axisLine={false} tickLine={false} tick={{ fill: '#6b7280', fontSize: 12 }} allowDecimals={false} domain={[0, 4]} />
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

          <div className="panel triggered-detectors-panel">
            <h3 className="panel-title">TRIGGERED DETECTORS</h3>
            <div className="detector-list">
              {detectors.filter(d => d.triggered).length === 0 ? (
                <div className="empty-state">No detectors triggered.</div>
              ) : (
                detectors.filter(d => d.triggered).map((det, i) => (
                  <div className="detector-list-item" key={i}>
                    <div className="detector-info">
                      <strong>{det.name}</strong>
                      <span className="muted">{det.reason || 'Flagged transactions detected'}</span>
                    </div>
                    <Badge value={det.severity} />
                  </div>
                ))
              )}
            </div>
          </div>

          <div className="panel notes-panel">
            <h3 className="panel-title">INVESTIGATOR NOTES</h3>
            <div className="note-input-row">
              <input value={note} onChange={(event) => setNote(event.target.value)} placeholder="Add a note..." />
              <button className="dark-button" onClick={addNote} type="button">ADD</button>
            </div>
            {message && <p className="success-text small-text">{message}</p>}
            <div className="notes-list" style={{ marginTop: '16px', display: 'flex', flexDirection: 'column', gap: '12px' }}>
              {investigatorNotes.length === 0 ? (
                <p className="muted">No notes yet.</p>
              ) : (
                investigatorNotes.map(n => (
                  <div key={n.id} style={{ padding: '12px', background: '#f9fafb', borderLeft: '4px solid #9ca3af', borderRadius: '4px' }}>
                    <p style={{ margin: '0 0 4px 0', fontSize: '14px' }}>{n.note_text}</p>
                    <span style={{ fontSize: '12px', color: '#6b7280' }}>{n.created_at ? new Date(n.created_at).toLocaleString() : 'Just now'}</span>
                  </div>
                ))
              )}
            </div>
          </div>
        </div>
        )
      )}
    </section>
  );
}
