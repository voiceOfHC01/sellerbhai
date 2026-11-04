import React, { useState, useEffect, useRef } from 'react';
import { apiClient } from '../api/client';
import { ThreadSummary, MessageDetail } from '../types';
import { 
  Inbox, MessageSquare, Send, CheckCircle2, XCircle, AlertTriangle, 
  Clock, ShieldAlert, UserCheck, Bot, User, RefreshCw, Check, Sparkles, Filter, Trash2 
} from 'lucide-react';

export const InboxPage: React.FC = () => {
  const [threads, setThreads] = useState<ThreadSummary[]>([]);
  const [selectedThread, setSelectedThread] = useState<ThreadSummary | null>(null);
  const [messages, setMessages] = useState<MessageDetail[]>([]);
  const [replyText, setReplyText] = useState('');
  const [loading, setLoading] = useState(true);
  const [sending, setSending] = useState(false);
  const [filter, setFilter] = useState<'all' | 'needs_human' | 'drafts' | 'takeover' | 'facebook' | 'instagram' | 'whatsapp'>('all');
  const [editingDraftId, setEditingDraftId] = useState<number | null>(null);
  const [draftEditText, setDraftEditText] = useState('');
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const messagesEndRef = useRef<HTMLDivElement>(null);

  const fetchThreads = async () => {
    try {
      const data = await apiClient.inbox.getThreads();
      setThreads(data);
      if (data.length > 0 && !selectedThread) {
        setSelectedThread(data[0]);
      } else if (selectedThread) {
        const updated = data.find((t) => t.id === selectedThread.id);
        if (updated) setSelectedThread(updated);
      }
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const fetchMessages = async (threadId: number) => {
    try {
      const data = await apiClient.inbox.getMessages(threadId);
      setMessages(data);
    } catch (err) {
      console.error(err);
    }
  };

  useEffect(() => {
    fetchThreads();
    const interval = setInterval(fetchThreads, 5000);
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    if (selectedThread) {
      fetchMessages(selectedThread.id);
    }
  }, [selectedThread?.id]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleSendReply = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedThread || !replyText.trim() || sending) return;

    setSending(true);
    setErrorMsg(null);
    try {
      await apiClient.inbox.sendManualReply(selectedThread.id, replyText.trim());
      setReplyText('');
      await fetchMessages(selectedThread.id);
      await fetchThreads();
    } catch (err: any) {
      setErrorMsg(err.response?.data?.detail || 'Failed to send reply.');
    } finally {
      setSending(false);
    }
  };

  const handleToggleAi = async () => {
    if (!selectedThread) return;
    await apiClient.inbox.toggleAi(selectedThread.id);
    fetchThreads();
  };

  const handleTakeover = async () => {
    if (!selectedThread) return;
    if (selectedThread.status === 'human_takeover') {
      await apiClient.inbox.resumeAi(selectedThread.id);
    } else {
      await apiClient.inbox.takeOver(selectedThread.id);
    }
    fetchThreads();
  };

  const handleApproveDraft = async (draftId: number) => {
    setErrorMsg(null);
    try {
      await apiClient.inbox.approveDraft(draftId);
      if (selectedThread) {
        await fetchMessages(selectedThread.id);
        await fetchThreads();
      }
    } catch (err: any) {
      setErrorMsg(err.response?.data?.detail || 'Failed to approve draft.');
    }
  };

  const handleDiscardDraft = async (draftId: number) => {
    if (confirm('Discard this AI draft?')) {
      await apiClient.inbox.discardDraft(draftId);
      if (selectedThread) {
        await fetchMessages(selectedThread.id);
        await fetchThreads();
      }
    }
  };

  const handleDeleteCustomerData = async () => {
    if (!selectedThread) return;
    if (confirm(`PERMANENT DATA DELETION (GDPR & Meta Compliance):\nAre you sure you want to permanently delete all personal data and conversation history for customer "${selectedThread.customer_name}"?`)) {
      try {
        await apiClient.inbox.deleteCustomerData(selectedThread.customer_id);
        alert('Customer data and associated threads permanently deleted.');
        setSelectedThread(null);
        await fetchThreads();
      } catch (err: any) {
        alert('Failed to delete customer data.');
      }
    }
  };

  const filteredThreads = threads.filter((t) => {
    if (filter === 'needs_human') return t.status === 'human_takeover';
    if (filter === 'drafts') return t.has_pending_draft;
    if (filter === 'takeover') return t.status === 'human_takeover';
    if (filter === 'facebook') return t.channel === 'facebook';
    if (filter === 'instagram') return t.channel === 'instagram';
    if (filter === 'whatsapp') return t.channel === 'whatsapp';
    return true;
  });

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6 h-[calc(100vh-4.5rem)] flex flex-col">
      {/* Page Header */}
      <div className="flex items-center justify-between pb-4 mb-4 border-b border-slate-200">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-xl font-bold text-slate-900">Unified Live Inbox</h1>
            <span className="px-2 py-0.5 rounded-full text-xs font-semibold bg-blue-100 text-blue-800">
              Messenger & Web Gateway
            </span>
          </div>
          <p className="text-xs text-slate-500 mt-0.5">
            Approve AI-generated drafts, monitor 24-hour messaging windows, or take over conversations in real time.
          </p>
        </div>

        <button
          onClick={fetchThreads}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-slate-300 hover:bg-slate-100 text-slate-700 text-xs font-medium transition-colors"
        >
          <RefreshCw className="w-3.5 h-3.5" />
          <span>Refresh</span>
        </button>
      </div>

      {/* Main 2-Pane Inbox Grid */}
      <div className="flex-1 grid grid-cols-1 md:grid-cols-12 gap-6 min-h-0">
        {/* Left Pane: Thread List (4 Cols) */}
        <div className="md:col-span-4 flex flex-col bg-white border border-slate-200 rounded-2xl shadow-sm overflow-hidden min-h-0">
          {/* Filter Pills */}
          <div className="p-3 border-b border-slate-100 bg-slate-50 flex items-center gap-1 overflow-x-auto text-xs no-scrollbar">
            {(['all', 'needs_human', 'drafts', 'facebook', 'instagram', 'whatsapp'] as const).map((f) => (
              <button
                key={f}
                onClick={() => setFilter(f)}
                className={`whitespace-nowrap px-3 py-1 rounded-lg font-medium transition-colors ${
                  filter === f
                    ? 'bg-blue-600 text-white'
                    : 'text-slate-600 hover:bg-slate-200'
                }`}
              >
                {f === 'all' && 'All Chats'}
                {f === 'needs_human' && 'Needs Human 🚨'}
                {f === 'drafts' && 'Needs Approval'}
                {f === 'facebook' && 'Messenger'}
                {f === 'instagram' && 'Instagram'}
                {f === 'whatsapp' && 'WhatsApp'}
              </button>
            ))}
          </div>

          {/* Threads Scroll List */}
          <div className="flex-1 overflow-y-auto divide-y divide-slate-100">
            {filteredThreads.length === 0 ? (
              <div className="p-8 text-center text-slate-400 text-xs">No conversations found.</div>
            ) : (
              filteredThreads.map((t) => {
                const isSelected = selectedThread?.id === t.id;
                return (
                  <div
                    key={t.id}
                    onClick={() => setSelectedThread(t)}
                    className={`p-3.5 cursor-pointer transition-colors relative flex flex-col gap-1.5 ${
                      isSelected ? 'bg-blue-50/70 border-l-4 border-blue-600' : 'hover:bg-slate-50'
                    }`}
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-1.5">
                        <span className="font-semibold text-xs text-slate-900 truncate max-w-[130px]">
                          {t.customer_name}
                        </span>
                        <span className="px-1.5 py-0.2 rounded text-[10px] font-semibold uppercase bg-slate-100 text-slate-600 border border-slate-200">
                          {t.channel}
                        </span>
                      </div>
                      <span className="text-[10px] text-slate-400">
                        {new Date(t.last_activity_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                      </span>
                    </div>

                    <p className="text-xs text-slate-500 line-clamp-1 font-bangla">
                      {t.last_message_text || 'No messages yet'}
                    </p>

                    <div className="flex items-center justify-between pt-1 text-[11px]">
                      {/* Window Guard Status Pill */}
                      <span className={`px-2 py-0.5 rounded-full text-[10px] font-semibold flex items-center gap-1 ${
                        t.is_window_active
                          ? 'bg-emerald-50 text-emerald-700 border border-emerald-200'
                          : 'bg-red-50 text-red-700 border border-red-200'
                      }`}>
                        <Clock className="w-2.5 h-2.5" />
                        {t.is_window_active ? `${t.window_hours_remaining}h left` : 'Expired'}
                      </span>

                      {/* Status Tags */}
                      <div className="flex items-center gap-1">
                        {t.has_pending_draft && (
                          <span className="px-1.5 py-0.5 rounded bg-amber-100 text-amber-800 font-bold text-[9px] animate-pulse">
                            AI Draft
                          </span>
                        )}
                        {t.status === 'human_takeover' && (
                          <span className="px-1.5 py-0.5 rounded bg-rose-100 text-rose-800 font-bold text-[9px] flex items-center gap-0.5 border border-rose-300">
                            <AlertTriangle className="w-2.5 h-2.5 text-rose-600" />
                            Needs Human
                          </span>
                        )}
                      </div>
                    </div>
                  </div>
                );
              })
            )}
          </div>
        </div>

        {/* Right Pane: Conversation View & Manual Reply (8 Cols) */}
        <div className="md:col-span-8 flex flex-col bg-white border border-slate-200 rounded-2xl shadow-sm overflow-hidden min-h-0">
          {!selectedThread ? (
            <div className="flex-1 flex items-center justify-center text-slate-400 text-sm">
              Select a conversation to view chat and reply
            </div>
          ) : (
            <>
              {/* Conversation Top Header */}
              <div className="p-4 border-b border-slate-200 bg-slate-50/70 flex items-center justify-between flex-wrap gap-3">
                <div>
                  <div className="flex items-center gap-2">
                    <h2 className="text-sm font-bold text-slate-900">{selectedThread.customer_name}</h2>
                    <span className="px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider bg-slate-200 text-slate-700">
                      {selectedThread.channel}
                    </span>
                    {selectedThread.customer_phone && (
                      <span className="text-xs text-slate-500 font-mono">
                        📞 {selectedThread.customer_phone}
                      </span>
                    )}
                  </div>

                  {/* 24-Hour Messaging Window Guard Indicator */}
                  <div className="flex items-center gap-2 mt-1">
                    <span className={`inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold ${
                      selectedThread.is_window_active
                        ? 'bg-emerald-100 text-emerald-800'
                        : 'bg-red-100 text-red-800'
                    }`}>
                      <Clock className="w-3 h-3" />
                      {selectedThread.is_window_active
                        ? `Meta 24h Window Active (${selectedThread.window_hours_remaining}h remaining)`
                        : 'Meta 24h Window Expired (Out-of-window sends blocked)'}
                    </span>
                  </div>
                </div>

                {/* Control Actions */}
                <div className="flex items-center gap-2">
                  <button
                    onClick={handleToggleAi}
                    className={`px-3 py-1.5 rounded-xl text-xs font-semibold flex items-center gap-1.5 border transition-all ${
                      selectedThread.ai_enabled
                        ? 'bg-emerald-50 text-emerald-700 border-emerald-300'
                        : 'bg-slate-100 text-slate-600 border-slate-300'
                    }`}
                  >
                    <Bot className="w-3.5 h-3.5" />
                    <span>AI: {selectedThread.ai_enabled ? 'ON' : 'OFF'}</span>
                  </button>

                  <button
                    onClick={handleTakeover}
                    className={`px-3 py-1.5 rounded-xl text-xs font-semibold flex items-center gap-1.5 border transition-all ${
                      selectedThread.status === 'human_takeover'
                        ? 'bg-blue-600 text-white border-blue-600'
                        : 'bg-purple-50 text-purple-700 border-purple-300 hover:bg-purple-100'
                    }`}
                  >
                    <UserCheck className="w-3.5 h-3.5" />
                    <span>{selectedThread.status === 'human_takeover' ? 'Resume AI' : 'Take Over'}</span>
                  </button>

                  <button
                    onClick={handleDeleteCustomerData}
                    title="Delete Customer Personal Data (GDPR / Meta Compliance)"
                    className="p-1.5 text-slate-400 hover:text-rose-600 hover:bg-rose-50 rounded-xl transition-colors border border-transparent hover:border-rose-200"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              </div>

              {/* Handover Alert Banner */}
              {selectedThread.status === 'human_takeover' && (
                <div className="bg-rose-50 border-b border-rose-200 px-4 py-2.5 flex items-center justify-between text-xs text-rose-900">
                  <div className="flex items-center gap-2">
                    <AlertTriangle className="w-4 h-4 text-rose-600 shrink-0" />
                    <span>
                      <strong className="font-semibold">Human Takeover Active:</strong> AI is paused for this thread.
                      {selectedThread.handover_reason && (
                        <span className="ml-1 text-rose-700 italic">({selectedThread.handover_reason})</span>
                      )}
                    </span>
                  </div>
                  <button
                    onClick={handleTakeover}
                    className="px-2.5 py-1 rounded-lg bg-rose-600 text-white font-medium hover:bg-rose-700 transition-colors shrink-0"
                  >
                    Resume AI
                  </button>
                </div>
              )}

              {/* Error Alert Banner */}
              {errorMsg && (
                <div className="p-3 bg-red-50 border-b border-red-200 text-red-700 text-xs flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <AlertTriangle className="w-4 h-4 flex-shrink-0" />
                    <span>{errorMsg}</span>
                  </div>
                  <button onClick={() => setErrorMsg(null)} className="underline font-bold">Dismiss</button>
                </div>
              )}

              {/* Message History & AI Draft Cards */}
              <div className="flex-1 overflow-y-auto p-4 space-y-4 bg-slate-50/30">
                {messages.map((m) => {
                  const isCustomer = m.sender_type === 'customer';
                  const isBot = m.sender_type === 'bot';
                  const isAdmin = m.sender_type === 'admin';

                  // If this is an AI Draft awaiting approval
                  if (m.is_draft) {
                    return (
                      <div
                        key={m.id}
                        className="bg-amber-50 border-2 border-amber-300 rounded-2xl p-4 shadow-sm my-3 animate-fade-in"
                      >
                        <div className="flex items-center justify-between pb-2 mb-2 border-b border-amber-200">
                          <div className="flex items-center gap-2">
                            <Sparkles className="w-4 h-4 text-amber-600" />
                            <span className="text-xs font-bold text-amber-900 uppercase tracking-wider">
                              AI Suggested Response (Draft - Requires Approval)
                            </span>
                          </div>
                          {m.language && (
                            <span className="px-2 py-0.5 rounded bg-amber-200 text-amber-900 font-mono text-[10px] uppercase">
                              {m.language}
                            </span>
                          )}
                        </div>

                        <p className="text-sm text-slate-800 leading-relaxed font-bangla whitespace-pre-line mb-3">
                          {m.content}
                        </p>

                        <div className="flex items-center justify-end gap-2 pt-2 border-t border-amber-200/60">
                          <button
                            onClick={() => handleDiscardDraft(m.id)}
                            className="px-3 py-1.5 rounded-lg border border-slate-300 text-slate-600 hover:bg-white text-xs font-medium transition-colors"
                          >
                            Discard
                          </button>
                          <button
                            onClick={() => handleApproveDraft(m.id)}
                            className="px-4 py-1.5 rounded-lg bg-blue-600 hover:bg-blue-500 text-white text-xs font-bold flex items-center gap-1.5 shadow-sm transition-all"
                          >
                            <Send className="w-3.5 h-3.5" />
                            <span>Approve & Send</span>
                          </button>
                        </div>
                      </div>
                    );
                  }

                  // Normal Sent Messages
                  return (
                    <div
                      key={m.id}
                      className={`flex items-start gap-2.5 ${isCustomer ? '' : 'flex-row-reverse'}`}
                    >
                      <div
                        className={`w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 text-xs font-semibold shadow-sm ${
                          isCustomer
                            ? 'bg-slate-700 text-white'
                            : isBot
                            ? 'bg-blue-600 text-white'
                            : 'bg-purple-600 text-white'
                        }`}
                      >
                        {isCustomer ? <User className="w-4 h-4" /> : isBot ? <Bot className="w-4 h-4" /> : <UserCheck className="w-4 h-4" />}
                      </div>

                      <div className={`max-w-[80%] flex flex-col ${isCustomer ? 'items-start' : 'items-end'}`}>
                        <div
                          className={`px-4 py-2.5 rounded-2xl text-sm leading-relaxed ${
                            isCustomer
                              ? 'bg-white border border-slate-200 text-slate-800 rounded-tl-none shadow-2xs font-bangla'
                              : isBot
                              ? 'bg-blue-600 text-white rounded-tr-none shadow-sm font-bangla'
                              : 'bg-purple-700 text-white rounded-tr-none shadow-sm font-bangla'
                          }`}
                        >
                          {m.is_voice_message && (
                            <div className="flex items-center gap-2 mb-1.5 pb-1.5 border-b border-slate-100 text-xs">
                              <span className="p-1 px-2 rounded-full bg-emerald-100 text-emerald-800 font-bold inline-flex items-center gap-1 text-[10px]">
                                🎙️ WhatsApp Voice Note
                              </span>
                              {m.voice_confidence !== undefined && m.voice_confidence !== null && (
                                <span className={`px-2 py-0.5 rounded-full text-[10px] font-semibold ${
                                  m.voice_confidence >= 0.60
                                    ? 'bg-emerald-50 text-emerald-700 border border-emerald-200'
                                    : 'bg-rose-50 text-rose-700 border border-rose-200 animate-pulse'
                                }`}>
                                  {Math.round(m.voice_confidence * 100)}% Confidence
                                </span>
                              )}
                            </div>
                          )}
                          <p className="whitespace-pre-line">{m.content}</p>
                        </div>

                        <div className="flex items-center gap-1.5 mt-1 px-1 text-[10px] text-slate-400">
                          <span>
                            {new Date(m.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                          </span>
                          <span>•</span>
                          <span className="capitalize">{m.sender_type}</span>
                          {m.delivery_status && (
                            <span className="text-[9px] uppercase font-mono">({m.delivery_status})</span>
                          )}
                        </div>
                      </div>
                    </div>
                  );
                })}
                <div ref={messagesEndRef} />
              </div>

              {/* Manual Reply Input Box */}
              <div className="p-3 border-t border-slate-200 bg-white">
                {!selectedThread.is_window_active && (
                  <div className="mb-2 p-2 rounded-lg bg-red-50 border border-red-200 text-red-700 text-[11px] flex items-center gap-2">
                    <ShieldAlert className="w-4 h-4 text-red-600 flex-shrink-0" />
                    <span>
                      Standard 24-hour messaging window has expired. Direct replies are blocked to comply with Meta Platform policies.
                    </span>
                  </div>
                )}

                <form onSubmit={handleSendReply} className="flex items-center gap-2">
                  <input
                    type="text"
                    value={replyText}
                    onChange={(e) => setReplyText(e.target.value)}
                    disabled={!selectedThread.is_window_active || sending}
                    placeholder={
                      selectedThread.is_window_active
                        ? "Type manual message to customer in Bangla, Banglish or English..."
                        : "Send blocked: 24h messaging window expired"
                    }
                    className="flex-1 px-4 py-2.5 bg-slate-100 border border-slate-200 rounded-xl text-sm focus:outline-none focus:border-blue-500 font-bangla disabled:bg-slate-200 disabled:cursor-not-allowed"
                  />
                  <button
                    type="submit"
                    disabled={!selectedThread.is_window_active || !replyText.trim() || sending}
                    className="px-4 py-2.5 bg-blue-600 hover:bg-blue-500 active:scale-95 text-white rounded-xl text-sm font-semibold shadow-sm disabled:opacity-40 transition-all flex items-center gap-1.5"
                  >
                    <Send className="w-4 h-4" />
                    <span>Send</span>
                  </button>
                </form>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
};
