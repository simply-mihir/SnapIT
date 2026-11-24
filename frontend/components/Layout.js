import Link from "next/link";
import ThemeToggle from "./ThemeToggle";
import { useAuth } from "../context/AuthContext";
import { pillCls } from "./ui";

/**
 * Shared page chrome — ambient background + top nav — so every page
 * (home, login, history) has the same look.
 */
export default function Layout({ children, width = "max-w-xl" }) {
  const { user, ready, signOut } = useAuth();

  return (
    <div className="relative min-h-screen grain overflow-hidden">
      <div className="halo halo-a animate-blob" aria-hidden="true" />
      <div className="halo halo-b animate-blob" aria-hidden="true" />
      <div className="halo halo-c animate-blob" aria-hidden="true" style={{ animationDelay: "2s" }} />
      <div className="halo halo-d animate-blob" aria-hidden="true" style={{ animationDelay: "4s" }} />
      <div className="halo halo-e animate-blob" aria-hidden="true" style={{ animationDelay: "6s" }} />

      <main className="relative z-10 min-h-screen flex flex-col">
        <nav className="w-full px-6 sm:px-10 py-6 flex items-center justify-between gap-3">
          <Link
            href="/"
            className="group inline-flex items-center gap-3 rounded-full
                       border border-ink-900/10 dark:border-cream-100/10
                       bg-cream-50/40 dark:bg-ink-800/30 backdrop-blur-md
                       px-4 sm:px-5 py-2 shadow-sm transition-all duration-300
                       hover:shadow-md hover:bg-cream-50/70 dark:hover:bg-ink-800/50
                       hover:border-accent/30"
          >
            <span className="font-serif text-xl sm:text-2xl tracking-tight text-ink-900 dark:text-cream-50 leading-none">
              Snap<span className="italic text-accent-deep dark:text-accent-soft font-normal">IT</span>
            </span>
            <span className="hidden sm:block h-4 w-px bg-ink-900/15 dark:bg-cream-100/15" />
            <span className="hidden sm:block text-[10px] uppercase tracking-[0.3em] font-light text-ink-700/60 dark:text-cream-100/60">
              URL Shortener
            </span>
          </Link>

          <div className="flex items-center gap-2 sm:gap-3">
            {ready && user && (
              <>
                <Link href="/history" className={pillCls}>
                  History
                </Link>
                <span
                  className="hidden sm:inline-flex max-w-[140px] truncate text-xs text-ink-700/70 dark:text-cream-100/60"
                  title={user.display_name || user.username || user.email}
                >
                  {user.display_name || user.username || user.email}
                </span>
                <button onClick={signOut} className={pillCls}>
                  Sign out
                </button>
              </>
            )}
            {ready && !user && (
              <Link href="/login" className={pillCls}>
                Sign in
              </Link>
            )}
            <ThemeToggle />
          </div>
        </nav>

        <section className="flex-1 flex justify-center px-6 sm:px-10 pb-16">
          <div className={`w-full ${width}`}>{children}</div>
        </section>
      </main>
    </div>
  );
}
