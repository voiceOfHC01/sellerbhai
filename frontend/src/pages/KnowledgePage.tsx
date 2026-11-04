import React, { useState, useEffect } from 'react';
import { apiClient } from '../api/client';
import { KBDocument } from '../types';
import { Plus, Edit2, Trash2, RefreshCw, CheckCircle, BookOpen, ShieldCheck, HelpCircle } from 'lucide-react';

export const KnowledgePage: React.FC = () => {
  const [docs, setDocs] = useState<KBDocument[]>([]);
  const [loading, setLoading] = useState(true);
  const [reindexing, setReindexing] = useState(false);
  const [reindexStatus, setReindexStatus] = useState<string | null>(null);

  const [activeTab, setActiveTab] = useState<'all' | 'policy' | 'faq'>('all');

  // Modal State
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingDoc, setEditingDoc] = useState<KBDocument | null>(null);
  const [docType, setDocType] = useState<'policy' | 'faq'>('policy');
  const [title, setTitle] = useState('');
  const [content, setContent] = useState('');

  const fetchDocs = async () => {
    try {
      setLoading(true);
      const data = await apiClient.kb.getDocuments(activeTab === 'all' ? undefined : activeTab);
      setDocs(data);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDocs();
  }, [activeTab]);

  const handleReindex = async () => {
    setReindexing(true);
    setReindexStatus(null);
    try {
      const res = await apiClient.kb.reindex();
      setReindexStatus(`Reindexed successfully! ${res.chunks_indexed} total chunks embedded into pgvector.`);
      setTimeout(() => setReindexStatus(null), 4000);
    } catch (err) {
      setReindexStatus('Reindexing failed. Check backend logs.');
    } finally {
      setReindexing(false);
    }
  };

  const openCreateModal = () => {
    setEditingDoc(null);
    setDocType('policy');
    setTitle('');
    setContent('');
    setIsModalOpen(true);
  };

  const openEditModal = (d: KBDocument) => {
    setEditingDoc(d);
    setDocType(d.doc_type as any);
    setTitle(d.title);
    setContent(d.content);
    setIsModalOpen(true);
  };

  const handleDelete = async (id: number) => {
    if (confirm('Delete this knowledge document?')) {
      await apiClient.kb.deleteDocument(id);
      fetchDocs();
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (editingDoc) {
      await apiClient.kb.updateDocument(editingDoc.id, {
        doc_type: docType,
        title,
        content,
      });
    } else {
      await apiClient.kb.createDocument({
        doc_type: docType,
        title,
        content,
        is_active: true,
      });
    }
    setIsModalOpen(false);
    fetchDocs();
  };

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 mb-8">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 tracking-tight">Knowledge Base & Policies</h1>
          <p className="text-sm text-slate-500 mt-1">
            Store FAQs, delivery guidelines, and return policies for precise RAG semantic retrieval.
          </p>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={handleReindex}
            disabled={reindexing}
            className="flex items-center gap-2 px-4 py-2.5 bg-slate-900 hover:bg-slate-800 text-white font-medium rounded-xl text-sm transition-all shadow-sm disabled:opacity-50"
          >
            <RefreshCw className={`w-4 h-4 ${reindexing ? 'animate-spin' : ''}`} />
            <span>{reindexing ? 'Reindexing Chunks...' : 'Reindex Knowledge'}</span>
          </button>
          <button
            onClick={openCreateModal}
            className="flex items-center gap-2 px-4 py-2.5 bg-blue-600 hover:bg-blue-500 text-white font-medium rounded-xl text-sm transition-all shadow-sm shadow-blue-500/20"
          >
            <Plus className="w-4 h-4" />
            <span>Add Entry</span>
          </button>
        </div>
      </div>

      {reindexStatus && (
        <div className="mb-6 p-4 rounded-xl bg-emerald-50 border border-emerald-200 text-emerald-800 text-sm flex items-center gap-2.5">
          <CheckCircle className="w-5 h-5 text-emerald-600" />
          <span>{reindexStatus}</span>
        </div>
      )}

      {/* Tabs */}
      <div className="flex items-center gap-2 mb-6 border-b border-slate-200 pb-3">
        {(['all', 'policy', 'faq'] as const).map((tab) => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            className={`px-4 py-2 rounded-lg text-sm font-medium capitalize transition-colors ${
              activeTab === tab
                ? 'bg-blue-50 text-blue-700'
                : 'text-slate-600 hover:text-slate-900 hover:bg-slate-100'
            }`}
          >
            {tab === 'all' ? 'All Entries' : tab === 'policy' ? 'Store Policies' : 'Customer FAQs'}
          </button>
        ))}
      </div>

      {/* Documents Grid */}
      {loading ? (
        <div className="py-24 text-center text-slate-400">Loading knowledge entries...</div>
      ) : docs.length === 0 ? (
        <div className="bg-white border border-slate-200 rounded-2xl p-12 text-center">
          <BookOpen className="w-12 h-12 text-slate-300 mx-auto mb-3" />
          <h3 className="text-base font-semibold text-slate-800">No entries in this category</h3>
          <p className="text-sm text-slate-500 mt-1">Click "Add Entry" above to add policies or common answers.</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {docs.map((doc) => (
            <div key={doc.id} className="bg-white border border-slate-200 rounded-2xl p-6 shadow-sm hover:shadow-md transition-shadow flex flex-col justify-between">
              <div>
                <div className="flex items-center justify-between mb-3">
                  <span className={`px-2.5 py-0.5 rounded-full text-xs font-semibold uppercase tracking-wider flex items-center gap-1 ${
                    doc.doc_type === 'policy'
                      ? 'bg-amber-50 text-amber-700 border border-amber-200'
                      : 'bg-indigo-50 text-indigo-700 border border-indigo-200'
                  }`}>
                    {doc.doc_type === 'policy' ? <ShieldCheck className="w-3.5 h-3.5" /> : <HelpCircle className="w-3.5 h-3.5" />}
                    <span>{doc.doc_type}</span>
                  </span>
                  <span className="text-xs text-slate-400 font-mono">ID: #{doc.id}</span>
                </div>
                <h3 className="text-base font-bold text-slate-900 mb-2">{doc.title}</h3>
                <p className="text-sm text-slate-600 leading-relaxed font-bangla whitespace-pre-line">{doc.content}</p>
              </div>

              <div className="mt-5 pt-3 border-t border-slate-100 flex items-center justify-end gap-2">
                <button
                  onClick={() => openEditModal(doc)}
                  className="p-2 text-slate-600 hover:text-blue-600 hover:bg-blue-50 rounded-lg transition-colors text-xs flex items-center gap-1"
                >
                  <Edit2 className="w-3.5 h-3.5" />
                  <span>Edit</span>
                </button>
                <button
                  onClick={() => handleDelete(doc.id)}
                  className="p-2 text-slate-600 hover:text-red-600 hover:bg-red-50 rounded-lg transition-colors text-xs flex items-center gap-1"
                >
                  <Trash2 className="w-3.5 h-3.5" />
                  <span>Delete</span>
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Add / Edit Modal */}
      {isModalOpen && (
        <div className="fixed inset-0 z-50 bg-slate-900/50 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl max-w-lg w-full p-6 shadow-2xl">
            <h2 className="text-lg font-bold text-slate-900 mb-4">
              {editingDoc ? 'Edit Knowledge Entry' : 'New Knowledge Entry'}
            </h2>
            <form onSubmit={handleSubmit} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-slate-600 mb-1">Type</label>
                <select
                  value={docType}
                  onChange={(e) => setDocType(e.target.value as any)}
                  className="w-full px-3.5 py-2.5 border border-slate-300 rounded-xl text-sm focus:outline-none focus:border-blue-500"
                >
                  <option value="policy">Store Policy (Delivery, Return, Payment)</option>
                  <option value="faq">Customer FAQ (General Question & Answer)</option>
                </select>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-600 mb-1">Title</label>
                <input
                  type="text"
                  required
                  value={title}
                  onChange={(e) => setTitle(e.target.value)}
                  className="w-full px-3.5 py-2.5 border border-slate-300 rounded-xl text-sm focus:outline-none focus:border-blue-500"
                  placeholder="e.g. Return & Exchange Policy"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-600 mb-1">Content (Bangla / English)</label>
                <textarea
                  rows={4}
                  required
                  value={content}
                  onChange={(e) => setContent(e.target.value)}
                  className="w-full px-3.5 py-2.5 border border-slate-300 rounded-xl text-sm font-bangla focus:outline-none focus:border-blue-500"
                  placeholder="Write clear policy details in Bangla, English or Banglish..."
                />
              </div>

              <div className="flex justify-end gap-3 pt-4 border-t border-slate-200">
                <button
                  type="button"
                  onClick={() => setIsModalOpen(false)}
                  className="px-4 py-2 border border-slate-300 text-slate-700 rounded-xl text-sm font-medium hover:bg-slate-50"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-5 py-2 bg-blue-600 hover:bg-blue-500 text-white rounded-xl text-sm font-semibold shadow-sm"
                >
                  {editingDoc ? 'Save Changes' : 'Save Entry'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
