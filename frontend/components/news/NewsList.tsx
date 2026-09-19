import React, { useState, useMemo } from "react";
import { NewsCard, NewsCardProps } from "./NewsCard";

export interface NewsListProps {
  articles?: NewsCardProps[];
  isLoading?: boolean;
  error?: string | null;
  onRetry?: () => void;
  selectedCategory?: string;
  onSelectCategory?: (category: string) => void;
  categories?: string[];
  searchQuery?: string;
  onSearchChange?: (query: string) => void;
  onArticleClick?: (article: NewsCardProps) => void;
  className?: string;
}

export function NewsList({
  articles = [],
  isLoading = false,
  error = null,
  onRetry,
  selectedCategory = "ALL",
  onSelectCategory,
  categories = ["ALL", "MARKETS", "AI", "CRYPTO", "TECH", "WORLD"],
  searchQuery = "",
  onSearchChange,
  onArticleClick,
  className = "",
}: NewsListProps) {
  const [internalSearch, setInternalSearch] = useState(searchQuery);
  const [internalCategory, setInternalCategory] = useState(selectedCategory);

  const activeSearch = searchQuery !== undefined ? searchQuery : internalSearch;
  const activeCategory = selectedCategory !== undefined ? selectedCategory : internalCategory;

  const handleSearchInput = (e: React.ChangeEvent<HTMLInputElement>) => {
    const val = e.target.value;
    if (onSearchChange) {
      onSearchChange(val);
    } else {
      setInternalSearch(val);
    }
  };

  const handleCategoryClick = (cat: string) => {
    if (onSelectCategory) {
      onSelectCategory(cat);
    } else {
      setInternalCategory(cat);
    }
  };

  // Filter articles based on category and search query if needed and not handled upstream
  const filteredArticles = useMemo(() => {
    return articles.filter((item) => {
      const matchesCategory =
        !activeCategory ||
        activeCategory === "ALL" ||
        (item.category && item.category.toUpperCase() === activeCategory.toUpperCase());

      const matchesSearch =
        !activeSearch ||
        activeSearch.trim() === "" ||
        (item.title && item.title.toLowerCase().includes(activeSearch.toLowerCase())) ||
        (item.headline && item.headline.toLowerCase().includes(activeSearch.toLowerCase())) ||
        (item.description && item.description.toLowerCase().includes(activeSearch.toLowerCase())) ||
        (item.summary && item.summary.toLowerCase().includes(activeSearch.toLowerCase())) ||
        (item.source && item.source.toLowerCase().includes(activeSearch.toLowerCase()));

      return matchesCategory && matchesSearch;
    });
  }, [articles, activeCategory, activeSearch]);

  return (
    <div className={`flex flex-col space-y-6 w-full ${className}`}>
      {/* HUD Header & Intelligence Stream Controls */}
      <div className="relative p-5 sm:p-6 bg-black/85 backdrop-blur-2xl border border-cyan-500/25 rounded-2xl shadow-[0_4px_30px_rgba(6,182,212,0.1)] overflow-hidden">
        {/* Decorative corner brackets and scanlines */}
        <div className="absolute top-0 right-0 w-4 h-4 border-t-2 border-r-2 border-cyan-400/60 pointer-events-none" aria-hidden="true" />
        <div className="absolute bottom-0 left-0 w-4 h-4 border-b-2 border-l-2 border-cyan-400/60 pointer-events-none" aria-hidden="true" />
        <div className="absolute inset-0 bg-[linear-gradient(to_bottom,transparent_98%,rgba(6,182,212,0.02)_100%)] bg-[size:100%_4px] pointer-events-none" aria-hidden="true" />

        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 relative z-10">
          {/* Title and Core Indicator */}
          <div className="flex items-center gap-3.5">
            <div className="relative w-10 h-10 rounded-full bg-cyan-950/80 border border-cyan-500/50 flex items-center justify-center shadow-[0_0_20px_rgba(6,182,212,0.35)] shrink-0">
              <div className="absolute inset-0 rounded-full border border-cyan-400/30 animate-ping opacity-40 pointer-events-none" aria-hidden="true" />
              <div className="w-4 h-4 rounded-full bg-cyan-400 shadow-[0_0_12px_rgba(6,182,212,1)]" />
              <span className="absolute -bottom-1 -right-1 w-2 h-2 rounded-full bg-cyan-300 animate-pulse" />
            </div>

            <div className="flex flex-col">
              <div className="flex items-center gap-2">
                <h2 className="text-base sm:text-lg font-bold font-mono tracking-wider text-white">
                  NEWS INTELLIGENCE
                </h2>
                <span className="text-[10px] font-mono bg-cyan-500/20 text-cyan-300 px-2 py-0.5 rounded border border-cyan-400/40">
                  STREAM ACTIVE
                </span>
              </div>
              <span className="text-[10px] font-mono text-cyan-400/70 tracking-widest uppercase">
                GLOBAL INFORMATION FEED • MONITORING AVAILABLE INTELLIGENCE
              </span>
            </div>
          </div>

          {/* Search Query Control */}
          <div className="relative w-full md:w-72">
            <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-cyan-400/60" aria-hidden="true">
              ⌕
            </div>
            <input
              type="text"
              value={activeSearch}
              onChange={handleSearchInput}
              placeholder="SEARCH INTELLIGENCE..."
              className="w-full pl-9 pr-4 py-2 bg-black/60 border border-cyan-500/30 focus:border-cyan-400 rounded-lg text-xs font-mono text-white placeholder-cyan-500/50 focus:outline-none focus:ring-1 focus:ring-cyan-400 transition-all shadow-[inset_0_0_10px_rgba(6,182,212,0.1)]"
              aria-label="Search intelligence briefings"
            />
          </div>
        </div>

        {/* Categories / Channels Filter Bar */}
        {categories && categories.length > 0 && (
          <div className="mt-5 pt-4 border-t border-cyan-500/20 flex items-center gap-2 overflow-x-auto custom-scrollbar pb-1">
            <span className="text-[10px] font-mono text-cyan-400/60 uppercase tracking-widest shrink-0 mr-1">
              CHANNELS:
            </span>
            {categories.map((cat) => {
              const isSelected = activeCategory.toUpperCase() === cat.toUpperCase();
              return (
                <button
                  key={cat}
                  type="button"
                  onClick={() => handleCategoryClick(cat)}
                  className={`px-3 py-1.5 rounded-lg text-xs font-mono tracking-wider uppercase transition-all shrink-0 border ${
                    isSelected
                      ? "bg-cyan-500/30 border-cyan-400 text-white font-bold shadow-[0_0_15px_rgba(6,182,212,0.35)]"
                      : "bg-black/40 border-cyan-500/20 text-cyan-400/70 hover:bg-cyan-500/10 hover:text-cyan-200 hover:border-cyan-500/40"
                  }`}
                >
                  {cat}
                </button>
              );
            })}
          </div>
        )}
      </div>

      {/* Loading State */}
      {isLoading && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
          {[1, 2, 3, 4, 5, 6].map((n) => (
            <div
              key={n}
              className="bg-black/60 border border-cyan-500/20 rounded-xl p-5 h-72 flex flex-col justify-between animate-pulse relative overflow-hidden"
            >
              <div className="absolute inset-0 bg-[linear-gradient(to_bottom,transparent_98%,rgba(6,182,212,0.04)_100%)] bg-[size:100%_4px] pointer-events-none" />
              <div className="space-y-3">
                <div className="h-3 bg-cyan-950/80 rounded w-1/3 border border-cyan-500/20" />
                <div className="h-32 bg-cyan-950/40 rounded-lg border border-cyan-500/20" />
                <div className="h-4 bg-cyan-950/80 rounded w-3/4 border border-cyan-500/20" />
                <div className="h-3 bg-cyan-950/50 rounded w-1/2 border border-cyan-500/20" />
              </div>
              <div className="h-3 bg-cyan-950/60 rounded w-1/4 border border-cyan-500/20 self-end" />
            </div>
          ))}
        </div>
      )}

      {/* Error State */}
      {!isLoading && error && (
        <div className="p-8 bg-black/85 backdrop-blur-2xl border border-red-500/40 rounded-2xl text-center space-y-4 shadow-[0_0_30px_rgba(239,68,68,0.15)]">
          <div className="w-12 h-12 mx-auto rounded-full bg-red-950/80 border border-red-500/50 flex items-center justify-center text-red-400 font-mono font-bold shadow-[0_0_15px_rgba(239,68,68,0.4)]">
            !
          </div>
          <div className="space-y-1">
            <h3 className="text-base font-bold font-mono text-white tracking-wider">
              INTELLIGENCE FEED ERROR
            </h3>
            <p className="text-xs font-mono text-red-300/80 max-w-md mx-auto">
              {error}
            </p>
          </div>
          {onRetry && (
            <button
              type="button"
              onClick={onRetry}
              className="px-5 py-2 bg-red-950/60 hover:bg-red-900/60 border border-red-500/50 rounded-lg text-xs font-mono text-red-200 transition-all shadow-[0_0_15px_rgba(239,68,68,0.2)]"
            >
              RETRY CONNECTION
            </button>
          )}
        </div>
      )}

      {/* Empty State */}
      {!isLoading && !error && filteredArticles.length === 0 && (
        <div className="p-12 bg-black/85 backdrop-blur-2xl border border-cyan-500/30 rounded-2xl text-center space-y-3 shadow-[0_4px_30px_rgba(6,182,212,0.1)]">
          <div className="w-10 h-10 mx-auto rounded-full bg-cyan-950/80 border border-cyan-500/40 flex items-center justify-center text-cyan-400 font-mono text-sm shadow-[0_0_15px_rgba(6,182,212,0.3)]" aria-hidden="true">
            ◉
          </div>
          <h3 className="text-base font-bold font-mono text-white tracking-wider">
            INTELLIGENCE STREAM EMPTY
          </h3>
          <p className="text-xs font-mono text-cyan-400/70 max-w-sm mx-auto">
            No available intelligence briefings found in this channel or matching your query criteria.
          </p>
        </div>
      )}

      {/* Articles Grid Stream */}
      {!isLoading && !error && filteredArticles.length > 0 && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
          {filteredArticles.map((article, idx) => (
            <NewsCard
              key={article.url || article.title || idx}
              {...article}
              onClick={onArticleClick ? () => onArticleClick(article) : article.onClick}
            />
          ))}
        </div>
      )}
    </div>
  );
}
