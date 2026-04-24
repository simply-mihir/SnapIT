import { useState } from "react";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

const EXPIRY_UNITS = [
  { id: "minutes", label: "Min", hint: "minutes", max: 525600 },
  { id: "hours", label: "Hr",  hint: "hours",   max: 8760   },
  { id: "days",  label: "Day", hint: "days",    max: 3650   },
];

export default function ShortenerForm() {
  const [originalUrl, setOriginalUrl] = useState("");
  const [customAlias, setCustomAlias] = useState("");
  const [expiresInValue, setExpiresInValue] = useState("");
  const [expiresInUnit, setExpiresInUnit] = useState("days");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const [copied, setCopied] = useState(false);

  const currentUnit = EXPIRY_UNITS.find((u) => u.id === expiresInUnit) || EXPIRY_UNITS[2];

  async function handleSubmit(e) {
    e.preventDefault();
    setError(null);
    setResult(null);
    setCopied(false);
    setLoading(true);

    const payload = { original_url: originalUrl };
    if (customAlias.trim()) payload.custom_alias = customAlias.trim();
    if (expiresInValue) {
      payload.expires_in_value = Number(expiresInValue);
      payload.expires_in_unit = expiresInUnit;
    }

    try {
      const res = await fetch(`${API_URL}/api/shorten`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      const body = await res.json().catch(() => ({}));
      if (!res.ok) {
        throw new Error(body.detail || `Request failed (${res.status})`);
      }
      setResult(body);
    } catch (err) {
      setError(err.message || "Something went wrong.");
    } finally {
      setLoading(false);
    }
  }

  async function handleCopy() {
    if (!result?.short_url) return;
    try {
      await navigator.clipboard.writeText(result.short_url);
      setCopied(true);
      setTimeout(() => setCopied(false), 1800);
    } catch {
      /* Older browsers — silent fail. The link remains selectable. */
    }
  }

  return (
    <div className="relative rounded-[28px] border border-ink-900/10 dark:border-cream-100/10 bg-cream-50/70 dark:bg-ink-800/60 backdrop-blur-xl shadow-glass-light dark:shadow-glass p-6 sm:p-8 animate-fade-in">
      {/* subtle top gradient accent */}
      <div
        aria-hidden="true"
        className="pointer-events-none absolute inset-x-0 -top-px h-px bg-gradient-to-r from-transparent via-accent/50 to-transparent"
      />

      <form onSubmit={handleSubmit} className="space-y-5">
        <Field label="Long URL" hint="The link you want to shorten.">
          <input
            type="url"
            required
            placeholder="https://example.com/very/long/path"
            value={originalUrl}
            onChange={(e) => setOriginalUrl(e.target.value)}
            className={inputCls}
          />
        </Field>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-5">
          <Field label="Custom alias" hint="Optional. 3-32 chars.">
            <input
              type="text"
              placeholder="my-link"
              value={customAlias}
              onChange={(e) => setCustomAlias(e.target.value)}
              className={inputCls}
            />
          </Field>
          <Field label="Expires in" hint={`Optional. In ${currentUnit.hint}.`}>
            <div className="flex items-stretch gap-2">
              <input
                type="number"
                min="1"
                max={currentUnit.max}
                placeholder={expiresInUnit === "minutes" ? "30" : expiresInUnit === "hours" ? "12" : "7"}
                value={expiresInValue}
                onChange={(e) => setExpiresInValue(e.target.value)}
                className={inputCls + " flex-1 min-w-0"}
              />
              <div
                role="radiogroup"
                aria-label="Expiration unit"
                className="inline-flex items-center rounded-2xl border border-ink-900/10 dark:border-cream-100/10 bg-cream-50/80 dark:bg-ink-900/50 p-1"
              >
                {EXPIRY_UNITS.map((u) => {
                  const active = u.id === expiresInUnit;
                  return (
                    <button
                      key={u.id}
                      type="button"
                      role="radio"
                      aria-checked={active}
                      onClick={() => setExpiresInUnit(u.id)}
                      className={
                        "px-2.5 py-1.5 rounded-xl text-[11px] font-medium uppercase tracking-widest transition-all " +
                        (active
                          ? "bg-ink-900 text-cream-50 dark:bg-cream-50 dark:text-ink-900 shadow-sm"
                          : "text-ink-700/60 dark:text-cream-100/50 hover:text-ink-900 dark:hover:text-cream-50")
                      }
                    >
                      {u.label}
                    </button>
                  );
                })}
              </div>
            </div>
          </Field>
        </div>

        <button
          type="submit"
          disabled={loading || !originalUrl}
          className="group relative w-full overflow-hidden rounded-2xl bg-ink-900 dark:bg-cream-50 text-cream-50 dark:text-ink-900 font-medium py-3.5 transition-all duration-300 hover:shadow-glow disabled:opacity-40 disabled:cursor-not-allowed"
        >
          <span className={"relative z-10 inline-flex items-center justify-center gap-2 " + (loading ? "opacity-0" : "opacity-100")}>
            Shorten
            <ArrowIcon className="transition-transform duration-300 group-hover:translate-x-0.5" />
          </span>
          {loading && (
            <span className="absolute inset-0 flex items-center justify-center gap-2">
              <Spinner />
              <span>Shortening</span>
            </span>
          )}
          {/* shimmer sweep on hover */}
          <span className="pointer-events-none absolute inset-0 btn-shimmer opacity-0 group-hover:opacity-100 animate-shimmer" />
        </button>
      </form>

      {error && (
        <div
          role="alert"
          className="mt-6 flex items-start gap-3 rounded-2xl border border-red-500/20 bg-red-500/5 dark:bg-red-500/10 px-4 py-3 text-sm text-red-700 dark:text-red-300 animate-fade-in"
        >
          <span className="mt-0.5 inline-flex h-5 w-5 shrink-0 items-center justify-center rounded-full border border-red-500/40 text-[10px]">!</span>
          <span className="leading-snug">{error}</span>
        </div>
      )}

      {result && (
        <div className="mt-7 animate-fade-in">
          <div className="mb-2.5 flex items-center gap-2">
            <span className="h-px flex-1 bg-ink-900/10 dark:bg-cream-100/10" />
            <span className="text-[10px] uppercase tracking-[0.22em] text-ink-700/60 dark:text-cream-100/50">
              your short url
            </span>
            <span className="h-px flex-1 bg-ink-900/10 dark:bg-cream-100/10" />
          </div>

          <div className="rounded-2xl border border-ink-900/10 dark:border-cream-100/10 bg-cream-100/60 dark:bg-ink-900/50 p-4 sm:p-5">
            <div className="flex items-center gap-3">
              <a
                href={result.short_url}
                target="_blank"
                rel="noreferrer"
                className="flex-1 truncate font-mono text-sm sm:text-base text-ink-900 dark:text-cream-50 hover:text-accent-deep dark:hover:text-accent-soft transition-colors"
              >
                {result.short_url}
              </a>
              <button
                onClick={handleCopy}
                className="shrink-0 inline-flex items-center gap-1.5 rounded-xl border border-ink-900/15 dark:border-cream-100/15 bg-cream-50/80 dark:bg-ink-800/80 px-3 py-2 text-xs font-medium hover:bg-cream-100 dark:hover:bg-ink-700 transition-all"
                aria-label={copied ? "Copied" : "Copy short URL"}
              >
                {copied ? (
                  <>
                    <CheckIcon /> Copied
                  </>
                ) : (
                  <>
                    <CopyIcon /> Copy
                  </>
                )}
              </button>
            </div>

            <div className="mt-3 flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-ink-700/60 dark:text-cream-100/50">
              <MetaChip label="Original">
                <span className="truncate max-w-[220px] inline-block align-bottom">
                  {result.original_url}
                </span>
              </MetaChip>
              {result.custom_alias && (
                <MetaChip label="Alias">{result.custom_alias}</MetaChip>
              )}
              {result.expires_at && (
                <MetaChip label="Expires">
                  {new Date(result.expires_at).toLocaleDateString(undefined, {
                    month: "short",
                    day: "numeric",
                    year: "numeric",
                  })}
                </MetaChip>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

/* ——— Small presentational helpers ——— */

function Field({ label, hint, children }) {
  return (
    <label className="block group">
      <div className="mb-2 flex items-baseline justify-between">
        <span className="text-xs font-medium uppercase tracking-[0.14em] text-ink-900/70 dark:text-cream-100/70">
          {label}
        </span>
        {hint && (
          <span className="text-[11px] text-ink-700/50 dark:text-cream-100/40">
            {hint}
          </span>
        )}
      </div>
      {children}
    </label>
  );
}

function MetaChip({ label, children }) {
  return (
    <span className="inline-flex items-center gap-1.5">
      <span className="text-[10px] uppercase tracking-widest text-ink-700/40 dark:text-cream-100/30">
        {label}
      </span>
      <span className="text-ink-900/80 dark:text-cream-100/80 font-mono">
        {children}
      </span>
    </span>
  );
}

function ArrowIcon({ className = "" }) {
  return (
    <svg
      className={className}
      width="16"
      height="16"
      viewBox="0 0 16 16"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      aria-hidden="true"
    >
      <path
        d="M3 8h10m0 0L8.5 3.5M13 8l-4.5 4.5"
        stroke="currentColor"
        strokeWidth="1.6"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

function CopyIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 16 16" fill="none" aria-hidden="true">
      <rect x="5" y="5" width="8" height="8" rx="1.5" stroke="currentColor" strokeWidth="1.4" />
      <path d="M3 11V4.5A1.5 1.5 0 0 1 4.5 3H11" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" />
    </svg>
  );
}

function CheckIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 16 16" fill="none" aria-hidden="true">
      <path d="M3 8.5L6.5 12L13 4.5" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

function Spinner() {
  return (
    <svg className="animate-spin" width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden="true">
      <circle cx="8" cy="8" r="6" stroke="currentColor" strokeOpacity="0.25" strokeWidth="1.6" />
      <path d="M14 8a6 6 0 0 0-6-6" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" />
    </svg>
  );
}

const inputCls =
  "w-full rounded-2xl border border-ink-900/10 dark:border-cream-100/10 " +
  "bg-cream-50/80 dark:bg-ink-900/50 text-ink-900 dark:text-cream-50 " +
  "px-4 py-3.5 text-sm placeholder:text-ink-700/35 dark:placeholder:text-cream-100/30 " +
  "font-mono tracking-tight " +
  "focus:outline-none focus:border-accent/60 focus:shadow-glow " +
  "transition-all duration-200";
