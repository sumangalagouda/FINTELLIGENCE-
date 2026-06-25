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
import SupervisorDashboard from './pages/SupervisorDashboard';
import EscalationsPage from './pages/Escalations';
import { apiFactory } from './services/api';
import { getDashboardOverview } from './services/dashboard';
import { getCaseDetail, listCases } from './services/cases';
import { getStatementTransactions } from './services/transactions';
import { getCaseGraph } from './services/graph';

const TOKEN_KEY = 'fintelligence_token';

const baseNavItems = [
  { id: 'dashboard', label: 'Dashboard', eyebrow: 'COMMAND', title: 'Dashboard', icon: Grid2X2 },
  { id: 'upload', label: 'Upload', eyebrow: 'INGEST', title: 'Upload statement', icon: UploadCloud },
  { id: 'cases', label: 'Cases', eyebrow: 'DOSSIERS', title: 'Cases', icon: Folder },
];

const workspaceTabs = [
  { id: 'summary', label: 'Summary' },
  { id: 'transactions', label: 'Transactions' },
  { id: 'fraud', label: 'Fraud Analysis' },
  { id: 'fund-flow', label: 'Fund Flow' },
  { id: 'money-trail', label: 'Money Trail' },
  { id: 'ai', label: 'AI Investigator' },
  { id: 'reports', label: 'Reports' },
  { id: 'evidence', label: 'Evidence Locker' },
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
  const [caseViewMode, setCaseViewMode] = useState('list');
  const [caseWorkspaceTab, setCaseWorkspaceTab] = useState('summary');
  const [caseFilter, setCaseFilter] = useState('all');
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

  const filteredCases = useMemo(() => {
    if (caseFilter === 'all') return cases;
    return cases.filter((c) => c.status === caseFilter);
  }, [cases, caseFilter]);

  const refreshCases = useCallback(async () => {
    const [data, overviewData] = await Promise.all([
      listCases(api),
      getDashboardOverview(api).catch(() => null)
    ]);
    setCases(data);
    if (overviewData) setOverview(overviewData);
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

        const detResults = await Promise.allSettled(
          detectorEndpoints.map(async ([name, path]) => {
            const result = await api(path, {
              method: 'POST',
              body: JSON.stringify({ case_id: selectedCaseId }),
            });
            return normalizeDetector(name, result);
          })
        );

        if (!alive) return;
        setDetectors(
          detResults.map((res, i) =>
            res.status === 'fulfilled'
              ? res.value
              : {
                  name: detectorEndpoints[i][0],
                  triggered: false,
                  severity: 'low',
                  score: 0,
                  reason: res.reason?.message,
                }
          )
        );
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

  const selectedCase = useMemo(() => {
    const summary = cases.find((item) => item.id === selectedCaseId);
    if (caseDetail && caseDetail.id === selectedCaseId) {
      return { ...summary, ...caseDetail };
    }
    return summary || caseDetail;
  }, [caseDetail, cases, selectedCaseId]);

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

  const sioNavItems = [
    { id: 'sio-dashboard', label: 'SIO Dashboard', eyebrow: 'OVERSIGHT', title: 'SIO Dashboard', icon: Shield },
    { id: 'escalations', label: 'Escalations Queue', eyebrow: 'REVIEW', title: 'Escalations Queue', icon: FileText },
  ];

  const currentNavItems = user?.role === 'supervisor' 
    ? [...sioNavItems, ...baseNavItems.filter(item => item.id !== 'upload' && item.id !== 'dashboard')] 
    : baseNavItems;

  const pageMeta = currentNavItems.find((item) => item.id === activeView) || currentNavItems[0];

  return (
    <div className="app-shell">
      <Sidebar
        activeView={activeView}
        navItems={currentNavItems}
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
      />

      <main className="workspace">
        {loading && (
          <div className="loading-overlay">
            <div className="spinner">Loading...</div>
          </div>
        )}

        <div className="page-topline" />
        <PageHeader 
          user={user} 
          meta={pageMeta} 
          selectedCaseId={selectedCaseId} 
          setSelectedCaseId={setSelectedCaseId} 
          cases={filteredCases}
          caseFilter={caseFilter}
          setCaseFilter={setCaseFilter} 
        />
        {notice && <div className="notice">{notice}</div>}

        {activeView === 'dashboard' && (
          <DashboardPage
            user={user}
            overview={overview}
            cases={filteredCases}
            caseDetail={caseDetail}
            selectedCase={selectedCase}
            transactions={transactions}
            detectors={detectors}
            setActiveView={setActiveView}
            setSelectedCaseId={setSelectedCaseId}
            setCaseViewMode={setCaseViewMode}
          />
        )}
        
        {activeView === 'sio-dashboard' && (
          <DashboardPage
            user={user}
            overview={overview}
            cases={filteredCases}
            caseDetail={caseDetail}
            selectedCase={selectedCase}
            transactions={transactions}
            detectors={detectors}
            setActiveView={setActiveView}
            setSelectedCaseId={setSelectedCaseId}
            setCaseViewMode={setCaseViewMode}
          />
        )}
        
        {activeView === 'escalations' && (
          <EscalationsPage
             api={api}
             cases={filteredCases}
             selectedCaseId={selectedCaseId}
             setSelectedCaseId={setSelectedCaseId}
             refreshCases={refreshCases}
             setActiveView={setActiveView}
             setCaseViewMode={setCaseViewMode}
          />
        )}

        {activeView === 'upload' && (
          <UploadPage
            api={api}
            refreshCases={refreshCases}
            selectedCaseId={selectedCaseId}
            setSelectedCaseId={setSelectedCaseId}
            setNotice={setNotice}
            setActiveView={setActiveView}
            setCaseViewMode={setCaseViewMode}
          />
        )}

        {activeView === 'cases' && caseViewMode === 'list' && (
          <CasesPage
            user={user}
            cases={filteredCases}
            selectedCaseId={selectedCaseId}
            setSelectedCaseId={(id) => { setSelectedCaseId(id); setCaseWorkspaceTab('summary'); }}
            caseDetail={caseDetail}
            detectors={detectors}
            api={api}
            viewMode="list"
            setViewMode={setCaseViewMode}
            refreshCases={refreshCases}
            setCaseDetail={setCaseDetail}
          />
        )}

        {activeView === 'cases' && caseViewMode === 'detail' && selectedCaseId && (
          <div className="case-workspace-container" style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
            <div className="case-workspace-nav" style={{ display: 'flex', gap: '8px', padding: '0 24px', background: 'white', borderBottom: '1px solid #e2e8f0', overflowX: 'auto' }}>
              {workspaceTabs.map(tab => (
                <button
                  key={tab.id}
                  onClick={() => setCaseWorkspaceTab(tab.id)}
                  style={{
                    padding: '16px 16px',
                    background: 'transparent',
                    border: 'none',
                    borderBottom: caseWorkspaceTab === tab.id ? '2px solid #3b82f6' : '2px solid transparent',
                    color: caseWorkspaceTab === tab.id ? '#3b82f6' : '#64748b',
                    fontWeight: caseWorkspaceTab === tab.id ? '600' : '500',
                    cursor: 'pointer',
                    whiteSpace: 'nowrap'
                  }}
                >
                  {tab.label}
                </button>
              ))}
            </div>
            
            <div className="case-workspace-content" style={{ flex: 1, overflowY: 'auto', background: '#f8fafc' }}>
              {caseWorkspaceTab === 'summary' && (
                <CasesPage
                  user={user}
                  cases={filteredCases}
                  selectedCaseId={selectedCaseId}
                  setSelectedCaseId={setSelectedCaseId}
                  caseDetail={caseDetail}
                  detectors={detectors}
                  api={api}
                  viewMode="detail"
                  setViewMode={setCaseViewMode}
                  refreshCases={refreshCases}
                  setCaseDetail={setCaseDetail}
                />
              )}
              {caseWorkspaceTab === 'transactions' && <TransactionsPage transactions={transactions} cases={filteredCases} selectedCaseId={selectedCaseId} setSelectedCaseId={setSelectedCaseId} selectedCase={selectedCase} api={api} forceDetailView={true} />}
              {caseWorkspaceTab === 'fraud' && <FraudPage detectors={detectors} runDetectors={runDetectors} loading={loading} cases={filteredCases} selectedCaseId={selectedCaseId} setSelectedCaseId={setSelectedCaseId} forceDetailView={true} />}
              {caseWorkspaceTab === 'fund-flow' && <FundFlowView graph={graph} transactions={transactions} cases={filteredCases} selectedCaseId={selectedCaseId} setSelectedCaseId={setSelectedCaseId} api={api} forceDetailView={true} />}
              {caseWorkspaceTab === 'money-trail' && <MoneyTrailPage graph={graph} transactions={transactions} selectedCase={selectedCase} caseDetail={caseDetail} cases={filteredCases} selectedCaseId={selectedCaseId} setSelectedCaseId={setSelectedCaseId} forceDetailView={true} />}
              {caseWorkspaceTab === 'ai' && <AiPage api={api} cases={filteredCases} selectedCaseId={selectedCaseId} setSelectedCaseId={setSelectedCaseId} chat={chat} setChat={setChat} transactions={transactions} forceDetailView={true} />}
              {caseWorkspaceTab === 'reports' && <ReportsPage api={api} cases={filteredCases} selectedCaseId={selectedCaseId} selectedCase={selectedCase} setSelectedCaseId={setSelectedCaseId} forceDetailView={true} />}
              {caseWorkspaceTab === 'evidence' && <EvidencePage cases={filteredCases} evidence={evidence} selectedCase={selectedCase} api={api} setEvidence={setEvidence} selectedCaseId={selectedCaseId} setSelectedCaseId={setSelectedCaseId} forceDetailView={true} />}
            </div>
          </div>
        )}

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
    transactions_involved: item?.transactions_involved || item?.transactions || item?.matches || [],
    metadata: item?.metadata || {}
  };
}
