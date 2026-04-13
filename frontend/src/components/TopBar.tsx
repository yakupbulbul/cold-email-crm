import { Bell, ChevronDown, Search, User } from "lucide-react";
import { useRouter } from "next/navigation";
import { useMemo, useState } from "react";

import { useAuth } from "@/context/AuthContext";

export default function TopBar({
  title,
  menuButton,
}: {
  title: string;
  menuButton?: React.ReactNode;
}) {
  const { user } = useAuth();
  const router = useRouter();
  const [query, setQuery] = useState("");
  const [focused, setFocused] = useState(false);

  const workspaceTargets = useMemo(
    () => [
      { label: "Dashboard", href: "/" },
      { label: "Domains", href: "/domains" },
      { label: "Mailboxes", href: "/mailboxes" },
      { label: "Campaigns", href: "/campaigns" },
      { label: "Contacts", href: "/contacts" },
      { label: "Lists", href: "/lists" },
      { label: "Warm-up", href: "/warmup" },
      { label: "Send Email", href: "/send-email" },
      { label: "Inbox", href: "/inbox" },
      { label: "Suppression", href: "/suppression" },
      { label: "Operations", href: "/ops" },
      { label: "Settings", href: "/settings" },
    ],
    [],
  );

  const results = useMemo(() => {
    const normalized = query.trim().toLowerCase();
    if (!normalized) return workspaceTargets;
    return workspaceTargets.filter((target) => target.label.toLowerCase().includes(normalized));
  }, [query, workspaceTargets]);

  const navigateToResult = (href?: string) => {
    if (!href) return;
    router.push(href);
    setQuery("");
    setFocused(false);
  };

  const handleSearchSubmit = (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    navigateToResult(results[0]?.href);
  };

  return (
    <header className="sticky top-0 z-30 border-b border-slate-200/80 bg-[rgba(244,247,251,0.92)] backdrop-blur">
      <div className="page-container flex items-center justify-between gap-3 px-4 py-2.5 sm:px-6 lg:px-8">
        <div className="flex min-w-0 items-center gap-3">
          <div className="lg:hidden">{menuButton}</div>
          <div className="hidden min-w-0 md:block">
            <div className="text-[11px] font-semibold uppercase tracking-[0.22em] text-slate-500">Workspace</div>
            <div className="truncate text-sm font-medium text-slate-900">{title}</div>
          </div>
        </div>

        <div className="flex min-w-0 flex-1 items-center justify-end gap-2.5">
          <form onSubmit={handleSearchSubmit} className="relative hidden min-w-0 flex-1 md:block md:max-w-md lg:max-w-lg">
            <div className="relative">
              <Search size={15} className="pointer-events-none absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-400" />
              <input
                type="search"
                value={query}
                onChange={(event) => setQuery(event.target.value)}
                onFocus={() => setFocused(true)}
                onBlur={() => window.setTimeout(() => setFocused(false), 120)}
                placeholder="Jump to page"
                className="w-full rounded-xl border border-slate-200 bg-white py-2.5 pl-10 pr-16 text-sm text-slate-900 outline-none focus:border-slate-300 focus:ring-2 focus:ring-slate-200"
              />
              <span className="pointer-events-none absolute right-3 top-1/2 -translate-y-1/2 rounded-md border border-slate-200 bg-slate-50 px-1.5 py-0.5 text-[10px] font-medium uppercase tracking-wide text-slate-500">
                Enter
              </span>
            </div>
            {focused && results.length > 0 ? (
              <div className="absolute left-0 right-0 top-[calc(100%+0.45rem)] z-40 overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-[0_18px_34px_rgba(15,23,42,0.12)]">
                {results.slice(0, 6).map((result) => (
                  <button
                    key={result.href}
                    type="button"
                    onClick={() => navigateToResult(result.href)}
                    className="flex w-full items-center justify-between border-b border-slate-100 px-3.5 py-2.5 text-left text-sm text-slate-700 transition-colors last:border-b-0 hover:bg-slate-50"
                  >
                    <span>{result.label}</span>
                    <span className="text-xs text-slate-400">{result.href}</span>
                  </button>
                ))}
              </div>
            ) : null}
          </form>

          <button className="relative inline-flex h-9 w-9 items-center justify-center rounded-xl border border-slate-200 bg-white text-slate-600 shadow-sm hover:bg-slate-50">
            <Bell size={16} />
            <span className="absolute right-2.5 top-2.5 h-2 w-2 rounded-full bg-rose-500 ring-2 ring-white"></span>
          </button>

          <button className="hidden items-center gap-2 rounded-xl border border-slate-200 bg-white px-2.5 py-1.5 text-left shadow-sm transition-colors hover:bg-slate-50 sm:flex">
            <div className="flex h-8 w-8 items-center justify-center rounded-xl bg-slate-900 text-white">
              <User size={14} />
            </div>
            <div className="min-w-0">
              <div className="truncate text-[13px] font-medium leading-5 text-slate-900">{user?.full_name || "Admin"}</div>
              <div className="truncate text-[11px] leading-4 text-slate-500">{user?.email || "Authenticated session"}</div>
            </div>
            <ChevronDown size={14} className="text-slate-400" />
          </button>

          <button className="inline-flex h-9 w-9 items-center justify-center rounded-xl border border-slate-200 bg-white text-slate-600 shadow-sm hover:bg-slate-50 sm:hidden">
            <User size={15} />
          </button>
        </div>
      </div>
    </header>
  );
}
