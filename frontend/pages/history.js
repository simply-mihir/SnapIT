import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/router";
import Layout from "../components/Layout";
import { useAuth } from "../context/AuthContext";
import { api } from "../lib/api";
import { ErrorBox, Eyebrow, Spinner, cardCls, smallBtnCls } from "../components/ui";

function fmtDate(iso) {
  return new Date(iso).toLocaleDateString(undefined, { month: "short", day: "numeric", year: "numeric" });
}

export default function HistoryPage() {
  const router = useRouter();
  const { token, user, ready } = useAuth();
  const [links, setLinks] = useState(null);
  const [error, setError] = useState(null);
  const [busyId, setBusyId] = useState(null);

  // Accounts are optional, but this page needs one.
  useEffect(() => {
    if (ready && !user) router.replace("/login");
  }, [ready, user, router]);

  const load = useCallback(async () => {
    setError(null);
    try {
      const data = await api("/api/me/links", { token });
      setLinks(data.items);
    } catch (err) {
      if (err.status === 401) router.replace("/login");
      else setError(err.message);
    }
  }, [token, router]);

  useEffect(() => {
    if (token) load();
  }, [token, load]);

  async function toggle(link) {
    setBusyId(link.short_id);
    setError(null);
    try {
      const updated = await api(`/api/links/${encodeURIComponent(link.short_id)}`, {
        method: "PATCH",
        token,
        body: { is_active: !link.is_active },
      });
      setLinks((ls) => ls.map((l) => (l.short_id === link.short_id ? { ...l, ...updated } : l)));
    } catch (err) {
      setError(err.message);
    } finally {
      setBusyId(null);
    }
  }

  return (
    <Layout width="max-w-3xl">
      <header className="mb-8 text-center animate-fade-in">
        <Eyebrow>your links</Eyebrow>
        <h1 className="headline font-serif text-5xl sm:text-6xl leading-[1] tracking-tightest">
          Link <span className="italic text-accent-deep dark:text-accent-soft">history</span>
        </h1>
        <p className="mt-4 text-sm text-ink-700/80 dark:text-cream-100/60 max-w-md mx-auto">
          Links you create while signed in show up here. Pause one and anyone
          opening it is turned away, resume it whenever you like.
        </p>
      </header>

      {error && (
        <div className="mb-5">
          <ErrorBox>{error}</ErrorBox>
        </div>
      )}

      {links === null && !error && (
        <div className="flex justify-center py-16 text-ink-700/60 dark:text-cream-100/50">
          <Spinner size={22} />
        </div>
      )}

      {links && links.length === 0 && (
        <div className={cardCls + " p-8 text-center"}>
          <p className="text-sm text-ink-700/80 dark:text-cream-100/60">
            No links yet. Shorten one while signed in and it will appear here.
          </p>
          <Link
            href="/"
            className="mt-5 inline-flex rounded-2xl bg-ink-900 dark:bg-cream-50 text-cream-50 dark:text-ink-900 px-5 py-2.5 text-sm font-medium transition-all hover:shadow-glow"
          >
            Shorten a link
          </Link>
        </div>
      )}

      {links && links.length > 0 && (
        <ul className="space-y-3">
          {links.map((link) => (
            <LinkRow key={link.short_id} link={link} busy={busyId === link.short_id} onToggle={() => toggle(link)} />
          ))}
        </ul>
      )}
    </Layout>
  );
}

function LinkRow({ link, busy, onToggle }) {
  const [copied, setCopied] = useState(false);
  const dimmed = !link.is_active || link.is_expired;

  async function copy() {
    try {
      await navigator.clipboard.writeText(link.short_url);
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    } catch {}
  }

  return (
    <li className={cardCls + " p-4 sm:p-5"}>
      <div className="flex flex-wrap items-center gap-3">
        <div className={"min-w-0 flex-1 " + (dimmed ? "opacity-60" : "")}>
          <div className="flex items-center gap-2.5">
            <a
              href={link.short_url}
              target="_blank"
              rel="noreferrer"
              className="truncate font-mono text-sm sm:text-base text-ink-900 dark:text-cream-50 hover:text-accent-deep dark:hover:text-accent-soft transition-colors"
            >
              {link.short_url.replace(/^https?:\/\//, "")}
            </a>
            <StatusChip link={link} />
          </div>
          <p className="mt-1 truncate text-xs text-ink-700/60 dark:text-cream-100/50" title={link.original_url}>
            {link.original_url}
          </p>
        </div>

        <div className="flex items-center gap-2">
          <button onClick={copy} className={smallBtnCls}>
            {copied ? "Copied" : "Copy"}
          </button>
          <button
            onClick={onToggle}
            disabled={busy}
            aria-label={link.is_active ? "Pause link" : "Resume link"}
            className={smallBtnCls + " min-w-[84px] justify-center"}
          >
            {busy ? <Spinner size={14} /> : link.is_active ? "Pause" : "Resume"}
          </button>
        </div>
      </div>

      <div className="mt-3 flex flex-wrap items-center gap-x-5 gap-y-1 text-xs text-ink-700/60 dark:text-cream-100/50">
        <Meta label="Created">{fmtDate(link.created_at)}</Meta>
        <Meta label="Clicks">{link.click_count}</Meta>
        {link.expires_at && <Meta label="Expires">{fmtDate(link.expires_at)}</Meta>}
      </div>
    </li>
  );
}

function StatusChip({ link }) {
  let label = "Active";
  let cls = "border-accent/40 text-accent-deep dark:text-accent-soft bg-accent/10";
  let dot = "bg-accent";
  if (link.is_expired) {
    label = "Expired";
    cls = "border-red-500/30 text-red-700 dark:text-red-300 bg-red-500/5";
    dot = "bg-red-500";
  } else if (!link.is_active) {
    label = "Paused";
    cls = "border-ink-900/20 dark:border-cream-100/20 text-ink-700 dark:text-cream-100/70 bg-ink-900/5 dark:bg-cream-100/5";
    dot = "bg-ink-500 dark:bg-cream-300";
  }
  return (
    <span className={`shrink-0 inline-flex items-center gap-1.5 rounded-full border px-2 py-0.5 text-[10px] uppercase tracking-widest ${cls}`}>
      <span className={`h-1.5 w-1.5 rounded-full ${dot}`} />
      {label}
    </span>
  );
}

function Meta({ label, children }) {
  return (
    <span className="inline-flex items-center gap-1.5">
      <span className="text-[10px] uppercase tracking-widest text-ink-700/40 dark:text-cream-100/30">{label}</span>
      <span className="text-ink-900/80 dark:text-cream-100/80 font-mono">{children}</span>
    </span>
  );
}
