import React, { useState, useEffect } from 'react';
import { apiClient } from '../api/client';
import { WhatsAppConnectionStatus, WhatsAppTemplate, UsageStats, UsageRates } from '../types';
import { 
  Phone, MessageSquare, Send, CheckCircle2, AlertTriangle, 
  DollarSign, Clock, ShieldAlert, Sparkles, RefreshCw, X, Check, 
  Layers, Plus, ExternalLink, HelpCircle, AlertCircle, Edit3 
} from 'lucide-react';

export const WhatsAppPage: React.FC = () => {
  const [waStatus, setWaStatus] = useState<WhatsAppConnectionStatus | null>(null);
  const [templates, setTemplates] = useState<WhatsAppTemplate[]>([]);
  const [usageStats, setUsageStats] = useState<UsageStats | null>(null);
  const [loading, setLoading] = useState(true);

  // Connect Modal State
  const [isConnectModalOpen, setIsConnectModalOpen] = useState(false);
  const [phoneNumberId, setPhoneNumberId] = useState('');
  const [wabaId, setWabaId] = useState('');
  const [displayPhone, setDisplayPhone] = useState('');
  const [accessToken, setAccessToken] = useState('');
  const [isTestNumber, setIsTestNumber] = useState(true);
  const [autoSend, setAutoSend] = useState(false);
  const [connecting, setConnecting] = useState(false);

  // Template Create Modal State
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
  const [newTplName, setNewTplName] = useState('');
  const [newTplCategory, setNewTplCategory] = useState<'UTILITY' | 'MARKETING' | 'AUTHENTICATION'>('UTILITY');
  const [newTplLanguage, setNewTplLanguage] = useState('bn');
  const [newTplHeader, setNewTplHeader] = useState('');
  const [newTplBody, setNewTplBody] = useState('');
  const [newTplFooter, setNewTplFooter] = useState('');
  const [creatingTpl, setCreatingTpl] = useState(false);

  // Send Template Modal State
  const [selectedTemplate, setSelectedTemplate] = useState<WhatsAppTemplate | null>(null);
  const [sendRecipient, setSendRecipient] = useState('');
  const [param1, setParam1] = useState('');
  const [param2, setParam2] = useState('');
  const [optedIn, setOptedIn] = useState(false);
  const [sendingTpl, setSendingTpl] = useState(false);
  const [sendError, setSendError] = useState<string | null>(null);

  // Pricing Rates Modal State
  const [isRatesModalOpen, setIsRatesModalOpen] = useState(false);
  const [ratesForm, setRatesForm] = useState<UsageRates>({
    rate_marketing: 5.50,
    rate_utility: 1.80,
    rate_service: 0.00,
    rate_authentication: 1.50,
    currency: 'BDT'
  });
  const [savingRates, setSavingRates] = useState(false);

  const fetchAll = async () => {
    try {
      setLoading(true);
      const [statusData, templatesData, statsData, ratesData] = await Promise.all([
        apiClient.whatsapp.getStatus(),
        apiClient.whatsapp.getTemplates(),
        apiClient.whatsapp.getUsageStats(),
        apiClient.whatsapp.getRates(),
      ]);
      setWaStatus(statusData);
      setTemplates(templatesData);
      setUsageStats(statsData);
      setRatesForm(ratesData);
      if (statusData.is_connected) {
        setPhoneNumberId(statusData.phone_number_id || '');
        setWabaId(statusData.waba_id || '');
        setDisplayPhone(statusData.phone_number || '');
        setIsTestNumber(statusData.is_test_number);
        setAutoSend(statusData.auto_send);
      }
    } catch (err) {
      console.error('Failed to load WhatsApp data:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAll();
  }, []);

  const handleConnect = async (e: React.FormEvent) => {
    e.preventDefault();
    setConnecting(true);
    try {
      await apiClient.whatsapp.connect({
        phone_number_id: phoneNumberId.trim(),
        waba_id: wabaId.trim() || undefined,
        phone_number: displayPhone.trim() || undefined,
        access_token: accessToken.trim(),
        is_test_number: isTestNumber,
        auto_send: autoSend,
      });
      setIsConnectModalOpen(false);
      setAccessToken('');
      await fetchAll();
      alert('WhatsApp Cloud API connected successfully!');
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Failed to connect WhatsApp account.');
    } finally {
      setConnecting(false);
    }
  };

  const handleDisconnect = async () => {
    if (confirm('Disconnect your WhatsApp Cloud API account?')) {
      await apiClient.whatsapp.disconnect();
      await fetchAll();
    }
  };

  const handleToggleAutoSend = async (val: boolean) => {
    setAutoSend(val);
    if (waStatus?.is_connected) {
      await apiClient.whatsapp.updateSettings({ auto_send: val });
      fetchAll();
    }
  };

  const handleCreateTemplate = async (e: React.FormEvent) => {
    e.preventDefault();
    setCreatingTpl(true);
    try {
      await apiClient.whatsapp.createTemplate({
        name: newTplName.trim(),
        category: newTplCategory,
        language: newTplLanguage,
        header_text: newTplHeader.trim() || undefined,
        body_text: newTplBody.trim(),
        footer_text: newTplFooter.trim() || undefined,
      });
      setIsCreateModalOpen(false);
      setNewTplName('');
      setNewTplBody('');
      setNewTplHeader('');
      setNewTplFooter('');
      await fetchAll();
      alert('Template created successfully!');
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Failed to create template.');
    } finally {
      setCreatingTpl(false);
    }
  };

  const handleSendTemplate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedTemplate || !sendRecipient.trim() || !optedIn) return;

    setSendingTpl(true);
    setSendError(null);
    try {
      const params = [];
      if (param1.trim()) params.push(param1.trim());
      if (param2.trim()) params.push(param2.trim());

      await apiClient.whatsapp.sendTemplate({
        template_name: selectedTemplate.name,
        recipient_phone: sendRecipient.trim(),
        language_code: selectedTemplate.language,
        body_parameters: params.length > 0 ? params : undefined,
        customer_opted_in: optedIn,
      });

      setSelectedTemplate(null);
      setSendRecipient('');
      setParam1('');
      setParam2('');
      setOptedIn(false);
      await fetchAll();
      alert('Template message dispatched successfully!');
    } catch (err: any) {
      setSendError(err.response?.data?.detail || 'Failed to send template message.');
    } finally {
      setSendingTpl(false);
    }
  };

  const handleSaveRates = async (e: React.FormEvent) => {
    e.preventDefault();
    setSavingRates(true);
    try {
      const updated = await apiClient.whatsapp.updateRates(ratesForm);
      setRatesForm(updated);
      setIsRatesModalOpen(false);
      await fetchAll();
      alert('Pricing rates updated successfully!');
    } catch (err: any) {
      alert('Failed to update rates.');
    } finally {
      setSavingRates(false);
    }
  };

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">
      {/* Top Banner */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 border-b border-slate-200 pb-5">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-2xl font-bold text-slate-900">WhatsApp Cloud API & Cost Hub</h1>
            <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-100 text-emerald-800">
              Phase 5
            </span>
          </div>
          <p className="text-sm text-slate-500 mt-1">
            Meta WhatsApp Cloud API integration, Customer Service Window policy, message template automation, and dynamic cost monitoring.
          </p>
        </div>

        <button
          onClick={fetchAll}
          className="flex items-center gap-1.5 px-3 py-2 rounded-xl border border-slate-300 hover:bg-slate-50 text-slate-700 text-sm font-medium transition-colors"
        >
          <RefreshCw className="w-4 h-4" />
          <span>Refresh</span>
        </button>
      </div>

      {/* 1. Connection Card with Test Number & Real Number Warnings */}
      <div className="bg-white border border-slate-200 rounded-2xl p-6 shadow-sm">
        <div className="flex items-center justify-between pb-4 mb-4 border-b border-slate-100 flex-wrap gap-3">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-emerald-600 flex items-center justify-center text-white shadow-md shadow-emerald-600/20">
              <Phone className="w-5 h-5" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h2 className="text-base font-bold text-slate-900">WhatsApp Cloud API Connection</h2>
                {waStatus?.is_connected && (
                  <span className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider ${
                    waStatus.is_test_number
                      ? 'bg-amber-100 text-amber-900 border border-amber-200'
                      : 'bg-emerald-100 text-emerald-900 border border-emerald-200'
                  }`}>
                    {waStatus.is_test_number ? 'Meta Test Number' : 'Live Real Number'}
                  </span>
                )}
              </div>
              <p className="text-xs text-slate-500">Official Cloud-hosted WhatsApp Business API from Meta.</p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <span className={`px-2.5 py-1 rounded-full text-xs font-bold flex items-center gap-1.5 ${
              waStatus?.is_connected
                ? 'bg-emerald-50 text-emerald-700 border border-emerald-200'
                : 'bg-slate-100 text-slate-500 border border-slate-200'
            }`}>
              <span className={`w-2 h-2 rounded-full ${waStatus?.is_connected ? 'bg-emerald-500' : 'bg-slate-400'}`} />
              <span>{waStatus?.is_connected ? 'Connected' : 'Not Connected'}</span>
            </span>

            {waStatus?.is_connected && (
              <button
                onClick={handleDisconnect}
                className="px-3 py-1.5 text-xs font-semibold text-red-600 hover:bg-red-50 rounded-lg transition-colors border border-red-200"
              >
                Disconnect
              </button>
            )}

            <button
              onClick={() => setIsConnectModalOpen(true)}
              className="px-4 py-1.5 text-xs font-bold bg-emerald-600 hover:bg-emerald-500 text-white rounded-lg shadow-sm transition-all"
            >
              {waStatus?.is_connected ? 'Reconnect WhatsApp' : 'Connect WhatsApp'}
            </button>
          </div>
        </div>

        {waStatus?.is_connected && (
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 p-4 rounded-xl bg-slate-50 border border-slate-200 mb-4 text-xs">
            <div>
              <span className="text-slate-400 font-semibold block">Phone Number ID</span>
              <span className="text-slate-800 font-mono font-bold">{waStatus.phone_number_id}</span>
            </div>
            <div>
              <span className="text-slate-400 font-semibold block">Display Number</span>
              <span className="text-slate-800 font-medium">{waStatus.phone_number || '+1 555-0199 (Test)'}</span>
            </div>
            <div>
              <span className="text-slate-400 font-semibold block">WABA ID</span>
              <span className="text-slate-800 font-mono">{waStatus.waba_id || 'Not specified'}</span>
            </div>
          </div>
        )}

        {/* AI Dispatch Mode Toggle */}
        <div className="pt-2 flex items-center justify-between border-t border-slate-100">
          <div>
            <p className="text-xs font-bold text-slate-800">WhatsApp AI Dispatch Mode</p>
            <p className="text-[11px] text-slate-500">
              {autoSend
                ? '⚡ Full Auto-pilot: AI replies directly within the 24h Customer Service Window.'
                : '🛡️ Approve Before Send: AI generates a draft. You inspect and click Send.'}
            </p>
          </div>

          <button
            type="button"
            onClick={() => handleToggleAutoSend(!autoSend)}
            className={`px-3 py-1.5 rounded-lg text-xs font-bold border transition-all ${
              autoSend
                ? 'bg-amber-100 text-amber-900 border-amber-300'
                : 'bg-emerald-50 text-emerald-800 border-emerald-300'
            }`}
          >
            {autoSend ? 'Full Auto-pilot' : 'Approve Before Send'}
          </button>
        </div>

        {/* Real Phone Number Migration Guide & Warnings Box */}
        <div className="mt-4 p-4 rounded-xl bg-amber-50/70 border border-amber-200 text-xs text-amber-900 space-y-2">
          <div className="flex items-center gap-1.5 font-bold text-amber-950">
            <AlertTriangle className="w-4 h-4 text-amber-600 shrink-0" />
            <span>Migrating from Test Number to Real Business Phone Number (Official Meta Requirements):</span>
          </div>
          <ul className="list-disc pl-5 space-y-1 text-slate-700">
            <li>
              <strong>Number Must Be Cleaned:</strong> The phone number must NOT be currently active on the consumer WhatsApp or WhatsApp Business mobile app. You must delete the account from your phone app first (<code className="text-slate-900 font-mono">Settings &gt; Account &gt; Delete My Account</code>).
            </li>
            <li>
              <strong>Business Verification & Tier Limits:</strong> Real numbers initially have a limit of 250 business-initiated conversations/day. Complete Meta Business Verification to unlock Tier 1 (1,000/day) and beyond.
            </li>
            <li>
              <strong>Display Name Review:</strong> Meta reviews your business display name against strict brand name guidelines before granting standard/green tick verification.
            </li>
            <li>
              <strong>Payment Method Attached:</strong> Meta requires a credit card or valid payment method attached to your WABA in Meta Business Manager to cover template and marketing fees.
            </li>
          </ul>
        </div>
      </div>

      {/* 2. Cost Awareness & Usage Statistics Strip */}
      <div className="bg-white border border-slate-200 rounded-2xl p-6 shadow-sm space-y-4">
        <div className="flex items-center justify-between pb-3 border-b border-slate-100 flex-wrap gap-2">
          <div>
            <h2 className="text-base font-bold text-slate-900 flex items-center gap-2">
              <DollarSign className="w-5 h-5 text-emerald-600" />
              <span>Cost Awareness & Usage Dashboard</span>
            </h2>
            <p className="text-xs text-slate-500">
              Estimated usage costs based on your dynamic regional pricing settings for {usageStats?.period || 'this month'}.
            </p>
          </div>

          <button
            onClick={() => setIsRatesModalOpen(true)}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-slate-300 hover:bg-slate-50 text-xs font-semibold text-slate-700 transition-colors"
          >
            <Edit3 className="w-3.5 h-3.5" />
            <span>Edit Pricing Rates</span>
          </button>
        </div>

        {/* Usage Counters */}
        <div className="grid grid-cols-2 sm:grid-cols-5 gap-3">
          <div className="p-3.5 rounded-xl border border-slate-200 bg-slate-50">
            <span className="text-xs text-slate-500 font-medium block">Total Messages</span>
            <span className="text-xl font-bold text-slate-900 mt-1 block">{usageStats?.total_messages || 0}</span>
            <span className="text-[10px] text-slate-400 mt-0.5 block">Current Month</span>
          </div>

          <div className="p-3.5 rounded-xl border border-blue-200 bg-blue-50/50">
            <span className="text-xs text-blue-700 font-semibold block">Service (Customer Care)</span>
            <span className="text-xl font-bold text-slate-900 mt-1 block">{usageStats?.service_count || 0}</span>
            <span className="text-[10px] text-blue-600 mt-0.5 block">
              @ {usageStats?.rates.service || 0} {usageStats?.currency}
            </span>
          </div>

          <div className="p-3.5 rounded-xl border border-emerald-200 bg-emerald-50/50">
            <span className="text-xs text-emerald-700 font-semibold block">Utility (Order Updates)</span>
            <span className="text-xl font-bold text-slate-900 mt-1 block">{usageStats?.utility_count || 0}</span>
            <span className="text-[10px] text-emerald-600 mt-0.5 block">
              @ {usageStats?.rates.utility || 0} {usageStats?.currency}
            </span>
          </div>

          <div className="p-3.5 rounded-xl border border-purple-200 bg-purple-50/50">
            <span className="text-xs text-purple-700 font-semibold block">Marketing (Promotions)</span>
            <span className="text-xl font-bold text-slate-900 mt-1 block">{usageStats?.marketing_count || 0}</span>
            <span className="text-[10px] text-purple-600 mt-0.5 block">
              @ {usageStats?.rates.marketing || 0} {usageStats?.currency}
            </span>
          </div>

          <div className="p-3.5 rounded-xl border border-amber-200 bg-amber-50/50">
            <span className="text-xs text-amber-800 font-semibold block">Est. Total Bill</span>
            <span className="text-xl font-bold text-emerald-700 mt-1 block">
              {usageStats?.estimated_cost || 0} {usageStats?.currency}
            </span>
            <span className="text-[10px] text-amber-700 mt-0.5 block">Dynamic Rates Applied</span>
          </div>
        </div>
      </div>

      {/* 3. Customer Service Window Policy & Template Manager */}
      <div className="bg-white border border-slate-200 rounded-2xl p-6 shadow-sm space-y-4">
        <div className="flex items-center justify-between pb-3 border-b border-slate-100 flex-wrap gap-2">
          <div>
            <div className="flex items-center gap-2">
              <h2 className="text-base font-bold text-slate-900 flex items-center gap-2">
                <Clock className="w-5 h-5 text-blue-600" />
                <span>Customer Service Window & Message Templates</span>
              </h2>
              <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-blue-100 text-blue-800">
                24h Window Guard
              </span>
            </div>
            <p className="text-xs text-slate-500 mt-0.5">
              Inside the 24h window: free-form replies are allowed. Outside 24h: only approved WhatsApp templates can be sent.
            </p>
          </div>

          <button
            onClick={() => setIsCreateModalOpen(true)}
            className="flex items-center gap-1.5 px-4 py-2 bg-slate-900 hover:bg-slate-800 text-white rounded-xl text-xs font-semibold shadow-sm transition-colors"
          >
            <Plus className="w-4 h-4" />
            <span>Create Template</span>
          </button>
        </div>

        {/* Templates Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 pt-2">
          {templates.map((tpl) => (
            <div key={tpl.id} className="p-4 rounded-xl border border-slate-200 bg-slate-50/60 flex flex-col justify-between space-y-3">
              <div>
                <div className="flex items-center justify-between">
                  <span className="font-mono font-bold text-xs text-slate-900 truncate max-w-[170px]">
                    {tpl.name}
                  </span>
                  <span className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase ${
                    tpl.category === 'MARKETING'
                      ? 'bg-purple-100 text-purple-800'
                      : tpl.category === 'UTILITY'
                      ? 'bg-emerald-100 text-emerald-800'
                      : 'bg-blue-100 text-blue-800'
                  }`}>
                    {tpl.category}
                  </span>
                </div>

                {tpl.header_text && (
                  <p className="text-[11px] font-bold text-slate-700 mt-2">{tpl.header_text}</p>
                )}
                <p className="text-xs text-slate-800 mt-1 font-bangla whitespace-pre-wrap bg-white p-2.5 rounded-lg border border-slate-200">
                  {tpl.body_text}
                </p>
                {tpl.footer_text && (
                  <p className="text-[10px] text-slate-400 mt-1 italic">{tpl.footer_text}</p>
                )}
              </div>

              <div className="pt-2 border-t border-slate-200 flex items-center justify-between">
                <span className="text-[11px] text-slate-500 font-medium">Lang: {tpl.language}</span>
                <button
                  onClick={() => {
                    setSelectedTemplate(tpl);
                    setSendRecipient('');
                    setParam1('');
                    setParam2('');
                    setOptedIn(false);
                    setSendError(null);
                  }}
                  className="flex items-center gap-1 px-3 py-1.5 bg-emerald-600 hover:bg-emerald-500 text-white rounded-lg text-xs font-semibold shadow-sm transition-colors"
                >
                  <Send className="w-3 h-3" />
                  <span>Send Template</span>
                </button>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Connect Modal */}
      {isConnectModalOpen && (
        <div className="fixed inset-0 z-50 bg-slate-900/50 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl max-w-lg w-full p-6 shadow-2xl border border-slate-200">
            <h3 className="text-base font-bold text-slate-900 mb-1">Connect WhatsApp Cloud API</h3>
            <p className="text-xs text-slate-500 mb-4">
              Enter your WhatsApp Phone Number ID and Access Token from the Meta Developer Dashboard.
            </p>

            <form onSubmit={handleConnect} className="space-y-4 text-xs">
              <div>
                <label className="block font-semibold text-slate-700 mb-1">WhatsApp Phone Number ID</label>
                <input
                  type="text"
                  required
                  value={phoneNumberId}
                  onChange={(e) => setPhoneNumberId(e.target.value)}
                  placeholder="e.g. 109283746501928"
                  className="w-full px-3 py-2 border border-slate-300 rounded-xl font-mono focus:outline-none focus:ring-2 focus:ring-emerald-600"
                />
              </div>

              <div>
                <label className="block font-semibold text-slate-700 mb-1">WhatsApp Business Account ID (WABA ID)</label>
                <input
                  type="text"
                  value={wabaId}
                  onChange={(e) => setWabaId(e.target.value)}
                  placeholder="e.g. 293847561029384"
                  className="w-full px-3 py-2 border border-slate-300 rounded-xl font-mono focus:outline-none focus:ring-2 focus:ring-emerald-600"
                />
              </div>

              <div>
                <label className="block font-semibold text-slate-700 mb-1">Display Phone Number (Optional)</label>
                <input
                  type="text"
                  value={displayPhone}
                  onChange={(e) => setDisplayPhone(e.target.value)}
                  placeholder="e.g. +8801711000000 or +1 555-0199"
                  className="w-full px-3 py-2 border border-slate-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-emerald-600"
                />
              </div>

              <div>
                <label className="block font-semibold text-slate-700 mb-1">Permanent Access Token (Encrypted on Save)</label>
                <input
                  type="password"
                  required
                  value={accessToken}
                  onChange={(e) => setAccessToken(e.target.value)}
                  placeholder="EAABwzLixxxx..."
                  className="w-full px-3 py-2 border border-slate-300 rounded-xl font-mono focus:outline-none focus:ring-2 focus:ring-emerald-600"
                />
              </div>

              <div className="space-y-2 pt-1">
                <label className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={isTestNumber}
                    onChange={(e) => setIsTestNumber(e.target.checked)}
                    className="w-4 h-4 text-emerald-600 rounded"
                  />
                  <span className="font-semibold text-slate-800">This is Meta's Test Phone Number (Sandbox mode)</span>
                </label>

                <label className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={autoSend}
                    onChange={(e) => setAutoSend(e.target.checked)}
                    className="w-4 h-4 text-emerald-600 rounded"
                  />
                  <span className="font-semibold text-slate-800">Enable Full Auto-Pilot (Default: Approve Before Send)</span>
                </label>
              </div>

              <div className="flex justify-end gap-2 pt-3 border-t border-slate-200">
                <button
                  type="button"
                  onClick={() => setIsConnectModalOpen(false)}
                  className="px-4 py-2 border border-slate-300 rounded-xl font-semibold text-slate-700 hover:bg-slate-50"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={connecting}
                  className="px-5 py-2 bg-emerald-600 hover:bg-emerald-500 text-white rounded-xl font-semibold shadow-sm"
                >
                  {connecting ? 'Encrypting & Connecting...' : 'Connect WhatsApp'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Create Template Modal */}
      {isCreateModalOpen && (
        <div className="fixed inset-0 z-50 bg-slate-900/50 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl max-w-lg w-full p-6 shadow-2xl border border-slate-200">
            <h3 className="text-base font-bold text-slate-900 mb-1">Create WhatsApp Message Template</h3>
            <p className="text-xs text-slate-500 mb-4">
              Create a template for customer notifications. Use <code className="text-slate-800 font-mono">{"{{1}}"}</code>, <code className="text-slate-800 font-mono">{"{{2}}"}</code> for variables.
            </p>

            <form onSubmit={handleCreateTemplate} className="space-y-4 text-xs">
              <div>
                <label className="block font-semibold text-slate-700 mb-1">Template Name</label>
                <input
                  type="text"
                  required
                  value={newTplName}
                  onChange={(e) => setNewTplName(e.target.value)}
                  placeholder="e.g. order_shipped_bd"
                  className="w-full px-3 py-2 border border-slate-300 rounded-xl font-mono focus:outline-none focus:ring-2 focus:ring-emerald-600"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block font-semibold text-slate-700 mb-1">Category</label>
                  <select
                    value={newTplCategory}
                    onChange={(e) => setNewTplCategory(e.target.value as any)}
                    className="w-full px-3 py-2 border border-slate-300 rounded-xl font-semibold focus:outline-none focus:ring-2 focus:ring-emerald-600"
                  >
                    <option value="UTILITY">UTILITY (Order / Status)</option>
                    <option value="MARKETING">MARKETING (Offers / Re-engagement)</option>
                    <option value="AUTHENTICATION">AUTHENTICATION (OTP)</option>
                  </select>
                </div>

                <div>
                  <label className="block font-semibold text-slate-700 mb-1">Language</label>
                  <select
                    value={newTplLanguage}
                    onChange={(e) => setNewTplLanguage(e.target.value)}
                    className="w-full px-3 py-2 border border-slate-300 rounded-xl font-semibold focus:outline-none focus:ring-2 focus:ring-emerald-600"
                  >
                    <option value="bn">Bangla (bn)</option>
                    <option value="en_US">English (en_US)</option>
                  </select>
                </div>
              </div>

              <div>
                <label className="block font-semibold text-slate-700 mb-1">Header Text (Optional)</label>
                <input
                  type="text"
                  value={newTplHeader}
                  onChange={(e) => setNewTplHeader(e.target.value)}
                  placeholder="e.g. অর্ডার ডেলিভারি আপডেট"
                  className="w-full px-3 py-2 border border-slate-300 rounded-xl font-bangla focus:outline-none focus:ring-2 focus:ring-emerald-600"
                />
              </div>

              <div>
                <label className="block font-semibold text-slate-700 mb-1">Body Text</label>
                <textarea
                  rows={3}
                  required
                  value={newTplBody}
                  onChange={(e) => setNewTplBody(e.target.value)}
                  placeholder="হ্যালো {{1}}, আপনার অর্ডার #{{2}} সফলভাবে ডেলিভারি এজেন্টের কাছে হস্তান্তর করা হয়েছে।"
                  className="w-full px-3 py-2 border border-slate-300 rounded-xl font-bangla focus:outline-none focus:ring-2 focus:ring-emerald-600"
                />
              </div>

              <div>
                <label className="block font-semibold text-slate-700 mb-1">Footer Text (Optional)</label>
                <input
                  type="text"
                  value={newTplFooter}
                  onChange={(e) => setNewTplFooter(e.target.value)}
                  placeholder="e.g. StyleCraft BD Support"
                  className="w-full px-3 py-2 border border-slate-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-emerald-600"
                />
              </div>

              <div className="flex justify-end gap-2 pt-3 border-t border-slate-200">
                <button
                  type="button"
                  onClick={() => setIsCreateModalOpen(false)}
                  className="px-4 py-2 border border-slate-300 rounded-xl font-semibold text-slate-700 hover:bg-slate-50"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={creatingTpl}
                  className="px-5 py-2 bg-emerald-600 hover:bg-emerald-500 text-white rounded-xl font-semibold shadow-sm"
                >
                  {creatingTpl ? 'Creating...' : 'Save Template'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Send Template Modal */}
      {selectedTemplate && (
        <div className="fixed inset-0 z-50 bg-slate-900/50 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl max-w-lg w-full p-6 shadow-2xl border border-slate-200">
            <h3 className="text-base font-bold text-slate-900 mb-1">Send Template: {selectedTemplate.name}</h3>
            <p className="text-xs text-slate-500 mb-3">
              Templates can be sent outside the 24h window to opted-in customers.
            </p>

            {sendError && (
              <div className="mb-3 p-3 rounded-xl bg-rose-50 border border-rose-200 text-rose-800 text-xs flex items-center gap-2">
                <AlertTriangle className="w-4 h-4 text-rose-600 shrink-0" />
                <span>{sendError}</span>
              </div>
            )}

            <form onSubmit={handleSendTemplate} className="space-y-4 text-xs">
              <div>
                <label className="block font-semibold text-slate-700 mb-1">Recipient Phone Number (with Country Code)</label>
                <input
                  type="text"
                  required
                  value={sendRecipient}
                  onChange={(e) => setSendRecipient(e.target.value)}
                  placeholder="e.g. 8801711223344"
                  className="w-full px-3 py-2 border border-slate-300 rounded-xl font-mono focus:outline-none focus:ring-2 focus:ring-emerald-600"
                />
              </div>

              <div>
                <label className="block font-semibold text-slate-700 mb-1">Variable {"{{1}}"} (e.g. Customer Name)</label>
                <input
                  type="text"
                  value={param1}
                  onChange={(e) => setParam1(e.target.value)}
                  placeholder="e.g. Tanveer"
                  className="w-full px-3 py-2 border border-slate-300 rounded-xl font-bangla focus:outline-none focus:ring-2 focus:ring-emerald-600"
                />
              </div>

              <div>
                <label className="block font-semibold text-slate-700 mb-1">Variable {"{{2}}"} (e.g. Order ID / Details)</label>
                <input
                  type="text"
                  value={param2}
                  onChange={(e) => setParam2(e.target.value)}
                  placeholder="e.g. 1024"
                  className="w-full px-3 py-2 border border-slate-300 rounded-xl font-mono focus:outline-none focus:ring-2 focus:ring-emerald-600"
                />
              </div>

              <div className="p-3 bg-emerald-50 rounded-xl border border-emerald-200">
                <label className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="checkbox"
                    required
                    checked={optedIn}
                    onChange={(e) => setOptedIn(e.target.checked)}
                    className="w-4 h-4 text-emerald-600 rounded"
                  />
                  <span className="font-bold text-emerald-950">
                    I confirm this customer has opted in to receive WhatsApp notifications from our business.
                  </span>
                </label>
              </div>

              <div className="flex justify-end gap-2 pt-3 border-t border-slate-200">
                <button
                  type="button"
                  onClick={() => setSelectedTemplate(null)}
                  className="px-4 py-2 border border-slate-300 rounded-xl font-semibold text-slate-700 hover:bg-slate-50"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={sendingTpl || !optedIn}
                  className="px-5 py-2 bg-emerald-600 hover:bg-emerald-500 text-white rounded-xl font-semibold shadow-sm disabled:opacity-50"
                >
                  {sendingTpl ? 'Dispatching...' : 'Send Template'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Dynamic Rates Modal */}
      {isRatesModalOpen && (
        <div className="fixed inset-0 z-50 bg-slate-900/50 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl max-w-lg w-full p-6 shadow-2xl border border-slate-200">
            <h3 className="text-base font-bold text-slate-900 mb-1">Configure WhatsApp Dynamic Rates</h3>
            <p className="text-xs text-slate-500 mb-4">
              Fill in current conversation rates from Meta's official pricing page. No prices are hard-coded.
            </p>

            <form onSubmit={handleSaveRates} className="space-y-4 text-xs">
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block font-semibold text-slate-700 mb-1">Marketing Rate</label>
                  <input
                    type="number"
                    step="0.01"
                    required
                    value={ratesForm.rate_marketing}
                    onChange={(e) => setRatesForm({ ...ratesForm, rate_marketing: parseFloat(e.target.value) || 0 })}
                    className="w-full px-3 py-2 border border-slate-300 rounded-xl font-mono"
                  />
                </div>

                <div>
                  <label className="block font-semibold text-slate-700 mb-1">Utility Rate</label>
                  <input
                    type="number"
                    step="0.01"
                    required
                    value={ratesForm.rate_utility}
                    onChange={(e) => setRatesForm({ ...ratesForm, rate_utility: parseFloat(e.target.value) || 0 })}
                    className="w-full px-3 py-2 border border-slate-300 rounded-xl font-mono"
                  />
                </div>

                <div>
                  <label className="block font-semibold text-slate-700 mb-1">Service (Support) Rate</label>
                  <input
                    type="number"
                    step="0.01"
                    required
                    value={ratesForm.rate_service}
                    onChange={(e) => setRatesForm({ ...ratesForm, rate_service: parseFloat(e.target.value) || 0 })}
                    className="w-full px-3 py-2 border border-slate-300 rounded-xl font-mono"
                  />
                </div>

                <div>
                  <label className="block font-semibold text-slate-700 mb-1">Currency Code</label>
                  <input
                    type="text"
                    required
                    value={ratesForm.currency}
                    onChange={(e) => setRatesForm({ ...ratesForm, currency: e.target.value.toUpperCase() })}
                    placeholder="BDT, USD"
                    className="w-full px-3 py-2 border border-slate-300 rounded-xl font-mono uppercase"
                  />
                </div>
              </div>

              <div className="flex justify-end gap-2 pt-3 border-t border-slate-200">
                <button
                  type="button"
                  onClick={() => setIsRatesModalOpen(false)}
                  className="px-4 py-2 border border-slate-300 rounded-xl font-semibold text-slate-700 hover:bg-slate-50"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={savingRates}
                  className="px-5 py-2 bg-emerald-600 hover:bg-emerald-500 text-white rounded-xl font-semibold shadow-sm"
                >
                  {savingRates ? 'Saving...' : 'Save Rates'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
