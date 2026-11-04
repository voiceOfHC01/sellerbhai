import React from 'react';
import { Shield, Lock, FileText, ArrowLeft } from 'lucide-react';
import { Link } from 'react-router-dom';

export const PrivacyPolicyPage: React.FC = () => {
  return (
    <div className="min-h-screen bg-slate-50 py-12 px-4 sm:px-6 lg:px-8 font-sans">
      <div className="max-w-3xl mx-auto bg-white rounded-3xl p-8 sm:p-12 shadow-sm border border-slate-200 space-y-6">
        <div className="flex items-center justify-between pb-4 border-b border-slate-100">
          <div className="flex items-center gap-2.5">
            <div className="w-9 h-9 rounded-xl bg-blue-600 text-white flex items-center justify-center font-bold">
              <Shield className="w-5 h-5" />
            </div>
            <div>
              <h1 className="text-xl font-bold text-slate-900">Privacy Policy & Meta Platform Compliance</h1>
              <p className="text-xs text-slate-500">Reply.BD Social Commerce AI Agent</p>
            </div>
          </div>

          <Link
            to="/login"
            className="flex items-center gap-1.5 text-xs font-semibold text-slate-600 hover:text-slate-900 bg-slate-100 px-3 py-1.5 rounded-xl transition-colors"
          >
            <ArrowLeft className="w-3.5 h-3.5" />
            <span>Back to Portal</span>
          </Link>
        </div>

        <div className="p-4 rounded-2xl bg-blue-50/70 border border-blue-200 text-xs text-blue-900 space-y-1">
          <p className="font-semibold">Commitment to Data Privacy & Protection</p>
          <p className="text-slate-600">
            This policy outlines how Reply.BD handles personal information collected during automated customer service across Facebook Pages, Instagram DMs, and WhatsApp Business API.
          </p>
        </div>

        <div className="space-y-4 text-xs text-slate-600 leading-relaxed">
          <h2 className="text-sm font-bold text-slate-900">1. Information We Collect</h2>
          <p>
            When customers interact with connected merchant channels, we process only the data strictly necessary for fulfilling customer service and order delivery:
          </p>
          <ul className="list-disc pl-5 space-y-1">
            <li>Public platform identifiers (Facebook Page-Scoped ID, Instagram Scoped ID, WhatsApp Phone Number).</li>
            <li>Conversation content (messages, voice note audio files for transcription, comments).</li>
            <li>Customer shipping information (Name, Bangladeshi phone number, physical address for Cash-on-Delivery fulfillment).</li>
          </ul>

          <h2 className="text-sm font-bold text-slate-900">2. How Data is Used & AI Guardrails</h2>
          <p>
            Customer queries are evaluated exclusively against the merchant’s verified catalog and knowledge base. We enforce strict prompt-injection defenses and never hallucinate unauthorized discounts. Access tokens from Meta are encrypted using AES-128 / Fernet encryption at rest.
          </p>

          <h2 className="text-sm font-bold text-slate-900">3. User Data Deletion (GDPR & Meta Compliance)</h2>
          <p>
            Any customer has the absolute right to have their personal data and conversation history permanently deleted at any time:
          </p>
          <ul className="list-disc pl-5 space-y-1">
            <li><strong>Automated Callback:</strong> Via Meta’s Data Deletion Request Callback endpoint at <code>/api/webhooks/meta/data-deletion</code>.</li>
            <li><strong>Merchant Dashboard:</strong> The store owner can click the "Delete Customer Data" button inside the Unified Inbox at any time.</li>
            <li><strong>Direct Contact:</strong> By sending an email to <code>privacy@replybd.com</code>.</li>
          </ul>

          <h2 className="text-sm font-bold text-slate-900">4. Third-Party Integrations</h2>
          <p>
            We interface solely with official Meta Graph API v21.0 endpoints. Customer data is never sold, leased, or transmitted to third-party data brokers.
          </p>
        </div>

        <div className="pt-4 border-t border-slate-100 flex items-center justify-between text-[11px] text-slate-400">
          <span>Effective Date: November 2026</span>
          <span>Version 1.0 (Meta App Review Compliant)</span>
        </div>
      </div>
    </div>
  );
};
