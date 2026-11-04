import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { apiClient } from '../api/client';
import { DashboardStats } from '../types';
import { 
  BarChart3, MessageSquare, Bot, User, ShoppingBag, Clock, 
  DollarSign, Sparkles, TrendingUp, RefreshCw, Facebook, Instagram, Phone, ArrowUpRight, Share2
} from 'lucide-react';

export const DashboardPage: React.FC = () => {
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [period, setPeriod] = useState<'today' | '7d' | '30d' | 'all'>('30d');
  const [loading, setLoading] = useState(true);

  const fetchStats = async () => {
    try {
      setLoading(true);
      const data = await apiClient.dashboard.getStats(period);
      setStats(data);
    } catch (err) {
      console.error('Failed to load dashboard metrics:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchStats();
  }, [period]);

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">
      {/* Top Banner */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 border-b border-slate-200 pb-5">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-2xl font-bold text-slate-900">Commerce Intelligence & Analytics</h1>
            <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-blue-100 text-blue-800">
              Executive View
            </span>
          </div>
          <p className="text-sm text-slate-500 mt-1">
            Real-time conversion metrics, AI automation share, response latencies, and AI token billing.
          </p>
        </div>

        {/* Period Selector & Refresh */}
        <div className="flex items-center gap-3">
          <div className="flex items-center bg-slate-100 p-1 rounded-xl text-xs font-semibold">
            {(['today', '7d', '30d', 'all'] as const).map((p) => (
              <button
                key={p}
                onClick={() => setPeriod(p)}
                className={`px-3 py-1.5 rounded-lg uppercase tracking-wider transition-all ${
                  period === p
                    ? 'bg-white text-slate-900 shadow-sm'
                    : 'text-slate-500 hover:text-slate-900'
                }`}
              >
                {p === 'today' ? 'Today' : p === '7d' ? '7 Days' : p === '30d' ? '30 Days' : 'All Time'}
              </button>
            ))}
          </div>

          <button
            onClick={fetchStats}
            className="flex items-center gap-1.5 px-3 py-2 rounded-xl border border-slate-300 hover:bg-slate-50 text-slate-700 text-sm font-medium transition-colors"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
            <span>Refresh</span>
          </button>
        </div>
      </div>

      {/* Meta Facebook & Instagram Automation Connection Banner */}
      <div className="bg-gradient-to-r from-blue-700 via-indigo-600 to-pink-600 rounded-2xl p-6 text-white shadow-lg flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
        <div className="space-y-1.5">
          <div className="flex items-center gap-2">
            <span className="px-2.5 py-0.5 rounded-full bg-white/20 text-xs font-semibold backdrop-blur">
              Meta AI Automation
            </span>
            <span className="text-xs text-blue-100 flex items-center gap-1">
              <Facebook className="w-3.5 h-3.5" /> Facebook Page & <Instagram className="w-3.5 h-3.5" /> Instagram DM
            </span>
          </div>
          <h2 className="text-xl font-bold tracking-tight">Connect Your Facebook Page & Instagram Account</h2>
          <p className="text-sm text-blue-100 max-w-2xl leading-relaxed">
            Link your Facebook business page or Instagram to let SellerBhai AI answer customer messages, check live product stock, share prices, and take orders automatically.
          </p>
        </div>
        <Link
          to="/settings"
          className="px-5 py-3 rounded-xl bg-white text-blue-700 hover:bg-blue-50 font-bold text-sm shadow transition-all flex items-center gap-2 whitespace-nowrap"
        >
          <Share2 className="w-4 h-4" />
          <span>Connect Facebook & Instagram</span>
          <ArrowUpRight className="w-4 h-4" />
        </Link>
      </div>

      {/* 5 Core Metric Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
        {/* Card 1: Replies Sent */}
        <div className="bg-white border border-slate-200 rounded-2xl p-5 shadow-sm space-y-2">
          <div className="flex items-center justify-between text-slate-500">
            <span className="text-xs font-semibold">Total Replies Sent</span>
            <div className="p-2 rounded-xl bg-blue-50 text-blue-600">
              <MessageSquare className="w-4 h-4" />
            </div>
          </div>
          <div className="text-2xl font-bold text-slate-900">
            {stats?.total_replies_sent.toLocaleString() || 0}
          </div>
          <div className="text-[11px] text-slate-500 flex items-center gap-1">
            <span>Bot + Manual Customer Replies</span>
          </div>
        </div>

        {/* Card 2: AI vs Manual Share */}
        <div className="bg-white border border-slate-200 rounded-2xl p-5 shadow-sm space-y-2">
          <div className="flex items-center justify-between text-slate-500">
            <span className="text-xs font-semibold">AI Automation Share</span>
            <div className="p-2 rounded-xl bg-emerald-50 text-emerald-600">
              <Bot className="w-4 h-4" />
            </div>
          </div>
          <div className="text-2xl font-bold text-emerald-600">
            {stats?.ai_share_percentage || 0}%
          </div>
          <div className="text-[11px] text-slate-500 flex items-center justify-between">
            <span className="text-emerald-700 font-medium">AI: {stats?.ai_replies_count || 0}</span>
            <span className="text-slate-400">Manual: {stats?.manual_replies_count || 0}</span>
          </div>
        </div>

        {/* Card 3: Chats -> Orders Conversion */}
        <div className="bg-white border border-slate-200 rounded-2xl p-5 shadow-sm space-y-2">
          <div className="flex items-center justify-between text-slate-500">
            <span className="text-xs font-semibold">Chats ➔ Orders</span>
            <div className="p-2 rounded-xl bg-purple-50 text-purple-600">
              <ShoppingBag className="w-4 h-4" />
            </div>
          </div>
          <div className="text-2xl font-bold text-purple-700">
            {stats?.conversion_rate_percentage || 0}%
          </div>
          <div className="text-[11px] text-slate-500">
            <span className="font-semibold text-slate-800">{stats?.total_orders || 0} orders</span> from {stats?.total_chats || 0} chats
          </div>
        </div>

        {/* Card 4: Avg Response Time */}
        <div className="bg-white border border-slate-200 rounded-2xl p-5 shadow-sm space-y-2">
          <div className="flex items-center justify-between text-slate-500">
            <span className="text-xs font-semibold">Avg AI Latency</span>
            <div className="p-2 rounded-xl bg-amber-50 text-amber-600">
              <Clock className="w-4 h-4" />
            </div>
          </div>
          <div className="text-2xl font-bold text-slate-900">
            {stats?.avg_response_time_ms ? `${stats.avg_response_time_ms} ms` : '0 ms'}
          </div>
          <div className="text-[11px] text-slate-500">
            Under 2.0s Meta Webhook SLA
          </div>
        </div>

        {/* Card 5: AI Token Cost */}
        <div className="bg-white border border-slate-200 rounded-2xl p-5 shadow-sm space-y-2">
          <div className="flex items-center justify-between text-slate-500">
            <span className="text-xs font-semibold">Estimated AI Cost</span>
            <div className="p-2 rounded-xl bg-teal-50 text-teal-600">
              <DollarSign className="w-4 h-4" />
            </div>
          </div>
          <div className="text-2xl font-bold text-teal-700">
            ৳{stats?.estimated_token_cost_bdt || 0}
          </div>
          <div className="text-[11px] text-slate-500">
            ${stats?.estimated_token_cost_usd || 0} • {stats?.total_tokens.toLocaleString() || 0} tokens
          </div>
        </div>
      </div>

      {/* Breakdown Strip & Recent Sales Stream */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
        {/* Left: Automation Bar & Channel Breakdown */}
        <div className="lg:col-span-7 bg-white border border-slate-200 rounded-2xl p-6 shadow-sm space-y-6">
          <div className="flex items-center justify-between border-b border-slate-100 pb-3">
            <h2 className="text-base font-bold text-slate-900 flex items-center gap-2">
              <TrendingUp className="w-5 h-5 text-blue-600" />
              <span>Automation vs Human Share</span>
            </h2>
            <span className="text-xs font-semibold text-slate-500">For {period}</span>
          </div>

          {/* Visual Percentage Progress Bar */}
          <div className="space-y-2">
            <div className="h-4 w-full bg-slate-100 rounded-full overflow-hidden flex">
              <div
                style={{ width: `${stats?.ai_share_percentage || 0}%` }}
                className="bg-emerald-500 h-full transition-all"
                title={`AI Automated: ${stats?.ai_share_percentage}%`}
              />
              <div
                style={{ width: `${stats?.manual_share_percentage || 0}%` }}
                className="bg-blue-500 h-full transition-all"
                title={`Manual Replies: ${stats?.manual_share_percentage}%`}
              />
            </div>
            <div className="flex justify-between text-xs text-slate-600">
              <span className="flex items-center gap-1.5 font-medium text-emerald-700">
                <span className="w-2.5 h-2.5 rounded-full bg-emerald-500 inline-block" />
                <span>AI Automated Replies: {stats?.ai_share_percentage || 0}% ({stats?.ai_replies_count || 0})</span>
              </span>
              <span className="flex items-center gap-1.5 font-medium text-blue-700">
                <span className="w-2.5 h-2.5 rounded-full bg-blue-500 inline-block" />
                <span>Human Takeovers: {stats?.manual_share_percentage || 0}% ({stats?.manual_replies_count || 0})</span>
              </span>
            </div>
          </div>

          {/* Channel Traffic Breakdown */}
          <div className="pt-3 border-t border-slate-100">
            <h3 className="text-xs font-bold text-slate-700 uppercase tracking-wider mb-3">
              Conversations by Channel
            </h3>
            <div className="grid grid-cols-3 gap-3">
              <div className="p-3 rounded-xl border border-blue-200 bg-blue-50/40 flex items-center gap-3">
                <Facebook className="w-6 h-6 text-blue-600" />
                <div>
                  <span className="text-xs font-bold text-slate-900 block">
                    {stats?.channel_breakdown.facebook || 0}
                  </span>
                  <span className="text-[10px] text-slate-500">Messenger</span>
                </div>
              </div>

              <div className="p-3 rounded-xl border border-pink-200 bg-pink-50/40 flex items-center gap-3">
                <Instagram className="w-6 h-6 text-pink-600" />
                <div>
                  <span className="text-xs font-bold text-slate-900 block">
                    {stats?.channel_breakdown.instagram || 0}
                  </span>
                  <span className="text-[10px] text-slate-500">Instagram DM</span>
                </div>
              </div>

              <div className="p-3 rounded-xl border border-emerald-200 bg-emerald-50/40 flex items-center gap-3">
                <Phone className="w-6 h-6 text-emerald-600" />
                <div>
                  <span className="text-xs font-bold text-slate-900 block">
                    {stats?.channel_breakdown.whatsapp || 0}
                  </span>
                  <span className="text-[10px] text-slate-500">WhatsApp</span>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Right: Recent Conversions & Sales Stream */}
        <div className="lg:col-span-5 bg-white border border-slate-200 rounded-2xl p-6 shadow-sm space-y-4">
          <div className="flex items-center justify-between border-b border-slate-100 pb-3">
            <h2 className="text-base font-bold text-slate-900 flex items-center gap-2">
              <ShoppingBag className="w-5 h-5 text-purple-600" />
              <span>Recent Chat Conversions</span>
            </h2>
            <span className="text-xs font-bold text-purple-700">
              Total ৳{stats?.total_sales_bdt.toLocaleString() || 0}
            </span>
          </div>

          {!stats?.recent_activity || stats.recent_activity.length === 0 ? (
            <div className="text-center py-8 text-xs text-slate-400">
              No orders converted in this period yet.
            </div>
          ) : (
            <div className="space-y-3">
              {stats.recent_activity.map((item) => (
                <div
                  key={item.id}
                  className="p-3 rounded-xl border border-slate-200 bg-slate-50/60 flex items-center justify-between text-xs"
                >
                  <div className="flex items-center gap-3">
                    <div className="w-8 h-8 rounded-lg bg-emerald-100 text-emerald-700 flex items-center justify-center font-bold">
                      ৳
                    </div>
                    <div>
                      <span className="font-bold text-slate-900 block">{item.title}</span>
                      <span className="text-[11px] text-slate-500">Buyer: {item.customer_name}</span>
                    </div>
                  </div>

                  <div className="text-right">
                    <span className="px-2 py-0.5 rounded text-[10px] font-bold uppercase bg-emerald-100 text-emerald-800">
                      {item.status}
                    </span>
                    <span className="text-[10px] text-slate-400 block mt-0.5">
                      {new Date(item.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
