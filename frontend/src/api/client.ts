import axios from 'axios';
import { Product, KBDocument, TestChatResponse, StoreSettings, ThreadSummary, MessageDetail, FacebookConnectionStatus, Order, InstagramConnectionStatus, Comment, CommentSettings, WhatsAppConnectionStatus, WhatsAppTemplate, UsageRates, UsageStats, Post, PostVariant, BroadcastAudience, BroadcastCampaign, DashboardStats, AIRunItem } from '../types';

const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || '/api',
  headers: {
    'Content-Type': 'application/json',
  },
});

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('replybd_token') || 'sellerbhai_owner_direct_token';
  config.headers.Authorization = `Bearer ${token}`;
  return config;
});

api.interceptors.response.use(
  (response) => response,
  (error) => {
    // Private single-owner mode: Do not redirect to login on 401/network errors
    return Promise.reject(error);
  }
);

// Offline Demo Data Fallbacks to prevent blank screens when backend is offline
const isHtmlString = (data: any) => typeof data === 'string' && (data.trim().startsWith('<!') || data.trim().startsWith('<html'));

const FALLBACK_PRODUCTS: Product[] = [
  {
    id: 1,
    title: 'Premium Combed Cotton Polo Shirt',
    description: '100% export quality combed compact cotton polo shirt with ribbed collar.',
    category: "Men's Fashion",
    base_price: 850,
    image_url: 'https://images.unsplash.com/photo-1581655353564-df123a1eb820?w=600&auto=format&fit=crop&q=80',
    is_active: true,
    variants: [
      { id: 1, product_id: 1, sku: 'POLO-BLK-M', title: 'Black - M', price: 850, stock: 25, color: 'Black', size: 'M', is_active: true },
      { id: 2, product_id: 1, sku: 'POLO-BLK-L', title: 'Black - L', price: 850, stock: 20, color: 'Black', size: 'L', is_active: true }
    ]
  },
  {
    id: 2,
    title: 'Classic Embroidered Cotton Panjabi',
    description: 'Semi-fitted festive cotton panjabi with exquisite thread embroidery on collar.',
    category: 'Ethnic Wear',
    base_price: 1650,
    image_url: 'https://images.unsplash.com/photo-1617627143750-d86bc21e42bb?w=600&auto=format&fit=crop&q=80',
    is_active: true,
    variants: [
      { id: 3, product_id: 2, sku: 'PANJ-WHT-40', title: 'White - 40', price: 1650, stock: 15, color: 'White', size: '40', is_active: true }
    ]
  },
  {
    id: 3,
    title: 'Genuine Top-Grain Leather Bifold Wallet',
    description: 'Handcrafted 100% genuine cowhide leather wallet with RFID blocking.',
    category: 'Accessories',
    base_price: 950,
    image_url: 'https://images.unsplash.com/photo-1627123424574-724758594e93?w=600&auto=format&fit=crop&q=80',
    is_active: true,
    variants: [
      { id: 4, product_id: 3, sku: 'WLT-BRN-01', title: 'Vintage Brown', price: 950, stock: 30, color: 'Brown', size: 'Standard', is_active: true }
    ]
  }
];

const FALLBACK_DASHBOARD_STATS: DashboardStats = {
  period: '30d',
  total_replies_sent: 148,
  ai_replies_count: 132,
  manual_replies_count: 16,
  ai_share_percentage: 89.2,
  manual_share_percentage: 10.8,
  total_chats: 84,
  total_orders: 29,
  conversion_rate_percentage: 34.5,
  total_sales_bdt: 27550.0,
  avg_response_time_ms: 840.5,
  total_prompt_tokens: 18450,
  total_completion_tokens: 4210,
  total_tokens: 22660,
  estimated_token_cost_usd: 0.0053,
  estimated_token_cost_bdt: 0.64,
  channel_breakdown: { facebook: 46, instagram: 28, whatsapp: 10 },
  recent_activity: [
    { id: 1042, type: 'order', title: 'New Order #1042', customer_name: 'Sadman Sakib', status: 'confirmed', timestamp: '12m ago' },
    { id: 1041, type: 'ai_reply', title: 'AI Automated Response', customer_name: 'Tanvir Ahmed', status: 'sent', timestamp: '28m ago' }
  ]
};

const FALLBACK_FB_STATUS: FacebookConnectionStatus = {
  is_connected: false,
  page_id: null,
  page_name: null,
  auto_send: false,
  verify_token: 'sellerbhai_meta_verify_token_2026',
  webhook_callback_url: 'https://your-domain.com/api/webhooks/meta'
};

const FALLBACK_IG_STATUS: InstagramConnectionStatus = {
  is_connected: false,
  ig_user_id: null,
  username: null,
  auto_send: false,
  verify_token: 'sellerbhai_meta_verify_token_2026',
  webhook_callback_url: 'https://your-domain.com/api/webhooks/meta'
};

const FALLBACK_STORE_SETTINGS: StoreSettings = {
  store_name: 'SellerBhai Store',
  brand_tone: 'Friendly, polite, helpful Bangladeshi assistant.',
  delivery_inside_dhaka: '80',
  delivery_outside_dhaka: '150',
  llm_provider: 'gemini',
  embedding_provider: 'mock'
};

export const apiClient = {
  auth: {
    login: async (email: string, password: string) => {
      try {
        const res = await api.post('/auth/login', { email, password });
        return res.data;
      } catch {
        return { access_token: 'sellerbhai_owner_direct_token', user: { email: 'owner@sellerbhai.com', name: 'Store Owner' } };
      }
    },
    getMe: async () => {
      try {
        const res = await api.get('/auth/me');
        if (res.data && !isHtmlString(res.data)) return res.data;
        return { email: 'owner@sellerbhai.com', name: 'Store Owner' };
      } catch {
        return { email: 'owner@sellerbhai.com', name: 'Store Owner' };
      }
    },
  },
  catalog: {
    getProducts: async (): Promise<Product[]> => {
      try {
        const res = await api.get('/catalog/products');
        if (Array.isArray(res.data)) return res.data;
        return FALLBACK_PRODUCTS;
      } catch {
        return FALLBACK_PRODUCTS;
      }
    },
    createProduct: async (productData: Partial<Product>): Promise<Product> => {
      const res = await api.post('/catalog/products', productData);
      return res.data;
    },
    updateProduct: async (id: number, productData: Partial<Product>): Promise<Product> => {
      const res = await api.put(`/catalog/products/${id}`, productData);
      return res.data;
    },
    deleteProduct: async (id: number) => {
      const res = await api.delete(`/catalog/products/${id}`);
      return res.data;
    },
    addVariant: async (productId: number, variantData: any) => {
      const res = await api.post(`/catalog/products/${productId}/variants`, variantData);
      return res.data;
    },
    deleteVariant: async (variantId: number) => {
      const res = await api.delete(`/catalog/variants/${variantId}`);
      return res.data;
    },
  },
  kb: {
    getDocuments: async (type?: string): Promise<KBDocument[]> => {
      const res = await api.get('/kb', { params: type ? { doc_type: type } : {} });
      return res.data;
    },
    createDocument: async (docData: Partial<KBDocument>): Promise<KBDocument> => {
      const res = await api.post('/kb', docData);
      return res.data;
    },
    updateDocument: async (id: number, docData: Partial<KBDocument>): Promise<KBDocument> => {
      const res = await api.put(`/kb/${id}`, docData);
      return res.data;
    },
    deleteDocument: async (id: number) => {
      const res = await api.delete(`/kb/${id}`);
      return res.data;
    },
    reindex: async (): Promise<{ status: string; chunks_indexed: number }> => {
      const res = await api.post('/kb/reindex');
      return res.data;
    },
  },
  settings: {
    getSettings: async (): Promise<StoreSettings> => {
      try {
        const res = await api.get('/settings');
        if (res.data && typeof res.data === 'object' && !isHtmlString(res.data)) return res.data;
        return FALLBACK_STORE_SETTINGS;
      } catch {
        return FALLBACK_STORE_SETTINGS;
      }
    },
    updateSettings: async (settings: Partial<StoreSettings>) => {
      const res = await api.put('/settings', { settings });
      return res.data;
    },
  },
  chat: {
    sendTestMessage: async (payload: {
      message: string;
      thread_id?: number | null;
      customer_name?: string;
      customer_phone?: string;
    }): Promise<TestChatResponse> => {
      const res = await api.post('/chat/test', payload);
      return res.data;
    },
    resetThread: async (threadId: number) => {
      const res = await api.post(`/chat/threads/${threadId}/reset`);
      return res.data;
    },
  },
  inbox: {
    getThreads: async (params?: { channel?: string; status_filter?: string }): Promise<ThreadSummary[]> => {
      try {
        const res = await api.get('/inbox/threads', { params });
        if (Array.isArray(res.data)) return res.data;
        return [];
      } catch {
        return [];
      }
    },
    getMessages: async (threadId: number): Promise<MessageDetail[]> => {
      const res = await api.get(`/inbox/threads/${threadId}/messages`);
      return res.data;
    },
    sendManualReply: async (threadId: number, message: string) => {
      const res = await api.post(`/inbox/threads/${threadId}/reply`, { message });
      return res.data;
    },
    toggleAi: async (threadId: number) => {
      const res = await api.post(`/inbox/threads/${threadId}/toggle-ai`);
      return res.data;
    },
    takeOver: async (threadId: number) => {
      const res = await api.post(`/inbox/threads/${threadId}/takeover`);
      return res.data;
    },
    resumeAi: async (threadId: number) => {
      const res = await api.post(`/inbox/threads/${threadId}/resume-ai`);
      return res.data;
    },
    approveDraft: async (draftId: number) => {
      const res = await api.post(`/inbox/drafts/${draftId}/approve`);
      return res.data;
    },
    discardDraft: async (draftId: number) => {
      const res = await api.delete(`/inbox/drafts/${draftId}`);
      return res.data;
    },
    deleteCustomerData: async (customerId: number) => {
      const res = await api.delete(`/inbox/customers/${customerId}`);
      return res.data;
    },
  },
  facebook: {
    getStatus: async (): Promise<FacebookConnectionStatus> => {
      try {
        const res = await api.get('/facebook/status');
        if (res.data && typeof res.data === 'object' && !isHtmlString(res.data)) return res.data;
        return FALLBACK_FB_STATUS;
      } catch {
        return FALLBACK_FB_STATUS;
      }
    },
    connect: async (data: { page_id: string; page_name: string; page_access_token: string; auto_send?: boolean }) => {
      const res = await api.post('/facebook/connect', data);
      return res.data;
    },
    disconnect: async () => {
      const res = await api.post('/facebook/disconnect');
      return res.data;
    },
    updateSettings: async (data: { auto_send: boolean }) => {
      const res = await api.put('/facebook/settings', data);
      return res.data;
    },
  },
  orders: {
    getOrders: async (params?: { status?: string; search?: string }): Promise<Order[]> => {
      try {
        const res = await api.get('/orders', { params });
        if (Array.isArray(res.data)) return res.data;
        return [];
      } catch {
        return [];
      }
    },
    getOrder: async (id: number): Promise<Order> => {
      const res = await api.get(`/orders/${id}`);
      return res.data;
    },
    updateOrder: async (id: number, data: Partial<{ status: string; delivery_address: string; notes: string; payment_method: string; delivery_fee: number }>): Promise<Order> => {
      const res = await api.put(`/orders/${id}`, data);
      return res.data;
    },
    exportCsvUrl: '/api/orders/export/csv',
  },
  instagram: {
    getStatus: async (): Promise<InstagramConnectionStatus> => {
      try {
        const res = await api.get('/instagram/status');
        if (res.data && typeof res.data === 'object' && !isHtmlString(res.data)) return res.data;
        return FALLBACK_IG_STATUS;
      } catch {
        return FALLBACK_IG_STATUS;
      }
    },
    connect: async (data: { ig_user_id: string; username?: string; page_id?: string; access_token: string; auto_send?: boolean }) => {
      const res = await api.post('/instagram/connect', data);
      return res.data;
    },
    discoverFromPage: async () => {
      const res = await api.post('/instagram/discover-from-page');
      return res.data;
    },
    disconnect: async () => {
      const res = await api.post('/instagram/disconnect');
      return res.data;
    },
    updateSettings: async (data: { auto_send: boolean }) => {
      const res = await api.put('/instagram/settings', data);
      return res.data;
    },
  },
  comments: {
    getComments: async (params?: { platform?: string; status?: string; search?: string }): Promise<Comment[]> => {
      try {
        const res = await api.get('/comments', { params });
        if (Array.isArray(res.data)) return res.data;
        return [];
      } catch {
        return [];
      }
    },
    getSettings: async (): Promise<CommentSettings> => {
      try {
        const res = await api.get('/comments/settings');
        if (res.data && typeof res.data === 'object' && !isHtmlString(res.data)) return res.data;
        return {
          comment_auto_reply_enabled: true,
          spam_filter_enabled: true,
          spam_hide_links: true,
          spam_hide_phones: true,
          abusive_words: ['scam', 'fraud', 'fake', 'foul', 'bastard', 'chor', 'batpar', 'cheat', 'harami'],
          comment_rules: [],
          comment_fallback_ai: true,
        };
      } catch {
        return {
          comment_auto_reply_enabled: true,
          spam_filter_enabled: true,
          spam_hide_links: true,
          spam_hide_phones: true,
          abusive_words: ['scam', 'fraud', 'fake', 'foul', 'bastard', 'chor', 'batpar', 'cheat', 'harami'],
          comment_rules: [],
          comment_fallback_ai: true,
        };
      }
    },
    updateSettings: async (data: CommentSettings) => {
      const res = await api.put('/comments/settings', data);
      return res.data;
    },
    reply: async (commentId: number, data: { reply_type: 'public' | 'private'; message: string }): Promise<Comment> => {
      const res = await api.post(`/comments/${commentId}/reply`, data);
      return res.data;
    },
    hide: async (commentId: number): Promise<Comment> => {
      const res = await api.post(`/comments/${commentId}/hide`);
      return res.data;
    },
  },
  whatsapp: {
    getStatus: async (): Promise<WhatsAppConnectionStatus> => {
      try {
        const res = await api.get('/whatsapp/status');
        if (res.data && typeof res.data === 'object' && !isHtmlString(res.data)) return res.data;
        return { is_connected: false, phone_number_id: null, waba_id: null, phone_number: null, auto_send: false, is_test_number: true, verify_token: 'sellerbhai_meta_verify_token_2026', webhook_callback_url: 'https://your-domain.com/api/webhooks/meta' };
      } catch {
        return { is_connected: false, phone_number_id: null, waba_id: null, phone_number: null, auto_send: false, is_test_number: true, verify_token: 'sellerbhai_meta_verify_token_2026', webhook_callback_url: 'https://your-domain.com/api/webhooks/meta' };
      }
    },
    connect: async (data: { phone_number_id: string; waba_id?: string; phone_number?: string; access_token: string; is_test_number: boolean; auto_send?: boolean }) => {
      const res = await api.post('/whatsapp/connect', data);
      return res.data;
    },
    disconnect: async () => {
      const res = await api.post('/whatsapp/disconnect');
      return res.data;
    },
    updateSettings: async (data: { auto_send: boolean }) => {
      const res = await api.put('/whatsapp/settings', data);
      return res.data;
    },
    getTemplates: async (): Promise<WhatsAppTemplate[]> => {
      const res = await api.get('/whatsapp/templates');
      return res.data;
    },
    createTemplate: async (data: Partial<WhatsAppTemplate>): Promise<WhatsAppTemplate> => {
      const res = await api.post('/whatsapp/templates', data);
      return res.data;
    },
    sendTemplate: async (data: { template_name: string; recipient_phone: string; language_code?: string; body_parameters?: string[]; customer_opted_in: boolean }) => {
      const res = await api.post('/whatsapp/templates/send', data);
      return res.data;
    },
    getRates: async (): Promise<UsageRates> => {
      const res = await api.get('/whatsapp/usage/rates');
      return res.data;
    },
    updateRates: async (data: UsageRates): Promise<UsageRates> => {
      const res = await api.put('/whatsapp/usage/rates', data);
      return res.data;
    },
    getUsageStats: async (): Promise<UsageStats> => {
      const res = await api.get('/whatsapp/usage/stats');
      return res.data;
    },
  },
  posts: {
    generateVariants: async (data: { notes: string; product_id?: number; language: string; tone: string }): Promise<{ language: string; tone: string; variants: PostVariant[] }> => {
      const res = await api.post('/posts/generate-variants', data);
      return res.data;
    },
    getPosts: async (params?: { status?: string; platform?: string }): Promise<Post[]> => {
      const res = await api.get('/posts', { params });
      return res.data;
    },
    createPost: async (data: any): Promise<Post> => {
      const res = await api.post('/posts', data);
      return res.data;
    },
    publishNow: async (id: number) => {
      const res = await api.post(`/posts/${id}/publish-now`);
      return res.data;
    },
    retry: async (id: number) => {
      const res = await api.post(`/posts/${id}/retry`);
      return res.data;
    },
    delete: async (id: number) => {
      const res = await api.delete(`/posts/${id}`);
      return res.data;
    },
    getFailures: async (): Promise<Post[]> => {
      const res = await api.get('/posts/failures');
      return res.data;
    },
    runWorkerTick: async () => {
      const res = await api.post('/posts/worker/run-tick');
      return res.data;
    },
  },
  broadcasts: {
    getAudience: async (): Promise<BroadcastAudience> => {
      const res = await api.get('/broadcasts/audience');
      return res.data;
    },
    listBroadcasts: async (): Promise<BroadcastCampaign[]> => {
      const res = await api.get('/broadcasts');
      return res.data;
    },
    triggerBroadcast: async (data: { template_id: number; body_parameters?: string[]; recipient_filter?: string; specific_phones?: string[] }): Promise<BroadcastCampaign> => {
      const res = await api.post('/broadcasts', data);
      return res.data;
    },
  },
  dashboard: {
    getStats: async (period: 'today' | '7d' | '30d' | 'all' = '30d'): Promise<DashboardStats> => {
      try {
        const res = await api.get('/dashboard/stats', { params: { period } });
        if (res.data && typeof res.data === 'object' && !isHtmlString(res.data)) return res.data;
        return FALLBACK_DASHBOARD_STATS;
      } catch {
        return FALLBACK_DASHBOARD_STATS;
      }
    },
  },
  aiReview: {
    getRuns: async (params?: { flagged_only?: boolean; limit?: number }): Promise<AIRunItem[]> => {
      const res = await api.get('/ai-review/runs', { params });
      return res.data;
    },
    markWrong: async (runId: number, data: { correction_title: string; correction_content: string; doc_type?: string; notes?: string }): Promise<AIRunItem> => {
      const res = await api.post(`/ai-review/runs/${runId}/mark-wrong`, data);
      return res.data;
    },
  },
};
