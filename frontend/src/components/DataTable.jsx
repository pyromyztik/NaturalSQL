import React, { useState, useMemo } from 'react';
import { Table, Download, Search, ChevronLeft, ChevronRight, ArrowUpDown, Clock } from 'lucide-react';

export default function DataTable({ 
  columns = [], 
  rows = [], 
  rowCount = 0, 
  durationMs = 0, 
  error = null 
}) {
  const [searchTerm, setSearchTerm] = useState('');
  const [sortCol, setSortCol] = useState(null);
  const [sortAsc, setSortAsc] = useState(true);
  const [page, setPage] = useState(1);
  const pageSize = 10;

  const filteredRows = useMemo(() => {
    if (!rows || rows.length === 0) return [];
    
    let res = [...rows];
    
    if (searchTerm.trim()) {
      const q = searchTerm.toLowerCase();
      res = res.filter(row => 
        Object.values(row).some(val => 
          String(val).toLowerCase().includes(q)
        )
      );
    }

    if (sortCol) {
      res.sort((a, b) => {
        const valA = a[sortCol];
        const valB = b[sortCol];
        if (valA === valB) return 0;
        if (valA === null || valA === undefined) return 1;
        if (valB === null || valB === undefined) return -1;
        
        if (typeof valA === 'number' && typeof valB === 'number') {
          return sortAsc ? valA - valB : valB - valA;
        }
        return sortAsc 
          ? String(valA).localeCompare(String(valB)) 
          : String(valB).localeCompare(String(valA));
      });
    }

    return res;
  }, [rows, searchTerm, sortCol, sortAsc]);

  const totalPages = Math.ceil(filteredRows.length / pageSize) || 1;
  const paginatedRows = useMemo(() => {
    const start = (page - 1) * pageSize;
    return filteredRows.slice(start, start + pageSize);
  }, [filteredRows, page, pageSize]);

  const handleSort = (col) => {
    if (sortCol === col) {
      setSortAsc(!sortAsc);
    } else {
      setSortCol(col);
      setSortAsc(true);
    }
  };

  const exportCSV = () => {
    if (!rows || rows.length === 0) return;
    const header = columns.join(',');
    const body = rows.map(r => 
      columns.map(c => {
        const val = r[c] !== null && r[c] !== undefined ? String(r[c]) : '';
        return `"${val.replace(/"/g, '""')}"`;
      }).join(',')
    ).join('\n');
    
    const blob = new Blob([`${header}\n${body}`], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `naturalsql_${Date.now()}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const exportJSON = () => {
    if (!rows || rows.length === 0) return;
    const blob = new Blob([JSON.stringify(rows, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `naturalsql_${Date.now()}.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  if (error) {
    return (
      <div className="rounded-xl border border-[#4a2424] bg-[#1e1515] p-3 text-xs text-[#fca5a5]">
        <div className="font-semibold mb-1">Execution Error</div>
        <p className="font-mono bg-[#140e0e] p-2 rounded border border-[#3b1a1a]">
          {error}
        </p>
      </div>
    );
  }

  if (!rows || rows.length === 0) {
    return (
      <div className="rounded-xl border border-[#2e2f32] bg-[#161718] p-6 text-center text-xs text-[#9aa0a6]">
        <div>Query executed successfully. 0 rows returned.</div>
        <div className="text-[11px] text-[#5f6368] mt-1 font-mono">{durationMs}ms</div>
      </div>
    );
  }

  return (
    <div className="rounded-xl border border-[#2e2f32] bg-[#161718] overflow-hidden flex flex-col">
      {/* Table Top Controls */}
      <div className="flex flex-wrap items-center justify-between gap-3 px-3.5 py-2 bg-[#1b1c1e] border-b border-[#2e2f32]">
        <div className="flex items-center gap-2.5">
          <div className="flex items-center gap-1.5 text-xs font-semibold text-[#e3e3e3]">
            <Table className="w-3.5 h-3.5 text-emerald-400" />
            <span>Query Results</span>
          </div>
          <span className="text-[#3c4043]">|</span>
          <div className="flex items-center gap-1.5 text-xs font-mono text-[#9aa0a6]">
            <span>{rows.length} {rows.length === 1 ? 'row' : 'rows'}</span>
            <span>•</span>
            <span>{durationMs}ms</span>
          </div>
        </div>

        <div className="flex items-center gap-2">
          {/* Search box */}
          <div className="relative">
            <Search className="w-3 h-3 text-[#5f6368] absolute left-2 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              value={searchTerm}
              onChange={(e) => {
                setSearchTerm(e.target.value);
                setPage(1);
              }}
              placeholder="Search table..."
              className="pl-7 pr-2 py-0.5 bg-[#131314] border border-[#2e2f32] focus:border-[#4a4d52] rounded-md text-xs text-[#e3e3e3] placeholder-[#5f6368] outline-none w-32 sm:w-44 transition-colors"
            />
          </div>

          <button
            onClick={exportCSV}
            title="Download CSV"
            className="px-2 py-0.5 bg-[#1e1f20] hover:bg-[#28292a] text-[#9aa0a6] hover:text-[#e3e3e3] text-xs font-mono rounded-md border border-[#2e2f32] transition-colors cursor-pointer"
          >
            csv
          </button>
          <button
            onClick={exportJSON}
            title="Download JSON"
            className="px-2 py-0.5 bg-[#1e1f20] hover:bg-[#28292a] text-[#9aa0a6] hover:text-[#e3e3e3] text-xs font-mono rounded-md border border-[#2e2f32] transition-colors cursor-pointer"
          >
            json
          </button>
        </div>
      </div>

      {/* Grid container */}
      <div className="overflow-x-auto max-h-80">
        <table className="w-full text-left text-xs text-[#d1d5db]">
          <thead className="bg-[#1e1f20] text-[#9aa0a6] uppercase text-[10px] tracking-wider sticky top-0 z-10 border-b border-[#2e2f32]">
            <tr>
              {columns.map((col) => (
                <th
                  key={col}
                  onClick={() => handleSort(col)}
                  className="px-3 py-2 font-medium cursor-pointer hover:text-[#e3e3e3] select-none transition-colors"
                >
                  <div className="flex items-center gap-1 font-mono">
                    <span>{col}</span>
                    <ArrowUpDown className="w-2.5 h-2.5 opacity-40 hover:opacity-100" />
                  </div>
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-[#242528]">
            {paginatedRows.map((row, rIdx) => (
              <tr key={rIdx} className="hover:bg-[#1c1d1f] transition-colors">
                {columns.map((col) => {
                  const val = row[col];
                  return (
                    <td key={col} className="px-3 py-2 font-mono whitespace-nowrap text-[#e3e3e3]">
                      {val === null || val === undefined ? (
                        <span className="text-[#5f6368] italic">NULL</span>
                      ) : (
                        String(val)
                      )}
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Pagination Footer */}
      {totalPages > 1 && (
        <div className="flex items-center justify-between px-3.5 py-1.5 bg-[#1b1c1e] border-t border-[#2e2f32] text-xs text-[#9aa0a6] font-mono">
          <div>
            {(page - 1) * pageSize + 1}-{Math.min(page * pageSize, filteredRows.length)} of {filteredRows.length}
          </div>
          <div className="flex items-center gap-1">
            <button
              onClick={() => setPage(p => Math.max(1, p - 1))}
              disabled={page === 1}
              className="p-1 rounded-md hover:bg-[#28292a] text-[#9aa0a6] hover:text-[#e3e3e3] disabled:opacity-30 disabled:cursor-not-allowed cursor-pointer"
            >
              <ChevronLeft className="w-3.5 h-3.5" />
            </button>
            <span>
              {page} / {totalPages}
            </span>
            <button
              onClick={() => setPage(p => Math.min(totalPages, p + 1))}
              disabled={page === totalPages}
              className="p-1 rounded-md hover:bg-[#28292a] text-[#9aa0a6] hover:text-[#e3e3e3] disabled:opacity-30 disabled:cursor-not-allowed cursor-pointer"
            >
              <ChevronRight className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
