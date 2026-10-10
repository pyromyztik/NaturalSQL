import React, { useState, useEffect } from 'react';
import { X, Database, Key, Link2, ChevronRight, ChevronDown, Table2 } from 'lucide-react';

export default function SchemaDrawer({ isOpen, onClose, catalog = null, onSelectIdentifier, onOpenDatabaseModal }) {
  const [expandedTables, setExpandedTables] = useState({});

  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.key === 'Escape') {
        onClose();
      }
    };
    if (isOpen) {
      window.addEventListener('keydown', handleKeyDown);
    }
    return () => {
      window.removeEventListener('keydown', handleKeyDown);
    };
  }, [isOpen, onClose]);

  if (!isOpen || !catalog) return null;

  const toggleTable = (tblName) => {
    setExpandedTables(prev => ({
      ...prev,
      [tblName]: !prev[tblName]
    }));
  };

  return (
    <div 
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-xs animate-overlay"
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <div className="w-full max-w-xl max-h-[85vh] bg-[#161718] border border-[#2e2f32] rounded-xl shadow-2xl flex flex-col overflow-hidden animate-modal">
        {/* Header */}
        <div className="p-4 bg-[#1b1c1e] border-b border-[#2e2f32] flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <div className="w-7 h-7 rounded-md bg-[#242528] flex items-center justify-center text-[#9aa0a6] shrink-0">
              <Database className="w-4 h-4 text-[#9aa0a6]" />
            </div>
            <div>
              <h3 className="text-xs font-semibold text-[#e3e3e3] flex items-center gap-2">
                <span>{catalog.name}</span>
                <span className="text-[10px] uppercase font-mono px-1.5 py-0.5 rounded-md bg-[#242528] border border-[#2e2f32] text-[#9aa0a6]">
                  {catalog.dialect}
                </span>
              </h3>
              <p className="text-[11px] text-[#5f6368] mt-0.5">{catalog.description}</p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            {onOpenDatabaseModal && (
              <button
                onClick={() => {
                  onClose();
                  onOpenDatabaseModal();
                }}
                className="px-2 py-1 text-[11px] rounded bg-[#242528] hover:bg-[#2c2d30] text-[#e3e3e3] border border-[#2e2f32] transition-colors cursor-pointer"
              >
                + Connect DB
              </button>
            )}
            <button
              onClick={onClose}
              className="p-1.5 rounded-md hover:bg-[#28292a] text-[#9aa0a6] hover:text-[#e3e3e3] transition-colors cursor-pointer"
              title="Close"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        </div>

        {/* Tables List */}
        <div className="flex-1 overflow-y-auto p-4 space-y-2.5">
          <div className="text-[11px] font-mono text-[#5f6368] uppercase mb-1">
            Tables ({catalog.tables ? catalog.tables.length : 0})
          </div>

          {catalog.tables && catalog.tables.map((table) => {
            const isExpanded = !!expandedTables[table.name];
            return (
              <div key={table.name} className="rounded-lg border border-[#242528] bg-[#1a1b1d] overflow-hidden transition-all duration-150">
                <button
                  onClick={() => toggleTable(table.name)}
                  className="w-full flex items-center justify-between p-2.5 hover:bg-[#202124] transition-colors text-left cursor-pointer"
                >
                  <div className="flex items-center gap-2">
                    <Table2 className="w-3.5 h-3.5 text-[#9aa0a6]" />
                    <span className="text-xs font-mono text-[#e3e3e3]">
                      {table.name}
                    </span>
                    <span className="text-[10px] text-[#5f6368] font-mono">
                      ({table.columns ? table.columns.length : 0})
                    </span>
                  </div>

                  <div className="text-[#5f6368]">
                    <ChevronDown className={`w-3.5 h-3.5 transition-transform duration-200 ${isExpanded ? 'rotate-180 text-[#e3e3e3]' : ''}`} />
                  </div>
                </button>

                {isExpanded && (
                  <div className="p-2 border-t border-[#242528] bg-[#131314] space-y-1 animate-fade-in">
                    {table.columns && table.columns.map((col) => (
                      <div 
                        key={col.name}
                        onClick={() => onSelectIdentifier && onSelectIdentifier(`${table.name}.${col.name}`)}
                        className="flex items-start justify-between p-1.5 rounded-md hover:bg-[#1e1f20] cursor-pointer transition-colors"
                      >
                        <div className="flex items-center gap-1.5">
                          {col.is_primary_key && (
                            <Key className="w-3 h-3 text-[#9aa0a6] shrink-0" title="Primary Key" />
                          )}
                          {col.is_foreign_key && (
                            <Link2 className="w-3 h-3 text-[#9aa0a6] shrink-0" title={`Foreign Key: ${col.foreign_target}`} />
                          )}
                          {!col.is_primary_key && !col.is_foreign_key && (
                            <span className="w-1 h-1 rounded-full bg-[#3c4043] shrink-0 ml-1 mr-1" />
                          )}
                          
                          <span className="text-xs font-mono text-[#d1d5db] hover:text-white">
                            {col.name}
                          </span>
                        </div>

                        <div className="text-right">
                          <span className="text-[10px] font-mono text-[#5f6368] uppercase">
                            {col.type}
                          </span>
                          {col.foreign_target && (
                            <span className="block text-[9px] font-mono text-[#9aa0a6]">
                              {col.foreign_target}
                            </span>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            );
          })}
        </div>

        <div className="p-2.5 bg-[#1b1c1e] border-t border-[#2e2f32] text-[11px] text-[#5f6368] font-mono text-center select-none">
          Click column to insert identifier
        </div>
      </div>
    </div>
  );
}
