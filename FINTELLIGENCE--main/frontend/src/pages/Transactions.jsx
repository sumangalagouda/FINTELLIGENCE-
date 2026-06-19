import { useMemo, useState } from 'react';
import { flexRender, getCoreRowModel, useReactTable } from '@tanstack/react-table';
import { Search } from 'lucide-react';
import Badge from '../shared/Badge';

const formatAmount = (value) => new Intl.NumberFormat('en-IN', { maximumFractionDigits: 0 }).format(Number(value || 0));

export default function Transactions({ transactions, selectedCase }) {
  const [query, setQuery] = useState('');
  const [flaggedOnly, setFlaggedOnly] = useState(false);

  const filtered = useMemo(() => transactions.filter((txn) => {
    const text = `${txn.description || ''} ${txn.sender_account || ''} ${txn.receiver_account || ''}`.toLowerCase();
    return text.includes(query.toLowerCase()) && (!flaggedOnly || txn.is_flagged || txn.risk_level !== 'low');
  }), [flaggedOnly, query, transactions]);

  const columns = useMemo(() => ([
    { accessorKey: 'date', header: 'Date', cell: ({ getValue }) => (getValue() ? String(getValue()).slice(0, 10) : '-') },
    { accessorKey: 'description', header: 'Description', cell: ({ getValue }) => getValue() || '-' },
    {
      id: 'counterparty',
      header: 'Sender - Receiver',
      cell: ({ row }) => `${row.original.sender_account || 'SELF'} - ${row.original.receiver_account || 'UNKNOWN'}`,
    },
    { accessorKey: 'amount', header: 'Amount', cell: ({ getValue }) => formatAmount(getValue()) },
    { accessorKey: 'type', header: 'Dr/Cr', cell: ({ getValue }) => String(getValue() || '-').toUpperCase() },
    {
      id: 'flags',
      header: 'Flags',
      cell: ({ row }) => <Badge value={row.original.risk_level || (row.original.is_flagged ? 'flagged' : 'clear')} />,
    },
  ]), []);

  // eslint-disable-next-line react-hooks/incompatible-library
  const table = useReactTable({
    data: filtered,
    columns,
    getCoreRowModel: getCoreRowModel(),
  });

  return (
    <section className="stack">
      <div className="toolbar">
        <div className="select-like">{selectedCase?.title || 'No case selected'} / {(selectedCase?.risk_level || 'open').toUpperCase()}</div>
        <label className="search-box">
          <Search size={16} />
          <input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search description / counterparty" />
        </label>
        <label className="check-label">
          <input checked={flaggedOnly} onChange={(event) => setFlaggedOnly(event.target.checked)} type="checkbox" />
          Flagged only
        </label>
        <span className="row-count">{filtered.length} rows</span>
      </div>

      <div className="table-shell">
        <table className="data-table">
          <thead>
            {table.getHeaderGroups().map((headerGroup) => (
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
            {table.getRowModel().rows.length > 0 ? table.getRowModel().rows.map((row) => (
              <tr key={row.id}>
                {row.getVisibleCells().map((cell) => (
                  <td key={cell.id} className={cell.column.id === 'description' ? 'truncate' : ''}>
                    {flexRender(cell.column.columnDef.cell, cell.getContext())}
                  </td>
                ))}
              </tr>
            )) : (
              <tr>
                <td colSpan={columns.length} className="empty-table">
                  No transactions match the current filters.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </section>
  );
}
