/**
 * Browser: same-origin by default (Next.js rewrites /api + /health → FastAPI).
 * SSR: hit the API directly via API_INTERNAL_BASE (Docker service name or loopback).
 * Set NEXT_PUBLIC_API_BASE only if the API is on a different public host.
 */
const API_BASE =
  typeof window === "undefined"
    ? process.env.API_INTERNAL_BASE || process.env.NEXT_PUBLIC_API_BASE || "http://127.0.0.1:8471"
    : process.env.NEXT_PUBLIC_API_BASE || "";

export type Category = {
  id: string;
  name: string;
  slug: string;
  description: string;
  adsense_slot_hint: string;
  is_active: boolean;
};

export type Topic = {
  id: string;
  category_id: string;
  batch_recommend_id: string;
  title: string;
  angle: string;
  seed_keywords: string[];
  score: number;
  status: string;
};

export type BatchItem = {
  id: string;
  topic_suggestion_id: string;
  post_id: string | null;
  sequence_index: number;
  status: string;
  topic_title?: string | null;
  post_title?: string | null;
  post_slug?: string | null;
  char_count?: number | null;
  review_status?: string | null;
};

export type Batch = {
  id: string;
  category_id: string;
  publish_mode: string;
  first_publish_at: string | null;
  interval_codes: string[];
  interval_mode: string;
  channels: string[];
  status: string;
  created_at: string;
  items: BatchItem[];
};

export type Post = {
  id: string;
  category_id: string;
  category_name?: string | null;
  title: string;
  slug: string;
  excerpt: string;
  body_markdown?: string | null;
  body_html?: string | null;
  char_count: number;
  status: string;
  model_id: string;
  adsense_eligible: boolean;
  review_status: string;
  review_notes: string;
  published_at: string | null;
  created_at: string;
  seo_tags: { tag: string; tag_type: string }[];
};

export type PublishJob = {
  id: string;
  post_id: string;
  post_title?: string | null;
  post_slug?: string | null;
  channel_code: string;
  run_at: string;
  status: string;
  attempt: number;
  result_payload?: Record<string, unknown> | null;
  last_error?: string | null;
};

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers || {}),
    },
    cache: "no-store",
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(text || `Request failed: ${res.status}`);
  }
  return res.json() as Promise<T>;
}

export const api = {
  health: () =>
    request<{
      status: string;
      mock_claude: boolean;
      database: string;
      scheduler: string;
      configured_channels?: string[];
    }>("/health"),
  categories: () => request<Category[]>("/api/v1/categories"),
  recommendTopics: (category_id: string) =>
    request<{ batch_recommend_id: string; mock_claude: boolean; topics: Topic[] }>(
      "/api/v1/topics/recommend",
      { method: "POST", body: JSON.stringify({ category_id }) },
    ),
  createBatch: (body: {
    category_id: string;
    topic_suggestion_ids: string[];
    publish_mode: "immediate" | "scheduled";
    first_publish_at?: string | null;
    interval_codes?: string[];
    interval_mode?: "sequential_cycle";
    channels?: string[];
  }) => request<Batch>("/api/v1/batches", { method: "POST", body: JSON.stringify(body) }),
  getBatch: (id: string) => request<Batch>(`/api/v1/batches/${id}`),
  listBatches: () => request<Batch[]>("/api/v1/batches"),
  listPosts: (status?: string) =>
    request<Post[]>(`/api/v1/posts${status ? `?status=${encodeURIComponent(status)}` : ""}`),
  getPost: (id: string) => request<Post>(`/api/v1/posts/${id}`),
  publishNow: (id: string) => request<Post>(`/api/v1/posts/${id}/publish`, { method: "POST" }),
  listJobs: (status?: string) =>
    request<PublishJob[]>(`/api/v1/jobs${status ? `?status=${encodeURIComponent(status)}` : ""}`),
  cancelJob: (id: string) => request<PublishJob>(`/api/v1/jobs/${id}/cancel`, { method: "POST" }),
  publicPosts: () => request<Post[]>("/api/v1/public/posts"),
  publicPost: (slug: string) => {
    let decoded = slug;
    try {
      decoded = decodeURIComponent(slug);
    } catch {
      decoded = slug;
    }
    return request<Post>(`/api/v1/public/posts/${encodeURIComponent(decoded)}`);
  },
};

export { API_BASE };
