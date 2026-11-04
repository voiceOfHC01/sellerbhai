export interface ProductVariant {
  id: number;
  product_id: number;
  sku: string;
  title: string;
  price: number;
  stock: number;
  color?: string | null;
  size?: string | null;
  image_url?: string | null;
  is_active: boolean;
}

export interface Product {
  id: number;
  title: string;
  description?: string | null;
  category?: string | null;
  base_price: number;
  image_url?: string | null;
  is_active: boolean;
  variants: ProductVariant[];
}

export interface KBDocument {
  id: number;
  doc_type: 'faq' | 'policy' | 'general';
  title: string;
  content: string;
  is_active: boolean;
}

export interface RetrievedSource {
  id: number;
  chunk_text: string;
  score: number;
  metadata?: any;
  product_id?: number | null;
  document_id?: number | null;
}

export interface ToolCallLog {
  tool: string;
  arguments: any;
  result: any;
}

export interface TestChatResponse {
  reply: string;
  detected_language: 'bangla' | 'banglish' | 'english';
  retrieved_sources: RetrievedSource[];
  tool_calls: ToolCallLog[];
  handover_triggered: boolean;
  thread_status: 'active' | 'human_takeover';
  thread_id: number;
  latency_ms?: number;
}

export interface AdminUser {
  id: number;
  email: string;
  name: string;
}

export interface StoreSettings {
  store_name: string;
  brand_tone: string;
  delivery_inside_dhaka: string;
  delivery_outside_dhaka: string;
  llm_provider: string;
  embedding_provider: string;
}

// Phase 2 Types
export interface ThreadSummary {
  id: number;
  channel: string;
  status: 'active' | 'human_takeover' | 'closed';
  ai_enabled: boolean;
  handover_reason?: string | null;
  last_activity_at: string;
  last_customer_message_at?: string | null;
  customer_id: number;
  customer_name: string;
  customer_phone?: string | null;
  last_message_text?: string | null;
  has_pending_draft: boolean;
  is_window_active: boolean;
  window_hours_remaining: number;
}

export interface MessageDetail {
  id: number;
  thread_id: number;
  sender_type: 'customer' | 'bot' | 'admin';
  content: string;
  language?: string | null;
  platform_message_id?: string | null;
  is_draft: boolean;
  delivery_status: 'sent' | 'draft' | 'failed' | 'blocked_outside_window';
  audio_url?: string | null;
  voice_transcript?: string | null;
  voice_confidence?: number | null;
  is_voice_message?: boolean;
  metadata_json?: any;
  created_at: string;
}

export interface FacebookConnectionStatus {
  is_connected: boolean;
  page_id?: string | null;
  page_name?: string | null;
  auto_send: boolean;
  connected_at?: string | null;
  verify_token: string;
  webhook_callback_url: string;
}

// Phase 3 Types
export interface OrderItem {
  id: number;
  product_id: number;
  product_variant_id?: number | null;
  quantity: number;
  unit_price: number;
  line_total: number;
  product_title?: string | null;
  variant_sku?: string | null;
}

export interface Order {
  id: number;
  customer_id: number;
  customer_name: string;
  customer_phone?: string | null;
  thread_id?: number | null;
  status: 'pending' | 'confirmed' | 'shipped' | 'delivered' | 'cancelled';
  payment_method: string;
  total_amount: number;
  delivery_fee: number;
  delivery_address?: string | null;
  notes?: string | null;
  created_at: string;
  updated_at: string;
  items: OrderItem[];
}

// Phase 4 Types
export interface InstagramConnectionStatus {
  is_connected: boolean;
  ig_user_id?: string | null;
  username?: string | null;
  page_id?: string | null;
  auto_send: boolean;
  connected_at?: string | null;
  verify_token: string;
  webhook_callback_url: string;
}

export interface Comment {
  id: number;
  platform: 'facebook' | 'instagram';
  platform_comment_id: string;
  post_id?: string | null;
  author_id: string;
  author_name?: string | null;
  message: string;
  status: 'pending' | 'replied' | 'hidden_spam' | 'ignored';
  actions_taken: string[];
  public_reply_text?: string | null;
  private_reply_text?: string | null;
  is_hidden: boolean;
  is_private_reply_sent: boolean;
  created_at: string;
  updated_at: string;
}

export interface CommentRule {
  keyword: string;
  public_reply: string;
  private_reply: string;
  send_private_dm: boolean;
}

export interface CommentSettings {
  comment_auto_reply_enabled: boolean;
  spam_filter_enabled: boolean;
  spam_hide_links: boolean;
  spam_hide_phones: boolean;
  abusive_words: string[];
  comment_rules: CommentRule[];
  comment_fallback_ai: boolean;
}

// Phase 5 Types
export interface WhatsAppConnectionStatus {
  is_connected: boolean;
  phone_number_id?: string | null;
  waba_id?: string | null;
  phone_number?: string | null;
  is_test_number: boolean;
  auto_send: boolean;
  connected_at?: string | null;
  verify_token: string;
  webhook_callback_url: string;
}

export interface WhatsAppTemplate {
  id: number;
  waba_id?: string | null;
  name: string;
  category: 'MARKETING' | 'UTILITY' | 'AUTHENTICATION' | 'SERVICE';
  language: string;
  status: string;
  header_text?: string | null;
  body_text: string;
  footer_text?: string | null;
  buttons_json?: any;
  created_at: string;
  updated_at: string;
}

export interface UsageRates {
  rate_marketing: number;
  rate_utility: number;
  rate_service: number;
  rate_authentication: number;
  currency: string;
}

export interface UsageStats {
  period: string;
  total_messages: number;
  service_count: number;
  utility_count: number;
  marketing_count: number;
  authentication_count: number;
  rates: Record<string, number>;
  currency: string;
  estimated_cost: number;
  breakdown_cost: Record<string, number>;
}

// Phase 6 Types: Posts, Scheduler, Calendar, Broadcasts
export interface PostVariant {
  variant_number: number;
  style_description: string;
  title: string;
  caption: string;
  hashtags: string;
}

export interface Post {
  id: number;
  title?: string | null;
  caption: string;
  hashtags?: string | null;
  media_urls?: string[] | null;
  language?: string | null;
  tone?: string | null;
  product_id?: number | null;
  product_title?: string | null;
  target_platforms?: string[] | null;
  status: 'draft' | 'scheduled' | 'publishing' | 'published' | 'failed';
  scheduled_at?: string | null;
  scheduled_at_dhaka?: string | null;
  published_at?: string | null;
  published_at_dhaka?: string | null;
  facebook_post_id?: string | null;
  instagram_media_id?: string | null;
  error_message?: string | null;
  retry_count: number;
  created_at: string;
}

export interface BroadcastAudience {
  opted_in_count: number;
  rates: Record<string, number>;
  currency: string;
  marketing_rate_per_recipient: number;
  utility_rate_per_recipient: number;
  estimated_marketing_cost: number;
  estimated_utility_cost: number;
  policy_warning: string;
}

export interface BroadcastCampaign {
  id: number;
  template_id: number;
  template_name: string;
  status: string;
  total_recipients: number;
  successful_sends: number;
  failed_sends: number;
  estimated_cost: number;
  actual_cost: number;
  currency: string;
  parameters_json?: any;
  error_summary?: string | null;
  created_at: string;
}

// Phase 7 Types: Dashboard Analytics & AI Review
export interface DashboardStats {
  period: string;
  total_replies_sent: number;
  ai_replies_count: number;
  manual_replies_count: number;
  ai_share_percentage: number;
  manual_share_percentage: number;
  total_chats: number;
  total_orders: number;
  conversion_rate_percentage: number;
  total_sales_bdt: number;
  avg_response_time_ms: number;
  total_prompt_tokens: number;
  total_completion_tokens: number;
  total_tokens: number;
  estimated_token_cost_usd: number;
  estimated_token_cost_bdt: number;
  channel_breakdown: Record<string, number>;
  recent_activity: Array<{
    id: number;
    type: string;
    title: string;
    customer_name: string;
    status: string;
    timestamp: string;
  }>;
}

export interface AIRunItem {
  id: number;
  thread_id?: number | null;
  message_id?: number | null;
  user_message?: string | null;
  prompt_tokens: number;
  completion_tokens: number;
  latency_ms: number;
  retrieved_chunks?: Array<{ text: string; score: number }> | null;
  tool_calls?: Array<{ tool: string; arguments: any; result: any }> | null;
  raw_response?: string | null;
  detected_language?: string | null;
  is_flagged_wrong: boolean;
  correction_notes?: string | null;
  corrected_kb_doc_id?: number | null;
  created_at: string;
}
