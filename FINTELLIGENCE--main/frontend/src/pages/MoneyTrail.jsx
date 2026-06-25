import { useMemo, useState } from 'react';
import FundFlowView from '../components/FundFlowView';
import CaseList from '../components/CaseList';

const formatDate = (value) => {
  if (!value) return '-';
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? String(value).slice(0, 10) : date.toISOString().slice(0, 10);
};

const formatMoney = (value) => new Intl.NumberFormat('en-IN', { maximumFractionDigits: 0 }).format(Number(value || 0));

export default function MoneyTrail({ graph, transactions, selectedCase, caseDetail, cases, selectedCaseId, setSelectedCaseId }) {
  const [pageViewMode, setPageViewMode] = useState('list');
  const summary = useMemo(() => {
    const dates = transactions
      .map((txn) => txn.date)
      .filter(Boolean)
      .map((date) => new Date(date))
      .filter((date) => !Number.isNaN(date.getTime()));

    const totalAmount = transactions.reduce((sum, txn) => sum + Number(txn.amount || 0), 0);
    const flagged = transactions.filter((txn) => txn.is_flagged || String(txn.risk_level || '').toLowerCase() !== 'low');

    const nodes = graph?.nodes || [];
    const links = graph?.links || graph?.edges || [];
    const degree = new Map();
    links.forEach((link) => {
      const source = typeof link.source === 'object' ? link.source.id : link.source;
      const target = typeof link.target === 'object' ? link.target.id : link.target;
      degree.set(source, (degree.get(source) || 0) + 1);
      degree.set(target, (degree.get(target) || 0) + 1);
    });

    const intermediaries = nodes.filter((node) => (degree.get(node.id) || 0) > 1);
    const uniqueParties = new Set(transactions.flatMap((txn) => [txn.sender_account, txn.receiver_account]).filter(Boolean));

    return {
      from: dates.length ? dates.reduce((min, date) => (date < min ? date : min), dates[0]) : null,
      to: dates.length ? dates.reduce((max, date) => (date > max ? date : max), dates[0]) : null,
      totalAmount,
      flaggedCount: flagged.length,
      intermediaryCount: intermediaries.length,
      uniquePartiesCount: nodes.length || uniqueParties.size,
      accountOwner:
        selectedCase?.title ||
        caseDetail?.statements?.[0]?.account_holder ||
        caseDetail?.statements?.[0]?.filename ||
        'Selected case',
      statementName: caseDetail?.statements?.[0]?.filename || 'No statement attached',
      patterns: [
        { label: 'Flagged / non-low transactions', value: flagged.length },
        { label: 'Intermediary accounts', value: intermediaries.length },
        { label: 'Unique parties', value: nodes.length || uniqueParties.size },
      ],
    };
  }, [caseDetail, graph, selectedCase, transactions]);

  const recentTransactions = transactions.slice(0, 8);

  return (
    <section className="stack money-trail-page">
      <div className="dashboard-hero hoste-style">
        <p className="eyebrow">TRAIL / TRACEABLE HISTORY</p>
        <h1>Money Trail</h1>
        <p className="subcopy">
          Traceable history of money movement for investigation, audit, AML, fraud detection, and compliance review.
        </p>
      </div>

      <div className="metric-grid three">
        <div className="metric metric-1">
          <span>Trail Range</span>
          <strong>{summary.from ? `${formatDate(summary.from)} - ${formatDate(summary.to)}` : 'No dates'}</strong>
          <small>Transaction dates</small>
        </div>
        <div className="metric metric-2">
          <span>Total Movement</span>
          <strong>{formatMoney(summary.totalAmount)}</strong>
          <small>Amounts moved</small>
        </div>
        <div className="metric metric-3">
          <span>Intermediaries</span>
          <strong>{summary.intermediaryCount}</strong>
          <small>Accounts between source and sink</small>
        </div>
      </div>

      <section className="panel money-section">
        <div className="panel-label">
          <span className="eyebrow">TRAIL OVERVIEW</span>
          <h2>What the trail means</h2>
        </div>
        <p className="money-copy">
          Money trail refers to the complete traceable history of money movement. It captures fund flows and supporting metadata
          such as transaction dates, amounts, account owners, intermediaries, and suspicious patterns.
        </p>
      </section>

      <section className="panel money-section">
        <div className="panel-label">
          <span className="eyebrow">TRAIL METADATA</span>
          <h2>Who, when, how much, and through whom</h2>
        </div>
        <div className="money-grid">
          <div className="money-card">
            <span>Account owner</span>
            <strong>{summary.accountOwner}</strong>
          </div>
          <div className="money-card">
            <span>Statement</span>
            <strong>{summary.statementName}</strong>
          </div>
          <div className="money-card">
            <span>Suspicious transfers</span>
            <strong>{summary.flaggedCount}</strong>
          </div>
          <div className="money-card">
            <span>Unique parties</span>
            <strong>{summary.uniquePartiesCount}</strong>
          </div>
        </div>
      </section>

      <section className="panel money-section">
        <div className="panel-label">
          <span className="eyebrow">SUSPICIOUS PATTERNS</span>
          <h2>Signals to review</h2>
        </div>
        <div className="money-list">
          {summary.patterns.map((item) => (
            <div className="money-list-item" key={item.label}>
              <span>{item.label}</span>
              <strong>{item.value}</strong>
            </div>
          ))}
        </div>
      </section>

      <section className="panel money-section">
        <div className="panel-label">
          <span className="eyebrow">RECENT TRANSFERS</span>
          <h2>Transaction trail</h2>
        </div>
        <div className="table-shell">
          <table className="data-table">
            <thead>
              <tr>
                <th>Date</th>
                <th>Amount</th>
                <th>Sender</th>
                <th>Receiver</th>
                <th>Risk</th>
              </tr>
            </thead>
            <tbody>
              {recentTransactions.map((txn) => (
                <tr key={txn.id}>
                  <td>{formatDate(txn.date)}</td>
                  <td>{formatMoney(txn.amount)}</td>
                  <td>{txn.sender_account || '-'}</td>
                  <td>{txn.receiver_account || '-'}</td>
                  <td>{txn.risk_level || 'low'}</td>
                </tr>
              ))}
              {recentTransactions.length === 0 && (
                <tr>
                  <td colSpan={5} className="empty-table">
                    No transactions available for the selected case.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </section>

      <section className="panel money-section">
        <div className="panel-label">
          <span className="eyebrow">VISUAL TRAIL</span>
          <h2>Fund flow map</h2>
        </div>
        <FundFlowView
          graph={graph}
          transactions={transactions}
          title="Money Trail"
          subtitle="Trace money movement, intermediaries, and suspicious routes through the selected case."
          eyebrow="TRAIL"
        />
      </section>
    </section>
  );
}

