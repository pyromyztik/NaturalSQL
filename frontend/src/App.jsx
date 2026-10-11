import React, { useState, useEffect, useRef } from 'react';
import { AlertTriangle, RotateCcw, ShieldAlert, Check, X, Database } from 'lucide-react';

import Navbar from './components/Navbar';
import TerminalView from './components/TerminalView';
import SQLViewer from './components/SQLViewer';
import DataTable from './components/DataTable';
import SchemaDrawer from './components/SchemaDrawer';
import PromptDock from './components/PromptDock';
import DatabaseConnectionModal from './components/DatabaseConnectionModal';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

const ChatMessageItem = React.memo(function ChatMessageItem({
  msg,
  isStreaming,
  isExecuting,
  onRetry,
  onExecuteManualSQL,
  onApproveMutation,
  onRejectMutation,
  activeCatalog
}) {
  if (msg.role === 'user') {
    return (
      <div id={`msg-${msg.id}`} className="flex justify-end animate-slide-up scroll-mt-20">
        <div className="max-w-xl px-4 py-2.5 rounded-2xl bg-[#28292a] border border-[#343538] text-[#e3e3e3] text-sm shadow-md space-y-2">
          <div>{msg.text}</div>
          {msg.retryContext && (
            <div className="pt-2 border-t border-[#3c4043] text-xs font-mono space-y-1">
              <div className="flex items-center gap-1.5 text-amber-400 font-sans font-medium text-[11px]">
                <RotateCcw className="w-3 h-3" />
                <span>Bundled Failure Context on Retry</span>
              </div>
              {msg.retryContext.errorFeedback && (
                <div className="text-[#fca5a5] text-[11px] truncate bg-[#1e1515] px-2 py-1 rounded border border-[#4a2424]" title={msg.retryContext.errorFeedback}>
                  Error: {msg.retryContext.errorFeedback}
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    );
  }

  return (
    <div id={`msg-${msg.id}`} className="space-y-3.5 animate-slide-up scroll-mt-20">
      {/* Terminal Execution Logs */}
      <TerminalView
        logs={msg.logs}
        streamTokens={msg.streamTokens}
        thinking={msg.thinking || msg.streamTokens?.thinking}
        isStreaming={isStreaming && msg.status === 'streaming'}
        attempts={msg.attempts}
        totalDurationMs={msg.totalDurationMs}
      />

      {/* Direct Conversational Response (if prompt is not an SQL query) */}
      {msg.responseText && (
        <div className="rounded-xl border border-[#2e2f32] bg-[#1a1b1d] p-4 text-sm text-[#e3e3e3] leading-relaxed shadow-lg animate-fade-in">
          <div className="flex items-center gap-2 mb-3 text-xs font-medium text-[#9aa0a6]">
            <span className="w-1.5 h-1.5 rounded-full bg-[#8ab4f8]" />
            <span>NaturalSQL Assistant</span>
          </div>
          <div className="text-sm text-[#d1d5db] leading-relaxed">
            <ReactMarkdown
              remarkPlugins={[remarkGfm]}
              components={{
                h1: ({ ...props }) => <h1 className="text-base font-semibold text-[#f1f3f4] mt-3 mb-1.5" {...props} />,
                h2: ({ ...props }) => <h2 className="text-sm font-semibold text-[#f1f3f4] mt-2.5 mb-1" {...props} />,
                h3: ({ ...props }) => <h3 className="text-xs font-semibold uppercase tracking-wider text-[#9aa0a6] mt-2 mb-1" {...props} />,
                p: ({ ...props }) => <p className="mb-2.5 leading-relaxed last:mb-0" {...props} />,
                ul: ({ ...props }) => <ul className="list-disc list-outside pl-5 mb-2.5 space-y-1 text-[#d1d5db]" {...props} />,
                ol: ({ ...props }) => <ol className="list-decimal list-outside pl-5 mb-2.5 space-y-1 text-[#d1d5db]" {...props} />,
                li: ({ ...props }) => <li className="pl-1 leading-relaxed" {...props} />,
                code: ({ inline, className, children, ...props }) => {
                  const isBlock = !inline && (String(children).includes('\n') || (className && className.includes('language-')));
                  if (isBlock) {
                    return (
                      <pre className="my-2.5 p-3 rounded-lg bg-[#131314] border border-[#2e2f32] overflow-x-auto font-mono text-xs text-[#a8c7fa] leading-relaxed">
                        <code {...props}>{children}</code>
                      </pre>
                    );
                  }
                  return (
                    <code className="px-1.5 py-0.5 rounded bg-[#242528] border border-[#343538] font-mono text-[12px] text-[#a8c7fa]" {...props}>
                      {children}
                    </code>
                  );
                },
                strong: ({ ...props }) => <strong className="font-semibold text-[#f1f3f4]" {...props} />,
                em: ({ ...props }) => <em className="italic text-[#e3e3e3]" {...props} />,
                blockquote: ({ ...props }) => (
                  <blockquote className="border-l-2 border-[#8ab4f8] pl-3 py-1 my-2 text-[#9aa0a6] italic bg-[#1e1f20]/50 rounded-r" {...props} />
                ),
                table: ({ ...props }) => (
                  <div className="overflow-x-auto my-2.5 rounded-lg border border-[#2e2f32]">
                    <table className="min-w-full text-xs text-left" {...props} />
                  </div>
                ),
                thead: ({ ...props }) => <thead className="bg-[#242528] text-[#9aa0a6] border-b border-[#2e2f32]" {...props} />,
                th: ({ ...props }) => <th className="px-3 py-2 font-medium" {...props} />,
                td: ({ ...props }) => <td className="px-3 py-2 border-b border-[#242528]/80 text-[#d1d5db]" {...props} />,
                hr: ({ ...props }) => <hr className="my-3 border-[#2e2f32]" {...props} />
              }}
            >
              {msg.responseText}
            </ReactMarkdown>
          </div>
        </div>
      )}

      {/* Auto-Patches Badges (if any applied) */}
      {msg.patchesApplied && msg.patchesApplied.length > 0 && (
        <div className="flex flex-wrap gap-1.5 pl-1">
          {msg.patchesApplied.map((patch, idx) => (
            <span 
              key={idx}
              className="px-2 py-0.5 rounded-md bg-[#1e1f20] border border-[#2e2f32] text-[11px] font-mono text-[#9aa0a6]"
            >
              {patch}
            </span>
          ))}
        </div>
      )}

      {/* Verified SQL Code */}
      {msg.finalSql && (
        <SQLViewer
          sql={msg.finalSql}
          isRunning={isExecuting}
          onRun={(sqlToRun) => onExecuteManualSQL(msg.id, sqlToRun)}
        />
      )}

      {/* Human-in-the-Loop Safety Approval Banner for Mutations */}
      {msg.approvalRequired && !msg.execution && !msg.rejected && (
        <div className="rounded-xl border border-amber-500/40 bg-[#221a0f] p-4 text-xs text-[#fde047] shadow-xl animate-fade-in space-y-3">
          <div className="flex items-start gap-3">
            <div className="w-7 h-7 rounded-lg bg-amber-500/20 flex items-center justify-center shrink-0 mt-0.5">
              <ShieldAlert className="w-4 h-4 text-amber-400" />
            </div>
            <div className="space-y-1">
              <div className="font-semibold text-sm text-[#fef08a] flex items-center gap-2">
                <span>Explicit Approval Required Before Execution</span>
                <span className="px-2 py-0.5 rounded text-[10px] font-mono bg-amber-500/20 text-amber-300 border border-amber-500/30">
                  {msg.mutationType || 'MUTATION'}
                </span>
              </div>
              <p className="text-[11px] text-[#fef9c3]/80 leading-relaxed">
                This query will alter, insert, or delete data on <strong className="text-white font-mono">{activeCatalog?.name || 'the connected database'}</strong>.
                Review the statement above. Execution will only proceed with your explicit confirmation.
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2.5 pt-1">
            <button
              onClick={() => onApproveMutation(msg.id, msg.finalSql)}
              disabled={isStreaming}
              className="flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white font-medium text-xs shadow-md transition-colors cursor-pointer"
            >
              <Check className="w-3.5 h-3.5" />
              <span>Approve & Execute</span>
            </button>

            <button
              onClick={() => onRejectMutation(msg.id)}
              disabled={isStreaming}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-[#28292a] hover:bg-[#343538] border border-[#3c4043] text-[#d1d5db] font-medium text-xs transition-colors cursor-pointer"
            >
              <X className="w-3.5 h-3.5" />
              <span>Reject / Cancel</span>
            </button>
          </div>
        </div>
      )}

      {/* Rejected Mutation Message */}
      {msg.rejected && (
        <div className="rounded-xl border border-[#3c4043] bg-[#1a1b1d] p-3 text-xs text-[#9aa0a6] flex items-center gap-2 animate-fade-in">
          <X className="w-4 h-4 text-red-400 shrink-0" />
          <span>Execution cancelled by user. No data was modified on the database.</span>
        </div>
      )}

      {/* Execution Results Data Grid (successful queries only) */}
      {msg.execution && !msg.execution.error && (
        <DataTable
          columns={msg.execution.columns || []}
          rows={msg.execution.rows || []}
          rowCount={msg.execution.row_count ?? msg.execution.rowCount ?? 0}
          durationMs={msg.execution.duration_ms ?? msg.execution.durationMs ?? 0}
        />
      )}

      {/* Unified Error State with Retry Option */}
      {(msg.error || msg.execution?.error) && (
        <div className="rounded-xl border border-[#4a2424] bg-[#1e1515] p-3 text-xs text-[#fca5a5] flex items-center justify-between animate-fade-in">
          <div className="space-y-1 pr-2 overflow-hidden">
            <div className="flex items-center gap-1.5 font-semibold">
              <AlertTriangle className="w-3.5 h-3.5 shrink-0" />
              <span>{msg.execution?.error ? "Execution Error" : "Compilation Issue"}</span>
            </div>
            <p className="font-mono text-[11px] text-[#fca5a5]/90 wrap-break-word whitespace-pre-wrap">
              {msg.error || msg.execution?.error}
            </p>
          </div>

          <button
            onClick={() => onRetry(msg)}
            disabled={isStreaming}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-md bg-[#28292a] hover:bg-[#343538] border border-[#3c4043] text-[#e3e3e3] font-mono text-xs transition-colors shrink-0 ml-3 disabled:opacity-50 cursor-pointer"
            title="Retry with bundled error context"
          >
            <RotateCcw className="w-3.5 h-3.5" />
            <span>Retry with Error Context</span>
          </button>
        </div>
      )}
    </div>
  );
});

export default function App() {
  const [catalogs, setCatalogs] = useState([]);
  const [selectedCatalogId, setSelectedCatalogId] = useState('');
  const [health, setHealth] = useState({});
  const [messages, setMessages] = useState([]);
  const [prompt, setPrompt] = useState('');
  const [isStreaming, setIsStreaming] = useState(false);
  const [schemaDrawerOpen, setSchemaDrawerOpen] = useState(false);
  const [connectionModalOpen, setConnectionModalOpen] = useState(false);
  
  const [executingMsgId, setExecutingMsgId] = useState(null);
  
  const abortControllerRef = useRef(null);
  const chatBottomRef = useRef(null);

  const scrollToBottom = (smooth = true) => {
    const doScroll = () => {
      if (chatBottomRef.current) {
        chatBottomRef.current.scrollIntoView({
          behavior: smooth ? 'smooth' : 'auto',
          block: 'end'
        });
      } else {
        window.scrollTo({
          top: document.documentElement.scrollHeight,
          behavior: smooth ? 'smooth' : 'auto'
        });
      }
    };
    doScroll();
    setTimeout(doScroll, 80);
  };

  const scrollToMessage = (msgId, smooth = true, block = 'start') => {
    const doScroll = () => {
      const el = document.getElementById(`msg-${msgId}`);
      if (el) {
        el.scrollIntoView({
          behavior: smooth ? 'smooth' : 'auto',
          block: block
        });
      }
    };
    doScroll();
    setTimeout(doScroll, 80);
  };

  const loadCatalogs = async (newActiveId = null) => {
    try {
      const res = await fetch('/api/catalogs');
      const data = await res.json();
      setCatalogs(data);
      if (newActiveId) {
        setSelectedCatalogId(newActiveId);
      } else if (data.length > 0) {
        setSelectedCatalogId(prev => (data.some(c => c.id === prev) ? prev : data[0].id));
      } else {
        setSelectedCatalogId('');
      }
    } catch (err) {
      console.error("Error loading catalogs:", err);
    }
  };

  useEffect(() => {
    fetch('/api/health')
      .then(res => res.json())
      .then(data => setHealth(data))
      .catch(err => console.error("Health check error:", err));

    loadCatalogs();
  }, []);

  const activeCatalog = catalogs.find(c => c.id === selectedCatalogId) || catalogs[0];

  const handleSubmit = async (textToSend = null, retryContext = null) => {
    const query = (textToSend || prompt).trim();
    if (!query || isStreaming) return;

    if (!selectedCatalogId && catalogs.length === 0) {
      setConnectionModalOpen(true);
      return;
    }

    setPrompt('');
    setIsStreaming(true);

    const userMessageId = `user_${Date.now()}`;
    const assistantMessageId = `asst_${Date.now()}`;

    setTimeout(() => {
      scrollToMessage(userMessageId, true);
    }, 50);

    setMessages(prev => [
      ...prev,
      {
        id: userMessageId,
        role: 'user',
        text: retryContext ? `Retry: ${query}` : query,
        retryContext: retryContext,
        timestamp: Date.now()
      },
      {
        id: assistantMessageId,
        role: 'assistant',
        question: query,
        logs: [],
        streamTokens: { content: '', thinking: '' },
        thinking: '',
        initialSql: '',
        finalSql: '',
        status: 'streaming',
        patchesApplied: [],
        healerIterations: [],
        execution: null,
        error: null,
        approvalRequired: false,
        isMutation: false,
        mutationType: null,
        rejected: false,
        timestamp: Date.now()
      }
    ]);

    abortControllerRef.current = new AbortController();

    // Compact recent context (strictly last 2 assistant turns) to keep VRAM low on 8GB VRAM systems
    const recentHistory = messages
      .filter(m => m.role === 'assistant' && (m.finalSql || m.responseText))
      .slice(-2)
      .map(m => ({
        question: m.question,
        sql: m.finalSql || null,
        response: m.responseText ? m.responseText.slice(0, 150) : null
      }));

    try {
      const response = await fetch('/api/chat/stream', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          question: query,
          catalog_id: selectedCatalogId || (activeCatalog?.id || ''),
          execute: true,
          failed_sql: retryContext?.failedSql || null,
          error_feedback: retryContext?.errorFeedback || null,
          history: recentHistory.length > 0 ? recentHistory : null
        }),
        signal: abortControllerRef.current.signal
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || `Server responded with ${response.status}`);
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';

      const processChunks = (rawChunk) => {
        const lines = rawChunk.split('\n');
        for (let line of lines) {
          line = line.trim();
          if (!line) continue;
          if (line.startsWith('data:')) {
            const jsonStr = line.replace(/^data:\s*/, '').trim();
            if (!jsonStr) continue;
            try {
              const event = JSON.parse(jsonStr);
              updateAssistantMessage(assistantMessageId, event);
            } catch (parseErr) {
              console.warn("SSE JSON Parse error:", parseErr, jsonStr);
            }
          }
        }
      };

      while (true) {
        const { value, done } = await reader.read();
        if (done) {
          if (buffer.trim()) {
            processChunks(buffer);
          }
          break;
        }

        buffer += decoder.decode(value, { stream: true });
        const normalized = buffer.replace(/\r\n/g, '\n').replace(/\r/g, '\n');
        const lastDoubleNewline = normalized.lastIndexOf('\n\n');
        
        if (lastDoubleNewline !== -1) {
          const completePart = normalized.slice(0, lastDoubleNewline);
          buffer = normalized.slice(lastDoubleNewline + 2);
          processChunks(completePart);
        }
      }
    } catch (err) {
      if (err.name === 'AbortError') {
        setMessages(prev => prev.map(msg => {
          if (msg.id === assistantMessageId) {
            return {
              ...msg,
              status: 'stopped',
              logs: [...(msg.logs || []), '[User] Generation stopped by user.']
            };
          }
          return msg;
        }));
      } else {
        console.error("Stream error:", err);
        setMessages(prev => prev.map(msg => {
          if (msg.id === assistantMessageId) {
            return {
              ...msg,
              status: 'error',
              error: err.message || "Failed to stream query compilation."
            };
          }
          return msg;
        }));
      }
    } finally {
      setIsStreaming(false);
      abortControllerRef.current = null;
    }
  };

  const updateAssistantMessage = (msgId, event) => {
    setMessages(prev => prev.map(msg => {
      if (msg.id !== msgId) return msg;

      const updated = { ...msg };

      switch (event.type) {
        case 'terminal_log':
          updated.logs = [...(updated.logs || []), event.line];
          break;

        case 'terminal_token':
          if (event.token_type === 'thinking') {
            updated.thinking = (updated.thinking || '') + event.token;
          }
          updated.streamTokens = {
            thinking: event.token_type === 'thinking' 
              ? (updated.streamTokens?.thinking || '') + event.token 
              : (updated.streamTokens?.thinking || ''),
            content: event.token_type === 'content'
              ? (updated.streamTokens?.content || '') + event.token
              : (updated.streamTokens?.content || '')
          };
          break;

        case 'generation_complete':
          updated.initialSql = event.sql;
          break;

        case 'surgical_feedback':
          updated.attempts = event.attempt + 1;
          updated.healerIterations = [
            ...(updated.healerIterations || []),
            {
              iteration: event.attempt,
              rejected_sql: event.rejected_sql,
              errors: event.errors,
              surgical_feedback: event.surgical_feedback
            }
          ];
          break;

        case 'query_verified':
          updated.finalSql = event.final_sql;
          updated.patchesApplied = event.patches_applied || [];
          updated.attempts = event.attempts || 1;
          updated.isMutation = event.is_mutation;
          updated.mutationType = event.mutation_type;
          scrollToBottom(true);
          break;

        case 'approval_required':
          updated.approvalRequired = true;
          updated.isMutation = true;
          updated.mutationType = event.mutation_type;
          updated.finalSql = event.final_sql || updated.finalSql;
          scrollToBottom(true);
          break;

        case 'direct_response':
          updated.responseText = event.text;
          scrollToBottom(true);
          break;

        case 'pipeline_complete':
          updated.status = event.status || 'done';
          updated.initialSql = event.initial_sql;
          updated.finalSql = event.final_sql;
          updated.attempts = event.attempts;
          updated.patchesApplied = event.patches_applied || [];
          updated.healerIterations = event.healerIterations || updated.healerIterations;
          updated.isMutation = event.is_mutation;
          updated.mutationType = event.mutation_type;
          if (event.status === 'approval_required') {
            updated.approvalRequired = true;
          }
          updated.execution = event.execution;
          updated.totalDurationMs = event.total_duration_ms;
          if (event.response_text) {
            updated.responseText = event.response_text;
          }
          if (event.logs) updated.logs = event.logs;
          scrollToBottom(true);
          break;

        case 'pipeline_failed':
          updated.status = 'failed';
          updated.error = event.error;
          updated.totalDurationMs = event.total_duration_ms;
          if (event.logs) updated.logs = event.logs;
          scrollToBottom(true);
          break;

        case 'error':
          updated.status = 'error';
          updated.error = event.message;
          scrollToBottom(true);
          break;

        default:
          break;
      }

      return updated;
    }));
  };

  const handleStop = () => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
    }
    setIsStreaming(false);
    setMessages(prev => prev.map(msg => {
      if (msg.status === 'streaming') {
        return {
          ...msg,
          status: 'stopped',
          logs: [...(msg.logs || []), '[User] Generation stopped by user.']
        };
      }
      return msg;
    }));
  };

  const handleClearChat = () => {
    setMessages([]);
  };

  const handleExecuteManualSQL = async (msgId, sqlToRun) => {
    scrollToBottom(true);
    setExecutingMsgId(msgId);
    try {
      const res = await fetch('/api/execute-sql', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          sql: sqlToRun,
          catalog_id: selectedCatalogId || (activeCatalog?.id || ''),
          user_approved: true // Manual Run button is an explicit user action
        })
      });
      const data = await res.json();
      
      setMessages(prev => prev.map(msg => {
        if (msg.id === msgId) {
          return {
            ...msg,
            finalSql: sqlToRun,
            approvalRequired: false,
            execution: data
          };
        }
        return msg;
      }));
      scrollToBottom(true);
    } catch (err) {
      console.error("Manual execution error:", err);
      scrollToBottom(true);
    } finally {
      setExecutingMsgId(null);
    }
  };

  const handleApproveMutation = async (msgId, sqlToRun) => {
    scrollToBottom(true);
    try {
      const res = await fetch('/api/execute-sql', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          sql: sqlToRun,
          catalog_id: selectedCatalogId || (activeCatalog?.id || ''),
          user_approved: true
        })
      });
      const data = await res.json();

      setMessages(prev => prev.map(msg => {
        if (msg.id === msgId) {
          return {
            ...msg,
            approvalRequired: false,
            execution: data
          };
        }
        return msg;
      }));
      scrollToBottom(true);
    } catch (err) {
      console.error("Approve mutation error:", err);
      scrollToBottom(true);
    }
  };

  const handleRejectMutation = (msgId) => {
    setMessages(prev => prev.map(msg => {
      if (msg.id === msgId) {
        return {
          ...msg,
          approvalRequired: false,
          rejected: true
        };
      }
      return msg;
    }));
    scrollToBottom(true);
  };

  const handleRetry = (failedMsg) => {
    const failedSql = failedMsg.finalSql || failedMsg.initialSql || '';
    const errorFeedback = failedMsg.execution?.error || failedMsg.error || '';
    handleSubmit(failedMsg.question, { failedSql, errorFeedback });
  };

  const handleForgetAllDatabases = async () => {
    if (!window.confirm("Are you sure you want to forget all connected databases? This will reset all saved connections.")) {
      return;
    }
    try {
      await fetch('/api/connections', { method: 'DELETE' });
      setCatalogs([]);
      setSelectedCatalogId('');
      setMessages([]);
    } catch (err) {
      console.error("Failed to forget databases:", err);
    }
  };

  return (
    <div className="flex flex-col min-h-screen bg-[#131314] text-[#e3e3e3] selection:bg-[#3c4043] selection:text-white">
      {/* Antigravity Desktop Navbar */}
      <Navbar
        onClearChat={handleClearChat}
        onOpenDatabaseModal={() => setConnectionModalOpen(true)}
        onForgetAllDatabases={handleForgetAllDatabases}
        activeCatalogName={activeCatalog?.name}
        activeDialect={activeCatalog?.dialect}
      />

      {/* Main View */}
      <main className="flex-1 max-w-4xl w-full mx-auto px-4 py-6 flex flex-col justify-between">
        {messages.length === 0 ? (
          /* Empty / Initial State */
          catalogs.length === 0 ? (
            <div className="flex-1 flex flex-col items-center justify-center my-auto w-full text-center max-w-md mx-auto space-y-4 animate-fade-in select-none">
              <div className="w-12 h-12 rounded-2xl bg-emerald-500/10 border border-emerald-500/25 flex items-center justify-center mx-auto text-emerald-400 shadow-lg shadow-emerald-950/20">
                <Database className="w-6 h-6" />
              </div>
              <div className="space-y-1">
                <h1 className="text-3xl font-semibold tracking-tight text-[#f1f3f4]">NaturalSQL</h1>
                <p className="text-xs text-[#9aa0a6] leading-relaxed pt-1">
                  Connect your Oracle, PostgreSQL, or MySQL database to begin querying, inserting, or modifying data in natural English.
                </p>
              </div>
              <button
                onClick={() => setConnectionModalOpen(true)}
                className="px-4 py-2 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-medium shadow-md transition-colors cursor-pointer flex items-center gap-2 mx-auto"
              >
                <span>Connect Database</span>
              </button>
            </div>
          ) : (
            <div className="flex-1 flex flex-col items-center justify-center my-auto w-full">
              <PromptDock
                prompt={prompt}
                setPrompt={setPrompt}
                onSubmit={() => handleSubmit()}
                isStreaming={isStreaming}
                onStop={handleStop}
                sampleQueries={[]}
                activeCatalog={activeCatalog}
                catalogs={catalogs}
                selectedCatalogId={selectedCatalogId}
                onSelectCatalog={(id) => setSelectedCatalogId(id)}
                onToggleSchema={() => setSchemaDrawerOpen(true)}
                onOpenDatabaseModal={() => setConnectionModalOpen(true)}
                isCentered={true}
              />
            </div>
          )
        ) : (
          /* Conversation Thread */
          <div className="space-y-6 pb-44">
            {messages.map((msg) => (
              <ChatMessageItem
                key={msg.id}
                msg={msg}
                isStreaming={isStreaming && msg.status === 'streaming'}
                isExecuting={executingMsgId === msg.id}
                onRetry={handleRetry}
                onExecuteManualSQL={handleExecuteManualSQL}
                onApproveMutation={handleApproveMutation}
                onRejectMutation={handleRejectMutation}
                activeCatalog={activeCatalog}
              />
            ))}
            <div ref={chatBottomRef} className="h-6" />
          </div>
        )}
      </main>

      {/* Floating Bottom Dock (when messages exist) */}
      {messages.length > 0 && (
        <footer className="sticky bottom-0 z-20 bg-linear-to-t from-[#131314] via-[#131314]/90 to-transparent pt-2">
          <PromptDock
            prompt={prompt}
            setPrompt={setPrompt}
            onSubmit={() => handleSubmit()}
            isStreaming={isStreaming}
            onStop={handleStop}
            sampleQueries={[]}
            activeCatalog={activeCatalog}
            catalogs={catalogs}
            selectedCatalogId={selectedCatalogId}
            onSelectCatalog={(id) => setSelectedCatalogId(id)}
            onToggleSchema={() => setSchemaDrawerOpen(true)}
            onOpenDatabaseModal={() => setConnectionModalOpen(true)}
            isCentered={false}
          />
        </footer>
      )}

      {/* Slide-over Schema Drawer */}
      <SchemaDrawer
        isOpen={schemaDrawerOpen}
        onClose={() => setSchemaDrawerOpen(false)}
        catalog={activeCatalog}
        onSelectIdentifier={(id) => setPrompt(prev => prev ? `${prev} ${id}` : id)}
        onOpenDatabaseModal={() => setConnectionModalOpen(true)}
      />

      {/* Live Database Connection Manager Modal */}
      <DatabaseConnectionModal
        isOpen={connectionModalOpen}
        onClose={() => setConnectionModalOpen(false)}
        catalogs={catalogs}
        activeCatalogId={selectedCatalogId}
        onSelectCatalog={(id) => setSelectedCatalogId(id)}
        onCatalogsUpdated={loadCatalogs}
        onForgetAllDatabases={handleForgetAllDatabases}
      />
    </div>
  );
}
