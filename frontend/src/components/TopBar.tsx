import { Activity, Bell, Check, ChevronDown, ClipboardList, LogOut, RefreshCcw, Search, Settings, User } from "lucide-react";
import { useRouter } from "next/navigation";
import { useEffect, useMemo, useRef, useState } from "react";

import { useAuth } from "@/context/AuthContext";
import { useApiService } from "@/services/api";
import type { HeaderNotification } from "@/types/models";

const severityStyles: Record<string, { border: string; badge: string }> = {
  critical: { border: "border-l-rose-500", badge: "text-rose-600" },
  warning: { border: "border-l-amber-500", badge: "text-amber-600" },
  info: { border: "border-l-[#2d6a4f]", badge: "text-[#2d6a4f]" },
  success: { border: "border-l-emerald-500", badge: "text-emerald-600" },
};

function formatRelativeTime(value: string) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "Unknown";
  const diffMs = Date.now() - date.getTime();
  const minutes = Math.max(0, Math.floor(diffMs / 60000));
  if (minutes < 1) return "Now";
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  return `${days}d ago`;
}

export default function TopBar({
  title,
  menuButton,
}: {
  title: string;
  menuButton?: React.ReactNode;
}) {
  const { user, logout } = useAuth();
  const { getNotificationSummary, markAllNotificationsRead, markNotificationRead } = useApiService();
  const router = useRouter();
  const [query, setQuery] = useState("");
  const [focused, setFocused] = useState(false);
  const [notificationsOpen, setNotificationsOpen] = useState(false);
  const [accountOpen, setAccountOpen] = useState(false);
  const [notifications, setNotifications] = useState<HeaderNotification[]>([]);
  const [unreadCount, setUnreadCount] = useState(0);
  const [notificationsLoading, setNotificationsLoading] = useState(false);
  const [notificationsError, setNotificationsError] = useState<string | null>(null);
  const notificationRef = useRef<HTMLDivElement | null>(null);
  const accountRef = useRef<HTMLDivElement | null>(null);

  const workspaceTargets = useMemo(
    () => [
      { label: "Dashboard", href: "/dashboard" },
      { label: "Command Center", href: "/command-center" },
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
      { label: "Quality Center", href: "/quality-center" },
      { label: "Settings", href: "/settings" },
    ],
    [],
  );

  const loadNotifications = async () => {
    setNotificationsLoading(true);
    setNotificationsError(null);
    try {
      const summary = await getNotificationSummary(20);
      setNotifications(summary?.items || []);
      setUnreadCount(summary?.unread_count || 0);
    } catch (error) {
      setNotificationsError(error instanceof Error ? error.message : "Notifications could not be loaded.");
    } finally {
      setNotificationsLoading(false);
    }
  };

  useEffect(() => {
    loadNotifications();
    const interval = window.setInterval(loadNotifications, 60000);
    return () => window.clearInterval(interval);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    const handleDocumentClick = (event: MouseEvent) => {
      const target = event.target as Node;
      if (notificationRef.current && !notificationRef.current.contains(target)) {
        setNotificationsOpen(false);
      }
      if (accountRef.current && !accountRef.current.contains(target)) {
        setAccountOpen(false);
      }
    };
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        setNotificationsOpen(false);
        setAccountOpen(false);
      }
    };
    document.addEventListener("mousedown", handleDocumentClick);
    document.addEventListener("keydown", handleKeyDown);
    return () => {
      document.removeEventListener("mousedown", handleDocumentClick);
      document.removeEventListener("keydown", handleKeyDown);
    };
  }, []);

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

  const handleNotificationClick = async (notification: HeaderNotification) => {
    if (!notification.read_at) {
      try {
        await markNotificationRead(notification.id);
        setNotifications((current) =>
          current.map((item) => (item.id === notification.id ? { ...item, read_at: new Date().toISOString() } : item)),
        );
        setUnreadCount((current) => Math.max(0, current - 1));
      } catch {
        // Navigation is more important than read state; keep failures visible via refresh.
      }
    }
    if (notification.href) {
      router.push(notification.href);
      setNotificationsOpen(false);
    }
  };

  const handleMarkAllRead = async () => {
    await markAllNotificationsRead();
    const now = new Date().toISOString();
    setNotifications((current) => current.map((item) => ({ ...item, read_at: item.read_at || now })));
    setUnreadCount(0);
  };

  const navigateFromAccount = (href: string) => {
    router.push(href);
    setAccountOpen(false);
  };

  return (
    <header className="sticky top-0 z-30 border-b border-[var(--border)] bg-[rgba(250,248,245,0.92)] backdrop-blur">
      <div className="page-container flex items-center justify-between gap-3 px-4 py-2.5 sm:px-6 lg:px-8">
        <div className="flex min-w-0 items-center gap-3">
          <div className="lg:hidden">{menuButton}</div>
          <div className="hidden min-w-0 md:block">
            <div className="text-[11px] font-semibold uppercase tracking-[0.22em] text-[var(--muted-foreground)]">Workspace</div>
            <div className="truncate text-sm font-medium text-[var(--foreground)]">{title}</div>
          </div>
        </div>

        <div className="flex min-w-0 flex-1 items-center justify-end gap-2.5">
          <form onSubmit={handleSearchSubmit} className="relative hidden min-w-0 flex-1 md:block md:max-w-md lg:max-w-lg">
            <div className="relative">
              <Search size={15} className="pointer-events-none absolute left-3.5 top-1/2 -translate-y-1/2 text-[var(--muted-foreground)]" />
              <input
                type="search"
                value={query}
                onChange={(event) => setQuery(event.target.value)}
                onFocus={() => setFocused(true)}
                onBlur={() => window.setTimeout(() => setFocused(false), 120)}
                placeholder="Jump to page"
                className="w-full rounded-xl border border-[var(--border)] bg-[var(--surface)] py-2.5 pl-10 pr-16 text-sm text-[var(--foreground)] outline-none focus:border-[var(--border-strong)] focus:ring-2 focus:ring-[#d4e4d3]"
              />
              <span className="pointer-events-none absolute right-3 top-1/2 -translate-y-1/2 rounded-md border border-[var(--border)] bg-[var(--surface-muted)] px-1.5 py-0.5 text-[10px] font-medium uppercase tracking-wide text-[var(--muted-foreground)]">
                Enter
              </span>
            </div>
            {focused && results.length > 0 ? (
              <div className="absolute left-0 right-0 top-[calc(100%+0.45rem)] z-40 overflow-hidden rounded-2xl border border-[var(--border)] bg-[var(--surface)] shadow-[0_18px_34px_rgba(45,31,20,0.1)]">
                {results.slice(0, 6).map((result) => (
                  <button
                    key={result.href}
                    type="button"
                    onClick={() => navigateToResult(result.href)}
                    className="flex w-full items-center justify-between border-b border-[var(--surface-muted)] px-3.5 py-2.5 text-left text-sm text-[var(--foreground)] transition-colors last:border-b-0 hover:bg-[var(--surface-muted)]"
                  >
                    <span>{result.label}</span>
                    <span className="text-xs text-[var(--muted-foreground)]">{result.href}</span>
                  </button>
                ))}
              </div>
            ) : null}
          </form>

          <div ref={notificationRef} className="relative">
            <button
              type="button"
              onClick={() => {
                setNotificationsOpen((open) => !open);
                setAccountOpen(false);
                if (!notificationsOpen) void loadNotifications();
              }}
              className="relative inline-flex h-9 w-9 items-center justify-center rounded-xl border border-[var(--border)] bg-[var(--surface)] text-[var(--muted-foreground)] shadow-sm hover:bg-[var(--surface-muted)] focus:outline-none focus:ring-2 focus:ring-[#d4e4d3]"
              aria-label={`Notifications${unreadCount ? `, ${unreadCount} unread` : ""}`}
              aria-expanded={notificationsOpen}
            >
              <Bell size={16} />
              {unreadCount > 0 ? (
                <span className="absolute -right-1 -top-1 min-w-[1.15rem] rounded-full bg-rose-600 px-1.5 py-0.5 text-[10px] font-bold leading-none text-white ring-2 ring-[var(--surface)]">
                  {unreadCount > 9 ? "9+" : unreadCount}
                </span>
              ) : null}
            </button>

            {notificationsOpen ? (
              <div className="absolute right-0 top-[calc(100%+0.55rem)] z-50 w-[min(calc(100vw-2rem),24rem)] overflow-hidden rounded-2xl border border-[var(--border)] bg-[var(--surface)] shadow-[0_22px_48px_rgba(45,31,20,0.12)]">
                <div className="flex items-center justify-between border-b border-[var(--surface-muted)] px-4 py-3">
                  <div>
                    <div className="text-sm font-semibold text-[var(--foreground)]">Notifications</div>
                    <div className="text-xs text-[var(--muted-foreground)]">{unreadCount ? `${unreadCount} unread operational item${unreadCount === 1 ? "" : "s"}` : "No unread operational items"}</div>
                  </div>
                  <div className="flex items-center gap-1.5">
                    <button
                      type="button"
                      onClick={() => void loadNotifications()}
                      className="inline-flex h-8 w-8 items-center justify-center rounded-lg text-[var(--muted-foreground)] hover:bg-[var(--surface-muted)] hover:text-[var(--foreground)]"
                      aria-label="Refresh notifications"
                    >
                      <RefreshCcw size={14} className={notificationsLoading ? "animate-spin" : ""} />
                    </button>
                    <button
                      type="button"
                      onClick={() => void handleMarkAllRead()}
                      disabled={unreadCount === 0}
                      className="inline-flex h-8 w-8 items-center justify-center rounded-lg text-[var(--muted-foreground)] hover:bg-[var(--surface-muted)] hover:text-[var(--foreground)] disabled:cursor-not-allowed disabled:opacity-40"
                      aria-label="Mark all notifications read"
                    >
                      <Check size={15} />
                    </button>
                  </div>
                </div>
                <div className="max-h-[25rem] overflow-y-auto">
                  {notificationsError ? (
                    <div className="px-4 py-6 text-sm text-rose-700">{notificationsError}</div>
                  ) : notificationsLoading && notifications.length === 0 ? (
                    <div className="px-4 py-6 text-sm text-[var(--muted-foreground)]">Loading operational notifications...</div>
                  ) : notifications.length === 0 ? (
                    <div className="px-4 py-6">
                      <div className="text-sm font-medium text-[var(--foreground)]">No actionable notifications</div>
                      <div className="mt-1 text-sm text-[var(--muted-foreground)]">The header will show real blockers, failures, and unread replies when they exist.</div>
                    </div>
                  ) : (
                    notifications.map((notification) => {
                      const isUnread = !notification.read_at;
                      const styles = severityStyles[notification.severity] || severityStyles.info;
                      return (
                        <button
                          key={notification.id}
                          type="button"
                          onClick={() => void handleNotificationClick(notification)}
                          className={`flex w-full border-b border-l-[3px] border-b-[var(--surface-muted)] px-4 py-3.5 text-left transition-colors last:border-b-0 hover:bg-[var(--surface-muted)] ${styles.border}`}
                        >
                          <span className="min-w-0 flex-1">
                            <span className="flex items-start justify-between gap-3">
                              <span className="text-sm font-semibold text-[var(--foreground)]">{notification.title}</span>
                              {isUnread ? <span className="mt-1 h-2 w-2 shrink-0 rounded-full bg-rose-500" /> : null}
                            </span>
                            <span className="mt-1 line-clamp-2 text-xs leading-5 text-[var(--muted-foreground)]">{notification.message}</span>
                            <span className="mt-2 flex items-center gap-1.5 text-[11px] tracking-wide text-[var(--muted-foreground)]">
                              <span className={`font-bold uppercase ${styles.badge}`}>{notification.severity}</span>
                              <span>·</span>
                              <span className="font-medium uppercase">{notification.source.replaceAll("_", " ")}</span>
                              <span>·</span>
                              <span>{formatRelativeTime(notification.created_at)}</span>
                            </span>
                          </span>
                        </button>
                      );
                    })
                  )}
                </div>
              </div>
            ) : null}
          </div>

          <div ref={accountRef} className="relative">
            <button
              type="button"
              onClick={() => {
                setAccountOpen((open) => !open);
                setNotificationsOpen(false);
              }}
              className="hidden items-center gap-2 rounded-xl border border-[var(--border)] bg-[var(--surface)] px-2.5 py-1.5 text-left shadow-sm transition-colors hover:bg-[var(--surface-muted)] focus:outline-none focus:ring-2 focus:ring-[#d4e4d3] sm:flex"
              aria-label="Account menu"
              aria-expanded={accountOpen}
            >
              <div className="flex h-8 w-8 items-center justify-center rounded-xl bg-[var(--primary)] text-white">
                <User size={14} />
              </div>
              <div className="min-w-0">
                <div className="truncate text-[13px] font-medium leading-5 text-[var(--foreground)]">{user?.full_name || "Admin"}</div>
                <div className="truncate text-[11px] leading-4 text-[var(--muted-foreground)]">{user?.email || "Authenticated session"}</div>
              </div>
              <ChevronDown size={14} className="text-[var(--muted-foreground)]" />
            </button>

            <button
              type="button"
              onClick={() => {
                setAccountOpen((open) => !open);
                setNotificationsOpen(false);
              }}
              className="inline-flex h-9 w-9 items-center justify-center rounded-xl border border-[var(--border)] bg-[var(--surface)] text-[var(--muted-foreground)] shadow-sm hover:bg-[var(--surface-muted)] focus:outline-none focus:ring-2 focus:ring-[#d4e4d3] sm:hidden"
              aria-label="Account menu"
              aria-expanded={accountOpen}
            >
              <User size={15} />
            </button>

            {accountOpen ? (
              <div className="absolute right-0 top-[calc(100%+0.55rem)] z-50 w-[min(calc(100vw-2rem),18rem)] overflow-hidden rounded-2xl border border-[var(--border)] bg-[var(--surface)] shadow-[0_22px_48px_rgba(45,31,20,0.12)]">
                <div className="border-b border-[var(--surface-muted)] px-4 py-3">
                  <div className="text-sm font-semibold text-[var(--foreground)]">{user?.full_name || "Admin"}</div>
                  <div className="mt-0.5 truncate text-xs text-[var(--muted-foreground)]">{user?.email || "Authenticated session"}</div>
                  <div className="mt-2 inline-flex rounded-full border border-[var(--border)] bg-[var(--surface-muted)] px-2 py-0.5 text-[10px] font-bold uppercase tracking-wide text-[var(--muted-foreground)]">
                    {user?.is_admin ? "Admin workspace" : "Workspace user"}
                  </div>
                </div>
                <div className="p-2">
                  <button type="button" onClick={() => navigateFromAccount("/settings")} className="flex w-full items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium text-[var(--foreground)] hover:bg-[var(--surface-muted)]">
                    <Settings size={15} /> Settings
                  </button>
                  <button type="button" onClick={() => navigateFromAccount("/command-center")} className="flex w-full items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium text-[var(--foreground)] hover:bg-[var(--surface-muted)]">
                    <ClipboardList size={15} /> Command Center
                  </button>
                  <button type="button" onClick={() => navigateFromAccount("/ops")} className="flex w-full items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium text-[var(--foreground)] hover:bg-[var(--surface-muted)]">
                    <Activity size={15} /> Ops / Health
                  </button>
                </div>
                <div className="border-t border-[var(--surface-muted)] p-2">
                  <button
                    type="button"
                    onClick={logout}
                    className="flex w-full items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-semibold text-rose-600 hover:bg-rose-50"
                  >
                    <LogOut size={15} /> Sign out
                  </button>
                </div>
              </div>
            ) : null}
          </div>
        </div>
      </div>
    </header>
  );
}
