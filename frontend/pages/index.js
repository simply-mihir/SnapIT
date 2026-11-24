import ShortenerForm from "../components/ShortenerForm";
import Layout from "../components/Layout";

export default function Home() {
  return (
    <Layout>
      <div className="flex min-h-[70vh] flex-col justify-center">
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
    </Layout>
  );
}
