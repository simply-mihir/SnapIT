import ShortenerForm from "../components/ShortenerForm";
import ThemeToggle from "../components/ThemeToggle";

export default function Home() {
  return (
    <div className="relative min-h-screen grain overflow-hidden">
      {/* Ambient background halos — rendered behind everything */}
      <div className="halo halo-a animate-blob" aria-hidden="true" />
      <div className="halo halo-b animate-blob" aria-hidden="true" />

      <main className="relative z-10 min-h-screen flex flex-col">
        {/* ——— Navigation ——— */}
        <nav className="w-full px-6 sm:px-10 py-6 flex items-center justify-between">
          <a href="/" className="group flex items-baseline gap-3">
            <span
              className="font-serif text-3xl sm:text-4xl font-black tracking-tight
                         bg-gradient-to-br from-amber-500 via-orange-500 to-rose-500
                         bg-clip-text text-transparent
                         drop-shadow-[0_4px_24px_rgba(245,158,11,0.35)]
                         transition-all duration-500
                         group-hover:tracking-normal
                         group-hover:drop-shadow-[0_4px_32px_rgba(245,158,11,0.55)]"
            >
              SnapIT
            </span>
            <span className="font-serif text-3xl sm:text-4xl font-black tracking-tight
                         bg-gradient-to-br from-amber-500 via-orange-500 to-rose-500
                         bg-clip-text text-transparent
                         drop-shadow-[0_4px_24px_rgba(245,158,11,0.35)]
                         transition-all duration-500
                         group-hover:tracking-normal
                         group-hover:drop-shadow-[0_4px_32px_rgba(245,158,11,0.55)]"
            >
              : URL Shortener
            </span>
          </a>
          <ThemeToggle />
        </nav>

        {/* ——— Hero + Form ——— */}
        <section className="flex-1 flex items-center justify-center px-6 sm:px-10 pb-16">
          <div className="w-full max-w-xl">
            <header className="mb-10 text-center animate-fade-in">
              <p className="mb-4 inline-flex items-center gap-2 rounded-full border border-ink-900/10 dark:border-cream-100/10 bg-cream-50/60 dark:bg-ink-800/50 backdrop-blur px-3 py-1 text-[11px] uppercase tracking-[0.18em] text-ink-700 dark:text-cream-200">
                <span className="inline-flex items-center gap-1.5">
                  <span className="h-1.5 w-1.5 rounded-full bg-accent animate-pulse" />
                  cached
                </span>
                <span className="text-ink-700/30 dark:text-cream-100/30">·</span>
                <span className="inline-flex items-center gap-1.5">
                  <span
                    className="h-1.5 w-1.5 rounded-full bg-accent animate-pulse"
                    style={{ animationDelay: "0.5s" }}
                  />
                  rate-limited
                </span>
                <span className="text-ink-700/30 dark:text-cream-100/30">·</span>
                <span className="inline-flex items-center gap-1.5">
                  <span
                    className="h-1.5 w-1.5 rounded-full bg-accent animate-pulse"
                    style={{ animationDelay: "1s" }}
                  />
                  analytics
                </span>
              </p>
              <h1 className="headline font-serif text-6xl sm:text-7xl leading-[0.95] tracking-tightest">
                Snap your links
                <br />
                <span className="italic text-accent-deep dark:text-accent-soft">short</span> &amp; sweet.
              </h1>
              <p className="mt-5 text-base text-ink-700/80 dark:text-cream-100/60 max-w-md mx-auto">
                Custom aliases, flexible expiration, and instant redirects —
                all backed by Redis caching.
              </p>
            </header>

            <ShortenerForm />

            <footer className="mt-12 text-center text-xs text-ink-700/50 dark:text-cream-100/40 tracking-wide">
              Built with FastAPI · PostgreSQL · Redis · Next.js
            </footer>
          </div>
        </section>
      </main>
    </div>
  );
}