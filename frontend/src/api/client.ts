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

export const apiClient = {
  auth: {
    login: async (email: string, password: string) => {
      const res = await api.post('/auth/login', { email, password });
      return res.data;
    },
    getMe: async () => {
      const res = await api.get('/auth/me');
      return res.data;
    },
  },
  catalog: {
    getProducts: async (): Promise<Product[]> => {
      const res = await api.get('/catalog/products');
      return res.data;
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
      const res = await api.get('/settings');
      return res.data;
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
      const res = await api.get('/inbox/threads', { params });
      return res.data;
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
      const res = await api.get('/facebook/status');
      return res.data;
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
      const res = await api.get('/orders', { params });
      return res.data;
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
      const res = await api.get('/instagram/status');
      return res.data;
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
      const res = await api.get('/comments', { params });
      return res.data;
    },
    getSettings: async (): Promise<CommentSettings> => {
      const res = await api.get('/comments/settings');
      return res.data;
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
      const res = await api.get('/whatsapp/status');
      return res.data;
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
      const res = await api.get('/dashboard/stats', { params: { period } });
      return res.data;
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
