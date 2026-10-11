import React, { useRef, useState, useEffect } from 'react';
import { ArrowRight, Square, Database, Layers, ChevronDown, Check, Plus } from 'lucide-react';

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
      if (!isStreaming && prompt.trim()) {
        onSubmit();
      }
    }
  };

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

      {/* Main Clean Input Box */}
      <div className="bg-[#1e1f20] border border-[#2e2f32] rounded-2xl p-3 shadow-lg focus-within:border-[#3c4043] transition-colors">
        <textarea
          ref={textareaRef}
          value={prompt}
          onChange={(e) => setPrompt(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Ask any question regarding your database..."
          disabled={isStreaming}
          rows={isCentered ? 2 : 1}
          className="w-full bg-transparent text-[#e3e3e3] placeholder-[#5f6368] text-sm outline-none resize-none leading-relaxed font-sans"
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
                <Database className="w-3.5 h-3.5 text-[#9aa0a6]" />
                <span className="font-medium text-xs">{activeCatalog?.name || "Select Database"}</span>
                <ChevronDown className={`w-3 h-3 text-[#5f6368] transition-transform duration-200 ${dropdownOpen ? 'rotate-180 text-[#e3e3e3]' : ''}`} />
              </button>

              {dropdownOpen && (
                <div className="absolute left-0 bottom-full mb-2 w-64 bg-[#1e1f20] border border-[#2e2f32] rounded-xl p-1.5 z-40 shadow-2xl animate-dropdown">
                  <div className="px-2.5 py-1 text-[10px] uppercase font-mono text-[#5f6368]">
                    Select Database
                  </div>
                  {catalogs.map((cat) => {
                    const isSelected = cat.id === (activeCatalog?.id || selectedCatalogId);
                    return (
                      <button
                        key={cat.id}
                        type="button"
                        onClick={() => {
                          if (onSelectCatalog) onSelectCatalog(cat.id);
                          setDropdownOpen(false);
                        }}
                        className={`w-full flex items-center justify-between px-2.5 py-1.5 rounded-md text-xs transition-colors duration-150 text-left cursor-pointer ${
                          isSelected 
                            ? "bg-[#28292a] text-[#e3e3e3] font-medium" 
                            : "text-[#9aa0a6] hover:bg-[#242528] hover:text-[#e3e3e3]"
                        }`}
                      >
                        <div>
                          <div>{cat.name}</div>
                          <div className="text-[10px] text-[#5f6368] font-mono">{cat.dialect?.toUpperCase()}</div>
                        </div>
                        {isSelected && <Check className="w-3.5 h-3.5 text-[#e3e3e3]" />}
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
                disabled={!prompt.trim()}
                className="flex items-center justify-center w-7 h-7 rounded-full bg-[#28292a] hover:bg-[#38393d] text-[#e3e3e3] disabled:opacity-30 disabled:cursor-not-allowed transition-all duration-150 cursor-pointer"
                title="Send query"
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
