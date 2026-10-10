import React, { useState, useRef, useEffect } from 'react';
import { Trash2, Plug, Database, MoreVertical, Unplug } from 'lucide-react';

export default function Navbar({
  onClearChat,
  onOpenDatabaseModal,
  onForgetAllDatabases,
  activeCatalogName,
  activeDialect
}) {
  const [menuOpen, setMenuOpen] = useState(false);
  const menuRef = useRef(null);

  useEffect(() => {
    const handleClickOutside = (e) => {
      if (menuRef.current && !menuRef.current.contains(e.target)) {
        setMenuOpen(false);
      }
    };
    if (menuOpen) {
      document.addEventListener('mousedown', handleClickOutside);
    }
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, [menuOpen]);

  return (
    <header className="sticky top-0 z-30 w-full bg-[#131314] border-b border-[#242528] px-4 py-2.5 select-none">
      <div className="flex items-center justify-between text-xs">
        {/* Brand */}
        <div className="flex items-center gap-2">
          <div className="w-5 h-5 rounded-md bg-emerald-500/10 border border-emerald-500/30 flex items-center justify-center">
            <Database className="w-3 h-3 text-emerald-400" />
          </div>
          <span className="font-semibold text-[#e3e3e3] tracking-tight">NaturalSQL</span>
          {activeCatalogName && (
            <span className="ml-2 px-2 py-0.5 rounded-md bg-[#1e1f20] border border-[#2e2f32] text-[11px] font-mono text-[#9aa0a6] hidden sm:inline-block">
              {activeCatalogName} {activeDialect ? `(${activeDialect.toUpperCase()})` : ''}
            </span>
          )}
        </div>

        {/* Right Actions */}
        <div className="flex items-center gap-2">
          {/* Database Connections Button */}
          <button
            onClick={onOpenDatabaseModal}
            title="Manage Database Connections"
            className="flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-[#1e1f20] hover:bg-[#28292a] text-[#e3e3e3] border border-[#2e2f32] hover:border-[#3c4043] transition-colors cursor-pointer text-xs"
          >
            <Plug className="w-3.5 h-3.5 text-emerald-400" />
            <span className="font-medium text-[11px]">Database Connections</span>
          </button>

          {/* Discreet Actions Dropdown (Clear Chat & Forget All DBs) */}
          <div className="relative" ref={menuRef}>
            <button
              onClick={() => setMenuOpen(!menuOpen)}
              title="More Actions"
              className="p-1.5 hover:text-[#e3e3e3] hover:bg-[#1e1f20] rounded-md text-[#5f6368] transition-colors cursor-pointer"
            >
              <MoreVertical className="w-3.5 h-3.5" />
            </button>

            {menuOpen && (
              <div className="absolute right-0 top-full mt-1.5 w-52 bg-[#1e1f20] border border-[#2e2f32] rounded-xl p-1.5 z-40 shadow-2xl animate-scale-up">
                <button
                  type="button"
                  onClick={() => {
                    setMenuOpen(false);
                    onClearChat();
                  }}
                  className="w-full flex items-center gap-2 px-2.5 py-1.5 rounded-lg text-xs text-[#9aa0a6] hover:text-[#e3e3e3] hover:bg-[#28292a] transition-colors text-left cursor-pointer"
                >
                  <Trash2 className="w-3.5 h-3.5 text-[#5f6368]" />
                  <span>Clear Conversation</span>
                </button>

                <div className="h-px bg-[#26272a] my-1" />

                <button
                  type="button"
                  onClick={() => {
                    setMenuOpen(false);
                    if (onForgetAllDatabases) onForgetAllDatabases();
                  }}
                  className="w-full flex items-center gap-2 px-2.5 py-1.5 rounded-lg text-xs text-red-400 hover:text-red-300 hover:bg-[#2a1315] transition-colors text-left cursor-pointer"
                >
                  <Unplug className="w-3.5 h-3.5" />
                  <span>Forget All Databases</span>
                </button>
              </div>
            )}
          </div>
        </div>
      </div>
    </header>
  );
}
