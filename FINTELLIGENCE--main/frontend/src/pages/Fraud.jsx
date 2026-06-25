import { useState } from 'react';
import DetectorCard from '../shared/DetectorCard';
import CaseList from '../components/CaseList';

export default function Fraud({ detectors, runDetectors, loading, cases, selectedCaseId, setSelectedCaseId }) {
  const triggered = detectors.filter((item) => item.triggered || item.score > 0);
  const passed = detectors.filter((item) => !triggered.includes(item));

  return (
    <section className="stack">
      <div className="toolbar right">
        <button className="primary-button" onClick={runDetectors} disabled={!selectedCaseId || loading} type="button">
          {loading ? 'Running detectors' : 'Run detector suite'}
        </button>
      </div>
      <div className="detector-grid">
        <div>
          <p className="eyebrow">TRIGGERED / {triggered.length}</p>
          {triggered.map((item) => <DetectorCard item={item} key={item.name} />)}
        </div>
        <div>
          <p className="eyebrow">PASSED / {passed.length}</p>
          {passed.map((item) => (
            <div className="passed-card" key={item.name}>
              <span>{item.name}</span>
              <strong>Clear</strong>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
