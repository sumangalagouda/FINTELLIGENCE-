import { useRef, useState } from 'react';
import { UploadCloud, FileText } from 'lucide-react';

export default function Upload({ api, refreshCases, selectedCaseId, setSelectedCaseId, setNotice, setActiveView, setCaseViewMode }) {
  const inputRef = useRef(null);
  const [file, setFile] = useState(null);
  const [busy, setBusy] = useState(false);
  const [popupMsg, setPopupMsg] = useState('');
  const [uploadedCaseId, setUploadedCaseId] = useState(null);

  const upload = async () => {
    if (!file) {
      setNotice('Choose a PDF, CSV, spreadsheet, or image before analyzing.');
      return;
    }
    setBusy(true);
    setNotice('');
    try {
      const form = new FormData();
      form.append('file', file);
      // Backend automatically generates a case if case_id is absent
      const result = await api('/upload/', { method: 'POST', body: form });
      setSelectedCaseId(result.case_id);
      await refreshCases();
      setUploadedCaseId(result.case_id);
      setPopupMsg(`Analyzed the statement succesfully and case is being created with ${result.case_id}`);
      setTimeout(() => setPopupMsg(''), 5000);
      setNotice('');
    } catch (error) {
      setNotice(error.message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <section className="upload-view">
      <p className="subcopy">PDF, CSV or Excel. We normalize into the canonical schema and run the detector suite automatically.</p>
      <button className="dropzone" type="button" onClick={() => inputRef.current?.click()}>
        <UploadCloud size={38} />
        <strong>{file ? file.name : 'Drop a statement here, or click to browse'}</strong>
        <span>PDF / CSV / XLSX / JPG / PNG</span>
      </button>
      <input
        ref={inputRef}
        type="file"
        accept=".pdf,.csv,.xls,.xlsx,.png,.jpg,.jpeg"
        hidden
        onChange={(event) => setFile(event.target.files?.[0] || null)}
      />
      <div className="upload-actions">
        <button className="primary-button" onClick={upload} disabled={busy} type="button">
          {busy ? 'Analyzing statement' : 'Analyze statement'}
        </button>
        {uploadedCaseId && (
          <button 
            className="secondary-button" 
            onClick={() => {
              setSelectedCaseId(uploadedCaseId);
              setCaseViewMode('detail');
              setActiveView('cases');
            }} 
            type="button"
            style={{ marginLeft: '12px' }}
          >
            View Case Summary
          </button>
        )}
        <span><FileText size={15} /> PDF</span>
        <span><FileText size={15} /> Spreadsheet</span>
        <span><FileText size={15} /> Image / scan</span>
      </div>
      {popupMsg && (
        <div style={{ position: 'fixed', top: 0, left: 0, right: 0, bottom: 0, background: 'rgba(255, 255, 255, 0.4)', backdropFilter: 'blur(8px)', zIndex: 9999, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
          <div style={{ background: 'white', border: '1px solid var(--success)', color: 'var(--success)', padding: '32px 48px', borderRadius: '12px', boxShadow: '0 24px 48px rgba(0,0,0,0.1)', fontWeight: '600', fontSize: '18px', textAlign: 'center', maxWidth: '600px', display: 'flex', flexDirection: 'column', gap: '16px', alignItems: 'center' }}>
            <div style={{ width: '48px', height: '48px', borderRadius: '24px', background: 'rgba(16, 185, 129, 0.1)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round"><polyline points="20 6 9 17 4 12"></polyline></svg>
            </div>
            {popupMsg}
          </div>
        </div>
      )}
    </section>
  );
}
