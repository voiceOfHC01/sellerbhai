import React, { useState, useEffect } from 'react';
import { apiClient } from '../api/client';
import { WhatsAppTemplate, BroadcastAudience, BroadcastCampaign } from '../types';
import { 
  Send, AlertTriangle, ShieldAlert, DollarSign, Users, 
  CheckCircle2, Clock, RefreshCw, Layers, HelpCircle, AlertCircle, X
} from 'lucide-react';

export const BroadcastPage: React.FC = () => {
  const [audience, setAudience] = useState<BroadcastAudience | null>(null);
  const [templates, setTemplates] = useState<WhatsAppTemplate[]>([]);
  const [campaigns, setCampaigns] = useState<BroadcastCampaign[]>([]);
  const [loading, setLoading] = useState(true);

  // Form State
  const [selectedTemplateId, setSelectedTemplateId] = useState<number | undefined>(undefined);
  const [param1, setParam1] = useState('');
  const [param2, setParam2] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isConfirmOpen, setIsConfirmOpen] = useState(false);

  const fetchAll = async () => {
    try {
      setLoading(true);
      const [audienceData, templatesData, campaignsData] = await Promise.all([
        apiClient.broadcasts.getAudience(),
        apiClient.whatsapp.getTemplates(),
        apiClient.broadcasts.listBroadcasts(),
      ]);
      setAudience(audienceData);
      // Filter strictly approved templates
      const approved = templatesData.filter((t) => t.status === 'APPROVED');
      setTemplates(approved);
      if (approved.length > 0 && !selectedTemplateId) {
        setSelectedTemplateId(approved[0].id);
      }
      setCampaigns(campaignsData);
    } catch (err) {
      console.error('Failed to load broadcast data:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAll();
  }, []);

  const selectedTemplate = templates.find((t) => t.id === selectedTemplateId);
  const recipientCount = audience?.opted_in_count || 0;
  const category = selectedTemplate?.category.toLowerCase() || 'marketing';
  const ratePerMsg = audience?.rates[category] || (category === 'marketing' ? 5.50 : 1.80);
  const estimatedCost = Number((recipientCount * ratePerMsg).toFixed(2));
  const currency = audience?.currency || 'BDT';

  const handleLaunchBroadcast = async () => {
    if (!selectedTemplateId) return;
    setIsSubmitting(true);
    try {
      const params = [];
      if (param1.trim()) params.push(param1.trim());
      if (param2.trim()) params.push(param2.trim());

      await apiClient.broadcasts.triggerBroadcast({
        template_id: selectedTemplateId,
        body_parameters: params.length > 0 ? params : undefined,
        recipient_filter: 'all_opted_in',
      });

      setIsConfirmOpen(false);
      setParam1('');
      setParam2('');
      await fetchAll();
      alert('WhatsApp Template Broadcast dispatched successfully to opted-in customers!');
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Failed to trigger broadcast.');
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
            <h1 className="text-2xl font-bold text-slate-900">WhatsApp Opt-in Template Broadcast</h1>
            <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-100 text-emerald-800">
              Direct 1-to-1 Notifications
            </span>
          </div>
          <p className="text-sm text-slate-500 mt-1">
            Send bulk approved utility or marketing template notifications strictly to opted-in WhatsApp customers.
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

      {/* 1. EXPLICIT WHATSAPP ARCHITECTURAL & COST WARNING BANNER */}
      <div className="p-5 rounded-2xl bg-amber-500/10 border-2 border-amber-500/30 shadow-sm space-y-3">
        <div className="flex items-center gap-2.5 text-amber-950 font-bold text-sm">
          <ShieldAlert className="w-5 h-5 text-amber-600 shrink-0" />
          <span>IMPORTANT: WhatsApp is NOT a Social Posting Feed or Public Timeline</span>
        </div>
        <p className="text-xs text-amber-900 leading-relaxed">
          Unlike Facebook Pages and Instagram, Meta does not provide a public feed or wall for WhatsApp Business API accounts. 
          Broadcasts here send individual, direct 1-to-1 messages via pre-approved WhatsApp Templates to customers who explicitly opted in.
        </p>
        <div className="p-3 rounded-xl bg-white/80 border border-amber-300 text-xs text-slate-800 flex items-center justify-between flex-wrap gap-2">
          <div className="flex items-center gap-2">
            <DollarSign className="w-4 h-4 text-emerald-600 shrink-0" />
            <span>
              <strong>Meta Pricing Model:</strong> Every delivered template message is billed to your Meta Business Account by category.
            </span>
          </div>
          <div className="text-[11px] font-mono text-slate-600">
            Current Rates: Marketing @ {audience?.rates.marketing || 5.50} {currency} | Utility @ {audience?.rates.utility || 1.80} {currency}
          </div>
        </div>
      </div>

      {/* 2. Broadcast Composer & Live Cost Estimator */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
        {/* Left: Broadcast Form */}
        <div className="lg:col-span-7 bg-white border border-slate-200 rounded-2xl p-6 shadow-sm space-y-5">
          <div className="flex items-center justify-between border-b border-slate-100 pb-3">
            <h2 className="text-base font-bold text-slate-900 flex items-center gap-2">
              <Send className="w-4 h-4 text-emerald-600" />
              <span>Compose Opt-in Broadcast</span>
            </h2>
            <span className="text-xs font-semibold text-emerald-700 bg-emerald-50 px-2.5 py-0.5 rounded-full">
              Only Approved Templates
            </span>
          </div>

          {/* Select Template */}
          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-1">
              Select Approved WhatsApp Template
            </label>
            {templates.length === 0 ? (
              <div className="p-3 rounded-xl bg-slate-50 border border-slate-200 text-xs text-slate-500">
                No approved templates found. Go to the WhatsApp page to create and approve templates.
              </div>
            ) : (
              <select
                value={selectedTemplateId || ''}
                onChange={(e) => setSelectedTemplateId(Number(e.target.value))}
                className="w-full text-xs rounded-xl border-slate-300 shadow-sm focus:border-emerald-500 focus:ring-emerald-500 p-2.5 bg-slate-50/50"
              >
                {templates.map((tpl) => (
                  <option key={tpl.id} value={tpl.id}>
                    {tpl.name} ({tpl.category} - {tpl.language})
                  </option>
                ))}
              </select>
            )}
          </div>

          {/* Template Body Preview */}
          {selectedTemplate && (
            <div className="p-4 rounded-xl border border-slate-200 bg-slate-50/70 space-y-2">
              <div className="flex items-center justify-between text-xs">
                <span className="font-bold text-slate-700">Template Preview</span>
                <span className="px-2 py-0.5 rounded text-[10px] font-bold uppercase bg-blue-100 text-blue-800">
                  {selectedTemplate.category}
                </span>
              </div>
              {selectedTemplate.header_text && (
                <div className="text-xs font-bold text-slate-900">{selectedTemplate.header_text}</div>
              )}
              <div className="text-xs text-slate-700 whitespace-pre-line leading-relaxed font-sans">
                {selectedTemplate.body_text}
              </div>
              {selectedTemplate.footer_text && (
                <div className="text-[11px] text-slate-400">{selectedTemplate.footer_text}</div>
              )}
            </div>
          )}

          {/* Parameters Inputs */}
          <div className="space-y-3">
            <label className="block text-xs font-semibold text-slate-700">
              Template Body Variables (Optional)
            </label>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <span className="text-[11px] text-slate-500 block mb-1">Variable {'{{1}}'}</span>
                <input
                  type="text"
                  value={param1}
                  onChange={(e) => setParam1(e.target.value)}
                  placeholder="e.g. Customer Name or Product"
                  className="w-full text-xs rounded-xl border-slate-300 shadow-sm focus:border-emerald-500 focus:ring-emerald-500 p-2.5"
                />
              </div>
              <div>
                <span className="text-[11px] text-slate-500 block mb-1">Variable {'{{2}}'}</span>
                <input
                  type="text"
                  value={param2}
                  onChange={(e) => setParam2(e.target.value)}
                  placeholder="e.g. 15% OFF or Order #1002"
                  className="w-full text-xs rounded-xl border-slate-300 shadow-sm focus:border-emerald-500 focus:ring-emerald-500 p-2.5"
                />
              </div>
            </div>
          </div>

          {/* Target Audience */}
          <div className="p-4 rounded-xl border border-slate-200 bg-slate-50 flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="w-9 h-9 rounded-xl bg-blue-100 text-blue-700 flex items-center justify-center font-bold">
                <Users className="w-5 h-5" />
              </div>
              <div>
                <div className="text-xs font-bold text-slate-900">Audience: All Opted-in WhatsApp Contacts</div>
                <div className="text-[11px] text-slate-500">Customers who opted in and have valid phone numbers</div>
              </div>
            </div>
            <span className="text-base font-bold text-slate-900">{recipientCount} Contacts</span>
          </div>

          <div className="flex justify-end pt-2">
            <button
              type="button"
              onClick={() => setIsConfirmOpen(true)}
              disabled={templates.length === 0 || recipientCount === 0}
              className="flex items-center gap-2 px-6 py-2.5 rounded-xl bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-bold shadow-md shadow-emerald-600/20 transition-all disabled:opacity-50"
            >
              <Send className="w-4 h-4" />
              <span>Review & Launch Broadcast</span>
            </button>
          </div>
        </div>

        {/* Right: Live Dynamic Cost Summary Card */}
        <div className="lg:col-span-5 space-y-6">
          <div className="bg-white border border-slate-200 rounded-2xl p-6 shadow-sm space-y-5">
            <div className="flex items-center justify-between border-b border-slate-100 pb-3">
              <h2 className="text-base font-bold text-slate-900 flex items-center gap-2">
                <DollarSign className="w-5 h-5 text-emerald-600" />
                <span>Live Cost Calculator</span>
              </h2>
              <span className="text-xs font-mono text-slate-400">Meta Billing</span>
            </div>

            <div className="space-y-3 text-xs">
              <div className="flex justify-between py-2 border-b border-slate-100">
                <span className="text-slate-500">Opted-in Recipients</span>
                <span className="font-bold text-slate-900">{recipientCount}</span>
              </div>

              <div className="flex justify-between py-2 border-b border-slate-100">
                <span className="text-slate-500">Template Category</span>
                <span className="font-bold uppercase text-slate-900">{category}</span>
              </div>

              <div className="flex justify-between py-2 border-b border-slate-100">
                <span className="text-slate-500">Rate per Recipient</span>
                <span className="font-bold text-slate-900">{ratePerMsg} {currency}</span>
              </div>

              <div className="p-4 rounded-xl bg-emerald-50/80 border border-emerald-200 flex items-center justify-between">
                <div>
                  <span className="text-xs font-bold text-emerald-950 block">Estimated Meta Charge</span>
                  <span className="text-[10px] text-emerald-700 block">Billed to your credit card on file</span>
                </div>
                <span className="text-xl font-extrabold text-emerald-700">
                  {estimatedCost} {currency}
                </span>
              </div>
            </div>

            <div className="p-3.5 rounded-xl bg-slate-50 border border-slate-200 text-[11px] text-slate-600 space-y-1">
              <div className="font-bold text-slate-800">Compliance & Safety:</div>
              <ul className="list-disc pl-4 space-y-0.5 text-slate-500">
                <li>Non-opted-in contacts are automatically skipped by the gateway.</li>
                <li>Each send is logged into the usage audit ledger for billing reconciliation.</li>
                <li>Templates must be approved by Meta before dispatch.</li>
              </ul>
            </div>
          </div>
        </div>
      </div>

      {/* 3. Broadcast Campaign History */}
      <div className="bg-white border border-slate-200 rounded-2xl p-6 shadow-sm space-y-4">
        <h2 className="text-base font-bold text-slate-900 flex items-center gap-2">
          <Clock className="w-5 h-5 text-blue-600" />
          <span>Broadcast Campaign History</span>
        </h2>

        {campaigns.length === 0 ? (
          <div className="text-center py-8 text-xs text-slate-400">
            No previous broadcasts recorded.
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-slate-200 text-xs">
              <thead className="bg-slate-50">
                <tr>
                  <th className="px-4 py-3 text-left font-semibold text-slate-700">Campaign / Template</th>
                  <th className="px-4 py-3 text-left font-semibold text-slate-700">Status</th>
                  <th className="px-4 py-3 text-left font-semibold text-slate-700">Recipients</th>
                  <th className="px-4 py-3 text-left font-semibold text-slate-700">Delivered</th>
                  <th className="px-4 py-3 text-left font-semibold text-slate-700">Actual Cost</th>
                  <th className="px-4 py-3 text-left font-semibold text-slate-700">Date</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 bg-white">
                {campaigns.map((camp) => (
                  <tr key={camp.id} className="hover:bg-slate-50/50">
                    <td className="px-4 py-3 font-medium text-slate-900">{camp.template_name}</td>
                    <td className="px-4 py-3">
                      <span className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase ${
                        camp.status === 'completed'
                          ? 'bg-emerald-100 text-emerald-800'
                          : camp.status === 'partial'
                          ? 'bg-amber-100 text-amber-800'
                          : 'bg-rose-100 text-rose-800'
                      }`}>
                        {camp.status}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-slate-600">{camp.total_recipients}</td>
                    <td className="px-4 py-3 text-emerald-600 font-semibold">{camp.successful_sends}</td>
                    <td className="px-4 py-3 font-bold text-slate-900">
                      {camp.actual_cost} {camp.currency}
                    </td>
                    <td className="px-4 py-3 text-slate-400">
                      {new Date(camp.created_at).toLocaleString('en-GB', { timeZone: 'Asia/Dhaka' })} (BST)
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Confirmation Modal */}
      {isConfirmOpen && (
        <div className="fixed inset-0 bg-slate-900/40 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl max-w-md w-full p-6 shadow-xl space-y-4">
            <div className="flex items-center justify-between pb-3 border-b border-slate-100">
              <h3 className="text-base font-bold text-slate-900 flex items-center gap-2">
                <AlertCircle className="w-5 h-5 text-amber-600" />
                <span>Confirm WhatsApp Broadcast</span>
              </h3>
              <button onClick={() => setIsConfirmOpen(false)} className="text-slate-400 hover:text-slate-600">
                <X className="w-5 h-5" />
              </button>
            </div>

            <p className="text-xs text-slate-600 leading-relaxed">
              You are about to dispatch template <strong>{selectedTemplate?.name}</strong> to{' '}
              <strong>{recipientCount} opted-in customers</strong>.
            </p>

            <div className="p-4 rounded-xl bg-amber-50 border border-amber-200 text-xs text-amber-900 space-y-1">
              <div className="font-bold">Estimated Cost: {estimatedCost} {currency}</div>
              <p className="text-[11px] text-slate-600">
                This charge will be billed directly to your linked credit card by Meta. This action cannot be undone.
              </p>
            </div>

            <div className="flex justify-end gap-3 pt-2">
              <button
                type="button"
                onClick={() => setIsConfirmOpen(false)}
                className="px-4 py-2 rounded-xl border border-slate-300 text-xs font-semibold text-slate-700 hover:bg-slate-50"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={handleLaunchBroadcast}
                disabled={isSubmitting}
                className="px-5 py-2 rounded-xl bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-bold shadow-md transition-all disabled:opacity-50"
              >
                {isSubmitting ? 'Dispatching...' : 'Yes, Launch Broadcast'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
