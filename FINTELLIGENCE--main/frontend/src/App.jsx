import { useCallback, useEffect, useMemo, useState } from 'react';
import {
  Archive,
  Bot,
  FileText,
  Folder,
  Grid2X2,
  Network,
  Shield,
  UploadCloud,
  WalletCards,
} from 'lucide-react';
import './App.css';
import Sidebar from './components/Sidebar';
import PageHeader from './components/PageHeader';
import LoginScreen from './components/LoginScreen';
import DashboardPage from './pages/Dashboard';
import TransactionsPage from './pages/Transactions';
import UploadPage from './pages/Upload';
import FraudPage from './pages/Fraud';
import FundFlowView from './components/FundFlowView';
import MoneyTrailPage from './pages/MoneyTrail';
import CasesPage from './pages/Cases';
import AiPage from './pages/Ai';
import ReportsPage from './pages/Reports';
import EvidencePage from './pages/Evidence';
import { apiFactory } from './services/api';
import { getDashboardOverview } from './services/dashboard';
import { getCaseDetail, listCases } from './services/cases';
import { getStatementTransactions } from './services/transactions';
import { getCaseGraph } from './services/graph';

const TOKEN_KEY = 'fintelligence_token';

const navItems = [
  { id: 'dashboard', label: 'Dashboard', eyebrow: 'COMMAND', title: 'Dashboard', icon: Grid2X2 },
  { id: 'upload', label: 'Upload', eyebrow: 'INGEST', title: 'Upload statement', icon: UploadCloud },
  { id: 'transactions', label: 'Transactions', eyebrow: 'LEDGER', title: 'Transactions', icon: WalletCards },
  { id: 'fraud', label: 'Fraud Analysis', eyebrow: 'SIGNAL', title: 'Fraud Analysis', icon: Shield },
  { id: 'fund-flow', label: 'Fund Flow', eyebrow: 'GRAPH', title: 'Fund Flow', icon: Network },
  { id: 'money-trail', label: 'Money Trail', eyebrow: 'TRAIL', title: 'Money Trail', icon: Network },
  { id: 'cases', label: 'Cases', eyebrow: 'DOSSIERS', title: 'Cases', icon: Folder },
  { id: 'ai', label: 'AI Investigator', eyebrow: 'CONVERSATIONAL', title: 'AI Investigator', icon: Bot },
  { id: 'reports', label: 'Reports', eyebrow: 'ARCHIVE', title: 'Reports', icon: FileText },
  { id: 'evidence', label: 'Evidence Locker', eyebrow: 'CHAIN OF CUSTODY', title: 'Evidence Locker', icon: Archive },
];

const detectorEndpoints = [
  ['Large Transaction', '/detect/large-transaction'],
  ['Dormant Account Revival', '/detect/dormant-revival'],
  ['Beneficiary Burst', '/detect/beneficiary-burst'],
  ['High Risk Time', '/detect/high-risk-time'],
  ['Structuring / Smurfing', '/detect/structuring'],
  ['Circular Flow', '/detect/circular-flow'],
];

export default function App() {
  const [token, setToken] = useState(() => localStorage.getItem(TOKEN_KEY) || '');
  const [user, setUser] = useState(null);
  const [activeView, setActiveView] = useState('dashboard');
  const [cases, setCases] = useState([]);
  const [selectedCaseId, setSelectedCaseId] = useState('');
  const [caseDetail, setCaseDetail] = useState(null);
  const [overview, setOverview] = useState(null);
  const [transactions, setTransactions] = useState([]);
  const [detectors, setDetectors] = useState([]);
  const [graph, setGraph] = useState(null);
  const [evidence, setEvidence] = useState([]);
  const [chat, setChat] = useState([]);
  const [loading, setLoading] = useState(false);
  const [notice, setNotice] = useState('');

  const api = useMemo(() => apiFactory(token), [token]);

  const refreshCases = useCallback(async () => {
    const data = await listCases(api);
    setCases(data);
    setSelectedCaseId((current) => (data.some((item) => item.id === current) ? current : data[0]?.id || ''));
    return data;
  }, [api]);

  useEffect(() => {
    if (!token) return;

    let alive = true;

    const hydrateSession = async () => {
      try {
        const [me, overviewData, caseData] = await Promise.all([
          api('/auth/me'),
          getDashboardOverview(api).catch(() => null),
          listCases(api),
        ]);

        if (!alive) return;
        setUser(me);
        setOverview(overviewData);
        setCases(caseData);
        setSelectedCaseId((current) => current || caseData[0]?.id || '');
      } catch (error) {
        if (!alive) return;
        setNotice(error.message);
        localStorage.removeItem(TOKEN_KEY);
        setToken('');
      }
    };

    hydrateSession();

    return () => {
      alive = false;
    };
  }, [api, token]);

  useEffect(() => {
    if (!token || !selectedCaseId) return;

    let alive = true;

    const loadCaseContext = async () => {
      setLoading(true);
      setNotice('');
      try {
        const detail = await getCaseDetail(api, selectedCaseId);
        if (!alive) return;

        setCaseDetail(detail);

        const statementId = detail.statements?.[0]?.id;
        const [txnPayload, graphData, evidenceData] = await Promise.all([
          statementId ? getStatementTransactions(api, statementId).catch(() => ({ transactions: [] })) : Promise.resolve({ transactions: [] }),
          getCaseGraph(api, selectedCaseId).catch(() => ({ nodes: [], links: [] })),
          api(`/evidence/${selectedCaseId}`).catch(() => []),
        ]);

        if (!alive) return;
        setTransactions(txnPayload.transactions || []);
        setGraph(graphData);
        setEvidence(evidenceData);
      } catch (error) {
        if (!alive) return;
        setNotice(error.message);
        setCaseDetail(null);
        setTransactions([]);
        setGraph(null);
        setEvidence([]);
      } finally {
        if (alive) setLoading(false);
      }
    };

    loadCaseContext();

    return () => {
      alive = false;
    };
  }, [api, selectedCaseId, token]);

  const selectedCase = useMemo(
    () => cases.find((item) => item.id === selectedCaseId) || caseDetail,
    [caseDetail, cases, selectedCaseId],
  );

  const runDetectors = useCallback(async () => {
    if (!selectedCaseId) return;
    setLoading(true);
    setNotice('');

    try {
      const results = await Promise.allSettled(
        detectorEndpoints.map(async ([name, path]) => {
          const result = await api(path, {
            method: 'POST',
            body: JSON.stringify({ case_id: selectedCaseId }),
          });
          return normalizeDetector(name, result);
        }),
      );

      setDetectors(
        results.map((result, index) =>
          result.status === 'fulfilled'
            ? result.value
            : {
              name: detectorEndpoints[index][0],
              triggered: false,
              severity: 'low',
              score: 0,
              reason: result.reason?.message,
            },
        ),
      );
    } finally {
      setLoading(false);
    }
  }, [api, selectedCaseId]);

  if (!token) {
    return <LoginScreen setToken={(value) => { localStorage.setItem(TOKEN_KEY, value); setToken(value); }} />;
  }

  const pageMeta = navItems.find((item) => item.id === activeView) || navItems[0];

  return (
    <div className="app-shell">
      <Sidebar
        activeView={activeView}
        setActiveView={setActiveView}
        user={user}
        onLogout={() => {
          localStorage.removeItem(TOKEN_KEY);
          setToken('');
          setUser(null);
          setCases([]);
          setSelectedCaseId('');
          setCaseDetail(null);
          setTransactions([]);
          setGraph(null);
          setEvidence([]);
          setDetectors([]);
        }}
        navItems={navItems}
      />

      <main className="workspace">
        {loading && (
          <div className="loading-overlay">
            <div className="spinner">Loading...</div>
          </div>
        )}

        <div className="page-topline" />
        <PageHeader meta={pageMeta} selectedCaseId={selectedCaseId} setSelectedCaseId={setSelectedCaseId} cases={cases} />
        {notice && <div className="notice">{notice}</div>}

        {activeView === 'dashboard' && (
          <DashboardPage
            overview={overview}
            cases={cases}
            caseDetail={caseDetail}
            selectedCase={selectedCase}
            transactions={transactions}
            detectors={detectors}
          />
        )}

        {activeView === 'upload' && (
          <UploadPage
            api={api}
            refreshCases={refreshCases}
            selectedCaseId={selectedCaseId}
            setSelectedCaseId={setSelectedCaseId}
            setNotice={setNotice}
          />
        )}

        {activeView === 'transactions' && <TransactionsPage transactions={transactions} selectedCase={selectedCase} />}

        {activeView === 'fraud' && (
          <FraudPage
            detectors={detectors}
            runDetectors={runDetectors}
            loading={loading}
            selectedCaseId={selectedCaseId}
          />
        )}

        {activeView === 'fund-flow' && <FundFlowView graph={graph} transactions={transactions} />}
        {activeView === 'money-trail' && (
          <MoneyTrailPage
            graph={graph}
            transactions={transactions}
            selectedCase={selectedCase}
            caseDetail={caseDetail}
          />
        )}
        {activeView === 'cases' && (
          <CasesPage
            cases={cases}
            selectedCaseId={selectedCaseId}
            setSelectedCaseId={setSelectedCaseId}
            caseDetail={caseDetail}
            detectors={detectors}
            api={api}
          />
        )}

        {activeView === 'ai' && <AiPage api={api} selectedCaseId={selectedCaseId} chat={chat} setChat={setChat} transactions={transactions} />}
        {activeView === 'reports' && <ReportsPage api={api} selectedCaseId={selectedCaseId} selectedCase={selectedCase} />}
        {activeView === 'evidence' && <EvidencePage evidence={evidence} selectedCase={selectedCase} />}
      </main>
    </div>
  );
}

function normalizeDetector(name, result) {
  const item = Array.isArray(result) ? result[0] : result;
  const triggered = Boolean(item?.triggered || item?.is_triggered || item?.matches?.length || item?.transactions?.length);

  return {
    name,
    triggered,
    score: item?.score || item?.risk_score || (triggered ? 50 : 0),
    severity: item?.severity || item?.risk_level || (triggered ? 'high' : 'low'),
    reason: item?.reason || item?.message || item?.description || (triggered ? 'Detector returned suspicious matches.' : 'No suspicious signal returned.'),
  };
}
