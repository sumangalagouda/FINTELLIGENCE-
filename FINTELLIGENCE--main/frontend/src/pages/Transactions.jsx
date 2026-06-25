import { useMemo, useState, useEffect } from 'react';
import { flexRender, getCoreRowModel, useReactTable } from '@tanstack/react-table';
import { Search } from 'lucide-react';
import Badge from '../shared/Badge';
import CaseList from '../components/CaseList';

const formatAmount = (value) => new Intl.NumberFormat('en-IN', { maximumFractionDigits: 0 }).format(Number(value || 0));

export default function Transactions({ transactions, selectedCase, api, cases, selectedCaseId, setSelectedCaseId }) {
  const [query, setQuery] = useState('');
  const [flaggedOnly, setFlaggedOnly] = useState(false);
  const [viewMode, setViewMode] = useState('transactions'); // 'transactions' | 'beneficiaries'
  const [pageViewMode, setPageViewMode] = useState('list'); // 'list' | 'detail'
  const [beneficiaries, setBeneficiaries] = useState([]);
  useEffect(() => {
    if (viewMode === 'beneficiaries' && selectedCase?.id && api) {
      api(`/cases/${selectedCase.id}/beneficiaries`).then((data) => {
        setBeneficiaries(data || []);
      }).catch(console.error);
    }
  }, [viewMode, selectedCase?.id, api]);

  const filtered = useMemo(() => transactions.filter((txn) => {
    const text = `${txn.date || ''} ${txn.description || ''} ${txn.sender_account || ''} ${txn.receiver_account || ''} ${txn.amount || ''}`.toLowerCase();
    return text.includes(query.toLowerCase()) && (!flaggedOnly || txn.is_flagged || txn.risk_level !== 'low');
  }), [flaggedOnly, query, transactions]);

  const columns = useMemo(() => ([
    { accessorKey: 'date', header: 'Date', cell: ({ getValue }) => (getValue() ? <span style={{ color: '#64748b', fontSize: '13px' }}>{String(getValue()).slice(0, 10)}</span> : '-') },
    { accessorKey: 'description', header: 'Description', cell: ({ getValue }) => <span style={{ fontWeight: '500', color: '#334155' }}>{getValue() || '-'}</span> },
    {
      id: 'counterparty',
      header: 'Sender - Receiver',
      cell: ({ row }) => `${row.original.sender_account || 'SELF'} → ${row.original.receiver_account || 'UNKNOWN'}`,
    },
    { accessorKey: 'amount', header: 'Amount', cell: ({ getValue }) => <span style={{ fontWeight: '600', color: '#0f172a', letterSpacing: '-0.02em' }}>₹{formatAmount(getValue())}</span> },
    { accessorKey: 'type', header: 'Type', cell: ({ getValue }) => {
      const type = String(getValue() || '-').toUpperCase();
      const isCr = type === 'CR' || type === 'CREDIT';
      return <span style={{ padding: '4px 8px', borderRadius: '4px', fontSize: '12px', fontWeight: 'bold', background: isCr ? '#ecfdf5' : '#fef2f2', color: isCr ? '#10b981' : '#ef4444' }}>{type}</span>;
    }},
    {
      id: 'flags',
      header: 'Risk Level',
      cell: ({ row }) => <Badge value={row.original.risk_level || (row.original.is_flagged ? 'flagged' : 'clear')} />,
    },
  ]), []);

  const beneficiaryColumns = useMemo(() => ([
    { accessorKey: 'account_number', header: 'Account Number', cell: ({ getValue }) => <span style={{ fontFamily: 'monospace', color: '#64748b' }}>{getValue() || '-'}</span> },
    { accessorKey: 'name', header: 'Name', cell: ({ getValue }) => <strong style={{ color: '#334155' }}>{getValue() || '-'}</strong> },
    { accessorKey: 'total_received', header: 'Total Received', cell: ({ getValue }) => <span style={{ fontWeight: 'bold', color: '#10b981' }}>₹{formatAmount(getValue())}</span> },
    {
      id: 'flags',
      header: 'Status',
      cell: ({ row }) => <Badge value={row.original.is_flagged ? 'high' : 'low'} />,
    },
  ]), []);

  // eslint-disable-next-line react-hooks/incompatible-library
  const table = useReactTable({
    data: filtered,
    columns,
    getCoreRowModel: getCoreRowModel(),
  });

  const bFiltered = useMemo(() => beneficiaries.filter((b) => {
    const text = `${b.name || ''} ${b.account_number || ''}`.toLowerCase();
    return text.includes(query.toLowerCase()) && (!flaggedOnly || b.is_flagged);
  }), [flaggedOnly, query, beneficiaries]);

  const bTable = useReactTable({
    data: bFiltered,
    columns: beneficiaryColumns,
    getCoreRowModel: getCoreRowModel(),
  });

  return (
    <section className="stack">
      <style>{`
        .premium-table-container {
          background: white;
          border-radius: 12px;
          box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05), 0 2px 4px -1px rgba(0, 0, 0, 0.03);
          border: 1px solid #e2e8f0;
          overflow: hidden;
          width: 100%;
          margin-top: 8px;
        }
        .premium-table {
          width: 100%;
          border-collapse: separate;
          border-spacing: 0;
          text-align: left;
        }
        .premium-table th {
          background: #f8fafc;
          padding: 16px 24px;
          font-size: 12px;
          font-weight: 600;
          color: #64748b;
          text-transform: uppercase;
          letter-spacing: 0.05em;
          border-bottom: 1px solid #e2e8f0;
        }
        .premium-table td {
          padding: 16px 24px;
          font-size: 14px;
          color: #334155;
          border-bottom: 1px solid #f1f5f9;
          transition: background-color 0.15s ease;
        }
        .premium-table tbody tr:last-child td {
          border-bottom: none;
        }
        .premium-table tbody tr {
          transition: all 0.2s;
        }
        .premium-table tbody tr:hover td {
          background: #f8fafc;
        }
        .truncate-cell {
          max-width: 250px;
          white-space: nowrap;
          overflow: hidden;
          text-overflow: ellipsis;
        }
      `}</style>

      <div style={{ marginBottom: '16px' }}>
         <button className="link-button" onClick={() => setPageViewMode('list')} style={{ border: 'none', background: 'transparent', color: 'var(--accent)', fontWeight: 'bold', display: 'flex', alignItems: 'center', gap: '8px', cursor: 'pointer' }}>&larr; Back to all cases</button>
      </div>
      <div className="toolbar" style={{ display: 'flex', flexWrap: 'wrap', gap: '16px', alignItems: 'center' }}>
        <div style={{ display: 'flex', background: '#f3f4f6', padding: '4px', borderRadius: '8px' }}>
          <button 
            onClick={() => setViewMode('transactions')} 
            style={{ border: 'none', background: viewMode === 'transactions' ? 'white' : 'transparent', padding: '6px 12px', borderRadius: '4px', cursor: 'pointer', fontWeight: viewMode === 'transactions' ? '600' : 'normal', boxShadow: viewMode === 'transactions' ? '0 1px 2px rgba(0,0,0,0.05)' : 'none' }}>
            Transactions
          </button>
          <button 
            onClick={() => setViewMode('beneficiaries')} 
            style={{ border: 'none', background: viewMode === 'beneficiaries' ? 'white' : 'transparent', padding: '6px 12px', borderRadius: '4px', cursor: 'pointer', fontWeight: viewMode === 'beneficiaries' ? '600' : 'normal', boxShadow: viewMode === 'beneficiaries' ? '0 1px 2px rgba(0,0,0,0.05)' : 'none' }}>
            Beneficiaries
          </button>
        </div>
        <div style={{ marginLeft: 'auto', display: 'flex', alignItems: 'center', gap: '8px', background: 'white', padding: '6px 16px', borderRadius: '20px', border: '1px solid #e2e8f0', boxShadow: '0 1px 2px rgba(0,0,0,0.05)' }}>
          <span style={{ fontSize: '13px', color: '#64748b', fontWeight: '500' }}>Investigation:</span>
          <span style={{ fontSize: '13px', fontWeight: 'bold', color: '#0f172a' }}>{selectedCase?.title || 'No case selected'}</span>
          <span style={{ color: '#cbd5e1' }}>|</span>
          <Badge value={selectedCase?.risk_level || 'open'} />
        </div>
        <label className="search-box">
          <Search size={16} />
          <input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search..." />
        </label>
        <label className="check-label">
          <input checked={flaggedOnly} onChange={(event) => setFlaggedOnly(event.target.checked)} type="checkbox" />
          Flagged only
        </label>
        <span className="row-count">{viewMode === 'transactions' ? filtered.length : bFiltered.length} rows</span>
      </div>

      <div className="premium-table-container">
        <table className="premium-table">
          <thead>
            {(viewMode === 'transactions' ? table : bTable).getHeaderGroups().map((headerGroup) => (
              <tr key={headerGroup.id}>
                {headerGroup.headers.map((header) => (
                  <th key={header.id} scope="col">
                    {header.isPlaceholder ? null : flexRender(header.column.columnDef.header, header.getContext())}
                  </th>
                ))}
              </tr>
            ))}
          </thead>
          <tbody>
            {(viewMode === 'transactions' ? table : bTable).getRowModel().rows.length > 0 ? (viewMode === 'transactions' ? table : bTable).getRowModel().rows.map((row) => (
              <tr key={row.id}>
                {row.getVisibleCells().map((cell) => (
                  <td key={cell.id} className={cell.column.id === 'description' ? 'truncate-cell' : ''}>
                    {flexRender(cell.column.columnDef.cell, cell.getContext())}
                  </td>
                ))}
              </tr>
            )) : (
              <tr>
                <td colSpan={viewMode === 'transactions' ? columns.length : beneficiaryColumns.length} style={{ textAlign: 'center', padding: '48px', color: '#94a3b8' }}>
                  No {viewMode} match the current filters.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </section>
  );
}
