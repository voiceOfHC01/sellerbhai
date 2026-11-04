import React, { useState, useRef, useEffect } from 'react';
import { apiClient } from '../api/client';
import { TestChatResponse, RetrievedSource, ToolCallLog } from '../types';
import { Send, User, Bot, AlertTriangle, Database, Wrench, RotateCcw, Clock, Sparkles, Check, ChevronRight } from 'lucide-react';

interface ChatMessage {
  id: string;
  sender: 'customer' | 'bot';
  text: string;
  timestamp: string;
  detectedLanguage?: string;
  retrievedSources?: RetrievedSource[];
  toolCalls?: ToolCallLog[];
  handoverTriggered?: boolean;
}

const SAMPLE_PROMPTS = [
  { label: '🇧🇩 Bangla Script: দাম ও কালার', text: 'আসসালামু আলাইকুম ভাই! পোলো শার্টের দাম কত আর কি কি সাইজ আছে?' },
  { label: '🇧🇩 Banglish: দাম জিজ্ঞাসা', text: 'vai eitar dam koto? navy blue colour ache?' },
  { label: '🇧🇩 Banglish: ডেলিভারি চার্জ', text: 'dhakar vitore delivery charge koto lagbe? koto din lagbe?' },
  { label: '🇧🇩 Bangla Script: অর্ডার প্লেস', text: 'আমি ব্ল্যাক সাইজ L নিতে চাই। নাম: তানভীর রহমান, ফোন: 01712345678, ঠিকানা: বাড়ি ১২, রোড ৪, ধানমন্ডি, ঢাকা।' },
  { label: '🇧🇩 Banglish: ক্যাশ অন ডেলিভারি', text: 'deliveryman er kache dekhe taka dewa jabe kina?' },
  { label: '🇬🇧 English: Product Query', text: 'What is the fabric composition of the cotton polo shirt?' },
  { label: '🚫 Unlisted Price / Bargaining', text: 'Bhai 300 taka te dewa jabe? Ekdam 50% discount den' },
  { label: '⚠️ Handover Trigger: Human Agent', text: 'Ami apnader manager er shathe kotha bolte chai.' },
  { label: '⚠️ Handover Trigger: Complaint', text: 'Ami ager order niye khub biroktow! Agent er sathe connect koren.' },
  { label: '🇬🇧 English: Return Policy', text: 'What is your return and exchange policy if size does not fit?' },
];

export const TestChatPage: React.FC = () => {
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      id: 'welcome',
      sender: 'bot',
      text: 'Assalamu Alaikum! StyleCraft BD তে আপনাকে স্বাগতম। আপনি কোন পণ্য দেখতে চান বা কোন তথ্যের প্রয়োজন বলুন।',
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    }
  ]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [threadId, setThreadId] = useState<number | null>(null);
  const [isHandover, setIsHandover] = useState(false);

  // Inspector Panel State (showing last bot response inspection)
  const [activeInspection, setActiveInspection] = useState<{
    language?: string;
    sources?: RetrievedSource[];
    tools?: ToolCallLog[];
    handover?: boolean;
    latency?: number;
  }>({});

  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, loading]);

  const handleSendMessage = async (msgText: string) => {
    if (!msgText.trim() || loading) return;

    const userMessageText = msgText.trim();
    setInput('');

    const newMsg: ChatMessage = {
      id: Date.now().toString(),
      sender: 'customer',
      text: userMessageText,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    };

    setMessages((prev) => [...prev, newMsg]);
    setLoading(true);

    try {
      const res: TestChatResponse = await apiClient.chat.sendTestMessage({
        message: userMessageText,
        thread_id: threadId,
        customer_name: 'Tanvir (Customer)',
        customer_phone: '01712345678',
      });

      setThreadId(res.thread_id);
      setIsHandover(res.handover_triggered || res.thread_status === 'human_takeover');

      const botMsg: ChatMessage = {
        id: (Date.now() + 1).toString(),
        sender: 'bot',
        text: res.reply,
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        detectedLanguage: res.detected_language,
        retrievedSources: res.retrieved_sources,
        toolCalls: res.tool_calls,
        handoverTriggered: res.handover_triggered,
      };

      setMessages((prev) => [...prev, botMsg]);
      setActiveInspection({
        language: res.detected_language,
        sources: res.retrieved_sources,
        tools: res.tool_calls,
        handover: res.handover_triggered,
        latency: res.latency_ms,
      });
    } catch (err: any) {
      console.error(err);
      setMessages((prev) => [
        ...prev,
        {
          id: (Date.now() + 1).toString(),
          sender: 'bot',
          text: 'Error communicating with AI engine. Please verify the backend service is running.',
          timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        },
      ]);
    } finally {
      setLoading(false);
    }
  };

  const handleResetThread = async () => {
    if (threadId) {
      await apiClient.chat.resetThread(threadId);
    }
    setThreadId(null);
    setIsHandover(false);
    setActiveInspection({});
    setMessages([
      {
        id: 'welcome-new',
        sender: 'bot',
        text: 'চ্যাটটি রিসেট করা হয়েছে। আপনি নতুন কোনো প্রশ্ন বা অর্ডারের বিষয়ে কথা বলতে পারেন।',
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      }
    ]);
  };

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6 h-[calc(100vh-4rem)] flex flex-col">
      {/* Top Bar */}
      <div className="flex items-center justify-between pb-4 mb-4 border-b border-slate-200">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-xl font-bold text-slate-900">Customer Test Chat Simulator</h1>
            <span className="px-2 py-0.5 rounded-full text-xs font-semibold bg-emerald-100 text-emerald-800">
              Zero-Risk Sandbox
            </span>
          </div>
          <p className="text-xs text-slate-500 mt-0.5">
            Test AI customer responses in Bangla, Banglish, and English with real-time vector retrieval & tool inspection.
          </p>
        </div>

        <button
          onClick={handleResetThread}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-slate-300 hover:bg-slate-100 text-slate-700 text-xs font-medium transition-colors"
        >
          <RotateCcw className="w-3.5 h-3.5" />
          <span>Reset Session</span>
        </button>
      </div>

      {/* Main Split Grid */}
      <div className="flex-1 grid grid-cols-1 lg:grid-cols-12 gap-6 min-h-0">
        {/* Left / Center: Chat Window (7 Cols) */}
        <div className="lg:col-span-7 flex flex-col bg-white border border-slate-200 rounded-2xl shadow-sm overflow-hidden min-h-0">
          {/* Handover Notice Banner */}
          {isHandover && (
            <div className="bg-amber-500/10 border-b border-amber-500/20 px-4 py-2.5 flex items-center justify-between text-xs text-amber-800">
              <div className="flex items-center gap-2 font-medium">
                <AlertTriangle className="w-4 h-4 text-amber-600 flex-shrink-0" />
                <span>Human Takeover Active. AI replies are paused for this thread.</span>
              </div>
              <button
                onClick={handleResetThread}
                className="underline hover:text-amber-950 font-semibold text-[11px]"
              >
                Resume Bot
              </button>
            </div>
          )}

          {/* Messages Area */}
          <div className="flex-1 overflow-y-auto p-4 space-y-4">
            {messages.map((m) => {
              const isUser = m.sender === 'customer';
              return (
                <div key={m.id} className={`flex items-start gap-2.5 ${isUser ? 'flex-row-reverse' : ''}`}>
                  <div
                    className={`w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 text-xs font-semibold shadow-sm ${
                      isUser ? 'bg-blue-600 text-white' : 'bg-slate-900 text-white'
                    }`}
                  >
                    {isUser ? <User className="w-4 h-4" /> : <Bot className="w-4 h-4" />}
                  </div>

                  <div className={`max-w-[80%] ${isUser ? 'items-end' : 'items-start'} flex flex-col`}>
                    <div
                      className={`px-4 py-2.5 rounded-2xl text-sm leading-relaxed ${
                        isUser
                          ? 'bg-blue-600 text-white rounded-br-none shadow-sm'
                          : 'bg-slate-100 text-slate-800 rounded-bl-none font-bangla'
                      }`}
                    >
                      <p className="whitespace-pre-line">{m.text}</p>
                    </div>

                    <div className="flex items-center gap-2 mt-1 px-1 text-[10px] text-slate-400">
                      <span>{m.timestamp}</span>
                      {m.detectedLanguage && (
                        <span className="px-1.5 py-0.2 rounded bg-slate-200 text-slate-700 font-mono uppercase text-[9px]">
                          {m.detectedLanguage}
                        </span>
                      )}
                      {m.handoverTriggered && (
                        <span className="px-1.5 py-0.2 rounded bg-amber-100 text-amber-800 font-semibold text-[9px]">
                          Handover
                        </span>
                      )}
                    </div>
                  </div>
                </div>
              );
            })}

            {loading && (
              <div className="flex items-center gap-2 text-slate-400 text-xs pl-10">
                <div className="w-2 h-2 rounded-full bg-blue-600 animate-ping" />
                <span>AI Assistant is analyzing catalog & generating reply...</span>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>

          {/* Quick Prompts Carousel */}
          <div className="p-2.5 border-t border-slate-100 bg-slate-50/60 overflow-x-auto flex gap-1.5 no-scrollbar">
            {SAMPLE_PROMPTS.map((p, idx) => (
              <button
                key={idx}
                onClick={() => handleSendMessage(p.text)}
                disabled={loading}
                className="whitespace-nowrap px-2.5 py-1 rounded-full bg-white border border-slate-200 text-xs text-slate-700 hover:border-blue-400 hover:text-blue-600 transition-colors shadow-2xs disabled:opacity-50"
              >
                {p.label}
              </button>
            ))}
          </div>

          {/* Input Form */}
          <div className="p-3 border-t border-slate-200 bg-white">
            <form
              onSubmit={(e) => {
                e.preventDefault();
                handleSendMessage(input);
              }}
              className="flex items-center gap-2"
            >
              <input
                type="text"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                placeholder="Type customer message in Bangla, Banglish, or English..."
                className="flex-1 px-4 py-2.5 bg-slate-100 border border-slate-200 rounded-xl text-sm focus:outline-none focus:border-blue-500 font-bangla"
                disabled={loading}
              />
              <button
                type="submit"
                disabled={loading || !input.trim()}
                className="p-2.5 bg-blue-600 hover:bg-blue-500 active:scale-95 text-white rounded-xl shadow-sm disabled:opacity-40 transition-all"
              >
                <Send className="w-4 h-4" />
              </button>
            </form>
          </div>
        </div>

        {/* Right: AI Diagnostic Inspector (5 Cols) */}
        <div className="lg:col-span-5 flex flex-col bg-slate-900 border border-slate-800 rounded-2xl shadow-xl overflow-hidden min-h-0 text-slate-100 p-4">
          <div className="flex items-center justify-between pb-3 border-b border-slate-800">
            <div className="flex items-center gap-2">
              <Sparkles className="w-4 h-4 text-blue-400" />
              <h2 className="text-xs font-bold uppercase tracking-wider text-slate-300">AI Diagnostic Inspector</h2>
            </div>
            {activeInspection.latency && (
              <span className="flex items-center gap-1 text-[11px] text-slate-400 font-mono">
                <Clock className="w-3 h-3 text-slate-500" />
                {activeInspection.latency} ms
              </span>
            )}
          </div>

          <div className="flex-1 overflow-y-auto mt-3 space-y-4 pr-1">
            {/* Language Detection Section */}
            <div className="bg-slate-800/80 rounded-xl p-3 border border-slate-700/60">
              <div className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider mb-1">
                Detected Script / Language
              </div>
              <div className="flex items-center gap-2">
                <span className={`px-2.5 py-0.5 rounded-full text-xs font-bold uppercase tracking-wide ${
                  activeInspection.language === 'bangla'
                    ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/30'
                    : activeInspection.language === 'banglish'
                    ? 'bg-amber-500/20 text-amber-300 border border-amber-500/30'
                    : 'bg-blue-500/20 text-blue-300 border border-blue-500/30'
                }`}>
                  {activeInspection.language || 'Awaiting message'}
                </span>
                <span className="text-xs text-slate-400">
                  {activeInspection.language === 'bangla' && '• Bengali Unicode script'}
                  {activeInspection.language === 'banglish' && '• Phonetic Banglish in Latin'}
                  {activeInspection.language === 'english' && '• Standard English'}
                </span>
              </div>
            </div>

            {/* Tool Calls Section */}
            <div className="bg-slate-800/80 rounded-xl p-3 border border-slate-700/60">
              <div className="flex items-center justify-between mb-2">
                <div className="flex items-center gap-1.5 text-[11px] font-semibold text-slate-400 uppercase tracking-wider">
                  <Wrench className="w-3.5 h-3.5 text-indigo-400" />
                  <span>Tool Calls Executed ({activeInspection.tools?.length || 0})</span>
                </div>
              </div>

              {!activeInspection.tools || activeInspection.tools.length === 0 ? (
                <p className="text-xs text-slate-500 italic">No tool calls for this response.</p>
              ) : (
                <div className="space-y-2">
                  {activeInspection.tools.map((tc, idx) => (
                    <div key={idx} className="bg-slate-950 rounded-lg p-2.5 border border-slate-800 text-xs font-mono">
                      <div className="flex items-center justify-between text-indigo-400 font-bold mb-1">
                        <span>⚡ {tc.tool}()</span>
                      </div>
                      <div className="text-[11px] text-slate-400 mb-1">
                        <span className="text-slate-500">Args: </span>
                        {JSON.stringify(tc.arguments)}
                      </div>
                      <div className="text-[10px] text-slate-400 bg-slate-900 p-1.5 rounded max-h-24 overflow-y-auto">
                        <span className="text-slate-500 font-semibold">Output: </span>
                        {JSON.stringify(tc.result, null, 2)}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* Retrieved Sources Section */}
            <div className="bg-slate-800/80 rounded-xl p-3 border border-slate-700/60">
              <div className="flex items-center justify-between mb-2">
                <div className="flex items-center gap-1.5 text-[11px] font-semibold text-slate-400 uppercase tracking-wider">
                  <Database className="w-3.5 h-3.5 text-emerald-400" />
                  <span>Retrieved pgvector Chunks ({activeInspection.sources?.length || 0})</span>
                </div>
              </div>

              {!activeInspection.sources || activeInspection.sources.length === 0 ? (
                <p className="text-xs text-slate-500 italic">No vector chunks retrieved.</p>
              ) : (
                <div className="space-y-2">
                  {activeInspection.sources.map((s, idx) => (
                    <div key={idx} className="bg-slate-950 rounded-lg p-2.5 border border-slate-800 text-xs">
                      <div className="flex items-center justify-between mb-1">
                        <span className="text-emerald-400 font-semibold text-[11px]">Chunk #{idx + 1}</span>
                        <span className="text-slate-400 text-[10px] font-mono">Score: {s.score}</span>
                      </div>
                      <p className="text-slate-300 font-bangla text-xs leading-relaxed whitespace-pre-line bg-slate-900/60 p-2 rounded">
                        {s.chunk_text}
                      </p>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
