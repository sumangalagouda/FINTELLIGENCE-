import { useState } from 'react';
import { FileText, Download } from 'lucide-react';
import CaseList from '../components/CaseList';

export default function Reports({ api, cases, selectedCaseId, setSelectedCaseId, selectedCase }) {
  const [pageViewMode, setPageViewMode] = useState('list');
  const [busy, setBusy] = useState(false);
  const download = async (url, method, filename) => {
    if (!selectedCaseId) return;
    setBusy(true);
    try {
      const blob = await api(url, { method, headers: {} });
      if (blob instanceof Blob) {
        const objectUrl = URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = objectUrl;
        link.download = filename;
        link.click();
        URL.revokeObjectURL(objectUrl);
      } else {
        // Fallback if not blob
        alert(blob.error || 'Failed to download report');
      }
    } catch (e) {
      alert('Error generating report: ' + e.message);
    } finally {
      setBusy(false);
    }
  };

  const reports = [
    { id: 'summary', title: `FINTELLIGENCE_Report_${selectedCaseId?.slice(0, 8) || 'case'}.pdf`, url: `/reports/generate/${selectedCaseId}`, method: 'GET' },
    { id: 'dossier_bank', title: `Dossier_BankFraud_${selectedCaseId?.slice(0, 8) || 'case'}.docx`, url: `/reports/dossier/${selectedCaseId}?authority=bank_fraud`, method: 'GET' },
    { id: 'dossier_aml', title: `Dossier_AML_${selectedCaseId?.slice(0, 8) || 'case'}.docx`, url: `/reports/dossier/${selectedCaseId}?authority=aml_team`, method: 'GET' },
    { id: 'dossier_cyber', title: `Dossier_CyberCrime_${selectedCaseId?.slice(0, 8) || 'case'}.docx`, url: `/reports/dossier/${selectedCaseId}?authority=cyber_crime`, method: 'GET' },
    { id: 'dossier_auditor', title: `Dossier_Auditor_${selectedCaseId?.slice(0, 8) || 'case'}.xlsx`, url: `/reports/dossier/${selectedCaseId}?authority=auditor`, method: 'GET' },
    { id: 'fir_draft', title: `FIR_Draft_${selectedCaseId?.slice(0, 8) || 'case'}.pdf`, url: `/reports/fir-draft/${selectedCaseId}`, method: 'POST' }
  ];

  return (
    <section className="panel stack">

      <div>
        <p className="subcopy">Generated PDF investigation packets: case summary, detector results, money trail, notes.</p>
      </div>
      <div className="table-frame">
        <table>
          <thead>
            <tr>
              <th>Filename</th>
              <th>Case</th>
              <th>Size</th>
              <th>Action</th>
            </tr>
          </thead>
          <tbody>
            {reports.map(report => (
              <tr key={report.id}>
                <td><FileText size={15} /> {report.title}</td>
                <td>{selectedCase?.id?.slice(0, 8) || '-'}</td>
                <td>Generated</td>
                <td>
                  <button className="link-button" onClick={() => download(report.url, report.method, report.title)} disabled={!selectedCaseId || busy} type="button">
                    <Download size={14} /> {busy ? 'Preparing' : 'Download'}
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
