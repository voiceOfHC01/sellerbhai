import React, { useState, useEffect } from 'react';
import { apiClient } from '../api/client';
import { AIRunItem } from '../types';
import { 
  CheckCircle2, XCircle, AlertTriangle, Sparkles, BookOpen, 
  RefreshCw, Search, Wrench, Clock, Database, Check, X, ShieldAlert, Plus
} from 'lucide-react';

export const AIReviewPage: React.FC = () => {
  const [runs, setRuns] = useState<AIRunItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [flaggedOnly, setFlaggedOnly] = useState(false);

  // Correction Modal State
  const [selectedRun, setSelectedRun] = useState<AIRunItem | null>(null);
  const [correctionTitle, setCorrectionTitle] = useState('');
  const [correctionContent, setCorrectionContent] = useState('');
  const [docType, setDocType] = useState<'faq' | 'policy'>('faq');
  const [notes, setNotes] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);

  const fetchRuns = async () => {
    try {
      setLoading(true);
      const data = await apiClient.aiReview.getRuns({ flagged_only: flaggedOnly, limit: 50 });
      setRuns(data);
    } catch (err) {
      console.error('Failed to load AI runs:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchRuns();
  }, [flaggedOnly]);

  const openCorrectionModal = (run: AIRunItem) => {
    setSelectedRun(run);
    setCorrectionTitle(run.user_message ? `Correction for: "${run.user_message.slice(0, 40)}..."` : 'Store Fact Correction');
    setCorrectionContent('');
    setDocType('faq');
    setNotes('');
  };

  const handleSaveCorrection = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedRun || !correctionTitle.trim() || !correctionContent.trim()) {
      alert('Please fill in both the title and the correct content.');
      return;
    }

    setIsSubmitting(true);
    try {
      await apiClient.aiReview.markWrong(selectedRun.id, {
        correction_title: correctionTitle.trim(),
        correction_content: correctionContent.trim(),
        doc_type: docType,
        notes: notes.trim() || undefined,
      });

      alert('Correction added to Knowledge Base and pgvector embeddings reindexed successfully! The AI has learned the new ground truth.');
      setSelectedRun(null);
      await fetchRuns();
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Failed to submit correction.');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">
      {/* Top Banner */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 border-b border-slate-200 pb-5">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-2xl font-bold text-slate-900">AI Quality Review & Corrections</h1>
            <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-purple-100 text-purple-800">
              RLHF & Ground Truth
            </span>
          </div>
          <p className="text-sm text-slate-500 mt-1">
            Audit AI generation runs, inspect retrieved vector sources and tool executions, and mark inaccurate replies to update store knowledge.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <label className="flex items-center gap-2 text-xs font-semibold text-slate-700 cursor-pointer bg-slate-100 px-3 py-2 rounded-xl">
            <input
              type="checkbox"
              checked={flaggedOnly}
              onChange={(e) => setFlaggedOnly(e.target.checked)}
              className="rounded text-purple-600 focus:ring-purple-500"
            />
            <span>Show Flagged Mistakes Only</span>
          </label>

          <button
            onClick={fetchRuns}
            className="flex items-center gap-1.5 px-3 py-2 rounded-xl border border-slate-300 hover:bg-slate-50 text-slate-700 text-sm font-medium transition-colors"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
            <span>Refresh</span>
          </button>
        </div>
      </div>

      {/* AI Runs List */}
      {runs.length === 0 ? (
        <div className="text-center py-12 bg-white border border-slate-200 rounded-2xl">
          <Sparkles className="w-12 h-12 text-slate-300 mx-auto mb-3" />
          <h3 className="text-sm font-bold text-slate-700">No AI Runs Recorded</h3>
          <p className="text-xs text-slate-400 mt-1">Customer chats and test interactions will appear here for quality review.</p>
        </div>
      ) : (
        <div className="space-y-4">
          {runs.map((run) => (
            <div
              key={run.id}
              className={`bg-white border rounded-2xl p-6 shadow-sm transition-all space-y-4 ${
                run.is_flagged_wrong ? 'border-amber-300 bg-amber-50/20' : 'border-slate-200'
              }`}
            >
              {/* Header: Run ID, Language, Latency & Status */}
              <div className="flex items-center justify-between border-b border-slate-100 pb-3 flex-wrap gap-2 text-xs">
                <div className="flex items-center gap-2.5">
                  <span className="font-mono font-bold text-slate-900">Run #{run.id}</span>
                  {run.thread_id && (
                    <span className="text-slate-400 font-mono">Thread #{run.thread_id}</span>
                  )}
                  {run.detected_language && (
                    <span className="px-2 py-0.5 rounded text-[10px] font-bold uppercase bg-slate-100 text-slate-700">
                      {run.detected_language}
                    </span>
                  )}
                </div>

                <div className="flex items-center gap-3">
                  <span className="text-slate-500 text-[11px] flex items-center gap-1">
                    <Clock className="w-3.5 h-3.5 text-slate-400" />
                    <span>{run.latency_ms} ms</span>
                  </span>
                  <span className="text-slate-400 text-[11px]">
                    Tokens: {run.prompt_tokens + run.completion_tokens}
                  </span>

                  {run.is_flagged_wrong ? (
                    <span className="px-2.5 py-0.5 rounded-full text-[10px] font-bold bg-amber-100 text-amber-900 border border-amber-300 flex items-center gap-1">
                      <AlertTriangle className="w-3 h-3 text-amber-600" />
                      <span>Correction Applied</span>
                    </span>
                  ) : (
                    <button
                      onClick={() => openCorrectionModal(run)}
                      className="px-2.5 py-1 rounded-lg bg-slate-900 hover:bg-slate-800 text-white text-xs font-semibold shadow-sm transition-colors flex items-center gap-1"
                    >
                      <XCircle className="w-3.5 h-3.5 text-rose-400" />
                      <span>Mark Wrong & Teach</span>
                    </button>
                  )}
                </div>
              </div>

              {/* Customer Prompt vs AI Answer */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {/* Customer Message */}
                <div className="p-3.5 rounded-xl bg-slate-50 border border-slate-200 space-y-1">
                  <span className="text-[11px] font-bold text-slate-500 block uppercase tracking-wider">
                    Customer Message
                  </span>
                  <p className="text-xs text-slate-800 font-medium whitespace-pre-wrap">
                    {run.user_message || '[Message record unattached or initial greeting]'}
                  </p>
                </div>

                {/* AI Reply */}
                <div className="p-3.5 rounded-xl bg-emerald-50/50 border border-emerald-200 space-y-1">
                  <span className="text-[11px] font-bold text-emerald-800 block uppercase tracking-wider">
                    AI Grounded Reply
                  </span>
                  <p className="text-xs text-slate-900 whitespace-pre-wrap leading-relaxed">
                    {run.raw_response}
                  </p>
                </div>
              </div>

              {/* RAG Retrieved Sources & Tool Calls */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs pt-1">
                {/* Retrieved Sources */}
                <div className="space-y-1.5">
                  <span className="font-bold text-slate-700 flex items-center gap-1 text-[11px]">
                    <Database className="w-3.5 h-3.5 text-blue-600" />
                    <span>Retrieved Knowledge Chunks ({run.retrieved_chunks?.length || 0})</span>
                  </span>

                  {!run.retrieved_chunks || run.retrieved_chunks.length === 0 ? (
                    <div className="text-[11px] text-slate-400 italic">No vector chunks retrieved</div>
                  ) : (
                    <div className="space-y-1">
                      {run.retrieved_chunks.map((chk: any, idx: number) => (
                        <div key={idx} className="p-2 rounded-lg bg-slate-50 border border-slate-200 text-[11px] text-slate-600 line-clamp-2">
                          <span className="font-mono text-blue-600 font-bold mr-1">[{chk.score?.toFixed(2) || '0.85'}]</span>
                          {chk.text}
                        </div>
                      ))}
                    </div>
                  )}
                </div>

                {/* Tool Calls */}
                <div className="space-y-1.5">
                  <span className="font-bold text-slate-700 flex items-center gap-1 text-[11px]">
                    <Wrench className="w-3.5 h-3.5 text-purple-600" />
                    <span>Tools Executed ({run.tool_calls?.length || 0})</span>
                  </span>

                  {!run.tool_calls || run.tool_calls.length === 0 ? (
                    <div className="text-[11px] text-slate-400 italic">No tool calls triggered</div>
                  ) : (
                    <div className="space-y-1">
                      {run.tool_calls.map((tc: any, idx: number) => (
                        <div key={idx} className="p-2 rounded-lg bg-purple-50/50 border border-purple-200 text-[11px] font-mono text-purple-900 flex items-center justify-between">
                          <span className="font-bold">{tc.tool}(...)</span>
                          <span className="text-purple-600 text-[10px]">executed</span>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </div>

              {/* Correction Notes if flagged */}
              {run.is_flagged_wrong && run.correction_notes && (
                <div className="p-3 rounded-xl bg-amber-50 border border-amber-200 text-xs text-amber-900">
                  <strong>Correction Logged:</strong> {run.correction_notes}
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      {/* "Mark Wrong & Add Ground Truth" Modal */}
      {selectedRun && (
        <div className="fixed inset-0 bg-slate-900/40 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl max-w-lg w-full p-6 shadow-xl space-y-4">
            <div className="flex items-center justify-between pb-3 border-b border-slate-100">
              <h3 className="text-base font-bold text-slate-900 flex items-center gap-2">
                <BookOpen className="w-5 h-5 text-purple-600" />
                <span>Add Ground Truth to Knowledge Base</span>
              </h3>
              <button onClick={() => setSelectedRun(null)} className="text-slate-400 hover:text-slate-600">
                <X className="w-5 h-5" />
              </button>
            </div>

            <p className="text-xs text-slate-500 leading-relaxed">
              Define the correct facts or policy for Run #{selectedRun.id}. This will immediately save to your Store Knowledge Base and re-embed into pgvector.
            </p>

            <form onSubmit={handleSaveCorrection} className="space-y-3">
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  Correction Document Title
                </label>
                <input
                  type="text"
                  value={correctionTitle}
                  onChange={(e) => setCorrectionTitle(e.target.value)}
                  placeholder="e.g. Panjabi Fabric & Cotton Blend FAQ"
                  className="w-full text-xs rounded-xl border-slate-300 shadow-sm focus:border-purple-500 focus:ring-purple-500 p-2.5"
                  required
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">Type</label>
                  <select
                    value={docType}
                    onChange={(e: any) => setDocType(e.target.value)}
                    className="w-full text-xs rounded-xl border-slate-300 shadow-sm focus:border-purple-500 focus:ring-purple-500 p-2"
                  >
                    <option value="faq">FAQ</option>
                    <option value="policy">Store Policy</option>
                  </select>
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">Auditor Notes</label>
                  <input
                    type="text"
                    value={notes}
                    onChange={(e) => setNotes(e.target.value)}
                    placeholder="e.g. AI misquoted delivery fee"
                    className="w-full text-xs rounded-xl border-slate-300 shadow-sm focus:border-purple-500 focus:ring-purple-500 p-2"
                  />
                </div>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  Ground Truth / Accurate Store Facts (In Bangla / English)
                </label>
                <textarea
                  rows={4}
                  value={correctionContent}
                  onChange={(e) => setCorrectionContent(e.target.value)}
                  placeholder="Write the exact accurate information the AI should answer in the future..."
                  className="w-full text-xs rounded-xl border-slate-300 shadow-sm focus:border-purple-500 focus:ring-purple-500 p-2.5 leading-relaxed"
                  required
                />
              </div>

              <div className="flex justify-end gap-3 pt-2">
                <button
                  type="button"
                  onClick={() => setSelectedRun(null)}
                  className="px-4 py-2 rounded-xl border border-slate-300 text-xs font-semibold text-slate-700 hover:bg-slate-50"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isSubmitting}
                  className="px-5 py-2 rounded-xl bg-purple-600 hover:bg-purple-700 text-white text-xs font-bold shadow-md transition-all disabled:opacity-50"
                >
                  {isSubmitting ? 'Reindexing...' : 'Save & Reindex Vector Store'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
