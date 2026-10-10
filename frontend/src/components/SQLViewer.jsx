import React, { useState } from 'react';
import { Copy, Check, Play, Edit3, Terminal } from 'lucide-react';

const SQL_KEYWORDS = new Set([
  'SELECT', 'FROM', 'WHERE', 'JOIN', 'LEFT', 'RIGHT', 'INNER', 'OUTER', 'FULL',
  'ON', 'GROUP', 'BY', 'ORDER', 'HAVING', 'LIMIT', 'OFFSET', 'AS', 'AND', 'OR',
  'NOT', 'IN', 'IS', 'NULL', 'LIKE', 'ILIKE', 'BETWEEN', 'CASE', 'WHEN', 'THEN',
  'ELSE', 'END', 'ASC', 'DESC', 'WITH', 'UNION', 'ALL', 'DISTINCT', 'OVER', 'PARTITION'
]);

const SQL_FUNCS = new Set([
  'COUNT', 'SUM', 'AVG', 'MIN', 'MAX', 'COALESCE', 'ROUND', 'UPPER', 'LOWER',
  'TRIM', 'CONCAT', 'NOW', 'DATE', 'STRFTIME', 'LENGTH', 'SUBSTR'
]);

export function highlightSQL(sql) {
  if (!sql) return '';
  
  const tokens = sql.split(/(\s+|--[^\n]*|'[^']*'|"[^"]*"|[(),;=<>!+*\/])/g);
  
  return tokens.map((token, idx) => {
    if (!token) return null;
    
    // Comments
    if (token.startsWith('--')) {
      return <span key={idx} className="sql-comment">{token}</span>;
    }
    // String literals
    if ((token.startsWith("'") && token.endsWith("'")) || (token.startsWith('"') && token.endsWith('"'))) {
      return <span key={idx} className="sql-string">{token}</span>;
    }
    // Numbers
    if (/^\d+(\.\d+)?$/.test(token)) {
      return <span key={idx} className="sql-number">{token}</span>;
    }
    
    const upper = token.toUpperCase();
    if (SQL_KEYWORDS.has(upper)) {
      return <span key={idx} className="sql-keyword">{token}</span>;
    }
    if (SQL_FUNCS.has(upper)) {
      return <span key={idx} className="sql-func">{token}</span>;
    }
    
    return <span key={idx} className="text-[#d1d5db]">{token}</span>;
  });
}

export default function SQLViewer({ sql, title = "Generated SQL Query", onRun, isRunning = false }) {
  const [copied, setCopied] = useState(false);
  const [isEditing, setIsEditing] = useState(false);
  const [editedSQL, setEditedSQL] = useState(sql);

  const handleCopy = () => {
    navigator.clipboard.writeText(isEditing ? editedSQL : sql);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleExecute = () => {
    if (onRun) {
      onRun(isEditing ? editedSQL : sql);
    }
  };

  return (
    <div className="rounded-xl border border-[#2e2f32] bg-[#161718] overflow-hidden">
      {/* Clean Stark Header */}
      <div className="flex items-center justify-between px-3.5 py-2 bg-[#1b1c1e] border-b border-[#2e2f32]">
        <div className="flex items-center gap-2">
          <Terminal className="w-3.5 h-3.5 text-[#9aa0a6]" />
          <span className="text-xs font-mono font-medium text-[#e3e3e3]">
            {title}
          </span>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={() => {
              setIsEditing(!isEditing);
              if (!isEditing) setEditedSQL(sql);
            }}
            className="px-2 py-0.5 text-[11px] font-mono text-[#9aa0a6] hover:text-[#e3e3e3] hover:bg-[#28292a] rounded-md transition-colors cursor-pointer"
          >
            {isEditing ? "View" : "Edit"}
          </button>

          {onRun && (
            <button
              onClick={handleExecute}
              disabled={isRunning}
              className="flex items-center gap-1 px-2.5 py-0.5 text-[11px] font-mono text-[#e3e3e3] bg-[#28292a] hover:bg-[#343538] border border-[#3c4043] rounded-md transition-colors disabled:opacity-50 cursor-pointer"
            >
              <Play className="w-3 h-3 fill-current" />
              <span>{isRunning ? "Running" : "Run"}</span>
            </button>
          )}

          <button
            onClick={handleCopy}
            className="flex items-center gap-1 px-2 py-0.5 text-[11px] font-mono text-[#9aa0a6] hover:text-[#e3e3e3] hover:bg-[#28292a] rounded-md transition-colors cursor-pointer"
          >
            {copied ? (
              <>
                <Check className="w-3 h-3 text-[#e3e3e3]" />
                <span>copied</span>
              </>
            ) : (
              <>
                <Copy className="w-3 h-3" />
                <span>copy</span>
              </>
            )}
          </button>
        </div>
      </div>

      {/* SQL Editor / Code Block */}
      <div className="p-3.5 bg-[#0e0f10] text-xs font-mono leading-relaxed overflow-x-auto">
        {isEditing ? (
          <textarea
            value={editedSQL}
            onChange={(e) => setEditedSQL(e.target.value)}
            className="w-full h-32 p-2 bg-[#131314] border border-[#2e2f32] rounded-md text-[#e3e3e3] focus:outline-none focus:border-[#4a4d52] font-mono text-xs resize-y"
            placeholder="Enter SQL query..."
          />
        ) : (
          <pre className="whitespace-pre-wrap select-text">
            {highlightSQL(sql)}
          </pre>
        )}
      </div>
    </div>
  );
}
