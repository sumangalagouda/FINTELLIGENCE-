import { useMemo, useState, useEffect } from 'react';
import FundFlowView from '../components/FundFlowView';
import FifoFundAttribution from '../components/FifoFundAttribution';
import CaseList from '../components/CaseList';

const formatDate = (value) => {
  if (!value) return '-';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return String(value).slice(0, 10);
  return new Intl.DateTimeFormat('en-US', { month: 'short', day: 'numeric', year: 'numeric' }).format(date);
};

const formatMoney = (value) => new Intl.NumberFormat('en-IN', { maximumFractionDigits: 0 }).format(Number(value || 0));

export default function MoneyTrail({ api, graph, transactions, selectedCase, caseDetail, cases, selectedCaseId, setSelectedCaseId }) {
  const [pageViewMode, setPageViewMode] = useState('list');
  const [fifoAccountId, setFifoAccountId] = useState(null);

  const uniqueAccounts = useMemo(() => {
    const accounts = new Set();
    transactions.forEach(txn => {
      if (txn.sender_account) accounts.add(txn.sender_account);
      if (txn.receiver_account) accounts.add(txn.receiver_account);
    });
    return Array.from(accounts).sort();
  }, [transactions]);

  useEffect(() => {
    // Default to main account holder
    if (uniqueAccounts.length > 0 && !fifoAccountId) {
      const mainAccount = caseDetail?.statements?.[0]?.account_holder || caseDetail?.statements?.[0]?.account_number;
      if (mainAccount && uniqueAccounts.includes(mainAccount)) {
        setFifoAccountId(mainAccount);
      } else {
        setFifoAccountId(uniqueAccounts[0]);
      }
    }
  }, [uniqueAccounts, caseDetail, fifoAccountId]);

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
        <p className="eyebrow">TRACEABLE HISTORY</p>
        <h1>Fund Flow & Tracking</h1>
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
          <span className="eyebrow">VISUAL TRAIL</span>
          <h2>Fund flow map</h2>
        </div>
        <FundFlowView
          api={api}
          graph={graph}
          transactions={transactions}
          selectedCaseId={selectedCaseId}
          onNodeClick={(nodeId) => setFifoAccountId(nodeId)}
        />
        
        {/* FIFO Tracking Section */}
        {uniqueAccounts.length > 0 && (
          <FifoFundAttribution
            api={api}
            caseId={selectedCaseId}
            uniqueAccounts={uniqueAccounts}
            selectedAccountId={fifoAccountId}
            onAccountSelect={setFifoAccountId}
          />
        )}
      </section>
    </section>
  );
}

