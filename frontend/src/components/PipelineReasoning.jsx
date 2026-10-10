import React, { useState } from 'react';
import { 
  Sparkles, CheckCircle2, ChevronDown, ChevronUp, Cpu, 
  ShieldCheck, AlertCircle, Wrench, Database, Layers, ArrowRight
} from 'lucide-react';
import HealerVisualizer from './HealerVisualizer';
import { highlightSQL } from './SQLViewer';

export default function PipelineReasoning({ 
  reasoning = {}, 
  isStreaming = false, 
  initialSql = "", 
  finalSql = "",
  patchesApplied = [],
  healerIterations = [],
  attempts = 1,
  totalDurationMs = 0
}) {
  const [isOpen, setIsOpen] = useState(true);

  // Status computation
  const hasHealer = healerIterations && healerIterations.length > 0;
  const hasPatches = patchesApplied && patchesApplied.length > 0;

  return (
    <div className="rounded-xl border border-white/10 bg-[#0b0f19]/80 backdrop-blur-md overflow-hidden transition-all shadow-xl">
      {/* Header bar */}
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="w-full flex items-center justify-between px-4 py-3 bg-white/[0.02] hover:bg-white/[0.04] transition-colors border-b border-white/5 text-left"
      >
        <div className="flex items-center gap-3">
          {isStreaming ? (
            <div className="relative flex items-center justify-center">
              <span className="w-3 h-3 rounded-full bg-violet-400 animate-ping absolute opacity-75" />
              <span className="w-2.5 h-2.5 rounded-full bg-violet-500" />
            </div>
          ) : (
            <CheckCircle2 className="w-4 h-4 text-emerald-400" />
          )}

          <div>
            <div className="flex items-center gap-2">
              <span className="text-xs font-semibold text-slate-200 tracking-wide">
                {isStreaming ? "Compiler Gatekeeper in Progress..." : "Compiler Gatekeeper Pipeline Trace"}
              </span>

              {attempts > 1 && (
                <span className="px-2 py-0.5 rounded-md bg-amber-500/15 border border-amber-500/30 text-[10px] font-medium text-amber-300">
                  {attempts} attempts (Surgically Repaired)
                </span>
              )}

              {hasPatches && (
                <span className="px-2 py-0.5 rounded-md bg-indigo-500/15 border border-indigo-500/30 text-[10px] font-medium text-indigo-300">
                  {patchesApplied.length} Auto-Patches
                </span>
              )}
            </div>
            
            <p className="text-[11px] text-slate-400 mt-0.5">
              {isStreaming 
                ? (reasoning.statusMessage || "Parsing AST, verifying semantic catalog and auto-patching...") 
                : `Verified in ${totalDurationMs}ms with 0-token auto-repairs and semantic AST bounding.`}
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2 text-slate-400">
          <span className="text-xs hidden sm:inline">{isOpen ? "Hide Trace" : "Show Trace"}</span>
          {isOpen ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
        </div>
      </button>

      {/* Expandable Trace Content */}
      {isOpen && (
        <div className="p-4 space-y-4 text-xs">
          {/* Timeline Nodes */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
            {/* Stage 1 */}
            <div className="p-3 rounded-lg bg-white/[0.02] border border-white/5 space-y-1.5">
              <div className="flex items-center justify-between text-slate-400">
                <span className="font-semibold text-slate-300 flex items-center gap-1.5">
                  <Cpu className="w-3.5 h-3.5 text-indigo-400" />
                  1. Local LLM Draft
                </span>
                <span className="text-[10px] text-slate-500">Ollama</span>
              </div>
              <p className="text-[11px] text-slate-400">
                Prompted model with token-bounded schema catalog and foreign keys.
              </p>
            </div>

            {/* Stage 2 */}
            <div className={`p-3 rounded-lg border space-y-1.5 ${
              hasHealer 
                ? "bg-amber-500/5 border-amber-500/20" 
                : "bg-white/[0.02] border-white/5"
            }`}>
              <div className="flex items-center justify-between text-slate-400">
                <span className="font-semibold text-slate-300 flex items-center gap-1.5">
                  <ShieldCheck className="w-3.5 h-3.5 text-violet-400" />
                  2. AST Gatekeeper
                </span>
                <span className={`text-[10px] font-mono px-1.5 py-0.5 rounded-md ${
                  hasHealer ? "bg-amber-500/20 text-amber-300" : "bg-emerald-500/20 text-emerald-300"
                }`}>
                  {hasHealer ? "Repaired" : "Passed"}
                </span>
              </div>
              <p className="text-[11px] text-slate-400">
                {hasHealer 
                  ? "Hallucinations caught & repaired via surgical feedback." 
                  : "Semantic AST check passed; table and column identifiers verified."}
              </p>
            </div>

            {/* Stage 3 */}
            <div className={`p-3 rounded-lg border space-y-1.5 ${
              hasPatches 
                ? "bg-indigo-500/5 border-indigo-500/20" 
                : "bg-white/[0.02] border-white/5"
            }`}>
              <div className="flex items-center justify-between text-slate-400">
                <span className="font-semibold text-slate-300 flex items-center gap-1.5">
                  <Wrench className="w-3.5 h-3.5 text-cyan-400" />
                  3. Rule-Based Patcher
                </span>
                <span className="text-[10px] font-mono px-1.5 py-0.5 rounded-md bg-cyan-500/20 text-cyan-300">
                  0 Tokens
                </span>
              </div>
              <p className="text-[11px] text-slate-400">
                {hasPatches 
                  ? "Auto-injected missing GROUP BY and safety LIMIT clauses." 
                  : "Query already strictly compliant; 0 AST mutations needed."}
              </p>
            </div>
          </div>

          {/* If Healer was invoked, show full ping-pong visualizer */}
          {hasHealer && (
            <HealerVisualizer 
              healerIterations={healerIterations} 
              patchesApplied={patchesApplied}
              attempts={attempts}
            />
          )}

          {/* Initial Draft vs Final Verified Diff View if different */}
          {initialSql && finalSql && initialSql.trim() !== finalSql.trim() && (
            <div className="rounded-lg border border-white/10 bg-black/40 p-3 space-y-2">
              <div className="flex items-center justify-between text-slate-400 text-[11px]">
                <span className="font-semibold text-slate-300">Query Evolution (Initial Raw vs Verified Final)</span>
                <span className="text-violet-400">Gatekeeper sanitized</span>
              </div>
              
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                <div>
                  <span className="text-[10px] uppercase font-mono text-slate-500 block mb-1">
                    Initial LLM SQL:
                  </span>
                  <pre className="p-2 bg-black/50 border border-white/5 rounded text-[11px] font-mono text-slate-400 overflow-x-auto whitespace-pre-wrap">
                    {initialSql}
                  </pre>
                </div>
                <div>
                  <span className="text-[10px] uppercase font-mono text-emerald-400 block mb-1">
                    Compiled & Verified SQL:
                  </span>
                  <pre className="p-2 bg-black/50 border border-emerald-500/20 rounded text-[11px] font-mono text-emerald-200 overflow-x-auto whitespace-pre-wrap">
                    {finalSql}
                  </pre>
                </div>
              </div>
            </div>
          )}

          {/* Auto-Patches list if no healer was needed */}
          {!hasHealer && hasPatches && (
            <div className="p-3 rounded-lg bg-violet-500/10 border border-violet-500/20">
              <span className="text-[11px] font-semibold text-violet-300 uppercase tracking-wider block mb-1">
                Deterministic AST Auto-Patches (Zero LLM Tokens):
              </span>
              <div className="space-y-1">
                {patchesApplied.map((patch, idx) => (
                  <div key={idx} className="text-xs text-violet-200 font-mono flex items-center gap-1.5">
                    <span className="w-1.5 h-1.5 rounded-full bg-violet-400" />
                    <span>{patch}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

