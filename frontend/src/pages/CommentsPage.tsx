import React, { useState, useEffect } from 'react';
import { apiClient } from '../api/client';
import { Comment, CommentSettings, CommentRule } from '../types';
import { 
  MessageSquare, ShieldAlert, Sparkles, Filter, Search, RefreshCw, 
  EyeOff, Send, CheckCircle2, AlertTriangle, Sliders, X, Check, ArrowRight, Lock 
} from 'lucide-react';

export const CommentsPage: React.FC = () => {
  const [comments, setComments] = useState<Comment[]>([]);
  const [loading, setLoading] = useState(true);
  const [platformFilter, setPlatformFilter] = useState<string>('all');
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [searchQuery, setSearchQuery] = useState('');
  
  // Settings Drawer/Modal State
  const [isSettingsOpen, setIsSettingsOpen] = useState(false);
  const [rulesConfig, setRulesConfig] = useState<CommentSettings>({
    comment_auto_reply_enabled: true,
    spam_filter_enabled: true,
    spam_hide_links: true,
    spam_hide_phones: true,
    abusive_words: ['scam', 'fraud', 'fake', 'foul', 'bastard', 'chor', 'batpar', 'cheat', 'harami'],
    comment_rules: [],
    comment_fallback_ai: true,
  });
  const [newAbusiveWord, setNewAbusiveWord] = useState('');
  const [savingSettings, setSavingSettings] = useState(false);

  // Manual Reply Modal State
  const [replyModalComment, setReplyModalComment] = useState<Comment | null>(null);
  const [manualReplyType, setManualReplyType] = useState<'public' | 'private'>('public');
  const [manualReplyText, setManualReplyText] = useState('');
  const [sendingReply, setSendingReply] = useState(false);
  const [replyError, setReplyError] = useState<string | null>(null);

  const fetchComments = async () => {
    try {
      setLoading(true);
      const params: { platform?: string; status?: string; search?: string } = {};
      if (platformFilter !== 'all') params.platform = platformFilter;
      if (statusFilter !== 'all') params.status = statusFilter;
      if (searchQuery.trim()) params.search = searchQuery.trim();

      const data = await apiClient.comments.getComments(params);
      setComments(data);
    } catch (err) {
      console.error('Failed to fetch comments:', err);
    } finally {
      setLoading(false);
    }
  };

  const fetchSettings = async () => {
    try {
      const data = await apiClient.comments.getSettings();
      setRulesConfig(data);
    } catch (err) {
      console.error('Failed to fetch comment settings:', err);
    }
  };

  useEffect(() => {
    fetchComments();
    fetchSettings();
  }, [platformFilter, statusFilter]);

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    fetchComments();
  };

  const handleSaveSettings = async (e: React.FormEvent) => {
    e.preventDefault();
    setSavingSettings(true);
    try {
      await apiClient.comments.updateSettings(rulesConfig);
      setIsSettingsOpen(false);
      alert('Comment automation and spam rules saved successfully!');
    } catch (err) {
      alert('Failed to save settings.');
    } finally {
      setSavingSettings(false);
    }
  };

  const handleAddAbusiveWord = () => {
    if (!newAbusiveWord.trim()) return;
    if (!rulesConfig.abusive_words.includes(newAbusiveWord.trim().toLowerCase())) {
      setRulesConfig({
        ...rulesConfig,
        abusive_words: [...rulesConfig.abusive_words, newAbusiveWord.trim().toLowerCase()],
      });
    }
    setNewAbusiveWord('');
  };

  const handleRemoveAbusiveWord = (word: string) => {
    setRulesConfig({
      ...rulesConfig,
      abusive_words: rulesConfig.abusive_words.filter((w) => w !== word),
    });
  };

  const handleAddRule = () => {
    const newRule: CommentRule = {
      keyword: '',
      public_reply: '',
      private_reply: '',
      send_private_dm: true,
    };
    setRulesConfig({
      ...rulesConfig,
      comment_rules: [...rulesConfig.comment_rules, newRule],
    });
  };

  const handleRemoveRule = (index: number) => {
    const updated = [...rulesConfig.comment_rules];
    updated.splice(index, 1);
    setRulesConfig({ ...rulesConfig, comment_rules: updated });
  };

  const handleRuleChange = (index: number, field: keyof CommentRule, val: any) => {
    const updated = [...rulesConfig.comment_rules];
    updated[index] = { ...updated[index], [field]: val };
    setRulesConfig({ ...rulesConfig, comment_rules: updated });
  };

  const openReplyModal = (comment: Comment) => {
    setReplyModalComment(comment);
    setManualReplyType('public');
    setManualReplyText('');
    setReplyError(null);
  };

  const handleSendManualReply = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!replyModalComment || !manualReplyText.trim()) return;

    setSendingReply(true);
    setReplyError(null);
    try {
      const updated = await apiClient.comments.reply(replyModalComment.id, {
        reply_type: manualReplyType,
        message: manualReplyText.trim(),
      });
      setComments(comments.map((c) => (c.id === updated.id ? updated : c)));
      setReplyModalComment(null);
    } catch (err: any) {
      setReplyError(err.response?.data?.detail || 'Failed to dispatch reply.');
    } finally {
      setSendingReply(false);
    }
  };

  const handleHideComment = async (commentId: number) => {
    if (confirm('Hide this comment from the public post?')) {
      try {
        const updated = await apiClient.comments.hide(commentId);
        setComments(comments.map((c) => (c.id === updated.id ? updated : c)));
      } catch (err: any) {
        alert(err.response?.data?.detail || 'Failed to hide comment.');
      }
    }
  };

  const getStatusBadge = (c: Comment) => {
    if (c.is_hidden || c.status === 'hidden_spam') {
      return (
        <span className="px-2.5 py-1 rounded-full text-xs font-semibold bg-rose-100 text-rose-800 border border-rose-200 inline-flex items-center gap-1">
          <EyeOff className="w-3 h-3" /> Hidden Spam
        </span>
      );
    }
    if (c.status === 'replied') {
      return (
        <span className="px-2.5 py-1 rounded-full text-xs font-semibold bg-emerald-100 text-emerald-800 border border-emerald-200 inline-flex items-center gap-1">
          <CheckCircle2 className="w-3 h-3" /> Replied
        </span>
      );
    }
    return (
      <span className="px-2.5 py-1 rounded-full text-xs font-semibold bg-amber-100 text-amber-800 border border-amber-200">
        Pending
      </span>
    );
  };

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-6">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 border-b border-slate-200 pb-5">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-2xl font-bold text-slate-900">Comments Automation & Moderation</h1>
            <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-blue-100 text-blue-800">
              Facebook & Instagram
            </span>
          </div>
          <p className="text-sm text-slate-500 mt-1">
            Automate public responses, send private DMs, and auto-hide spam links, phone numbers, and abusive words.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={fetchComments}
            className="flex items-center gap-1.5 px-3 py-2 rounded-xl border border-slate-300 hover:bg-slate-50 text-slate-700 text-sm font-medium transition-colors"
          >
            <RefreshCw className="w-4 h-4" />
            <span>Refresh</span>
          </button>

          <button
            onClick={() => setIsSettingsOpen(true)}
            className="flex items-center gap-2 px-4 py-2 rounded-xl bg-slate-900 hover:bg-slate-800 text-white text-sm font-semibold shadow-sm transition-colors"
          >
            <Sliders className="w-4 h-4" />
            <span>Rules & Spam Settings</span>
          </button>
        </div>
      </div>

      {/* Filter and Search Bar */}
      <div className="bg-white p-4 rounded-2xl border border-slate-200 shadow-sm flex flex-col md:flex-row gap-4 items-center justify-between">
        <form onSubmit={handleSearch} className="flex-1 flex items-center gap-2 w-full">
          <div className="relative flex-1">
            <Search className="w-4 h-4 text-slate-400 absolute left-3.5 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              placeholder="Search comments, author name, or post ID..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-10 pr-4 py-2 border border-slate-300 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-blue-600"
            />
          </div>
          <button
            type="submit"
            className="px-4 py-2 bg-blue-600 hover:bg-blue-500 text-white rounded-xl text-sm font-semibold transition-colors shrink-0"
          >
            Search
          </button>
        </form>

        <div className="flex items-center gap-3 w-full md:w-auto overflow-x-auto text-xs no-scrollbar">
          {/* Platform Filters */}
          <div className="flex items-center gap-1 bg-slate-100 p-1 rounded-xl">
            {(['all', 'facebook', 'instagram'] as const).map((p) => (
              <button
                key={p}
                onClick={() => setPlatformFilter(p)}
                className={`px-3 py-1 rounded-lg font-semibold uppercase text-[11px] transition-colors ${
                  platformFilter === p
                    ? 'bg-white text-slate-900 shadow-sm'
                    : 'text-slate-600 hover:text-slate-900'
                }`}
              >
                {p}
              </button>
            ))}
          </div>

          {/* Status Filters */}
          <div className="flex items-center gap-1 bg-slate-100 p-1 rounded-xl">
            {(['all', 'replied', 'hidden_spam', 'pending'] as const).map((st) => (
              <button
                key={st}
                onClick={() => setStatusFilter(st)}
                className={`px-3 py-1 rounded-lg font-semibold text-[11px] capitalize transition-colors ${
                  statusFilter === st
                    ? 'bg-white text-slate-900 shadow-sm'
                    : 'text-slate-600 hover:text-slate-900'
                }`}
              >
                {st.replace('_', ' ')}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Comments List Table */}
      <div className="bg-white border border-slate-200 rounded-2xl shadow-sm overflow-hidden">
        {loading ? (
          <div className="p-12 text-center text-slate-500">Loading comments...</div>
        ) : comments.length === 0 ? (
          <div className="p-16 text-center">
            <MessageSquare className="w-12 h-12 text-slate-300 mx-auto mb-3" />
            <h3 className="text-base font-semibold text-slate-900">No comments found</h3>
            <p className="text-sm text-slate-500 mt-1 max-w-sm mx-auto">
              Comments received on your Facebook Page feed or Instagram posts will appear here along with the automated action taken.
            </p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-slate-200 text-sm">
              <thead className="bg-slate-50 text-slate-600 text-xs font-semibold uppercase tracking-wider">
                <tr>
                  <th className="py-3.5 px-4 text-left">Platform</th>
                  <th className="py-3.5 px-4 text-left">Author</th>
                  <th className="py-3.5 px-4 text-left">Comment Text</th>
                  <th className="py-3.5 px-4 text-left">Status</th>
                  <th className="py-3.5 px-4 text-left">Actions Taken</th>
                  <th className="py-3.5 px-4 text-left">Replies Delivered</th>
                  <th className="py-3.5 px-4 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-200">
                {comments.map((c) => (
                  <tr key={c.id} className="hover:bg-slate-50/80 transition-colors">
                    <td className="py-4 px-4 whitespace-nowrap">
                      {c.platform === 'instagram' ? (
                        <span className="px-2.5 py-1 rounded-lg text-xs font-bold text-white bg-gradient-to-r from-purple-600 to-pink-600 inline-flex items-center gap-1 shadow-sm">
                          Instagram
                        </span>
                      ) : (
                        <span className="px-2.5 py-1 rounded-lg text-xs font-bold text-white bg-blue-600 inline-flex items-center gap-1 shadow-sm">
                          Facebook
                        </span>
                      )}
                    </td>
                    <td className="py-4 px-4 whitespace-nowrap">
                      <div className="font-semibold text-slate-900">{c.author_name || 'Anonymous User'}</div>
                      <div className="text-[11px] text-slate-400 font-mono">ID: {c.author_id}</div>
                    </td>
                    <td className="py-4 px-4 max-w-sm">
                      <p className="text-xs text-slate-800 font-bangla font-medium">{c.message}</p>
                      <div className="text-[10px] text-slate-400 mt-0.5">
                        Post ID: {c.post_id || 'N/A'} • {new Date(c.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                      </div>
                    </td>
                    <td className="py-4 px-4 whitespace-nowrap">
                      {getStatusBadge(c)}
                    </td>
                    <td className="py-4 px-4 max-w-xs">
                      <div className="flex flex-wrap gap-1">
                        {c.actions_taken && c.actions_taken.length > 0 ? (
                          c.actions_taken.map((act, idx) => (
                            <span
                              key={idx}
                              className={`px-2 py-0.5 rounded text-[10px] font-semibold ${
                                act.includes('hidden_spam')
                                  ? 'bg-rose-100 text-rose-800'
                                  : act.includes('private_reply_sent')
                                  ? 'bg-purple-100 text-purple-800'
                                  : act.includes('public_reply_sent')
                                  ? 'bg-blue-100 text-blue-800'
                                  : act.includes('blocked')
                                  ? 'bg-amber-100 text-amber-900'
                                  : 'bg-slate-100 text-slate-700'
                              }`}
                            >
                              {act}
                            </span>
                          ))
                        ) : (
                          <span className="text-slate-400 text-xs italic">None</span>
                        )}
                      </div>
                    </td>
                    <td className="py-4 px-4 max-w-xs space-y-1">
                      {c.public_reply_text && (
                        <div className="text-[11px] bg-slate-50 p-2 rounded-lg border border-slate-200">
                          <span className="font-bold text-slate-600 block text-[9px] uppercase">Public Reply:</span>
                          <span className="text-slate-800 font-bangla">{c.public_reply_text}</span>
                        </div>
                      )}
                      {c.private_reply_text && (
                        <div className="text-[11px] bg-purple-50 p-2 rounded-lg border border-purple-200">
                          <span className="font-bold text-purple-700 block text-[9px] uppercase flex items-center gap-1">
                            <Lock className="w-2.5 h-2.5" /> Private DM Sent (Limit 1x):
                          </span>
                          <span className="text-purple-900 font-bangla">{c.private_reply_text}</span>
                        </div>
                      )}
                      {!c.public_reply_text && !c.private_reply_text && (
                        <span className="text-slate-400 text-xs">No reply dispatched</span>
                      )}
                    </td>
                    <td className="py-4 px-4 text-right whitespace-nowrap">
                      <div className="flex items-center justify-end gap-1.5">
                        <button
                          onClick={() => openReplyModal(c)}
                          className="px-2.5 py-1 text-xs font-semibold text-blue-600 hover:bg-blue-50 rounded-lg transition-colors border border-blue-200"
                        >
                          Reply
                        </button>
                        {!c.is_hidden && (
                          <button
                            onClick={() => handleHideComment(c.id)}
                            className="p-1 text-slate-500 hover:text-rose-600 hover:bg-rose-50 rounded-lg transition-colors"
                            title="Hide Comment"
                          >
                            <EyeOff className="w-4 h-4" />
                          </button>
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Rules & Spam Settings Modal */}
      {isSettingsOpen && (
        <div className="fixed inset-0 z-50 bg-slate-900/50 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl max-w-3xl w-full max-h-[90vh] flex flex-col shadow-2xl border border-slate-200 overflow-hidden">
            <div className="p-4 border-b border-slate-200 bg-slate-50 flex items-center justify-between">
              <div>
                <h3 className="font-bold text-slate-900 text-base">Comment Automation & Moderation Rules</h3>
                <p className="text-xs text-slate-500">Configure keyword rules, private DM triggers, and automated spam filtering.</p>
              </div>
              <button
                onClick={() => setIsSettingsOpen(false)}
                className="p-1 text-slate-400 hover:text-slate-600 rounded-lg"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <form onSubmit={handleSaveSettings} className="p-6 overflow-y-auto space-y-6 flex-1">
              {/* Global Toggles */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 p-4 rounded-xl bg-slate-50 border border-slate-200">
                <label className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={rulesConfig.comment_auto_reply_enabled}
                    onChange={(e) => setRulesConfig({ ...rulesConfig, comment_auto_reply_enabled: e.target.checked })}
                    className="w-4 h-4 text-blue-600 rounded"
                  />
                  <span className="text-xs font-bold text-slate-800">Enable Automated Comment Replies</span>
                </label>

                <label className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={rulesConfig.spam_filter_enabled}
                    onChange={(e) => setRulesConfig({ ...rulesConfig, spam_filter_enabled: e.target.checked })}
                    className="w-4 h-4 text-blue-600 rounded"
                  />
                  <span className="text-xs font-bold text-slate-800">Enable Spam Auto-Hide</span>
                </label>

                <label className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={rulesConfig.spam_hide_links}
                    onChange={(e) => setRulesConfig({ ...rulesConfig, spam_hide_links: e.target.checked })}
                    className="w-4 h-4 text-blue-600 rounded"
                  />
                  <span className="text-xs text-slate-700">Auto-hide external links & URLs</span>
                </label>

                <label className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={rulesConfig.spam_hide_phones}
                    onChange={(e) => setRulesConfig({ ...rulesConfig, spam_hide_phones: e.target.checked })}
                    className="w-4 h-4 text-blue-600 rounded"
                  />
                  <span className="text-xs text-slate-700">Auto-hide phone numbers</span>
                </label>
              </div>

              {/* Abusive Words List */}
              <div>
                <label className="block text-xs font-bold text-slate-800 uppercase mb-2">
                  Abusive / Prohibited Words List (Auto-Hides Comment)
                </label>
                <div className="flex flex-wrap gap-1.5 mb-2.5">
                  {rulesConfig.abusive_words.map((w) => (
                    <span
                      key={w}
                      className="px-2.5 py-1 rounded-lg text-xs font-semibold bg-rose-50 text-rose-700 border border-rose-200 flex items-center gap-1.5"
                    >
                      <span>{w}</span>
                      <button
                        type="button"
                        onClick={() => handleRemoveAbusiveWord(w)}
                        className="hover:text-rose-900"
                      >
                        ×
                      </button>
                    </span>
                  ))}
                </div>
                <div className="flex gap-2">
                  <input
                    type="text"
                    value={newAbusiveWord}
                    onChange={(e) => setNewAbusiveWord(e.target.value)}
                    placeholder="Add abusive keyword..."
                    className="px-3 py-1.5 border border-slate-300 rounded-xl text-xs flex-1 focus:outline-none focus:ring-2 focus:ring-blue-600"
                    onKeyDown={(e) => {
                      if (e.key === 'Enter') {
                        e.preventDefault();
                        handleAddAbusiveWord();
                      }
                    }}
                  />
                  <button
                    type="button"
                    onClick={handleAddAbusiveWord}
                    className="px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-white rounded-xl text-xs font-semibold"
                  >
                    Add Word
                  </button>
                </div>
              </div>

              {/* Keyword Reply Rules */}
              <div>
                <div className="flex items-center justify-between mb-2">
                  <label className="block text-xs font-bold text-slate-800 uppercase">
                    Keyword Reply Templates
                  </label>
                  <button
                    type="button"
                    onClick={handleAddRule}
                    className="text-xs font-bold text-blue-600 hover:text-blue-700"
                  >
                    + Add New Rule
                  </button>
                </div>

                <div className="space-y-3">
                  {rulesConfig.comment_rules.map((rule, idx) => (
                    <div key={idx} className="p-3.5 rounded-xl border border-slate-200 bg-slate-50/50 space-y-2 text-xs">
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2 flex-1 mr-2">
                          <span className="font-bold text-slate-600">Keyword:</span>
                          <input
                            type="text"
                            value={rule.keyword}
                            onChange={(e) => handleRuleChange(idx, 'keyword', e.target.value)}
                            placeholder="e.g. dam, price, koto"
                            className="px-2.5 py-1 bg-white border border-slate-300 rounded-lg text-xs font-mono flex-1 focus:outline-none focus:ring-1 focus:ring-blue-600"
                          />
                        </div>
                        <button
                          type="button"
                          onClick={() => handleRemoveRule(idx)}
                          className="text-xs text-rose-600 hover:text-rose-800 font-semibold"
                        >
                          Delete
                        </button>
                      </div>

                      <div>
                        <span className="font-bold text-slate-600 block mb-0.5">Public Comment Reply:</span>
                        <input
                          type="text"
                          value={rule.public_reply}
                          onChange={(e) => handleRuleChange(idx, 'public_reply', e.target.value)}
                          placeholder="e.g. ধন্যবাদ কমেন্টের জন্য! দাম ইনবক্সে পাঠানো হয়েছে।"
                          className="w-full px-2.5 py-1.5 bg-white border border-slate-300 rounded-lg text-xs font-bangla focus:outline-none focus:ring-1 focus:ring-blue-600"
                        />
                      </div>

                      <div className="space-y-1">
                        <label className="flex items-center gap-1.5 cursor-pointer">
                          <input
                            type="checkbox"
                            checked={rule.send_private_dm}
                            onChange={(e) => handleRuleChange(idx, 'send_private_dm', e.target.checked)}
                            className="w-3.5 h-3.5 text-blue-600 rounded"
                          />
                          <span className="font-bold text-purple-800">Send Private Reply into Customer's DM</span>
                        </label>
                        {rule.send_private_dm && (
                          <textarea
                            rows={2}
                            value={rule.private_reply}
                            onChange={(e) => handleRuleChange(idx, 'private_reply', e.target.value)}
                            placeholder="e.g. আসসালামু আলাইকুম! আমাদের পোলো শার্টের দাম মাত্র ৮৫০ টাকা..."
                            className="w-full px-2.5 py-1.5 bg-white border border-slate-300 rounded-lg text-xs font-bangla focus:outline-none focus:ring-1 focus:ring-blue-600"
                          />
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              <div className="flex items-center justify-end gap-2 pt-4 border-t border-slate-200">
                <button
                  type="button"
                  onClick={() => setIsSettingsOpen(false)}
                  className="px-4 py-2 border border-slate-300 rounded-xl text-xs font-semibold text-slate-700 hover:bg-slate-50"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={savingSettings}
                  className="px-5 py-2 bg-blue-600 hover:bg-blue-500 text-white rounded-xl text-xs font-semibold shadow-sm disabled:opacity-50"
                >
                  {savingSettings ? 'Saving...' : 'Save Rules & Settings'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Manual Reply Modal */}
      {replyModalComment && (
        <div className="fixed inset-0 z-50 bg-slate-900/50 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl max-w-lg w-full p-6 shadow-2xl border border-slate-200">
            <div className="flex items-center justify-between pb-3 border-b border-slate-200">
              <h3 className="font-bold text-slate-900 text-base">Reply to Comment</h3>
              <button onClick={() => setReplyModalComment(null)} className="p-1 text-slate-400 hover:text-slate-600">
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="my-3 p-3 rounded-xl bg-slate-50 border border-slate-200 text-xs">
              <span className="font-semibold text-slate-500 block">User Comment:</span>
              <p className="text-slate-800 font-medium font-bangla mt-0.5">{replyModalComment.message}</p>
            </div>

            {replyError && (
              <div className="mb-3 p-3 rounded-xl bg-rose-50 border border-rose-200 text-rose-800 text-xs flex items-center gap-2">
                <AlertTriangle className="w-4 h-4 text-rose-600 shrink-0" />
                <span>{replyError}</span>
              </div>
            )}

            <form onSubmit={handleSendManualReply} className="space-y-4">
              <div>
                <label className="block text-xs font-bold text-slate-700 uppercase mb-1">Reply Destination</label>
                <div className="grid grid-cols-2 gap-2">
                  <button
                    type="button"
                    onClick={() => setManualReplyType('public')}
                    className={`py-2 px-3 rounded-xl text-xs font-semibold border transition-all ${
                      manualReplyType === 'public'
                        ? 'bg-blue-50 text-blue-700 border-blue-600 shadow-sm'
                        : 'bg-slate-50 text-slate-600 border-slate-200'
                    }`}
                  >
                    Public Comment Reply
                  </button>
                  <button
                    type="button"
                    onClick={() => setManualReplyType('private')}
                    disabled={replyModalComment.is_private_reply_sent}
                    className={`py-2 px-3 rounded-xl text-xs font-semibold border transition-all ${
                      manualReplyType === 'private'
                        ? 'bg-purple-50 text-purple-700 border-purple-600 shadow-sm'
                        : replyModalComment.is_private_reply_sent
                        ? 'bg-slate-100 text-slate-400 border-slate-200 cursor-not-allowed'
                        : 'bg-slate-50 text-slate-600 border-slate-200'
                    }`}
                  >
                    {replyModalComment.is_private_reply_sent ? 'Private DM (Sent Already)' : 'Private Reply (DM)'}
                  </button>
                </div>
                {manualReplyType === 'private' && (
                  <p className="text-[11px] text-purple-700 mt-1 flex items-center gap-1 font-medium">
                    <Lock className="w-3 h-3" /> Meta limit: only ONE private reply may be sent per comment.
                  </p>
                )}
              </div>

              <div>
                <label className="block text-xs font-bold text-slate-700 uppercase mb-1">Message Text</label>
                <textarea
                  rows={3}
                  required
                  value={manualReplyText}
                  onChange={(e) => setManualReplyText(e.target.value)}
                  placeholder="Type your response in Bangla, Banglish, or English..."
                  className="w-full px-3 py-2 border border-slate-300 rounded-xl text-xs font-bangla focus:outline-none focus:ring-2 focus:ring-blue-600"
                />
              </div>

              <div className="flex justify-end gap-2 pt-2 border-t border-slate-200">
                <button
                  type="button"
                  onClick={() => setReplyModalComment(null)}
                  className="px-4 py-2 border border-slate-300 rounded-xl text-xs font-semibold text-slate-700 hover:bg-slate-50"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={sendingReply}
                  className="px-5 py-2 bg-blue-600 hover:bg-blue-500 text-white rounded-xl text-xs font-semibold shadow-sm disabled:opacity-50"
                >
                  {sendingReply ? 'Dispatching...' : 'Send Reply'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
