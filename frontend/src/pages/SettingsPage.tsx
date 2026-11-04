import React, { useState, useEffect } from 'react';
import { apiClient } from '../api/client';
import { StoreSettings, FacebookConnectionStatus, InstagramConnectionStatus } from '../types';
import { 
  Save, CheckCircle, Sliders, Sparkles, Truck, ShieldAlert, 
  Share2, Key, Link2, Copy, Check, Power, RefreshCw, AlertCircle, Instagram, Compass 
} from 'lucide-react';

export const SettingsPage: React.FC = () => {
  const [settings, setSettings] = useState<StoreSettings>({
    store_name: 'StyleCraft BD',
    brand_tone: 'Friendly, polite, helpful Bangladeshi online shop assistant. Speak naturally in the customer\'s language (Bangla, Banglish, or English). Always address customers respectfully.',
    delivery_inside_dhaka: '80',
    delivery_outside_dhaka: '150',
    llm_provider: 'mock',
    embedding_provider: 'mock',
  });
  const [fbStatus, setFbStatus] = useState<FacebookConnectionStatus | null>(null);
  const [igStatus, setIgStatus] = useState<InstagramConnectionStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [status, setStatus] = useState<string | null>(null);

  // Facebook Connection Modal State
  const [isFbModalOpen, setIsFbModalOpen] = useState(false);
  const [pageId, setPageId] = useState('');
  const [pageName, setPageName] = useState('');
  const [pageAccessToken, setPageAccessToken] = useState('');
  const [autoSend, setAutoSend] = useState(false);
  const [fbSaving, setFbSaving] = useState(false);
  const [copiedVerify, setCopiedVerify] = useState(false);

  // Instagram Connection Modal State
  const [isIgModalOpen, setIsIgModalOpen] = useState(false);
  const [igUserId, setIgUserId] = useState('');
  const [igUsername, setIgUsername] = useState('');
  const [igAccessToken, setIgAccessToken] = useState('');
  const [igAutoSend, setIgAutoSend] = useState(false);
  const [igSaving, setIgSaving] = useState(false);
  const [discoveringIg, setDiscoveringIg] = useState(false);

  const fetchAll = async () => {
    try {
      setLoading(true);
      const [sData, fbData, igData] = await Promise.all([
        apiClient.settings.getSettings(),
        apiClient.facebook.getStatus(),
        apiClient.instagram.getStatus(),
      ]);
      setSettings(sData);
      setFbStatus(fbData);
      setIgStatus(igData);
      if (fbData.is_connected) {
        setPageId(fbData.page_id || '');
        setPageName(fbData.page_name || '');
        setAutoSend(fbData.auto_send);
      }
      if (igData.is_connected) {
        setIgUserId(igData.ig_user_id || '');
        setIgUsername(igData.username || '');
        setIgAutoSend(igData.auto_send);
      }
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAll();
  }, []);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setStatus(null);
    try {
      await apiClient.settings.updateSettings(settings);
      setStatus('Store settings updated successfully!');
      setTimeout(() => setStatus(null), 3000);
    } catch (err) {
      setStatus('Failed to update settings.');
    } finally {
      setSaving(false);
    }
  };

  const handleSaveFacebook = async (e: React.FormEvent) => {
    e.preventDefault();
    setFbSaving(true);
    try {
      await apiClient.facebook.connect({
        page_id: pageId,
        page_name: pageName,
        page_access_token: pageAccessToken,
        auto_send: autoSend,
      });
      setIsFbModalOpen(false);
      setPageAccessToken('');
      await fetchAll();
      setStatus('Facebook Page connected successfully!');
      setTimeout(() => setStatus(null), 3000);
    } catch (err) {
      alert('Failed to connect Facebook page.');
    } finally {
      setFbSaving(false);
    }
  };

  const handleDisconnectFb = async () => {
    if (confirm('Disconnect your Facebook Page?')) {
      await apiClient.facebook.disconnect();
      await fetchAll();
    }
  };

  const handleToggleAutoSend = async (val: boolean) => {
    setAutoSend(val);
    if (fbStatus?.is_connected) {
      await apiClient.facebook.updateSettings({ auto_send: val });
      fetchAll();
    }
  };

  const handleSaveInstagram = async (e: React.FormEvent) => {
    e.preventDefault();
    setIgSaving(true);
    try {
      await apiClient.instagram.connect({
        ig_user_id: igUserId,
        username: igUsername,
        access_token: igAccessToken,
        auto_send: igAutoSend,
      });
      setIsIgModalOpen(false);
      setIgAccessToken('');
      await fetchAll();
      setStatus('Instagram Professional account connected successfully!');
      setTimeout(() => setStatus(null), 3000);
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Failed to connect Instagram account.');
    } finally {
      setIgSaving(false);
    }
  };

  const handleDisconnectIg = async () => {
    if (confirm('Disconnect your Instagram Professional account?')) {
      await apiClient.instagram.disconnect();
      await fetchAll();
    }
  };

  const handleToggleIgAutoSend = async (val: boolean) => {
    setIgAutoSend(val);
    if (igStatus?.is_connected) {
      await apiClient.instagram.updateSettings({ auto_send: val });
      fetchAll();
    }
  };

  const handleDiscoverInstagram = async () => {
    setDiscoveringIg(true);
    try {
      const res = await apiClient.instagram.discoverFromPage();
      if (res.found) {
        setIgUserId(res.ig_user_id);
        setIgUsername(res.username || '');
        setIsIgModalOpen(true);
      } else {
        alert(res.message || 'No linked Instagram Professional account found on this Facebook Page.');
      }
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Failed to discover linked Instagram account.');
    } finally {
      setDiscoveringIg(false);
    }
  };

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
    setCopiedVerify(true);
    setTimeout(() => setCopiedVerify(false), 2000);
  };

  if (loading) {
    return <div className="p-8 text-center text-slate-400">Loading settings...</div>;
  }

  return (
    <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">
      <div>
        <h1 className="text-2xl font-bold text-slate-900 tracking-tight">Channel & Platform Settings</h1>
        <p className="text-sm text-slate-500 mt-1">
          Manage Facebook Page connection, webhook credentials, brand persona, and messaging policies.
        </p>
      </div>

      {status && (
        <div className="p-4 rounded-xl bg-emerald-50 border border-emerald-200 text-emerald-800 text-sm flex items-center gap-2.5">
          <CheckCircle className="w-5 h-5 text-emerald-600" />
          <span>{status}</span>
        </div>
      )}

      {/* 1. Facebook Page Connection Card */}
      <div className="bg-white border border-slate-200 rounded-2xl p-6 shadow-sm">
        <div className="flex items-center justify-between pb-4 mb-4 border-b border-slate-100">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-blue-600 flex items-center justify-center text-white shadow-md shadow-blue-600/20">
              <Share2 className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-base font-bold text-slate-900">Facebook Page Integration</h2>
              <p className="text-xs text-slate-500">Connect your official Meta Messenger Business Page.</p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <span className={`px-2.5 py-1 rounded-full text-xs font-bold flex items-center gap-1.5 ${
              fbStatus?.is_connected
                ? 'bg-emerald-50 text-emerald-700 border border-emerald-200'
                : 'bg-slate-100 text-slate-500 border border-slate-200'
            }`}>
              <span className={`w-2 h-2 rounded-full ${fbStatus?.is_connected ? 'bg-emerald-500' : 'bg-slate-400'}`} />
              <span>{fbStatus?.is_connected ? 'Connected' : 'Not Connected'}</span>
            </span>

            {fbStatus?.is_connected ? (
              <button
                onClick={handleDisconnectFb}
                className="px-3 py-1.5 text-xs font-semibold text-red-600 hover:bg-red-50 rounded-lg transition-colors border border-red-200"
              >
                Disconnect
              </button>
            ) : null}

            <button
              onClick={() => setIsFbModalOpen(true)}
              className="px-4 py-1.5 text-xs font-bold bg-blue-600 hover:bg-blue-500 text-white rounded-lg shadow-sm transition-all"
            >
              {fbStatus?.is_connected ? 'Reconnect Page' : 'Connect Page'}
            </button>
          </div>
        </div>

        {fbStatus?.is_connected && (
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 p-4 rounded-xl bg-slate-50 border border-slate-200 mb-4 text-xs">
            <div>
              <span className="text-slate-400 font-semibold block">Connected Page Name</span>
              <span className="text-slate-800 font-bold text-sm">{fbStatus.page_name}</span>
            </div>
            <div>
              <span className="text-slate-400 font-semibold block">Page ID</span>
              <span className="text-slate-800 font-mono">{fbStatus.page_id}</span>
            </div>
          </div>
        )}

        {/* AI Reply Mode Switch: Approve-Before-Send vs Auto-Pilot */}
        <div className="mt-4 pt-4 border-t border-slate-100 flex items-center justify-between">
          <div>
            <p className="text-xs font-bold text-slate-800">Messenger AI Dispatch Mode</p>
            <p className="text-[11px] text-slate-500">
              {autoSend
                ? '⚡ Full Auto-pilot: AI replies directly to incoming customer messages without delay.'
                : '🛡️ Approve Before Send (Recommended): AI generates a draft reply. You click Send or edit in Unified Inbox.'}
            </p>
          </div>

          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={() => handleToggleAutoSend(!autoSend)}
              className={`px-3 py-1.5 rounded-lg text-xs font-bold border transition-all ${
                autoSend
                  ? 'bg-amber-100 text-amber-900 border-amber-300'
                  : 'bg-blue-50 text-blue-700 border-blue-300'
              }`}
            >
              {autoSend ? 'Full Auto-pilot' : 'Approve Before Send'}
            </button>
          </div>
        </div>

        {/* Webhook Configuration Helper Details */}
        <div className="mt-5 p-4 rounded-xl bg-slate-900 text-slate-200 text-xs space-y-3">
          <div className="flex items-center justify-between font-bold text-slate-100">
            <span className="flex items-center gap-1.5">
              <Link2 className="w-4 h-4 text-blue-400" />
              Meta App Webhook Setup Details
            </span>
          </div>

          <div className="space-y-2">
            <div>
              <span className="text-slate-400 text-[10px] uppercase font-semibold">Callback URL:</span>
              <div className="flex items-center justify-between bg-slate-950 p-2 rounded border border-slate-800 font-mono text-[11px] text-blue-300">
                <span>https://your-public-domain.com/api/webhooks/meta</span>
              </div>
            </div>

            <div>
              <span className="text-slate-400 text-[10px] uppercase font-semibold">Verify Token:</span>
              <div className="flex items-center justify-between bg-slate-950 p-2 rounded border border-slate-800 font-mono text-[11px] text-emerald-300">
                <span>{fbStatus?.verify_token || 'replybd_meta_verify_token_2026'}</span>
                <button
                  type="button"
                  onClick={() => copyToClipboard(fbStatus?.verify_token || 'replybd_meta_verify_token_2026')}
                  className="p-1 hover:text-white"
                >
                  {copiedVerify ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* 2. Instagram Professional Integration Card */}
      <div className="bg-white border border-slate-200 rounded-2xl p-6 shadow-sm">
        <div className="flex items-center justify-between pb-4 mb-4 border-b border-slate-100 flex-wrap gap-3">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-yellow-500 via-pink-600 to-purple-700 flex items-center justify-center text-white shadow-md shadow-pink-600/20">
              <Instagram className="w-5 h-5" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h2 className="text-base font-bold text-slate-900">Instagram Professional Integration</h2>
                <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-pink-50 text-pink-700 border border-pink-200">
                  Business & Creator
                </span>
              </div>
              <p className="text-xs text-slate-500">Automate Instagram Direct Messages (DMs) and post comments.</p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <span className={`px-2.5 py-1 rounded-full text-xs font-bold flex items-center gap-1.5 ${
              igStatus?.is_connected
                ? 'bg-emerald-50 text-emerald-700 border border-emerald-200'
                : 'bg-slate-100 text-slate-500 border border-slate-200'
            }`}>
              <span className={`w-2 h-2 rounded-full ${igStatus?.is_connected ? 'bg-emerald-500' : 'bg-slate-400'}`} />
              <span>{igStatus?.is_connected ? 'Connected' : 'Not Connected'}</span>
            </span>

            {fbStatus?.is_connected && !igStatus?.is_connected && (
              <button
                onClick={handleDiscoverInstagram}
                disabled={discoveringIg}
                className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold text-purple-700 bg-purple-50 hover:bg-purple-100 border border-purple-200 rounded-lg transition-colors"
                title="Queries your connected Facebook Page for linked Instagram Business account"
              >
                <Compass className="w-3.5 h-3.5" />
                <span>{discoveringIg ? 'Scanning Page...' : 'Auto-Discover from FB'}</span>
              </button>
            )}

            {igStatus?.is_connected ? (
              <button
                onClick={handleDisconnectIg}
                className="px-3 py-1.5 text-xs font-semibold text-red-600 hover:bg-red-50 rounded-lg transition-colors border border-red-200"
              >
                Disconnect
              </button>
            ) : null}

            <button
              onClick={() => setIsIgModalOpen(true)}
              className="px-4 py-1.5 text-xs font-bold bg-gradient-to-r from-purple-600 to-pink-600 hover:from-purple-500 hover:to-pink-500 text-white rounded-lg shadow-sm transition-all"
            >
              {igStatus?.is_connected ? 'Reconnect IG' : 'Connect Instagram'}
            </button>
          </div>
        </div>

        {igStatus?.is_connected && (
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 p-4 rounded-xl bg-slate-50 border border-slate-200 mb-4 text-xs">
            <div>
              <span className="text-slate-400 font-semibold block">Connected Username</span>
              <span className="text-slate-800 font-bold text-sm">@{igStatus.username || 'instagram_user'}</span>
            </div>
            <div>
              <span className="text-slate-400 font-semibold block">Instagram Account ID</span>
              <span className="text-slate-800 font-mono">{igStatus.ig_user_id}</span>
            </div>
          </div>
        )}

        {/* Instagram AI Reply Mode Switch */}
        <div className="mt-4 pt-4 border-t border-slate-100 flex items-center justify-between">
          <div>
            <p className="text-xs font-bold text-slate-800">Instagram DM AI Dispatch Mode</p>
            <p className="text-[11px] text-slate-500">
              {igAutoSend
                ? '⚡ Full Auto-pilot: AI replies directly to incoming Instagram DMs within the 24h window.'
                : '🛡️ Approve Before Send (Recommended): AI generates a draft. You approve or edit before send.'}
            </p>
          </div>

          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={() => handleToggleIgAutoSend(!igAutoSend)}
              className={`px-3 py-1.5 rounded-lg text-xs font-bold border transition-all ${
                igAutoSend
                  ? 'bg-amber-100 text-amber-900 border-amber-300'
                  : 'bg-purple-50 text-purple-700 border-purple-300'
              }`}
            >
              {igAutoSend ? 'Full Auto-pilot' : 'Approve Before Send'}
            </button>
          </div>
        </div>
      </div>

      {/* 3. Store Brand Persona & Delivery Settings */}
      <form onSubmit={handleSubmit} className="space-y-6">
        <div className="bg-white border border-slate-200 rounded-2xl p-6 shadow-sm">
          <div className="flex items-center gap-2 text-sm font-bold text-slate-800 mb-4 pb-2 border-b border-slate-100">
            <Sparkles className="w-4 h-4 text-blue-600" />
            <span>Brand Persona & Tone</span>
          </div>

          <div className="space-y-4">
            <div>
              <label className="block text-xs font-semibold text-slate-600 mb-1">Store / Brand Name</label>
              <input
                type="text"
                required
                value={settings.store_name}
                onChange={(e) => setSettings({ ...settings, store_name: e.target.value })}
                className="w-full px-3.5 py-2.5 border border-slate-300 rounded-xl text-sm focus:outline-none focus:border-blue-500 font-medium"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-600 mb-1">
                System Brand Tone (Instructions to AI)
              </label>
              <textarea
                rows={3}
                required
                value={settings.brand_tone}
                onChange={(e) => setSettings({ ...settings, brand_tone: e.target.value })}
                className="w-full px-3.5 py-2.5 border border-slate-300 rounded-xl text-sm focus:outline-none focus:border-blue-500 font-bangla"
              />
            </div>
          </div>
        </div>

        {/* Delivery Defaults */}
        <div className="bg-white border border-slate-200 rounded-2xl p-6 shadow-sm">
          <div className="flex items-center gap-2 text-sm font-bold text-slate-800 mb-4 pb-2 border-b border-slate-100">
            <Truck className="w-4 h-4 text-blue-600" />
            <span>Default Delivery Charges (BDT ৳)</span>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-semibold text-slate-600 mb-1">Inside Dhaka City (৳)</label>
              <input
                type="number"
                required
                value={settings.delivery_inside_dhaka}
                onChange={(e) => setSettings({ ...settings, delivery_inside_dhaka: e.target.value })}
                className="w-full px-3.5 py-2.5 border border-slate-300 rounded-xl text-sm focus:outline-none focus:border-blue-500 font-medium"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-600 mb-1">Outside Dhaka City (৳)</label>
              <input
                type="number"
                required
                value={settings.delivery_outside_dhaka}
                onChange={(e) => setSettings({ ...settings, delivery_outside_dhaka: e.target.value })}
                className="w-full px-3.5 py-2.5 border border-slate-300 rounded-xl text-sm focus:outline-none focus:border-blue-500 font-medium"
              />
            </div>
          </div>
        </div>

        <div className="flex justify-end">
          <button
            type="submit"
            disabled={saving}
            className="flex items-center gap-2 px-6 py-2.5 bg-blue-600 hover:bg-blue-500 text-white rounded-xl text-sm font-semibold shadow-sm disabled:opacity-50"
          >
            <Save className="w-4 h-4" />
            <span>{saving ? 'Saving...' : 'Save All Settings'}</span>
          </button>
        </div>
      </form>

      {/* Connect Facebook Page Modal */}
      {isFbModalOpen && (
        <div className="fixed inset-0 z-50 bg-slate-900/50 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl max-w-lg w-full p-6 shadow-2xl">
            <h2 className="text-lg font-bold text-slate-900 mb-2">Connect Facebook Page</h2>
            <p className="text-xs text-slate-500 mb-4">
              Enter your Facebook Page ID and Page Access Token. The token will be encrypted using AES/Fernet.
            </p>

            <form onSubmit={handleSaveFacebook} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-slate-600 mb-1">Page Name</label>
                <input
                  type="text"
                  required
                  value={pageName}
                  onChange={(e) => setPageName(e.target.value)}
                  placeholder="e.g. StyleCraft BD Official"
                  className="w-full px-3.5 py-2.5 border border-slate-300 rounded-xl text-sm focus:outline-none focus:border-blue-500"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-600 mb-1">Facebook Page ID</label>
                <input
                  type="text"
                  required
                  value={pageId}
                  onChange={(e) => setPageId(e.target.value)}
                  placeholder="e.g. 102938475610293"
                  className="w-full px-3.5 py-2.5 border border-slate-300 rounded-xl text-sm focus:outline-none focus:border-blue-500 font-mono"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-600 mb-1">
                  Page Access Token (Encrypted on Save)
                </label>
                <input
                  type="password"
                  required
                  value={pageAccessToken}
                  onChange={(e) => setPageAccessToken(e.target.value)}
                  placeholder="EAABwzLixxxx..."
                  className="w-full px-3.5 py-2.5 border border-slate-300 rounded-xl text-sm focus:outline-none focus:border-blue-500 font-mono"
                />
              </div>

              <div className="flex items-center gap-2 pt-2">
                <input
                  type="checkbox"
                  id="modalAutoSend"
                  checked={autoSend}
                  onChange={(e) => setAutoSend(e.target.checked)}
                  className="w-4 h-4 text-blue-600 rounded"
                />
                <label htmlFor="modalAutoSend" className="text-xs text-slate-700 font-medium">
                  Enable Full Auto-Pilot (Default is unchecked: Approve Before Send)
                </label>
              </div>

              <div className="flex justify-end gap-3 pt-4 border-t border-slate-200">
                <button
                  type="button"
                  onClick={() => setIsFbModalOpen(false)}
                  className="px-4 py-2 border border-slate-300 text-slate-700 rounded-xl text-sm font-medium hover:bg-slate-50"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={fbSaving}
                  className="px-5 py-2 bg-blue-600 hover:bg-blue-500 text-white rounded-xl text-sm font-semibold shadow-sm"
                >
                  {fbSaving ? 'Encrypting & Saving...' : 'Save & Connect'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Connect Instagram Professional Modal */}
      {isIgModalOpen && (
        <div className="fixed inset-0 z-50 bg-slate-900/50 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl max-w-lg w-full p-6 shadow-2xl">
            <h2 className="text-lg font-bold text-slate-900 mb-2">Connect Instagram Professional Account</h2>
            <p className="text-xs text-slate-500 mb-4">
              Enter your Instagram Professional (Business or Creator) Account ID and Page/User Access Token. The token is encrypted using AES/Fernet.
            </p>

            <form onSubmit={handleSaveInstagram} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-slate-600 mb-1">Instagram Username</label>
                <input
                  type="text"
                  required
                  value={igUsername}
                  onChange={(e) => setIgUsername(e.target.value)}
                  placeholder="e.g. stylecraft_bd"
                  className="w-full px-3.5 py-2.5 border border-slate-300 rounded-xl text-sm focus:outline-none focus:border-purple-500 font-medium"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-600 mb-1">
                  Instagram Account ID (IG_USER_ID)
                </label>
                <input
                  type="text"
                  required
                  value={igUserId}
                  onChange={(e) => setIgUserId(e.target.value)}
                  placeholder="e.g. 1784140012345678"
                  className="w-full px-3.5 py-2.5 border border-slate-300 rounded-xl text-sm focus:outline-none focus:border-purple-500 font-mono"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-600 mb-1">
                  Access Token (Page Token with IG Scopes or User Token)
                </label>
                <input
                  type="password"
                  required
                  value={igAccessToken}
                  onChange={(e) => setIgAccessToken(e.target.value)}
                  placeholder="EAABwzLixxxx..."
                  className="w-full px-3.5 py-2.5 border border-slate-300 rounded-xl text-sm focus:outline-none focus:border-purple-500 font-mono"
                />
                <p className="text-[10px] text-slate-400 mt-1">
                  You can use the same Facebook Page Access Token if it has <code className="text-slate-600">instagram_manage_messages</code> and <code className="text-slate-600">instagram_manage_comments</code> permissions.
                </p>
              </div>

              <div className="flex items-center gap-2 pt-1">
                <input
                  type="checkbox"
                  id="modalIgAutoSend"
                  checked={igAutoSend}
                  onChange={(e) => setIgAutoSend(e.target.checked)}
                  className="w-4 h-4 text-purple-600 rounded"
                />
                <label htmlFor="modalIgAutoSend" className="text-xs text-slate-700 font-medium">
                  Enable Full Auto-Pilot for Instagram (Default is unchecked: Approve Before Send)
                </label>
              </div>

              <div className="flex justify-end gap-3 pt-4 border-t border-slate-200">
                <button
                  type="button"
                  onClick={() => setIsIgModalOpen(false)}
                  className="px-4 py-2 border border-slate-300 text-slate-700 rounded-xl text-sm font-medium hover:bg-slate-50"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={igSaving}
                  className="px-5 py-2 bg-gradient-to-r from-purple-600 to-pink-600 hover:from-purple-500 hover:to-pink-500 text-white rounded-xl text-sm font-semibold shadow-sm"
                >
                  {igSaving ? 'Encrypting & Saving...' : 'Save & Connect'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
