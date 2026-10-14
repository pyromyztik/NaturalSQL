import React, { useRef, useState, useEffect } from 'react';
import { ArrowRight, Square, Database, Layers, ChevronDown, Check, Plus, AlertCircle, RotateCcw, Loader2 } from 'lucide-react';

export default function PromptDock({ 
  prompt, 
  setPrompt, 
  onSubmit, 
  isStreaming, 
  onStop, 
  sampleQueries = [],
  activeCatalog = null,
  catalogs = [],
  selectedCatalogId,
  onSelectCatalog,
  onToggleSchema,
  onOpenDatabaseModal,
  onReconnect,
  reconnectingId,
  isCentered = false
}) {
  const textareaRef = useRef(null);
  const dropdownRef = useRef(null);
  const [dropdownOpen, setDropdownOpen] = useState(false);

  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 180)}px`;
    }
  }, [prompt]);

  useEffect(() => {
    const handleClickOutside = (e) => {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target)) {
        setDropdownOpen(false);
      }
    };
    if (dropdownOpen) {
      document.addEventListener('mousedown', handleClickOutside);
    }
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, [dropdownOpen]);

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      if (!isStreaming && prompt.trim() && !isCurrentOffline) {
        onSubmit();
      }
    }
  };

  const isCurrentOffline = Boolean(activeCatalog && (activeCatalog.error || activeCatalog.status === 'offline'));
  const isCurrentConnecting = Boolean(activeCatalog && activeCatalog.status === 'connecting');

  return (
    <div className={`w-full max-w-2xl mx-auto px-4 ${isCentered ? 'my-auto py-12' : 'pb-6 pt-2'}`}>
      {/* Claude-style Hero Header over Chatbox */}
      {isCentered && (
        <div className="mb-8 flex flex-col items-center justify-center text-center animate-fade-in select-none">
          <h1 className="text-3xl sm:text-4xl font-semibold tracking-tight text-[#f1f3f4]">
            NaturalSQL 
          </h1>
          <p className="text-xs sm:text-sm text-[#9aa0a6] mt-2 font-normal">
            Query and interact with your database in natural English
          </p>
        </div>
      )}

      {/* Offline Database Warning Banner */}
      {isCurrentOffline && (
        <div className="mb-3 p-3 rounded-xl bg-[#2a1315] border border-[#5c1d24] text-xs text-[#fca5a5] flex items-center justify-between shadow-lg animate-fade-in">
          <div className="flex items-center gap-2 overflow-hidden mr-2">
            <AlertCircle className="w-4 h-4 text-red-400 shrink-0" />
            <div className="truncate">
              <span className="font-semibold text-white">{activeCatalog?.name}</span> is offline or unreachable.
              <span className="text-red-300/80 ml-1 text-[11px] hidden sm:inline">Start the database server or switch databases.</span>
            </div>
          </div>
          <div className="flex items-center gap-2 shrink-0">
            {onReconnect && (
              <button
                type="button"
                onClick={() => onReconnect(activeCatalog?.id)}
                disabled={reconnectingId === activeCatalog?.id}
                className="px-2.5 py-1 rounded-lg bg-[#3d181c] hover:bg-[#522026] text-red-200 border border-red-800 text-[11px] font-medium transition-colors cursor-pointer flex items-center gap-1.5 shadow-xs"
              >
                {reconnectingId === activeCatalog?.id ? (
                  <Loader2 className="w-3 h-3 animate-spin text-red-300" />
                ) : (
                  <RotateCcw className="w-3 h-3 text-red-300" />
                )}
                <span>{reconnectingId === activeCatalog?.id ? "Connecting..." : "Reconnect"}</span>
              </button>
            )}
            <button
              type="button"
              onClick={onOpenDatabaseModal}
              className="text-[11px] text-red-300 hover:text-white underline cursor-pointer"
            >
              Manage
            </button>
          </div>
        </div>
      )}

      {/* Main Clean Input Box */}
      <div className="bg-[#1e1f20] border border-[#2e2f32] rounded-2xl p-3 shadow-lg focus-within:border-[#3c4043] transition-colors">
        <textarea
          ref={textareaRef}
          value={prompt}
          onChange={(e) => setPrompt(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={
            isCurrentOffline 
              ? `${activeCatalog?.name || 'Selected database'} is currently offline/unreachable. Switch database or click Reconnect.` 
              : isCurrentConnecting
                ? `Checking connection to ${activeCatalog?.name || 'database'}...`
                : "Ask any question regarding your database..."
          }
          disabled={isStreaming || isCurrentOffline}
          rows={isCentered ? 2 : 1}
          className="w-full bg-transparent text-[#e3e3e3] placeholder-[#5f6368] text-sm outline-none resize-none leading-relaxed font-sans disabled:opacity-50"
        />

        {/* Bottom Action Bar */}
        <div className="flex items-center justify-between pt-2 border-t border-[#26272a] mt-1 text-xs">
          {/* Database Selector & Schema View */}
          <div className="flex items-center gap-1.5">
            {/* Database Selector */}
            <div className="relative" ref={dropdownRef}>
              <button
                type="button"
                onClick={() => setDropdownOpen(!dropdownOpen)}
                className="flex items-center gap-1.5 px-2 py-1 rounded-md hover:bg-[#28292a] text-[#9aa0a6] hover:text-[#e3e3e3] transition-colors cursor-pointer"
                title="Select Active Database"
              >
                <div className="relative flex items-center">
                  <Database className="w-3.5 h-3.5 text-[#9aa0a6]" />
                  <span className={`absolute -top-0.5 -right-0.5 w-1.5 h-1.5 rounded-full ${
                    isCurrentOffline 
                      ? 'bg-red-500 shadow-xs shadow-red-500/50' 
                      : isCurrentConnecting 
                        ? 'bg-amber-400 animate-pulse' 
                        : 'bg-emerald-500'
                  }`} />
                </div>
                <span className="font-medium text-xs truncate max-w-37.5">{activeCatalog?.name || "Select Database"}</span>
                {isCurrentOffline && (
                  <span className="text-[10px] text-red-400 font-mono bg-red-950/60 px-1 rounded border border-red-800/40">Offline</span>
                )}
                {isCurrentConnecting && (
                  <span className="text-[10px] text-amber-400 font-mono bg-amber-950/60 px-1 rounded border border-amber-800/40 animate-pulse">Checking</span>
                )}
                <ChevronDown className={`w-3 h-3 text-[#5f6368] transition-transform duration-200 ${dropdownOpen ? 'rotate-180 text-[#e3e3e3]' : ''}`} />
              </button>

              {dropdownOpen && (
                <div className="absolute left-0 bottom-full mb-2 w-72 bg-[#1e1f20] border border-[#2e2f32] rounded-xl p-1.5 z-40 shadow-2xl animate-dropdown">
                  <div className="px-2.5 py-1 text-[10px] uppercase font-mono text-[#5f6368]">
                    Select Database
                  </div>
                  {catalogs.map((cat) => {
                    const isSelected = cat.id === (activeCatalog?.id || selectedCatalogId);
                    const isCatOffline = Boolean(cat.error || cat.status === 'offline');
                    const isCatConnecting = cat.status === 'connecting';
                    const isCatOnline = !isCatOffline && !isCatConnecting;
                    const isReconnectingThis = reconnectingId === cat.id;

                    return (
                      <button
                        key={cat.id}
                        type="button"
                        disabled={isCatOffline || isCatConnecting}
                        onClick={() => {
                          if (isCatOffline || isCatConnecting) return;
                          if (onSelectCatalog) onSelectCatalog(cat.id);
                          setDropdownOpen(false);
                        }}
                        title={
                          isCatOffline 
                            ? `Offline / Unreachable: ${cat.error ? cat.error.split('\n')[0] : 'Connection refused'}` 
                            : isCatConnecting 
                              ? 'Checking database connection...' 
                              : `${cat.name} (${cat.tables?.length || 0} tables)`
                        }
                        className={`w-full flex items-center justify-between px-2.5 py-1.5 rounded-md text-xs transition-colors duration-150 text-left ${
                          isCatOffline
                            ? "opacity-45 text-[#6b7280] bg-transparent hover:bg-transparent cursor-not-allowed select-none"
                            : isCatConnecting
                              ? "opacity-70 text-[#9aa0a6] bg-transparent cursor-wait select-none"
                              : isSelected 
                                ? "bg-[#28292a] text-[#e3e3e3] font-medium cursor-pointer" 
                                : "text-[#9aa0a6] hover:bg-[#242528] hover:text-[#e3e3e3] cursor-pointer"
                        }`}
                      >
                        <div className="flex items-center gap-2 overflow-hidden">
                          <span className={`w-2 h-2 rounded-full shrink-0 ${
                            isCatOffline 
                              ? 'bg-red-500 shadow-xs shadow-red-500/50' 
                              : isCatConnecting 
                                ? 'bg-amber-400 animate-pulse' 
                                : 'bg-emerald-500'
                          }`} />
                          <div className="truncate">
                            <div className={`truncate font-medium ${isCatOffline ? 'text-[#80868b]' : ''}`}>
                              {cat.name}
                            </div>
                            <div className="text-[10px] text-[#5f6368] font-mono flex items-center gap-1.5">
                              <span>{cat.dialect?.toUpperCase()}</span>
                              <span>&bull;</span>
                              {isCatOffline ? (
                                <span className="text-red-400 font-medium">Offline / Unreachable</span>
                              ) : isCatConnecting ? (
                                <span className="text-amber-400 font-mono">Checking...</span>
                              ) : (
                                <span>{cat.tables?.length || 0} tables</span>
                              )}
                            </div>
                          </div>
                        </div>
                        {isCatOffline && (
                          <span className="text-[9px] font-mono text-red-400 bg-red-950/60 border border-red-800/40 px-1.5 py-0.2 rounded shrink-0 ml-1.5">
                            Offline
                          </span>
                        )}
                        {isCatConnecting && (
                          <span className="text-[9px] font-mono text-amber-400 bg-amber-950/60 border border-amber-800/40 px-1.5 py-0.2 rounded shrink-0 ml-1.5 animate-pulse">
                            Checking
                          </span>
                        )}
                        {isSelected && isCatOnline && (
                          <Check className="w-3.5 h-3.5 text-[#e3e3e3] shrink-0 ml-1.5" />
                        )}
                      </button>
                    );
                  })}

                  <div className="h-px bg-[#2e2f32] my-1" />
                  <button
                    type="button"
                    onClick={() => {
                      setDropdownOpen(false);
                      if (onOpenDatabaseModal) onOpenDatabaseModal();
                    }}
                    className="w-full flex items-center gap-2 px-2.5 py-1.5 rounded-md text-xs text-emerald-400 hover:bg-[#242528] transition-colors text-left cursor-pointer font-medium"
                  >
                    <Plus className="w-3.5 h-3.5" />
                    <span>Connect New Database...</span>
                  </button>
                </div>
              )}
            </div>

            <div className="h-3 w-px bg-[#2e2f32]" />

            {/* Schema Viewer button */}
            <button
              type="button"
              onClick={onToggleSchema}
              className="flex items-center gap-1.5 px-2 py-1 rounded-md hover:bg-[#28292a] text-[#9aa0a6] hover:text-[#e3e3e3] transition-colors cursor-pointer"
              title="Inspect Database Schema"
            >
              <Layers className="w-3.5 h-3.5 text-[#9aa0a6]" />
              <span className="font-medium text-xs">Schema</span>
            </button>
          </div>

          {/* Send / Stop Action Button */}
          <div>
            {isStreaming ? (
              <button
                type="button"
                onClick={onStop}
                className="flex items-center justify-center w-7 h-7 rounded-full bg-[#3c4043] hover:bg-[#4a4d52] text-[#e3e3e3] transition-colors cursor-pointer"
                title="Stop generation"
              >
                <Square className="w-3 h-3 fill-current" />
              </button>
            ) : (
              <button
                type="button"
                onClick={onSubmit}
                disabled={!prompt.trim() || isCurrentOffline}
                className="flex items-center justify-center w-7 h-7 rounded-full bg-[#28292a] hover:bg-[#38393d] text-[#e3e3e3] disabled:opacity-30 disabled:cursor-not-allowed transition-all duration-150 cursor-pointer"
                title={isCurrentOffline ? "Cannot run query while database is offline" : "Send query"}
              >
                <ArrowRight className="w-4 h-4" />
              </button>
            )}
          </div>
        </div>
      </div>

      {/* Prompt Suggestions - lines one after the other below the main chat box */}
      {isCentered && sampleQueries && sampleQueries.length > 0 && !isStreaming && (
        <div className="mt-4 flex flex-col space-y-1.5 animate-fade-in">
          {sampleQueries.map((q, idx) => {
            const queryText = q.question || q.title;
            return (
              <button
                key={idx}
                type="button"
                onClick={() => {
                  setPrompt(queryText);
                  if (textareaRef.current) textareaRef.current.focus();
                }}
                className="w-full text-left text-xs text-[#9aa0a6] hover:text-[#e3e3e3] transition-colors py-1 flex items-start gap-2.5 group cursor-pointer"
              >
                <span className="text-[#5f6368] group-hover:text-[#e3e3e3] group-hover:translate-x-1 transition-all duration-150 font-mono select-none mt-0.5 inline-block">
                  →
                </span>
                <span className="leading-relaxed">
                  {queryText}
                </span>
              </button>
            );
          })}
        </div>
      )}
    </div>
  );
}
