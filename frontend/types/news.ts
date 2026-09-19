// Fast/frontend/types/news.ts
// News data contracts for KING ZARRY AI web frontend.
// Types only. No React, logic, API calls, or side effects.

/**
 * Common news categories.
 */
export type NewsCategory =
  | "market"
  | "crypto"
  | "forex"
  | "stocks"
  | "economy"
  | "technology"
  | "politics"
  | "business"
  | "general"
  | string;

/**
 * Core news article contract.
 */
export interface NewsArticle {
  id: string | number;

  title: string;
  headline?: string | null;

  summary?: string | null;
  description?: string | null;
  content?: string | null;

  source?: string | null;
  source_name?: string | null;

  author?: string | null;

  category?: NewsCategory | null;

  url?: string | null;
  link?: string | null;

  image_url?: string | null;
  image?: string | null;
  thumbnail?: string | null;

  published_at?: string | null;
  publishedAt?: string | null;
  created_at?: string | null;
  updated_at?: string | null;

  /**
   * AI-generated fields are optional because they should
   * only be displayed when actually provided by the backend.
   */
  ai_summary?: string | null;
  aiSummary?: string | null;
  ai_analysis?: string | null;
  aiAnalysis?: string | null;

  sentiment?: string | null;
  relevance?: number | null;
  impact?: string | null;

  tags?: string[] | null;

  featured?: boolean;
  breaking?: boolean;

  loading?: boolean;
  isLoading?: boolean;
  error?: string | null;
}

/**
 * Alias used by components that refer to individual
 * news items rather than articles.
 */
export type NewsItem = NewsArticle;

/**
 * News feed response.
 */
export interface NewsResponse {
  articles: NewsArticle[];

  total?: number;
  page?: number;
  page_size?: number;
  pageSize?: number;

  has_more?: boolean;
  hasMore?: boolean;

  next_page?: number | null;
  nextPage?: number | null;

  status?: string;
  message?: string;
}

/**
 * Search/filter parameters for a news feed.
 */
export interface NewsQuery {
  query?: string;
  category?: NewsCategory;
  source?: string;
  page?: number;
  page_size?: number;
  pageSize?: number;
  limit?: number;
}

/**
 * News category/filter option.
 */
export interface NewsCategoryOption {
  value: string;
  label: string;
}

/**
 * News feed state.
 */
export interface NewsState {
  articles: NewsArticle[];
  isLoading: boolean;
  error: string | null;

  query?: string;
  category?: NewsCategory | null;

  page?: number;
  hasMore?: boolean;
}

/**
 * Lightweight news item used by lists, cards,
 * search results, and featured sections.
 */
export interface NewsListItem extends NewsArticle {
  title: string;
}
