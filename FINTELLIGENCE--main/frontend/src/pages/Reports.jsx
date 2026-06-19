import { useState } from 'react';
import { FileText, Download } from 'lucide-react';

export default function Reports({ api, selectedCaseId, selectedCase }) {
  const [busy, setBusy] = useState(false);
  const download = async () => {
    if (!selectedCaseId) return;
    setBusy(true);
    try {
      const blob = await api(`/reports/generate/${selectedCaseId}`, { headers: {} });
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `FINTELLIGENCE_Report_${selectedCaseId.slice(0, 8)}.pdf`;
      link.click();
      URL.revokeObjectURL(url);
    } finally {
      setBusy(false);
    }
  };

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
            <tr>
              <td><FileText size={15} /> FINTELLIGENCE_Report_{selectedCaseId?.slice(0, 8) || 'case'}.pdf</td>
              <td>{selectedCase?.id?.slice(0, 8) || '-'}</td>
              <td>Generated</td>
              <td>
                <button className="link-button" onClick={download} disabled={!selectedCaseId || busy} type="button">
                  <Download size={14} /> {busy ? 'Preparing' : 'Download'}
                </button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>
  );
}
