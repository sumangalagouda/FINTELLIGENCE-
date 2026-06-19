import { useRef, useState } from 'react';
import { UploadCloud, FileText } from 'lucide-react';

export default function Upload({ api, refreshCases, selectedCaseId, setSelectedCaseId, setNotice }) {
  const inputRef = useRef(null);
  const [file, setFile] = useState(null);
  const [caseTitle, setCaseTitle] = useState('Statement investigation');
  const [busy, setBusy] = useState(false);

  const upload = async () => {
    if (!file) {
      setNotice('Choose a PDF, CSV, spreadsheet, or image before analyzing.');
      return;
    }
    setBusy(true);
    setNotice('');
    try {
      let caseId = selectedCaseId;
      if (!caseId) {
        const created = await api('/cases/', {
          method: 'POST',
          body: JSON.stringify({ title: caseTitle, description: 'Uploaded from forensic intake workspace.', severity: 'medium' }),
        });
        caseId = created.id;
        setSelectedCaseId(caseId);
      }
      const form = new FormData();
      form.append('case_id', caseId);
      form.append('file', file);
      const result = await api('/upload/', { method: 'POST', body: form });
      await refreshCases();
      setNotice(`Statement analyzed: ${result.transactions_count} transactions from ${result.bank_detected || 'uploaded file'}.`);
    } catch (error) {
      setNotice(error.message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <section className="upload-view">
      <p className="subcopy">PDF, CSV or Excel. We normalize into the canonical schema and run the detector suite automatically.</p>
      <label className="case-title">
        <span>Case title for new uploads</span>
        <input value={caseTitle} onChange={(event) => setCaseTitle(event.target.value)} />
      </label>
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
        <span><FileText size={15} /> PDF</span>
        <span><FileText size={15} /> Spreadsheet</span>
        <span><FileText size={15} /> Image / scan</span>
      </div>
    </section>
  );
}
