import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/router";
import Layout from "../components/Layout";
import { useAuth } from "../context/AuthContext";
import { api } from "../lib/api";
import { ErrorBox, Eyebrow, Field, Spinner, cardCls, inputCls, primaryBtnCls } from "../components/ui";

export default function LoginPage() {
  const router = useRouter();
  const { user, ready, signIn } = useAuth();
  const [mode, setMode] = useState("login"); // "login" | "register"
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [googleClientId, setGoogleClientId] = useState(null);

  // Already signed in → straight to history.
  useEffect(() => {
    if (ready && user) router.replace("/history");
  }, [ready, user, router]);

  useEffect(() => {
    api("/api/auth/config")
      .then((c) => setGoogleClientId(c.google_client_id))
      .catch(() => {});
  }, []);

  async function handleSubmit(e) {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      const res = await api(`/api/auth/${mode === "login" ? "login" : "register"}`, {
        method: "POST",
        body: { username, password },
      });
      signIn(res);
      router.push("/history");
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  async function handleGoogle(credential) {
    setError(null);
    try {
      const res = await api("/api/auth/google", { method: "POST", body: { credential } });
      signIn(res);
      router.push("/history");
    } catch (err) {
      setError(err.message);
    }
  }

  const isLogin = mode === "login";

  return (
    <Layout width="max-w-md">
      <div className="flex min-h-[70vh] flex-col justify-center">
        <header className="mb-8 text-center animate-fade-in">
          <Eyebrow>optional account</Eyebrow>
          <h1 className="headline font-serif text-5xl leading-[1] tracking-tightest">
            {isLogin ? "Welcome " : "Keep your "}
            <span className="italic text-accent-deep dark:text-accent-soft">
              {isLogin ? "back" : "links"}
            </span>
          </h1>
          <p className="mt-4 text-sm text-ink-700/80 dark:text-cream-100/60 max-w-sm mx-auto">
            You never need an account to shorten a link. Sign in only if you want
            a history of your links, with the option to pause and resume them.
          </p>
        </header>

        <div className={cardCls + " p-6 sm:p-8"}>
          <div
            aria-hidden="true"
            className="pointer-events-none absolute inset-x-0 -top-px h-px bg-gradient-to-r from-transparent via-accent/50 to-transparent"
          />

          <div
            role="tablist"
            className="mb-6 grid grid-cols-2 rounded-2xl border border-ink-900/10 dark:border-cream-100/10 bg-cream-50/80 dark:bg-ink-900/50 p-1"
          >
            {[
              ["login", "Sign in"],
              ["register", "Create account"],
            ].map(([id, label]) => (
              <button
                key={id}
                type="button"
                role="tab"
                aria-selected={mode === id}
                onClick={() => {
                  setMode(id);
                  setError(null);
                }}
                className={
                  "py-2 rounded-xl text-[11px] font-medium uppercase tracking-widest transition-all " +
                  (mode === id
                    ? "bg-ink-900 text-cream-50 dark:bg-cream-50 dark:text-ink-900 shadow-sm"
                    : "text-ink-700/60 dark:text-cream-100/50 hover:text-ink-900 dark:hover:text-cream-50")
                }
              >
                {label}
              </button>
            ))}
          </div>

          <form onSubmit={handleSubmit} className="space-y-5">
            <Field label="Username" hint={isLogin ? "Or your Google email." : "3-32 chars."}>
              <input
                type="text"
                required
                autoComplete="username"
                autoCapitalize="none"
                spellCheck={false}
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                placeholder="your-name"
                className={inputCls}
              />
            </Field>
            <Field label="Password" hint={isLogin ? undefined : "At least 8 characters."}>
              <input
                type="password"
                required
                minLength={isLogin ? 1 : 8}
                autoComplete={isLogin ? "current-password" : "new-password"}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••"
                className={inputCls}
              />
            </Field>

            <button type="submit" disabled={loading || !username || !password} className={primaryBtnCls}>
              <span className={"relative z-10 inline-flex items-center justify-center gap-2 " + (loading ? "opacity-0" : "")}>
                {isLogin ? "Sign in" : "Create account"}
              </span>
              {loading && (
                <span className="absolute inset-0 flex items-center justify-center">
                  <Spinner />
                </span>
              )}
            </button>
          </form>

          {googleClientId && (
            <>
              <div className="my-6 flex items-center gap-3">
                <span className="h-px flex-1 bg-ink-900/10 dark:bg-cream-100/10" />
                <span className="text-[10px] uppercase tracking-[0.22em] text-ink-700/60 dark:text-cream-100/50">
                  or
                </span>
                <span className="h-px flex-1 bg-ink-900/10 dark:bg-cream-100/10" />
              </div>
              <GoogleButton clientId={googleClientId} onCredential={handleGoogle} />
            </>
          )}

          {error && (
            <div className="mt-6">
              <ErrorBox>{error}</ErrorBox>
            </div>
          )}
        </div>

        <p className="mt-8 text-center text-xs text-ink-700/50 dark:text-cream-100/40">
          Just want a quick link?{" "}
          <a href="/" className="underline decoration-accent/50 underline-offset-4 hover:text-ink-900 dark:hover:text-cream-50">
            Go back, no sign-in needed
          </a>
        </p>
      </div>
    </Layout>
  );
}

/** Google Identity Services button; hands the ID token to the backend. */
function GoogleButton({ clientId, onCredential }) {
  const ref = useRef(null);
  const cbRef = useRef(onCredential);
  cbRef.current = onCredential;

  useEffect(() => {
    let cancelled = false;

    function render() {
      if (cancelled || !window.google?.accounts?.id || !ref.current) return;
      window.google.accounts.id.initialize({
        client_id: clientId,
        callback: (resp) => cbRef.current(resp.credential),
      });
      window.google.accounts.id.renderButton(ref.current, {
        theme: document.documentElement.classList.contains("dark") ? "filled_black" : "outline",
        size: "large",
        shape: "pill",
        text: "continue_with",
        width: 300,
      });
    }

    if (window.google?.accounts?.id) {
      render();
    } else {
      let script = document.getElementById("google-gsi");
      if (!script) {
        script = document.createElement("script");
        script.id = "google-gsi";
        script.src = "https://accounts.google.com/gsi/client";
        script.async = true;
        document.body.appendChild(script);
      }
      script.addEventListener("load", render);
    }
    return () => {
      cancelled = true;
    };
  }, [clientId]);

  return <div ref={ref} className="flex justify-center min-h-[44px]" />;
}
