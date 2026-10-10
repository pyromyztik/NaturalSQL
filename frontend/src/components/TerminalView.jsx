import React, { useState, useEffect, useRef } from 'react';
import { Terminal, Copy, Check, ChevronDown, ChevronUp, Loader2 } from 'lucide-react';

export default function TerminalView({ 
  logs = [], 
  streamTokens = { thinking: '', content: '' }, 
  thinking = '',
  isStreaming = false, 
  attempts = 1, 
  totalDurationMs = 0 
}) {
  const [isOpen, setIsOpen] = useState(isStreaming);
  const wasStreamingRef = useRef(isStreaming);
  const [copied, setCopied] = useState(false);
  const terminalBoxRef = useRef(null);
  const userScrolledTerminalRef = useRef(false);

  const activeThinking = thinking || streamTokens?.thinking || '';

  useEffect(() => {
    // When streaming finishes, automatically collapse the terminal output
    if (wasStreamingRef.current && !isStreaming) {
      setIsOpen(false);
    } else if (!wasStreamingRef.current && isStreaming) {
      // When streaming begins, expand to show live compiler reasoning
      setIsOpen(true);
      userScrolledTerminalRef.current = false;
    }
    wasStreamingRef.current = isStreaming;
  }, [isStreaming]);

  const rawLogText = [
    ...logs,
    activeThinking ? `[Thinking] ${activeThinking}` : '',
    streamTokens?.content ? `[Generating] ${streamTokens.content}` : ''
  ].filter(Boolean).join('\n');

  useEffect(() => {
    if (isStreaming && isOpen && terminalBoxRef.current && !userScrolledTerminalRef.current) {
      // Smoothly scroll only within the terminal box itself without touching the window
      terminalBoxRef.current.scrollTop = terminalBoxRef.current.scrollHeight;
    }
  }, [logs, streamTokens, isStreaming, isOpen]);

  const handleTerminalScroll = () => {
    if (!terminalBoxRef.current) return;
    const { scrollTop, scrollHeight, clientHeight } = terminalBoxRef.current;
    userScrolledTerminalRef.current = (scrollHeight - scrollTop - clientHeight) > 30;
  };

  const handleCopy = () => {
    navigator.clipboard.writeText(rawLogText);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="rounded-xl border border-[#2e2f32] bg-[#161718] overflow-hidden transition-all duration-200">
      {/* Header */}
      <div className={`flex items-center justify-between px-3.5 py-2 bg-[#1b1c1e] ${isOpen ? 'border-b border-[#2e2f32]' : ''} transition-colors`}>
        <button 
          onClick={() => setIsOpen(!isOpen)}
          className="flex items-center gap-2 text-left text-xs text-[#9aa0a6] hover:text-[#e3e3e3] transition-colors cursor-pointer"
        >
          <Terminal className="w-3.5 h-3.5 text-[#9aa0a6]" />
          <span className="font-mono font-medium">Terminal Logs</span>
          {attempts > 1 && (
            <span className="px-1.5 py-0.5 rounded-md text-[10px] bg-[#2e2f32] text-[#e3e3e3] font-mono">
              {attempts} attempts
            </span>
          )}
          {totalDurationMs > 0 && (
            <span className="text-[11px] text-[#5f6368] font-mono">
              ({totalDurationMs}ms)
            </span>
          )}
          <ChevronDown className={`w-3.5 h-3.5 ml-1 transition-transform duration-200 ${isOpen ? 'rotate-180 text-[#e3e3e3]' : ''}`} />
        </button>

        <div className="flex items-center gap-2">
          {isStreaming && (
            <span className="flex items-center gap-1.5 text-[11px] text-[#9aa0a6] font-mono">
              <span className="w-2.5 h-2.5 rounded-full border-2 border-[#5f6368] border-t-[#e3e3e3] animate-spin" />
              <span>generating</span>
            </span>
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

      {/* Terminal Body */}
      {isOpen && (
        <div 
          ref={terminalBoxRef}
          onScroll={handleTerminalScroll}
          className="p-3.5 bg-[#0e0f10] text-xs font-mono text-[#d1d5db] overflow-y-auto max-h-80 leading-relaxed animate-fade-in"
        >
          <div className="space-y-1">
            {logs && logs.map((line, idx) => {
              const isError = line.includes('[Error]') || line.includes('[Fatal]') || line.includes('FAILED');
              const isSuccess = line.includes('PASSED') || line.includes('Success');
              const isHealer = line.includes('[Healer]') || line.includes('Feedback');
              const isPatch = line.includes('Auto-Patches') || line.includes('Auto-patched');
              
              let textColor = 'text-[#9aa0a6]';
              if (isError) textColor = 'text-[#f87171]';
              else if (isSuccess) textColor = 'text-[#e3e3e3] font-semibold';
              else if (isHealer) textColor = 'text-[#fcd34d]';
              else if (isPatch) textColor = 'text-[#e3e3e3]';
              else if (line.startsWith('===') || line.startsWith('---')) textColor = 'text-[#5f6368]';

              return (
                <div key={idx} className={`${textColor} whitespace-pre-wrap`}>
                  {line}
                </div>
              );
            })}

            {/* Thought Tokens (Preserved after streaming) */}
            {activeThinking && (
              <div className="text-[#71767b] italic whitespace-pre-wrap mt-1">
                <span className="text-[#8ab4f8] not-italic font-semibold">[Thinking] </span>
                {activeThinking}
                {isStreaming && !streamTokens?.content && <span className="animate-pulse not-italic font-normal">▋</span>}
              </div>
            )}

            {/* Live Streaming SQL Content Tokens */}
            {isStreaming && streamTokens?.content && (
              <div className="text-[#e3e3e3] whitespace-pre-wrap mt-1">
                <span className="text-[#34d399] font-semibold">[Output] </span>
                {streamTokens.content}
                <span className="animate-pulse font-normal">▋</span>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
