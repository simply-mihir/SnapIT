/* Shared presentational pieces so every page uses the same look. */

export const cardCls =
  "relative rounded-[28px] border border-ink-900/10 dark:border-cream-100/10 " +
  "bg-cream-50/70 dark:bg-ink-800/60 backdrop-blur-xl " +
  "shadow-glass-light dark:shadow-glass animate-fade-in";

export const inputCls =
  "w-full rounded-2xl border border-ink-900/10 dark:border-cream-100/10 " +
  "bg-cream-50/80 dark:bg-ink-900/50 text-ink-900 dark:text-cream-50 " +
  "px-4 py-3.5 text-sm placeholder:text-ink-700/35 dark:placeholder:text-cream-100/30 " +
  "font-mono tracking-tight " +
  "focus:outline-none focus:border-accent/60 focus:shadow-glow " +
  "transition-all duration-200";

export const primaryBtnCls =
  "group relative w-full overflow-hidden rounded-2xl bg-ink-900 dark:bg-cream-50 " +
  "text-cream-50 dark:text-ink-900 font-medium py-3.5 transition-all duration-300 " +
  "hover:shadow-glow disabled:opacity-40 disabled:cursor-not-allowed";

export const pillCls =
  "inline-flex items-center gap-2 rounded-full border border-ink-900/10 dark:border-cream-100/10 " +
  "bg-cream-50/60 dark:bg-ink-800/60 backdrop-blur px-4 py-2 text-xs font-medium " +
  "text-ink-900 dark:text-cream-50 transition-all hover:shadow-glow hover:border-accent/30";

export const smallBtnCls =
  "shrink-0 inline-flex items-center gap-1.5 rounded-xl border border-ink-900/15 dark:border-cream-100/15 " +
  "bg-cream-50/80 dark:bg-ink-800/80 px-3 py-2 text-xs font-medium " +
  "hover:bg-cream-100 dark:hover:bg-ink-700 transition-all disabled:opacity-40 disabled:cursor-not-allowed";

export function Field({ label, hint, children }) {
  return (
    <label className="block group">
      <div className="mb-2 flex items-baseline justify-between">
        <span className="text-xs font-medium uppercase tracking-[0.14em] text-ink-900/70 dark:text-cream-100/70">
          {label}
        </span>
        {hint && (
          <span className="text-[11px] text-ink-700/50 dark:text-cream-100/40">{hint}</span>
        )}
      </div>
      {children}
    </label>
  );
}

export function ErrorBox({ children }) {
  return (
    <div
      role="alert"
      className="flex items-start gap-3 rounded-2xl border border-red-500/20 bg-red-500/5 dark:bg-red-500/10 px-4 py-3 text-sm text-red-700 dark:text-red-300 animate-fade-in"
    >
      <span className="mt-0.5 inline-flex h-5 w-5 shrink-0 items-center justify-center rounded-full border border-red-500/40 text-[10px]">
        !
      </span>
      <span className="leading-snug">{children}</span>
    </div>
  );
}

export function Spinner({ size = 16 }) {
  return (
    <svg className="animate-spin" width={size} height={size} viewBox="0 0 16 16" fill="none" aria-hidden="true">
      <circle cx="8" cy="8" r="6" stroke="currentColor" strokeOpacity="0.25" strokeWidth="1.6" />
      <path d="M14 8a6 6 0 0 0-6-6" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" />
    </svg>
  );
}

export function Eyebrow({ children }) {
  return (
    <p className="mb-4 inline-flex items-center gap-2 rounded-full border border-ink-900/10 dark:border-cream-100/10 bg-cream-50/60 dark:bg-ink-800/50 backdrop-blur px-3 py-1 text-[11px] uppercase tracking-[0.18em] text-ink-700 dark:text-cream-200">
      <span className="h-1.5 w-1.5 rounded-full bg-accent animate-pulse" />
      {children}
    </p>
  );
}
