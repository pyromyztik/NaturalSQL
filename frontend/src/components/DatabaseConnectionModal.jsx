import React, { useState, useEffect } from 'react';
import { 
  X, Database, Check, Trash2, AlertCircle, 
  Loader2, Plus, Plug, ShieldCheck, Unplug 
} from 'lucide-react';

export default function DatabaseConnectionModal({
  isOpen,
  onClose,
  catalogs = [],
  activeCatalogId,
  onSelectCatalog,
  onCatalogsUpdated,
  onForgetAllDatabases
}) {
  const [activeTab, setActiveTab] = useState('connect'); // 'connect' | 'manage'
  const [connectionString, setConnectionString] = useState('');
  const [name, setName] = useState('');
  const [testing, setTesting] = useState(false);
  const [testResult, setTestResult] = useState(null);
  const [connecting, setConnecting] = useState(false);
  const [error, setError] = useState(null);
  const [successMsg, setSuccessMsg] = useState(null);

  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.key === 'Escape') onClose();
    };
    if (isOpen) {
      window.addEventListener('keydown', handleKeyDown);
      setError(null);
      setSuccessMsg(null);
      setTestResult(null);
    }
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  const handleTestConnection = async () => {
    if (!connectionString.trim()) {
      setError("Please enter a connection URI or terminal string to test.");
      return;
    }
    setError(null);
    setTestResult(null);
    setTesting(true);

    try {
      const res = await fetch('/api/connections/test', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ connection_string: connectionString.trim() })
      });
      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.detail || "Connection test failed.");
      }
      setTestResult(data);
      if (data.success && !name) {
        setName(`${data.dialect.toUpperCase()} (${data.display_url})`);
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setTesting(false);
    }
  };

  const handleConnectSubmit = async (e) => {
    e.preventDefault();
    if (!connectionString.trim()) {
      setError("Please enter a connection URI or terminal string.");
      return;
    }
    setError(null);
    setSuccessMsg(null);
    setConnecting(true);

    try {
      const dbName = name.trim() || `${testResult?.dialect?.toUpperCase() || 'Connected'} Database`;
      const res = await fetch('/api/connections', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: dbName,
          connection_string: connectionString.trim()
        })
      });

      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.detail || "Failed to establish connection.");
      }

      setSuccessMsg(data.message || "Database connected successfully!");
      setConnectionString('');
      setName('');
      setTestResult(null);

      if (onCatalogsUpdated) {
        await onCatalogsUpdated(data.catalog.id);
      }
      if (onSelectCatalog) {
        onSelectCatalog(data.catalog.id);
      }

      setTimeout(() => {
        onClose();
      }, 1000);
    } catch (err) {
      setError(err.message);
    } finally {
      setConnecting(false);
    }
  };

  const handleDeleteConnection = async (connId, e) => {
    e.stopPropagation();
    if (!window.confirm(`Are you sure you want to disconnect database '${connId}'?`)) {
      return;
    }

    try {
      const res = await fetch(`/api/connections/${connId}`, {
        method: 'DELETE'
      });
      if (!res.ok) {
        const data = await res.json();
        throw new Error(data.detail || "Failed to disconnect database.");
      }
      if (onCatalogsUpdated) {
        await onCatalogsUpdated();
      }
    } catch (err) {
      setError(err.message);
    }
  };


  const getDialectBadge = (dialect = '') => {
    const d = dialect.toLowerCase();
    if (d.includes('oracle')) {
      return <span className="px-1.5 py-0.5 rounded text-[10px] font-mono font-medium bg-[#ea580c]/15 text-[#fb923c] border border-[#ea580c]/30">Oracle</span>;
    }
    if (d.includes('postgres')) {
      return <span className="px-1.5 py-0.5 rounded text-[10px] font-mono font-medium bg-[#3b82f6]/15 text-[#93c5fd] border border-[#3b82f6]/30">PostgreSQL</span>;
    }
    if (d.includes('mysql')) {
      return <span className="px-1.5 py-0.5 rounded text-[10px] font-mono font-medium bg-[#06b6d4]/15 text-[#67e8f9] border border-[#06b6d4]/30">MySQL</span>;
    }
    return <span className="px-1.5 py-0.5 rounded text-[10px] font-mono font-medium bg-[#10b981]/15 text-[#6ee7b7] border border-[#10b981]/30">{dialect.toUpperCase()}</span>;
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/75 backdrop-blur-xs animate-fade-in">
      <div 
        className="w-full max-w-xl bg-[#1a1b1d] border border-[#2e2f32] rounded-2xl shadow-2xl overflow-hidden flex flex-col max-h-[90vh] animate-scale-up"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Modal Header */}
        <div className="flex items-center justify-between px-5 py-3.5 border-b border-[#2e2f32] bg-[#141517]">
          <div className="flex items-center gap-2">
            <Plug className="w-4 h-4 text-emerald-400" />
            <h2 className="text-sm font-semibold text-[#e3e3e3] tracking-tight">Database Connections</h2>
          </div>
          <button 
            onClick={onClose}
            className="p-1 text-[#9aa0a6] hover:text-[#e3e3e3] hover:bg-[#28292a] rounded-lg transition-colors cursor-pointer"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Tab Switcher */}
        <div className="flex items-center border-b border-[#2e2f32] bg-[#161719] px-5 gap-4">
          <button
            onClick={() => setActiveTab('connect')}
            className={`py-2.5 text-xs font-medium border-b-2 transition-colors cursor-pointer flex items-center gap-1.5 ${
              activeTab === 'connect' 
                ? 'border-emerald-500 text-[#e3e3e3]' 
                : 'border-transparent text-[#9aa0a6] hover:text-[#e3e3e3]'
            }`}
          >
            <Plus className="w-3.5 h-3.5 text-emerald-400" />
            <span>Connect New Database</span>
          </button>

          <button
            onClick={() => setActiveTab('manage')}
            className={`py-2.5 text-xs font-medium border-b-2 transition-colors cursor-pointer flex items-center gap-1.5 ${
              activeTab === 'manage' 
                ? 'border-emerald-500 text-[#e3e3e3]' 
                : 'border-transparent text-[#9aa0a6] hover:text-[#e3e3e3]'
            }`}
          >
            <Database className="w-3.5 h-3.5 text-[#9aa0a6]" />
            <span>Active Connections ({catalogs.length})</span>
          </button>
        </div>

        {/* Modal Body */}
        <div className="p-5 overflow-y-auto flex-1 space-y-4">
          {error && (
            <div className="p-3 bg-[#2a1215] border border-[#5c1d24] text-[#f87171] rounded-xl text-xs flex items-start gap-2 animate-fade-in">
              <AlertCircle className="w-4 h-4 shrink-0 mt-0.5" />
              <div className="flex-1 font-mono text-[11px] leading-relaxed">{error}</div>
            </div>
          )}

          {successMsg && (
            <div className="p-3 bg-[#0d2818] border border-[#1b4d2e] text-[#4ade80] rounded-xl text-xs flex items-center gap-2 animate-fade-in">
              <Check className="w-4 h-4 shrink-0" />
              <span>{successMsg}</span>
            </div>
          )}

          {/* TAB 1: Connect New Database */}
          {activeTab === 'connect' && (
            <form onSubmit={handleConnectSubmit} className="space-y-4">
              <div>
                <label className="block text-xs font-medium text-[#c4c7c5] mb-1">
                  Database Connection URI (Standard format)
                </label>
                <div className="relative">
                  <input
                    type="text"
                    value={connectionString}
                    onChange={(e) => {
                      setConnectionString(e.target.value);
                      setError(null);
                      setTestResult(null);
                    }}
                    placeholder="e.g. postgresql://postgres:password@localhost:5432/dbname"
                    className="w-full px-3 py-2 bg-[#121315] border border-[#2e2f32] rounded-xl text-xs font-mono text-[#e3e3e3] placeholder-[#5f6368] focus:outline-none focus:border-emerald-500 transition-colors"
                  />
                </div>
                <p className="mt-1.5 text-[11px] text-[#80868b] leading-relaxed">
                  Enter a standard Database URI (<code className="text-[#a8c7fa]">dialect://user:pass@host:port/db</code>) or terminal EZConnect (<code className="text-[#a8c7fa]">user/pass@host:1521/service</code>).
                </p>
              </div>


              {/* Friendly Name Input */}
              <div>
                <label className="block text-xs font-medium text-[#c4c7c5] mb-1">
                  Database Friendly Name (Optional)
                </label>
                <input
                  type="text"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder="e.g. Production Oracle / Analytics Postgres"
                  className="w-full px-3 py-2 bg-[#121315] border border-[#2e2f32] rounded-xl text-xs text-[#e3e3e3] placeholder-[#5f6368] focus:outline-none focus:border-[#4a4d52]"
                />
              </div>

              {/* Real-time Connection Test Results Banner */}
              {testResult && (
                <div className={`p-3 rounded-xl border text-xs ${
                  testResult.success 
                    ? 'bg-[#0f2418] border-[#1e4d31] text-[#6ee7b7]' 
                    : 'bg-[#291215] border-[#521c22] text-[#fca5a5]'
                }`}>
                  {testResult.success ? (
                    <div className="space-y-1">
                      <div className="flex items-center gap-1.5 font-semibold">
                        <Check className="w-4 h-4 text-emerald-400" />
                        <span>Connection Verified: {testResult.dialect.toUpperCase()}</span>
                      </div>
                      <p className="text-[11px] text-[#9ae6b4] font-mono">
                        Successfully reflected {testResult.table_count} table(s): {testResult.tables?.slice(0, 6).join(', ')}{testResult.table_count > 6 ? '...' : ''}
                      </p>
                    </div>
                  ) : (
                    <div className="space-y-1">
                      <div className="flex items-center gap-1.5 font-semibold">
                        <AlertCircle className="w-4 h-4 text-red-400" />
                        <span>Connection Failed</span>
                      </div>
                      <p className="text-[11px] font-mono text-red-300">{testResult.error}</p>
                    </div>
                  )}
                </div>
              )}

              {/* Footer Action Buttons */}
              <div className="flex items-center justify-between pt-2">
                <button
                  type="button"
                  onClick={handleTestConnection}
                  disabled={testing || !connectionString.trim()}
                  className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-[#242528] hover:bg-[#2c2d31] border border-[#343538] text-xs font-medium text-[#e3e3e3] transition-colors disabled:opacity-50 cursor-pointer"
                >
                  {testing ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <ShieldCheck className="w-3.5 h-3.5 text-cyan-400" />}
                  <span>{testing ? "Testing..." : "Test Connection"}</span>
                </button>

                <div className="flex items-center gap-2">
                  <button
                    type="button"
                    onClick={onClose}
                    className="px-3 py-1.5 rounded-lg text-xs text-[#9aa0a6] hover:text-[#e3e3e3] hover:bg-[#242528] transition-colors cursor-pointer"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    disabled={connecting || !connectionString.trim()}
                    className="flex items-center gap-1.5 px-4 py-1.5 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-xs font-medium text-white transition-colors disabled:opacity-50 cursor-pointer shadow-md"
                  >
                    {connecting ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Plug className="w-3.5 h-3.5" />}
                    <span>{connecting ? "Connecting..." : "Connect & Save"}</span>
                  </button>
                </div>
              </div>
            </form>
          )}

          {/* TAB 2: Active Connections */}
          {activeTab === 'manage' && (
            <div className="space-y-3">
              {catalogs.length === 0 ? (
                <div className="text-center py-8 text-[#5f6368] space-y-2">
                  <Database className="w-8 h-8 mx-auto opacity-50" />
                  <p className="text-xs">No database connections saved.</p>
                  <button
                    type="button"
                    onClick={() => setActiveTab('connect')}
                    className="text-xs text-emerald-400 hover:underline cursor-pointer"
                  >
                    Connect a database now &rarr;
                  </button>
                </div>
              ) : (
                <>
                  {catalogs.map((cat) => {
                    const isActive = cat.id === activeCatalogId;
                    const tableCount = cat.tables?.length || 0;
                    return (
                      <div
                        key={cat.id}
                        onClick={() => {
                          if (onSelectCatalog) onSelectCatalog(cat.id);
                          onClose();
                        }}
                        className={`p-3.5 rounded-xl border transition-all cursor-pointer flex items-center justify-between group ${
                          isActive
                            ? 'bg-[#1e2320] border-emerald-500/50 shadow-md'
                            : 'bg-[#151618] border-[#2e2f32] hover:border-[#3c4043] hover:bg-[#1a1b1e]'
                        }`}
                      >
                        <div className="space-y-1">
                          <div className="flex items-center gap-2">
                            <span className="text-xs font-semibold text-[#e3e3e3]">{cat.name}</span>
                            {getDialectBadge(cat.dialect)}
                            {isActive && (
                              <span className="text-[10px] font-medium text-emerald-400 bg-emerald-950/60 border border-emerald-800/60 px-1.5 py-0.2 rounded-full">
                                Active
                              </span>
                            )}
                          </div>
                          <div className="text-[11px] font-mono text-[#80868b] truncate max-w-sm">
                            {cat.display_url || cat.id}
                          </div>
                          <div className="text-[11px] text-[#9aa0a6]">
                            {tableCount} table(s) introspected: {cat.tables?.slice(0, 4).map(t => t.name).join(', ')}{tableCount > 4 ? '...' : ''}
                          </div>
                        </div>

                        <div className="flex items-center gap-2">
                          <button
                            type="button"
                            onClick={(e) => handleDeleteConnection(cat.id, e)}
                            title="Disconnect Database"
                            className="p-1.5 text-[#5f6368] hover:text-[#f87171] hover:bg-[#281c1c] rounded-lg transition-colors cursor-pointer opacity-70 group-hover:opacity-100"
                          >
                            <Trash2 className="w-3.5 h-3.5" />
                          </button>
                        </div>
                      </div>
                    );
                  })}

                  {/* Reset All Connections Button */}
                  <div className="pt-3 border-t border-[#26272a] flex justify-end">
                    <button
                      type="button"
                      onClick={() => {
                        if (onForgetAllDatabases) {
                          onForgetAllDatabases();
                          onClose();
                        }
                      }}
                      className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs text-red-400 hover:text-red-300 hover:bg-[#2a1315] border border-red-950 transition-colors cursor-pointer"
                    >
                      <Unplug className="w-3.5 h-3.5" />
                      <span>Forget All Databases</span>
                    </button>
                  </div>
                </>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
