import React, { useState, useEffect } from 'react';
import { apiClient } from '../api/client';
import { Post, PostVariant, Product } from '../types';
import { 
  Calendar as CalendarIcon, Sparkles, Send, Clock, AlertTriangle, 
  CheckCircle2, RefreshCw, Plus, Image as ImageIcon, Trash2, 
  Facebook, Instagram, Eye, Check, ExternalLink, HelpCircle, AlertCircle
} from 'lucide-react';

export const PostsPage: React.FC = () => {
  const [activeTab, setActiveTab] = useState<'composer' | 'calendar'>('composer');
  const [posts, setPosts] = useState<Post[]>([]);
  const [products, setProducts] = useState<Product[]>([]);
  const [failedPosts, setFailedPosts] = useState<Post[]>([]);
  const [loading, setLoading] = useState(true);
  const [statusFilter, setStatusFilter] = useState<string>('all');

  // Composer State
  const [notes, setNotes] = useState('');
  const [selectedProductId, setSelectedProductId] = useState<number | undefined>(undefined);
  const [language, setLanguage] = useState<'Bangla' | 'Banglish' | 'English'>('Bangla');
  const [tone, setTone] = useState('Sales / Promotional');
  const [mediaUrls, setMediaUrls] = useState<string[]>(['']);
  const [targetPlatforms, setTargetPlatforms] = useState<string[]>(['facebook', 'instagram']);
  
  // AI Generated Variants
  const [variants, setVariants] = useState<PostVariant[]>([]);
  const [isGenerating, setIsGenerating] = useState(false);
  const [selectedVariantIndex, setSelectedVariantIndex] = useState<number | null>(null);

  // Editable Post Draft Form
  const [postTitle, setPostTitle] = useState('');
  const [postCaption, setPostCaption] = useState('');
  const [postHashtags, setPostHashtags] = useState('');
  const [publishMode, setPublishMode] = useState<'draft' | 'publish_now' | 'schedule'>('schedule');
  const [scheduledDhaka, setScheduledDhaka] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);

  // Worker tick state
  const [ticking, setTicking] = useState(false);

  const fetchAll = async () => {
    try {
      setLoading(true);
      const [postsData, failuresData, productsData] = await Promise.all([
        apiClient.posts.getPosts(),
        apiClient.posts.getFailures(),
        apiClient.catalog.getProducts(),
      ]);
      setPosts(postsData);
      setFailedPosts(failuresData);
      setProducts(productsData);
    } catch (err) {
      console.error('Failed to load posts data:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAll();
    // Default scheduled time: tomorrow 03:00 PM Dhaka time
    const tomorrow = new Date();
    tomorrow.setDate(tomorrow.getDate() + 1);
    tomorrow.setHours(15, 0, 0, 0);
    const pad = (n: number) => n.toString().padStart(2, '0');
    const defaultDhakaStr = `${tomorrow.getFullYear()}-${pad(tomorrow.getMonth() + 1)}-${pad(tomorrow.getDate())}T15:00`;
    setScheduledDhaka(defaultDhakaStr);
  }, []);

  const handleGenerateVariants = async () => {
    if (!notes.trim() && !selectedProductId) {
      alert('Please enter some notes or select a product to generate captions.');
      return;
    }
    setIsGenerating(true);
    try {
      const res = await apiClient.posts.generateVariants({
        notes: notes.trim(),
        product_id: selectedProductId,
        language,
        tone,
      });
      setVariants(res.variants);
      if (res.variants.length > 0) {
        applyVariantToEditor(res.variants[0], 0);
      }
    } catch (err: any) {
      alert('Failed to generate AI variants.');
    } finally {
      setIsGenerating(false);
    }
  };

  const applyVariantToEditor = (variant: PostVariant, index: number) => {
    setSelectedVariantIndex(index);
    setPostTitle(variant.title);
    setPostCaption(variant.caption);
    setPostHashtags(variant.hashtags);
  };

  const handleAddMediaUrl = () => {
    setMediaUrls([...mediaUrls, '']);
  };

  const handleMediaUrlChange = (index: number, val: string) => {
    const updated = [...mediaUrls];
    updated[index] = val;
    setMediaUrls(updated);
  };

  const handleRemoveMediaUrl = (index: number) => {
    setMediaUrls(mediaUrls.filter((_, i) => i !== index));
  };

  const handlePlatformToggle = (platform: string) => {
    if (targetPlatforms.includes(platform)) {
      if (targetPlatforms.length === 1) return; // keep at least 1
      setTargetPlatforms(targetPlatforms.filter((p) => p !== platform));
    } else {
      setTargetPlatforms([...targetPlatforms, platform]);
    }
  };

  const handleSavePost = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!postCaption.trim()) {
      alert('Caption cannot be empty.');
      return;
    }
    const cleanMedia = mediaUrls.map((u) => u.trim()).filter((u) => u.length > 0);
    if (targetPlatforms.includes('instagram') && cleanMedia.length === 0) {
      alert('Instagram Content Publishing requires at least one public image URL (JPEG/PNG).');
      return;
    }

    setIsSubmitting(true);
    try {
      await apiClient.posts.createPost({
        title: postTitle.trim() || undefined,
        caption: postCaption.trim(),
        hashtags: postHashtags.trim() || undefined,
        media_urls: cleanMedia,
        language,
        tone,
        product_id: selectedProductId,
        target_platforms: targetPlatforms,
        publish_mode: publishMode,
        scheduled_at_dhaka: publishMode === 'schedule' ? scheduledDhaka : undefined,
        variants_json: variants.length > 0 ? variants : undefined,
      });

      alert(
        publishMode === 'publish_now'
          ? 'Post published immediately!'
          : publishMode === 'schedule'
          ? 'Post successfully scheduled in Asia/Dhaka time!'
          : 'Post saved as draft!'
      );

      // Reset form and switch to calendar tab
      setPostTitle('');
      setPostCaption('');
      setPostHashtags('');
      setVariants([]);
      setSelectedVariantIndex(null);
      await fetchAll();
      setActiveTab('calendar');
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Failed to save/publish post.');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handlePublishNow = async (id: number) => {
    try {
      await apiClient.posts.publishNow(id);
      await fetchAll();
      alert('Post dispatched to publishing APIs!');
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Failed to publish post.');
    }
  };

  const handleRetry = async (id: number) => {
    try {
      const res = await apiClient.posts.retry(id);
      await fetchAll();
      if (res.status === 'published') {
        alert('Post retry succeeded! Published to targets.');
      } else {
        alert(`Retry attempted: ${res.errors ? res.errors.join(', ') : 'Still failing'}`);
      }
    } catch (err: any) {
      alert('Failed to retry post.');
    }
  };

  const handleDelete = async (id: number) => {
    if (confirm('Delete this post?')) {
      try {
        await apiClient.posts.delete(id);
        await fetchAll();
      } catch (err) {
        alert('Failed to delete post.');
      }
    }
  };

  const handleRunWorkerTick = async () => {
    setTicking(true);
    try {
      const res = await apiClient.posts.runWorkerTick();
      await fetchAll();
      alert(`Worker Tick Executed:\nProcessed ${res.scheduled_posts_due} due scheduled posts.`);
    } catch (err) {
      alert('Failed to run scheduler tick.');
    } finally {
      setTicking(false);
    }
  };

  const filteredPosts = posts.filter((p) => {
    if (statusFilter === 'all') return true;
    return p.status === statusFilter;
  });

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">
      {/* Top Banner */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 border-b border-slate-200 pb-5">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-2xl font-bold text-slate-900">Social Commerce Studio</h1>
            <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-100 text-emerald-800">
              Phase 6
            </span>
          </div>
          <p className="text-sm text-slate-500 mt-1">
            AI post composer, 3-variant Bangla/Banglish copywriting, official Facebook & Instagram publishing, and Asia/Dhaka calendar scheduler.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <div className="px-3 py-1.5 rounded-xl border border-slate-200 bg-slate-50 text-xs font-medium text-slate-600 flex items-center gap-1.5">
            <Clock className="w-3.5 h-3.5 text-blue-600" />
            <span>Asia/Dhaka (UTC+6 BST)</span>
          </div>

          <button
            onClick={handleRunWorkerTick}
            disabled={ticking}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl border border-slate-300 hover:bg-slate-50 text-xs font-semibold text-slate-700 transition-colors"
            title="Trigger background worker check for scheduled posts"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${ticking ? 'animate-spin' : ''}`} />
            <span>Worker Tick</span>
          </button>
        </div>
      </div>

      {/* Failure Notice Banner */}
      {failedPosts.length > 0 && (
        <div className="p-4 rounded-2xl bg-rose-50 border border-rose-200 shadow-sm space-y-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2 text-rose-800 font-bold text-sm">
              <AlertTriangle className="w-5 h-5 text-rose-600 shrink-0" />
              <span>{failedPosts.length} Post(s) Failed to Publish</span>
            </div>
            <span className="text-xs text-rose-600 font-medium">Safe against double-posting</span>
          </div>

          <div className="space-y-2">
            {failedPosts.map((fp) => (
              <div key={fp.id} className="p-3 rounded-xl bg-white border border-rose-200 flex items-center justify-between flex-wrap gap-2 text-xs">
                <div>
                  <span className="font-bold text-slate-900">Post #{fp.id}: </span>
                  <span className="text-slate-600 truncate max-w-xs">{fp.title || fp.caption.slice(0, 50)}...</span>
                  <div className="text-rose-700 mt-0.5 text-[11px] font-mono">
                    Error: {fp.error_message || 'API connection or media validation failure'}
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-slate-400">Retries: {fp.retry_count}</span>
                  <button
                    onClick={() => handleRetry(fp.id)}
                    className="px-2.5 py-1 rounded-lg bg-rose-600 hover:bg-rose-700 text-white font-semibold shadow-sm transition-colors"
                  >
                    Retry Now
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Tabs */}
      <div className="flex border-b border-slate-200">
        <button
          onClick={() => setActiveTab('composer')}
          className={`pb-3 px-4 text-sm font-semibold border-b-2 flex items-center gap-2 transition-colors ${
            activeTab === 'composer'
              ? 'border-emerald-600 text-emerald-600'
              : 'border-transparent text-slate-500 hover:text-slate-800'
          }`}
        >
          <Sparkles className="w-4 h-4" />
          <span>Post Composer & AI Generator</span>
        </button>

        <button
          onClick={() => setActiveTab('calendar')}
          className={`pb-3 px-4 text-sm font-semibold border-b-2 flex items-center gap-2 transition-colors ${
            activeTab === 'calendar'
              ? 'border-emerald-600 text-emerald-600'
              : 'border-transparent text-slate-500 hover:text-slate-800'
          }`}
        >
          <CalendarIcon className="w-4 h-4" />
          <span>Calendar & Scheduled Queue ({posts.length})</span>
        </button>
      </div>

      {/* TAB 1: POST COMPOSER */}
      {activeTab === 'composer' && (
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
          {/* Left Column: Creative Brief & AI Generator */}
          <div className="lg:col-span-5 space-y-6">
            <div className="bg-white border border-slate-200 rounded-2xl p-6 shadow-sm space-y-4">
              <div className="flex items-center justify-between border-b border-slate-100 pb-3">
                <h2 className="text-base font-bold text-slate-900 flex items-center gap-2">
                  <Sparkles className="w-4 h-4 text-emerald-600" />
                  <span>1. Creative Brief & Angle</span>
                </h2>
                <span className="text-xs text-slate-400">Generates 3 Variants</span>
              </div>

              {/* Product Select (Optional) */}
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  Select Product from Catalog (Optional)
                </label>
                <select
                  value={selectedProductId || ''}
                  onChange={(e) => setSelectedProductId(e.target.value ? Number(e.target.value) : undefined)}
                  className="w-full text-xs rounded-xl border-slate-300 shadow-sm focus:border-emerald-500 focus:ring-emerald-500 p-2.5 bg-slate-50/50"
                >
                  <option value="">-- No specific catalog item --</option>
                  {products.map((p) => (
                    <option key={p.id} value={p.id}>
                      {p.title} (৳{p.base_price})
                    </option>
                  ))}
                </select>
              </div>

              {/* Notes */}
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  Merchant Notes / Key Selling Points
                </label>
                <textarea
                  rows={3}
                  value={notes}
                  onChange={(e) => setNotes(e.target.value)}
                  placeholder="e.g. নতুন সুতি পাঞ্জাবি কালেকশন, প্রিমিয়াম এমব্রয়ডারি, ঢাকার ভিতরে ডেলিভারি ৬০ টাকা, সীমিত স্টক..."
                  className="w-full text-xs rounded-xl border-slate-300 shadow-sm focus:border-emerald-500 focus:ring-emerald-500 p-2.5"
                />
              </div>

              {/* Language & Tone */}
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">Language</label>
                  <select
                    value={language}
                    onChange={(e: any) => setLanguage(e.target.value)}
                    className="w-full text-xs rounded-xl border-slate-300 shadow-sm focus:border-emerald-500 focus:ring-emerald-500 p-2"
                  >
                    <option value="Bangla">বাংলা (Bangla Script)</option>
                    <option value="Banglish">Banglish (Phonetic)</option>
                    <option value="English">English</option>
                  </select>
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">Brand Tone</label>
                  <select
                    value={tone}
                    onChange={(e) => setTone(e.target.value)}
                    className="w-full text-xs rounded-xl border-slate-300 shadow-sm focus:border-emerald-500 focus:ring-emerald-500 p-2"
                  >
                    <option value="Sales / Promotional">Sales / Promotional</option>
                    <option value="Friendly">Friendly & Welcoming</option>
                    <option value="Urgent / Limited Offer">Urgent / Limited Stock</option>
                    <option value="Formal / Elegant">Formal & Elegant</option>
                    <option value="Storytelling">Storytelling & Relatable</option>
                  </select>
                </div>
              </div>

              {/* Generate Button */}
              <button
                type="button"
                onClick={handleGenerateVariants}
                disabled={isGenerating}
                className="w-full flex items-center justify-center gap-2 py-2.5 px-4 rounded-xl bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-700 hover:to-teal-700 text-white font-bold text-xs shadow-md shadow-emerald-600/20 transition-all disabled:opacity-50"
              >
                <Sparkles className={`w-4 h-4 ${isGenerating ? 'animate-spin' : ''}`} />
                <span>{isGenerating ? 'Generating 3 Variants...' : 'Generate 3 AI Variants'}</span>
              </button>
            </div>

            {/* Generated Variants Display */}
            {variants.length > 0 && (
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <h3 className="text-xs font-bold text-slate-900 uppercase tracking-wider">
                    AI Generated Copy Options ({variants.length})
                  </h3>
                  <span className="text-[11px] text-slate-400">Click to apply to form</span>
                </div>

                {variants.map((v, idx) => (
                  <div
                    key={idx}
                    onClick={() => applyVariantToEditor(v, idx)}
                    className={`p-4 rounded-2xl border transition-all cursor-pointer ${
                      selectedVariantIndex === idx
                        ? 'border-emerald-500 bg-emerald-50/50 shadow-sm ring-2 ring-emerald-500/20'
                        : 'border-slate-200 bg-white hover:border-slate-300'
                    }`}
                  >
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-xs font-bold text-slate-900 flex items-center gap-1.5">
                        <span className="w-5 h-5 rounded-full bg-slate-900 text-white flex items-center justify-center text-[10px]">
                          {v.variant_number}
                        </span>
                        <span>{v.style_description}</span>
                      </span>
                      {selectedVariantIndex === idx && (
                        <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-600 text-white flex items-center gap-1">
                          <Check className="w-3 h-3" />
                          <span>Active</span>
                        </span>
                      )}
                    </div>

                    <div className="text-xs font-semibold text-slate-900 mb-1">{v.title}</div>
                    <p className="text-xs text-slate-600 line-clamp-3 whitespace-pre-line mb-2">
                      {v.caption}
                    </p>
                    <div className="text-[11px] text-emerald-700 font-mono truncate">{v.hashtags}</div>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Right Column: Editable Post Form & Publisher */}
          <div className="lg:col-span-7 space-y-6">
            <form onSubmit={handleSavePost} className="bg-white border border-slate-200 rounded-2xl p-6 shadow-sm space-y-5">
              <div className="flex items-center justify-between border-b border-slate-100 pb-3">
                <h2 className="text-base font-bold text-slate-900 flex items-center gap-2">
                  <Eye className="w-4 h-4 text-emerald-600" />
                  <span>2. Review, Edit & Schedule</span>
                </h2>
                <span className="text-xs text-slate-500">Edit freely before saving</span>
              </div>

              {/* Target Platforms */}
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1.5">
                  Target Social Platforms
                </label>
                <div className="flex items-center gap-3">
                  <button
                    type="button"
                    onClick={() => handlePlatformToggle('facebook')}
                    className={`flex items-center gap-2 px-3 py-2 rounded-xl text-xs font-semibold border transition-all ${
                      targetPlatforms.includes('facebook')
                        ? 'border-blue-500 bg-blue-50 text-blue-800'
                        : 'border-slate-200 bg-white text-slate-400'
                    }`}
                  >
                    <Facebook className="w-4 h-4 text-blue-600" />
                    <span>Facebook Page Feed / Photos</span>
                  </button>

                  <button
                    type="button"
                    onClick={() => handlePlatformToggle('instagram')}
                    className={`flex items-center gap-2 px-3 py-2 rounded-xl text-xs font-semibold border transition-all ${
                      targetPlatforms.includes('instagram')
                        ? 'border-pink-500 bg-pink-50 text-pink-800'
                        : 'border-slate-200 bg-white text-slate-400'
                    }`}
                  >
                    <Instagram className="w-4 h-4 text-pink-600" />
                    <span>Instagram Professional Feed</span>
                  </button>
                </div>
              </div>

              {/* Media URLs */}
              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <label className="block text-xs font-semibold text-slate-700">
                    Image URLs (JPEG/PNG, Aspect Ratio 4:5 to 1.91:1)
                  </label>
                  <button
                    type="button"
                    onClick={handleAddMediaUrl}
                    className="text-xs text-emerald-600 font-bold hover:underline flex items-center gap-1"
                  >
                    <Plus className="w-3.5 h-3.5" />
                    <span>Add Image URL</span>
                  </button>
                </div>

                {mediaUrls.map((url, idx) => (
                  <div key={idx} className="flex items-center gap-2">
                    <input
                      type="url"
                      value={url}
                      onChange={(e) => handleMediaUrlChange(idx, e.target.value)}
                      placeholder="https://your-public-cdn.com/images/product1.jpg"
                      className="flex-1 text-xs rounded-xl border-slate-300 shadow-sm focus:border-emerald-500 focus:ring-emerald-500 p-2.5"
                    />
                    {mediaUrls.length > 1 && (
                      <button
                        type="button"
                        onClick={() => handleRemoveMediaUrl(idx)}
                        className="p-2 text-slate-400 hover:text-rose-600"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    )}
                  </div>
                ))}
                <p className="text-[11px] text-slate-400">
                  Meta Instagram Content Publishing API requires a direct public JPEG/PNG image URL. Facebook Page photos accept up to 4MB.
                </p>
              </div>

              {/* Title / Hook */}
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  Headline / Catchy Title
                </label>
                <input
                  type="text"
                  value={postTitle}
                  onChange={(e) => setPostTitle(e.target.value)}
                  placeholder="e.g. ✨ প্রিমিয়াম সুতি পাঞ্জাবি কালেকশন — সীমিত স্টক!"
                  className="w-full text-xs rounded-xl border-slate-300 shadow-sm focus:border-emerald-500 focus:ring-emerald-500 p-2.5 font-medium"
                />
              </div>

              {/* Caption */}
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  Post Caption / Body Text
                </label>
                <textarea
                  rows={8}
                  value={postCaption}
                  onChange={(e) => setPostCaption(e.target.value)}
                  placeholder="Full caption text with Bangladeshi greetings, product details, delivery charge, and order call to action..."
                  className="w-full text-xs rounded-xl border-slate-300 shadow-sm focus:border-emerald-500 focus:ring-emerald-500 p-2.5 font-sans whitespace-pre-wrap leading-relaxed"
                />
              </div>

              {/* Hashtags */}
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  Hashtags (Max 30 for Instagram)
                </label>
                <input
                  type="text"
                  value={postHashtags}
                  onChange={(e) => setPostHashtags(e.target.value)}
                  placeholder="#BDOnlineShop #DhakaShopping #PanjabiBD #EidFashion"
                  className="w-full text-xs rounded-xl border-slate-300 shadow-sm focus:border-emerald-500 focus:ring-emerald-500 p-2.5 font-mono text-emerald-800"
                />
              </div>

              {/* Publishing Schedule Options */}
              <div className="p-4 rounded-xl border border-slate-200 bg-slate-50/60 space-y-3">
                <label className="block text-xs font-bold text-slate-900">Publishing Mode</label>
                <div className="grid grid-cols-3 gap-2">
                  <button
                    type="button"
                    onClick={() => setPublishMode('schedule')}
                    className={`py-2 px-3 rounded-xl text-xs font-semibold border transition-all ${
                      publishMode === 'schedule'
                        ? 'border-emerald-600 bg-emerald-600 text-white shadow-sm'
                        : 'border-slate-200 bg-white text-slate-600'
                    }`}
                  >
                    Schedule for Later
                  </button>
                  <button
                    type="button"
                    onClick={() => setPublishMode('publish_now')}
                    className={`py-2 px-3 rounded-xl text-xs font-semibold border transition-all ${
                      publishMode === 'publish_now'
                        ? 'border-blue-600 bg-blue-600 text-white shadow-sm'
                        : 'border-slate-200 bg-white text-slate-600'
                    }`}
                  >
                    Publish Immediately
                  </button>
                  <button
                    type="button"
                    onClick={() => setPublishMode('draft')}
                    className={`py-2 px-3 rounded-xl text-xs font-semibold border transition-all ${
                      publishMode === 'draft'
                        ? 'border-slate-800 bg-slate-800 text-white shadow-sm'
                        : 'border-slate-200 bg-white text-slate-600'
                    }`}
                  >
                    Save as Draft
                  </button>
                </div>

                {publishMode === 'schedule' && (
                  <div className="pt-2">
                    <label className="block text-xs font-semibold text-slate-700 mb-1 flex items-center justify-between">
                      <span>Schedule Date & Time (Asia/Dhaka BST, UTC+6):</span>
                      <span className="text-slate-400 text-[10px]">Stored in UTC</span>
                    </label>
                    <input
                      type="datetime-local"
                      value={scheduledDhaka}
                      onChange={(e) => setScheduledDhaka(e.target.value)}
                      className="w-full text-xs rounded-xl border-slate-300 shadow-sm focus:border-emerald-500 focus:ring-emerald-500 p-2.5 bg-white"
                    />
                  </div>
                )}
              </div>

              {/* Submit Button */}
              <div className="flex justify-end pt-2">
                <button
                  type="submit"
                  disabled={isSubmitting}
                  className="flex items-center gap-2 px-6 py-2.5 rounded-xl bg-slate-900 hover:bg-slate-800 text-white text-xs font-bold shadow-md transition-all disabled:opacity-50"
                >
                  <Send className="w-4 h-4" />
                  <span>
                    {isSubmitting
                      ? 'Processing...'
                      : publishMode === 'publish_now'
                      ? 'Publish to Social Channels'
                      : publishMode === 'schedule'
                      ? 'Confirm & Schedule Post'
                      : 'Save Post as Draft'}
                  </span>
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* TAB 2: CALENDAR & SCHEDULED QUEUE */}
      {activeTab === 'calendar' && (
        <div className="space-y-6">
          {/* Filter Bar */}
          <div className="flex items-center justify-between flex-wrap gap-3 pb-2">
            <div className="flex items-center gap-1.5 bg-slate-100 p-1 rounded-xl">
              {['all', 'scheduled', 'published', 'draft', 'failed'].map((st) => (
                <button
                  key={st}
                  onClick={() => setStatusFilter(st)}
                  className={`px-3 py-1.5 rounded-lg text-xs font-semibold uppercase tracking-wider transition-all ${
                    statusFilter === st
                      ? 'bg-white text-slate-900 shadow-sm'
                      : 'text-slate-500 hover:text-slate-900'
                  }`}
                >
                  {st}
                </button>
              ))}
            </div>

            <button
              onClick={() => setActiveTab('composer')}
              className="flex items-center gap-1.5 px-4 py-2 rounded-xl bg-slate-900 hover:bg-slate-800 text-white text-xs font-semibold shadow-sm transition-colors"
            >
              <Plus className="w-4 h-4" />
              <span>Compose New Post</span>
            </button>
          </div>

          {/* Posts List / Grid */}
          {filteredPosts.length === 0 ? (
            <div className="text-center py-12 bg-white border border-slate-200 rounded-2xl">
              <CalendarIcon className="w-12 h-12 text-slate-300 mx-auto mb-3" />
              <h3 className="text-sm font-bold text-slate-700">No Posts Found</h3>
              <p className="text-xs text-slate-400 mt-1">There are no posts matching the current filter.</p>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
              {filteredPosts.map((post) => (
                <div
                  key={post.id}
                  className={`bg-white border rounded-2xl p-5 shadow-sm flex flex-col justify-between space-y-4 transition-all ${
                    post.status === 'failed'
                      ? 'border-rose-300 bg-rose-50/20'
                      : post.status === 'published'
                      ? 'border-emerald-200'
                      : 'border-slate-200'
                  }`}
                >
                  <div className="space-y-3">
                    {/* Header: Platforms & Status Badge */}
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-1.5">
                        {post.target_platforms?.includes('facebook') && (
                          <span className="p-1 rounded bg-blue-50 text-blue-600" title="Facebook Page">
                            <Facebook className="w-4 h-4" />
                          </span>
                        )}
                        {post.target_platforms?.includes('instagram') && (
                          <span className="p-1 rounded bg-pink-50 text-pink-600" title="Instagram Feed">
                            <Instagram className="w-4 h-4" />
                          </span>
                        )}
                      </div>

                      <span
                        className={`px-2.5 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wider ${
                          post.status === 'published'
                            ? 'bg-emerald-100 text-emerald-800'
                            : post.status === 'scheduled'
                            ? 'bg-blue-100 text-blue-800'
                            : post.status === 'failed'
                            ? 'bg-rose-100 text-rose-800'
                            : 'bg-slate-100 text-slate-700'
                        }`}
                      >
                        {post.status}
                      </span>
                    </div>

                    {/* Image Preview Thumbnail (if any) */}
                    {post.media_urls && post.media_urls.length > 0 && post.media_urls[0] && (
                      <div className="w-full h-36 rounded-xl overflow-hidden bg-slate-100 border border-slate-200">
                        <img
                          src={post.media_urls[0]}
                          alt="Post media preview"
                          className="w-full h-full object-cover"
                          onError={(e) => {
                            (e.target as HTMLElement).style.display = 'none';
                          }}
                        />
                      </div>
                    )}

                    {/* Content Preview */}
                    <div>
                      {post.title && (
                        <h4 className="text-xs font-bold text-slate-900 line-clamp-1 mb-1">
                          {post.title}
                        </h4>
                      )}
                      <p className="text-xs text-slate-600 line-clamp-3 whitespace-pre-line leading-relaxed">
                        {post.caption}
                      </p>
                      {post.hashtags && (
                        <div className="text-[11px] text-emerald-700 font-mono mt-1.5 line-clamp-1">
                          {post.hashtags}
                        </div>
                      )}
                    </div>

                    {/* Timing & Error Details */}
                    <div className="pt-2 border-t border-slate-100 text-[11px] space-y-1">
                      {post.scheduled_at_dhaka && (
                        <div className="text-slate-600 flex items-center gap-1">
                          <Clock className="w-3.5 h-3.5 text-blue-600 shrink-0" />
                          <span>Scheduled: {post.scheduled_at_dhaka}</span>
                        </div>
                      )}
                      {post.published_at_dhaka && (
                        <div className="text-emerald-700 flex items-center gap-1 font-medium">
                          <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600 shrink-0" />
                          <span>Published: {post.published_at_dhaka}</span>
                        </div>
                      )}
                      {post.facebook_post_id && (
                        <div className="text-slate-400 font-mono text-[10px]">
                          FB ID: {post.facebook_post_id}
                        </div>
                      )}
                      {post.instagram_media_id && (
                        <div className="text-slate-400 font-mono text-[10px]">
                          IG ID: {post.instagram_media_id}
                        </div>
                      )}
                      {post.error_message && (
                        <div className="text-rose-600 bg-rose-50 p-2 rounded-lg text-[10px] font-mono leading-tight">
                          {post.error_message}
                        </div>
                      )}
                    </div>
                  </div>

                  {/* Actions */}
                  <div className="pt-3 border-t border-slate-100 flex items-center justify-between">
                    <button
                      onClick={() => handleDelete(post.id)}
                      className="p-1.5 text-slate-400 hover:text-rose-600 transition-colors"
                      title="Delete Post"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>

                    <div className="flex items-center gap-2">
                      {post.status === 'failed' && (
                        <button
                          onClick={() => handleRetry(post.id)}
                          className="px-2.5 py-1 rounded-lg bg-rose-600 hover:bg-rose-700 text-white text-xs font-semibold transition-colors"
                        >
                          Retry
                        </button>
                      )}
                      {post.status !== 'published' && (
                        <button
                          onClick={() => handlePublishNow(post.id)}
                          className="px-2.5 py-1 rounded-lg bg-slate-900 hover:bg-slate-800 text-white text-xs font-semibold transition-colors"
                        >
                          Publish Now
                        </button>
                      )}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
};
