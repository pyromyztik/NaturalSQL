import React, { useState } from 'react';
import { Stethoscope, AlertTriangle, ArrowRight, RefreshCw, CheckCircle2, ChevronDown, ChevronUp, Cpu, ShieldAlert } from 'lucide-react';
import { highlightSQL } from './SQLViewer';

export default function HealerVisualizer({ healerIterations = [], patchesApplied = [], attempts = 1 }) {
  const [expandedIter, setExpandedIter] = useState(0);

  if (!healerIterations || healerIterations.length === 0) {
    if (patchesApplied && patchesApplied.length > 0) {
      return (
        <div className="rounded-xl border border-emerald-500/30 bg-emerald-950/20 p-4">
          <div className="flex items-center gap-2 text-emerald-400 font-medium text-xs mb-2">
            <CheckCircle2 className="w-4 h-4 text-emerald-400" />
            <span>AST Semantic Check Passed on Attempt #1</span>
          </div>
          <div className="space-y-1.5 pl-6">
            {patchesApplied.map((patch, idx) => (
              <div key={idx} className="text-xs text-emerald-200/90 font-mono flex items-center gap-1.5">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-400" />
                <span>{patch}</span>
              </div>
            ))}
          </div>
        </div>
      );
    }
    return null;
  }

  return (
    <div className="rounded-xl border border-amber-500/30 bg-[#0e121e] overflow-hidden shadow-2xl">
      {/* Header Banner */}
      <div className="flex items-center justify-between px-4 py-3 bg-amber-500/10 border-b border-amber-500/20">
        <div className="flex items-center gap-2.5">
          <div className="p-1.5 rounded-lg bg-amber-500/20 border border-amber-500/30">
            <Stethoscope className="w-4 h-4 text-amber-400 animate-pulse" />
          </div>
          <div>
            <h4 className="text-xs font-bold text-amber-300 tracking-wide uppercase flex items-center gap-2">
              <span>Surgical Healer Feedback Loop</span>
              <span className="px-2 py-0.5 rounded-md bg-amber-500/20 border border-amber-500/30 text-[10px] text-amber-300 lowercase font-mono">
                {healerIterations.length} {healerIterations.length === 1 ? 'repair cycle' : 'repair cycles'}
              </span>
            </h4>
            <p className="text-[11px] text-amber-200/70">
              The AST Gatekeeper caught schema hallucinations and boundedly prompted the LLM with surgical fixes.
            </p>
          </div>
        </div>
      </div>

      {/* Ping-Pong Loop Visualizer */}
      <div className="p-4 space-y-4">
        {healerIterations.map((iter, idx) => {
          const isExpanded = expandedIter === idx;
          return (
            <div 
              key={idx} 
              className="rounded-lg border border-white/10 bg-black/40 overflow-hidden"
            >
              <button
                onClick={() => setExpandedIter(isExpanded ? -1 : idx)}
                className="w-full flex items-center justify-between p-3 bg-white/2 hover:bg-white/5 transition-colors text-left"
              >
                <div className="flex items-center gap-2.5">
                  <span className="flex items-center justify-center w-5 h-5 rounded-full bg-rose-500/20 text-rose-300 font-bold text-[10px] border border-rose-500/30">
                    {iter.iteration || (idx + 1)}
                  </span>
                  <div>
                    <span className="text-xs font-semibold text-slate-200">
                      Iteration #{iter.iteration || (idx + 1)}: Schema Hallucination Detected
                    </span>
                    <span className="block text-[11px] text-slate-400">
                      {iter.errors && iter.errors[0] ? iter.errors[0] : "Invalid table or column identifier"}
                    </span>
                  </div>
                </div>

                <div className="flex items-center gap-2 text-slate-400">
                  <span className="text-[11px]">Details</span>
                  {isExpanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
                </div>
              </button>

              {isExpanded && (
                <div className="p-3.5 border-t border-white/5 space-y-3 text-xs">
                  {/* Ping-pong step diagram */}
                  <div className="flex items-center justify-between px-3 py-2 rounded-lg bg-white/2 border border-white/5 text-[11px]">
                    <div className="flex items-center gap-1.5 text-slate-300 font-medium">
                      <Cpu className="w-3.5 h-3.5 text-indigo-400" />
                      <span>1. LLM Generation</span>
                    </div>
                    <ArrowRight className="w-3.5 h-3.5 text-amber-400 animate-ping-pong" />
                    <div className="flex items-center gap-1.5 text-rose-300 font-medium">
                      <ShieldAlert className="w-3.5 h-3.5 text-rose-400" />
                      <span>2. AST Gatekeeper Rejection</span>
                    </div>
                    <ArrowRight className="w-3.5 h-3.5 text-amber-400 animate-ping-pong" />
                    <div className="flex items-center gap-1.5 text-emerald-300 font-medium">
                      <RefreshCw className="w-3.5 h-3.5 text-emerald-400" />
                      <span>3. Surgical Repair Turn</span>
                    </div>
                  </div>

                  {/* Rejected Query */}
                  <div>
                    <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider block mb-1">
                      Rejected Query (Attempt #{iter.iteration}):
                    </span>
                    <pre className="p-2.5 rounded-lg bg-black/60 border border-white/5 text-slate-300 font-mono text-[11px] whitespace-pre-wrap overflow-x-auto">
                      {highlightSQL(iter.rejected_sql)}
                    </pre>
                  </div>

                  {/* Surgical Feedback */}
                  <div>
                    <span className="text-[11px] font-semibold text-amber-400 uppercase tracking-wider flex items-center gap-1 mb-1">
                      <AlertTriangle className="w-3 h-3 text-amber-400" />
                      Surgical Feedback Sent to LLM (with RapidFuzz suggestions):
                    </span>
                    <div className="p-2.5 rounded-lg bg-amber-500/10 border border-amber-500/20 text-amber-200/90 font-mono text-[11px] whitespace-pre-wrap">
                      {iter.surgical_feedback || (iter.errors ? iter.errors.join("\n") : "")}
                    </div>
                  </div>
                </div>
              )}
            </div>
          );
        })}

        {/* Patches notice */}
        {patchesApplied && patchesApplied.length > 0 && (
          <div className="p-3 rounded-lg bg-violet-500/10 border border-violet-500/20">
            <span className="text-[11px] font-semibold text-violet-300 uppercase tracking-wider block mb-1.5">
              Deterministic AST Auto-Patches Applied (0 Tokens):
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
    </div>
  );
}

