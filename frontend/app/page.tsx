'use client';

import { useCallback, useEffect, useMemo, useState } from 'react';
import { createClient } from '@supabase/supabase-js';
import { ArrowDownUp, ArrowUpRight, CalendarDays, Check, ChevronDown, CircleAlert, Clock3, ExternalLink, Filter, LoaderCircle, Search, X, Zap } from 'lucide-react';

type Article = {
  id: string;
  source_url: string;
  source_name: string | null;
  discovery_method: 'RSS' | 'ACTIVE_SEARCH' | string | null;
  search_query_used: string | null;
  published_at: string | null;
  scraped_at: string | null;
  iso_week: string | null;
  region_group: string | null;
  secondary_regions: string[] | null;
  country_code: string | null;
  original_language: string | null;
  category_tags: string[] | null;
  mentioned_entities: string[] | null;
  importance_score: number | null;
  title_original: string | null;
  title_en: string | null;
  summary_bullets_en: string[] | null;
  strategic_implication_en: string | null;
};
type ArticleText = { full_text_original: string | null; full_text_en: string | null };
type ViewMode = 'side' | 'english' | 'original';

const REGIONS = ['KR', 'JP', 'TW', 'SG', 'SEA', 'AU_NZ', 'MENA', 'MX', 'BR', 'ZA'];
const TAGS = ['#CPO_Network', '#eMSP_Roaming', '#Policy_Subsidy', '#Hardware_Tech', '#Grid_Energy', '#OEM_Initiative', '#Partnership_MnA'];
const FEED_COLUMNS = 'id,source_url,source_name,discovery_method,search_query_used,published_at,scraped_at,iso_week,region_group,secondary_regions,country_code,original_language,category_tags,mentioned_entities,importance_score,title_original,title_en,summary_bullets_en,strategic_implication_en';
const FLAGS: Record<string, string> = { KR: '🇰🇷', JP: '🇯🇵', TW: '🇹🇼', SG: '🇸🇬', TH: '🇹🇭', ID: '🇮🇩', VN: '🇻🇳', MY: '🇲🇾', AU: '🇦🇺', NZ: '🇳🇿', AE: '🇦🇪', SA: '🇸🇦', QA: '🇶🇦', EG: '🇪🇬', IL: '🇮🇱', MX: '🇲🇽', BR: '🇧🇷', ZA: '🇿🇦' };
const REGION_NAMES: Record<string, string> = { KR: 'South Korea', JP: 'Japan', TW: 'Taiwan', SG: 'Singapore', SEA: 'Southeast Asia', AU_NZ: 'Australia & NZ', MENA: 'Middle East & North Africa', MX: 'Mexico', BR: 'Brazil', ZA: 'South Africa' };
const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL;
const supabaseKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;
const supabase = supabaseUrl && supabaseKey ? createClient(supabaseUrl, supabaseKey) : null;

function dateLabel(value: string | null) {
  if (!value) return 'Date unavailable';
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? 'Date unavailable' : new Intl.DateTimeFormat('en', { day: '2-digit', month: 'short', year: 'numeric' }).format(date);
}
function flagFor(code: string | null) { return code ? FLAGS[code.toUpperCase()] ?? '🌐' : '🌐'; }
function searchableText(article: Article) {
  return [article.title_en, ...(article.summary_bullets_en ?? []), ...(article.mentioned_entities ?? [])].filter(Boolean).join(' ').toLocaleLowerCase();
}

export default function Dashboard() {
  const [articles, setArticles] = useState<Article[]>([]);
  const [loading, setLoading] = useState(true);
  const [feedError, setFeedError] = useState('');
  const [region, setRegion] = useState('All');
  const [tags, setTags] = useState<string[]>([]);
  const [timeframe, setTimeframe] = useState('All');
  const [fromDate, setFromDate] = useState('');
  const [toDate, setToDate] = useState('');
  const [search, setSearch] = useState('');
  const [activeArticle, setActiveArticle] = useState<Article | null>(null);
  const [articleText, setArticleText] = useState<ArticleText | null>(null);
  const [readerLoading, setReaderLoading] = useState(false);
  const [readerError, setReaderError] = useState('');
  const [viewMode, setViewMode] = useState<ViewMode>('side');

  useEffect(() => {
    if (!supabase) { setLoading(false); return; }
    let cancelled = false;
    (async () => {
      try {
        const { data, error } = await supabase.from('ev_charging_articles').select(FEED_COLUMNS).order('published_at', { ascending: false }).limit(500);
        if (cancelled) return;
        if (error) setFeedError(error.message);
        else setArticles((data ?? []) as unknown as Article[]);
      } catch (error) {
        if (!cancelled) setFeedError(error instanceof Error ? error.message : String(error));
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => { cancelled = true; };
  }, []);

  const weeks = useMemo(() => Array.from(new Set(articles.map((article) => article.iso_week).filter((week): week is string => Boolean(week)))).sort().reverse(), [articles]);
  const filteredArticles = useMemo(() => {
    const query = search.trim().toLocaleLowerCase();
    const now = Date.now();
    // ponytail: client-side filter over 500 rows; server-side PostgREST filters when data grows
    return articles.filter((article) => {
      if (region !== 'All' && article.region_group !== region) return false;
      if (tags.length && !tags.some((tag) => article.category_tags?.includes(tag))) return false;
      if (timeframe === 'Last 7 Days' || timeframe === 'Last 30 Days') {
        const date = article.published_at ? new Date(article.published_at).getTime() : NaN;
        const days = timeframe === 'Last 7 Days' ? 7 : 30;
        if (!Number.isFinite(date) || date < now - days * 86400000 || date > now) return false;
      } else if (timeframe !== 'All' && timeframe !== 'Custom Date Range' && article.iso_week !== timeframe) return false;
      if (timeframe === 'Custom Date Range' && article.published_at) {
        const date = article.published_at.slice(0, 10);
        if (fromDate && date < fromDate) return false;
        if (toDate && date > toDate) return false;
      } else if (timeframe === 'Custom Date Range' && (fromDate || toDate)) return false;
      if (query && !searchableText(article).includes(query)) return false;
      return true;
    });
  }, [articles, region, tags, timeframe, fromDate, toDate, search]);

  const openReader = useCallback(async (article: Article) => {
    setActiveArticle(article);
    setArticleText(null);
    setReaderError('');
    setReaderLoading(true);
    setViewMode('side');
    if (!supabase) { setReaderLoading(false); setReaderError('Supabase env not configured.'); return; }
    try {
      const { data, error } = await supabase.from('ev_charging_articles').select('full_text_original,full_text_en').eq('id', article.id).single();
      if (error) setReaderError(error.message);
      else setArticleText(data as ArticleText);
    } catch (error) {
      setReaderError(error instanceof Error ? error.message : String(error));
    } finally {
      setReaderLoading(false);
    }
  }, []);

  const closeReader = useCallback(() => { setActiveArticle(null); setArticleText(null); setReaderError(''); }, []);
  useEffect(() => {
    if (!activeArticle) return;
    const onKeyDown = (event: KeyboardEvent) => { if (event.key === 'Escape') closeReader(); };
    window.addEventListener('keydown', onKeyDown);
    return () => window.removeEventListener('keydown', onKeyDown);
  }, [activeArticle, closeReader]);

  const toggleTag = (tag: string) => setTags((selected) => selected.includes(tag) ? selected.filter((item) => item !== tag) : [...selected, tag]);
  const resetFilters = () => { setRegion('All'); setTags([]); setTimeframe('All'); setFromDate(''); setToDate(''); setSearch(''); };

  return <main className="min-h-screen bg-ink text-slate-100">
    <div className="pointer-events-none fixed inset-0 bg-[radial-gradient(ellipse_at_top_right,rgba(27,85,76,.13),transparent_44%)]" />
    <div className="relative mx-auto max-w-[1440px] px-4 pb-20 pt-7 sm:px-8 lg:px-12">
      <header className="mb-8 flex flex-col justify-between gap-6 border-b border-line pb-7 md:flex-row md:items-end">
        <div>
          <div className="mb-3 inline-flex items-center gap-2 rounded-full border border-accent/20 bg-accent/[0.07] px-3 py-1 text-[10px] font-bold uppercase tracking-[.2em] text-accent"><Zap size={12} /> Regional intelligence archive</div>
          <h1 className="text-balance text-3xl font-semibold tracking-[-.04em] text-white sm:text-4xl">EV Charging Market Intelligence</h1>
          <p className="mt-2 max-w-3xl text-sm leading-6 text-muted">News and strategic signals across Korea, Japan, Taiwan, Southeast Asia, ANZ, MENA, Mexico, Brazil and South Africa.</p>
        </div>
        <div className="flex items-center gap-3 self-start rounded-xl border border-line bg-panel/80 px-4 py-3 md:self-auto"><span className="relative flex h-2.5 w-2.5"><span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-accent opacity-30"/><span className="relative inline-flex h-2.5 w-2.5 rounded-full bg-accent"/></span><div><div className="text-[10px] font-semibold uppercase tracking-[.16em] text-muted">Archive status</div><div className="mt-0.5 text-xs font-medium text-slate-200">{loading ? 'Connecting to archive' : feedError ? 'Connection issue' : 'Live feed'}</div></div></div>
      </header>

      {!supabase && <div role="status" className="mb-6 flex items-start gap-3 rounded-xl border border-amber-400/30 bg-amber-400/[0.08] p-4 text-sm text-amber-100"><CircleAlert className="mt-0.5 shrink-0 text-amber-300" size={18}/><div><strong className="font-semibold">Supabase env not configured</strong><p className="mt-1 text-amber-100/75">Add NEXT_PUBLIC_SUPABASE_URL and NEXT_PUBLIC_SUPABASE_ANON_KEY to load the archive.</p></div></div>}
      {feedError && <div role="alert" className="mb-6 flex items-start gap-3 rounded-xl border border-rose-400/30 bg-rose-400/[0.08] p-4 text-sm text-rose-100"><CircleAlert className="mt-0.5 shrink-0" size={18}/><div><strong>Could not load articles</strong><p className="mt-1 break-words text-rose-100/75">{feedError}</p></div></div>}

      <section aria-label="Article filters" className="mb-7 rounded-2xl border border-line bg-panel/80 p-4 shadow-glow sm:p-5">
        <div className="mb-4 flex flex-wrap items-center justify-between gap-3"><div className="flex items-center gap-2 text-sm font-semibold text-slate-100"><Filter size={15} className="text-accent"/> Refine intelligence</div><button onClick={resetFilters} className="inline-flex min-h-9 items-center gap-1.5 rounded-lg px-2.5 text-xs font-medium text-muted transition hover:bg-white/5 hover:text-white"><X size={13}/> Clear filters</button></div>
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-[1fr_1fr_1.15fr_1.45fr]">
          <label className="relative block"><span className="mb-1.5 block text-[10px] font-bold uppercase tracking-[.15em] text-muted">Market</span><select value={region} onChange={(event) => setRegion(event.target.value)} className="h-11 w-full appearance-none rounded-lg border border-line bg-[#0b1219] px-3 pr-9 text-sm text-slate-100 outline-none transition focus:border-accent/60"><option>All</option>{REGIONS.map((item) => <option key={item} value={item}>{item} · {REGION_NAMES[item]}</option>)}</select><ChevronDown size={15} className="pointer-events-none absolute bottom-3 right-3 text-muted"/></label>
          <label className="relative block"><span className="mb-1.5 block text-[10px] font-bold uppercase tracking-[.15em] text-muted">Timeframe</span><select value={timeframe} onChange={(event) => setTimeframe(event.target.value)} className="h-11 w-full appearance-none rounded-lg border border-line bg-[#0b1219] px-3 pr-9 text-sm text-slate-100 outline-none transition focus:border-accent/60"><option>All</option><option>Last 7 Days</option><option>Last 30 Days</option><option>Custom Date Range</option>{weeks.map((week) => <option value={week} key={week}>{week}</option>)}</select><ChevronDown size={15} className="pointer-events-none absolute bottom-3 right-3 text-muted"/></label>
          <div className="relative block sm:col-span-2 lg:col-span-1"><label htmlFor="article-search" className="mb-1.5 block text-[10px] font-bold uppercase tracking-[.15em] text-muted">Search coverage</label><Search size={16} className="absolute bottom-3.5 left-3 text-muted"/><input id="article-search" type="search" value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Title, summary, entity..." className="h-11 w-full rounded-lg border border-line bg-[#0b1219] pl-9 pr-3 text-base text-slate-100 outline-none placeholder:text-slate-600 transition focus:border-accent/60 sm:text-sm"/></div>
          <div className="flex items-end"><div className="grid w-full grid-cols-2 gap-2">{timeframe === 'Custom Date Range' ? <><label className="min-w-0"><span className="mb-1.5 block text-[10px] font-bold uppercase tracking-[.15em] text-muted">From</span><input aria-label="Start date" type="date" value={fromDate} onChange={(event) => setFromDate(event.target.value)} className="h-11 w-full min-w-0 rounded-lg border border-line bg-[#0b1219] px-2 text-base text-slate-200 outline-none focus:border-accent/60 sm:text-sm"/></label><label className="min-w-0"><span className="mb-1.5 block text-[10px] font-bold uppercase tracking-[.15em] text-muted">To</span><input aria-label="End date" type="date" value={toDate} onChange={(event) => setToDate(event.target.value)} className="h-11 w-full min-w-0 rounded-lg border border-line bg-[#0b1219] px-2 text-base text-slate-200 outline-none focus:border-accent/60 sm:text-sm"/></label></> : <div className="col-span-2 flex h-11 items-center gap-2 rounded-lg border border-line/70 bg-[#0b1219]/60 px-3 text-xs text-muted"><CalendarDays size={14} className="text-accent/80"/> Filter by week or publication date</div>}</div></div>
        </div>
        <div className="mt-4 border-t border-line/70 pt-4"><div className="mb-2.5 text-[10px] font-bold uppercase tracking-[.15em] text-muted">Intelligence categories <span className="ml-1 font-normal normal-case tracking-normal text-slate-600">(select multiple)</span></div><div className="flex flex-wrap gap-2">{TAGS.map((tag) => { const selected = tags.includes(tag); return <button key={tag} onClick={() => toggleTag(tag)} aria-pressed={selected} className={`inline-flex min-h-8 items-center gap-1.5 rounded-md border px-2.5 text-[11px] font-medium transition ${selected ? 'border-accent/40 bg-accent/10 text-accent' : 'border-line bg-[#0b1219] text-slate-400 hover:border-slate-500 hover:text-slate-200'}`}>{selected && <Check size={11}/>} {tag}</button>; })}</div></div>
      </section>

      <div className="mb-4 flex flex-wrap items-center justify-between gap-2"><div className="text-sm font-medium text-slate-300">Latest intelligence <span className="ml-1.5 rounded-md bg-white/[0.06] px-2 py-1 text-xs text-muted">{loading ? '…' : filteredArticles.length}</span></div><div className="inline-flex items-center gap-1.5 text-[11px] text-slate-500"><ArrowDownUp size={13}/> Sorted by publication date</div></div>
      {loading && <div className="flex min-h-48 items-center justify-center gap-3 text-sm text-muted"><LoaderCircle size={18} className="animate-spin text-accent"/> Loading market signals…</div>}
      {!loading && !feedError && filteredArticles.length === 0 && <div className="rounded-2xl border border-dashed border-line bg-panel/45 px-5 py-16 text-center"><div className="mx-auto mb-3 flex h-11 w-11 items-center justify-center rounded-full border border-line bg-[#0b1219] text-muted"><Search size={18}/></div><h2 className="text-base font-semibold text-slate-200">No articles match these filters</h2><p className="mt-1.5 text-sm text-muted">Try broadening your market, timeframe, or search terms.</p><button onClick={resetFilters} className="mt-4 rounded-lg border border-line px-3 py-2 text-xs font-semibold text-accent hover:bg-accent/5">Clear all filters</button></div>}
      <div className="grid gap-4">{!loading && filteredArticles.map((article) => <article key={article.id} role="button" tabIndex={0} onClick={() => void openReader(article)} onKeyDown={(event) => { if (event.key === 'Enter' || event.key === ' ') { event.preventDefault(); void openReader(article); } }} className="group cursor-pointer rounded-2xl border border-line bg-panel/75 p-4 transition duration-200 hover:border-slate-600 hover:bg-panel sm:p-5 lg:p-6">
        <div className="mb-4 flex flex-wrap items-center gap-2"><span className="inline-flex items-center gap-1.5 rounded-md border border-line bg-[#0b1219] px-2 py-1 text-[11px] font-semibold text-slate-200"><span className="text-sm">{flagFor(article.country_code)}</span>{article.region_group || 'Other'}</span><span className="inline-flex items-center gap-1 rounded-md border border-line/80 bg-white/[0.03] px-2 py-1 text-[10px] font-medium text-slate-400">{article.discovery_method === 'RSS' ? '📡 RSS' : '🔍 Active Search'}</span><span className="inline-flex items-center gap-1 rounded-md border border-amber-400/20 bg-amber-300/[0.06] px-2 py-1 text-[11px] font-semibold text-amber-200">★ {article.importance_score ?? '—'}<span className="font-normal text-amber-100/60">/5</span></span><span className="ml-auto inline-flex items-center gap-1.5 text-[11px] text-slate-500"><Clock3 size={12}/>{dateLabel(article.published_at)}</span></div>
        <div className="mb-3 flex flex-wrap gap-1.5">{(article.category_tags ?? []).map((tag) => <span key={tag} className="rounded border border-accent/15 bg-accent/[0.05] px-2 py-1 text-[10px] font-medium text-accent/80">{tag}</span>)}</div>
        <div className="flex items-start justify-between gap-4"><h2 className="max-w-5xl text-lg font-semibold leading-snug tracking-[-.015em] text-slate-100 transition group-hover:text-white sm:text-xl">{article.title_en || article.title_original || 'Untitled article'}</h2><ArrowUpRight size={17} className="mt-1 shrink-0 text-slate-600 transition group-hover:-translate-y-0.5 group-hover:translate-x-0.5 group-hover:text-accent"/></div>
        <div className="mt-2 text-[11px] text-slate-500">{article.source_name || 'Unknown source'}</div>
        {!!article.summary_bullets_en?.length && <ul className="mt-4 space-y-2">{article.summary_bullets_en.map((bullet, index) => <li key={`${index}-${bullet}`} className="flex gap-2.5 text-sm leading-6 text-slate-300"><span className="mt-[9px] h-1 w-1 shrink-0 rounded-full bg-slate-500"/>{bullet}</li>)}</ul>}
        {article.strategic_implication_en && <div className="mt-4 rounded-lg border-l-2 border-accent/70 bg-accent/[0.055] px-4 py-3"><div className="mb-1 text-[10px] font-bold uppercase tracking-[.16em] text-accent">So what</div><p className="text-sm leading-6 text-slate-200/90">{article.strategic_implication_en}</p></div>}
        <div className="mt-4 flex flex-wrap items-center justify-between gap-2 border-t border-line/70 pt-3"><span className="text-xs font-medium text-slate-400">{article.source_name || 'Source unavailable'}</span>{article.iso_week && <span className="text-[10px] font-medium tracking-wide text-slate-600">{article.iso_week}</span>}</div>
      </article>)}</div>

      {activeArticle && <div className="fixed inset-0 z-50 flex items-end justify-center bg-black/75 p-0 backdrop-blur-sm sm:items-center sm:p-5" onMouseDown={(event) => { if (event.target === event.currentTarget) closeReader(); }}><section role="dialog" aria-modal="true" aria-labelledby="reader-title" className="flex max-h-[96vh] w-full max-w-6xl flex-col overflow-hidden rounded-t-2xl border border-line bg-[#0c131b] shadow-2xl sm:max-h-[90vh] sm:rounded-2xl">
        <header className="flex items-start justify-between gap-4 border-b border-line px-4 py-4 sm:px-6"><div className="min-w-0"><div className="mb-2 flex flex-wrap items-center gap-2 text-[10px] font-semibold uppercase tracking-[.12em] text-muted"><span>{flagFor(activeArticle.country_code)} {activeArticle.region_group || 'Other'}</span><span className="text-slate-700">/</span><span>{activeArticle.source_name || 'Source'}</span><span className="text-slate-700">/</span><span>{dateLabel(activeArticle.published_at)}</span></div><h2 id="reader-title" className="line-clamp-2 text-base font-semibold leading-snug text-white sm:text-lg">{activeArticle.title_en || activeArticle.title_original || 'Untitled article'}</h2></div><div className="flex shrink-0 items-center gap-1.5"><a href={activeArticle.source_url} target="_blank" rel="noreferrer" aria-label="Open source article in new tab" className="flex h-9 w-9 items-center justify-center rounded-lg border border-line text-slate-400 transition hover:bg-white/5 hover:text-accent"><ExternalLink size={16}/></a><button onClick={closeReader} aria-label="Close reader" className="flex h-9 w-9 items-center justify-center rounded-lg border border-line text-slate-400 transition hover:bg-white/5 hover:text-white"><X size={17}/></button></div></header>
        <div className="flex flex-wrap items-center justify-between gap-3 border-b border-line/80 px-4 py-3 sm:px-6"><div className="inline-flex rounded-lg border border-line bg-[#080d13] p-1" role="tablist" aria-label="Article text view">{([['side', 'Side-by-Side'], ['english', 'English Only'], ['original', 'Original Only']] as const).map(([mode, label]) => <button key={mode} role="tab" aria-selected={viewMode === mode} onClick={() => setViewMode(mode)} className={`rounded-md px-2.5 py-1.5 text-[11px] font-medium transition sm:px-3 ${viewMode === mode ? 'bg-slate-700/70 text-white' : 'text-muted hover:text-slate-200'}`}>{label}</button>)}</div><div className="text-[10px] text-slate-600">Original language: {activeArticle.original_language || 'Unknown'}</div></div>
        <div className={`min-h-0 flex-1 overflow-auto p-4 sm:p-6 ${viewMode === 'side' ? 'grid gap-4 md:grid-cols-2' : ''}`}>
          {readerLoading && <div className="flex min-h-52 items-center justify-center gap-3 text-sm text-muted"><LoaderCircle size={18} className="animate-spin text-accent"/>Loading full article…</div>}
          {readerError && <div role="alert" className="flex items-start gap-3 rounded-xl border border-rose-400/30 bg-rose-400/[0.08] p-4 text-sm text-rose-100"><CircleAlert size={17} className="mt-0.5 shrink-0"/><div><strong>Could not load the full article</strong><p className="mt-1 break-words text-rose-100/75">{readerError}</p></div></div>}
          {!readerLoading && !readerError && articleText && <>{(viewMode === 'side' || viewMode === 'original') && <section className="min-w-0 rounded-xl border border-line/80 bg-[#080d13]/55 p-4 sm:p-5"><h3 className="mb-3 text-[10px] font-bold uppercase tracking-[.16em] text-muted">Original · {activeArticle.original_language || 'language unknown'}</h3><div className="whitespace-pre-wrap break-words text-sm leading-7 text-slate-300">{articleText.full_text_original || 'No original-language text available.'}</div></section>}{(viewMode === 'side' || viewMode === 'english') && <section className="min-w-0 rounded-xl border border-line/80 bg-[#080d13]/55 p-4 sm:p-5"><h3 className="mb-3 text-[10px] font-bold uppercase tracking-[.16em] text-accent">English translation</h3><div className="whitespace-pre-wrap break-words text-sm leading-7 text-slate-300">{articleText.full_text_en || 'No English translation available.'}</div></section>}</>}
        </div>
      </section></div>}
    </div>
  </main>;
}
