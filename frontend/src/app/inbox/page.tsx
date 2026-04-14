"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { AlertCircle, Inbox as InboxIcon, LoaderCircle, Mailbox, RefreshCw, Search, ShieldAlert } from "lucide-react";

import { useApiService } from "@/services/api";
import { InboxStatus, Message, Thread } from "@/types/models";
import Spinner from "@/components/ui/Spinner";
import { EmptyState, MetricCard, PageHeader, SurfaceCard } from "@/components/ui/primitives";

function formatDateTime(value?: string | null) {
  if (!value) return "Not available";
  return new Date(value.endsWith("Z") ? value : `${value}Z`).toLocaleString();
}

export default function InboxPage() {
  const { getInboxStatus, getThreads, getThread, syncInbox, loading, error } = useApiService();
  const [status, setStatus] = useState<InboxStatus | null>(null);
  const [threads, setThreads] = useState<Thread[]>([]);
  const [selectedThreadId, setSelectedThreadId] = useState<string | null>(null);
  const [selectedThread, setSelectedThread] = useState<(Thread & { messages: Message[] }) | null>(null);
  const [mailboxFilter, setMailboxFilter] = useState<string>("all");
  const [showUnreadOnly, setShowUnreadOnly] = useState(false);
  const [search, setSearch] = useState("");
  const [syncMessage, setSyncMessage] = useState<string | null>(null);
  const [syncError, setSyncError] = useState<string | null>(null);
  const [syncing, setSyncing] = useState(false);

  const queryString = useMemo(() => {
    const params = new URLSearchParams();
    if (mailboxFilter !== "all") params.set("mailbox_id", mailboxFilter);
    if (showUnreadOnly) params.set("unread_only", "true");
    if (search.trim()) params.set("search", search.trim());
    return params.toString();
  }, [mailboxFilter, showUnreadOnly, search]);

  const refreshInbox = useCallback(async () => {
    const [statusData, threadData] = await Promise.all([
      getInboxStatus(),
      getThreads(queryString),
    ]);
    if (statusData) setStatus(statusData);
    if (threadData) {
      setThreads(threadData);
      setSelectedThreadId((current) => current && threadData.some((thread) => thread.id === current) ? current : threadData[0]?.id ?? null);
    }
  }, [getInboxStatus, getThreads, queryString]);

  useEffect(() => {
    refreshInbox();
  }, [refreshInbox]);

  useEffect(() => {
    if (!selectedThreadId) {
      setSelectedThread(null);
      return;
    }
    const loadThread = async () => {
      const detail = await getThread(selectedThreadId);
      if (detail) {
        setSelectedThread(detail);
      }
    };
    loadThread();
  }, [selectedThreadId, getThread]);

  const handleManualSync = async () => {
    try {
      setSyncing(true);
      setSyncError(null);
      setSyncMessage(null);
      const result = await syncInbox(mailboxFilter !== "all" ? mailboxFilter : undefined);
      const imported = result.results.reduce((sum, item) => sum + item.imported_count, 0);
      const failed = result.results.filter((item) => item.status === "failing").length;
      setSyncMessage(
        failed > 0
          ? `Inbox sync completed with ${failed} failing mailbox${failed === 1 ? "" : "es"} and ${imported} imported message${imported === 1 ? "" : "s"}.`
          : `Inbox sync completed and imported ${imported} message${imported === 1 ? "" : "s"}.`,
      );
      await refreshInbox();
    } catch (err) {
      setSyncError(err instanceof Error ? err.message : "Inbox sync failed.");
    } finally {
      setSyncing(false);
    }
  };

  if (error && !status) {
    return (
      <div className="space-y-6">
        <PageHeader
          eyebrow="Inbox"
          title="Inbox"
          description="Review incoming replies, mailbox conversations, and inbox sync health from one operational workspace."
        />
        <SurfaceCard className="flex min-h-[18rem] flex-col items-center justify-center gap-4 p-10 text-center">
          <div className="flex h-12 w-12 items-center justify-center rounded-2xl border border-red-200 bg-red-50 text-red-600">
            <ShieldAlert size={22} />
          </div>
          <div>
            <h2 className="text-lg font-semibold text-slate-900">Inbox Unavailable</h2>
            <p className="mt-2 max-w-lg text-sm text-slate-600">The backend failed while loading inbox status or thread data.</p>
          </div>
          <p className="rounded-xl border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">{error}</p>
        </SurfaceCard>
      </div>
    );
  }

  if (!status && loading) {
    return (
      <div className="space-y-6">
        <PageHeader
          eyebrow="Inbox"
          title="Inbox"
          description="Review incoming replies, mailbox conversations, and inbox sync health from one operational workspace."
        />
        <SurfaceCard className="flex min-h-[18rem] items-center justify-center">
          <Spinner size="lg" />
        </SurfaceCard>
      </div>
    );
  }

  const blockers = status?.blockers ?? [];
  const hasThreads = threads.length > 0;

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Inbox"
        title="Inbox"
        description="Review incoming replies, mailbox conversations, and inbox sync health from one operational workspace."
        actions={(
          <div className="flex flex-wrap items-center gap-2">
            <button
              type="button"
              onClick={() => refreshInbox()}
              className="btn-secondary"
            >
              Refresh view
            </button>
            <button
              type="button"
              onClick={handleManualSync}
              disabled={syncing}
              className="btn-primary inline-flex items-center gap-2 disabled:cursor-not-allowed disabled:opacity-60"
            >
              {syncing ? <LoaderCircle size={16} className="animate-spin" /> : <RefreshCw size={16} />}
              Sync inbox
            </button>
          </div>
        )}
      />

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <MetricCard title="Threads" value={status?.threads_count ?? 0} detail={`${status?.unread_threads_count ?? 0} unread`} icon={InboxIcon} />
        <MetricCard title="Messages Today" value={status?.messages_received_today ?? 0} detail={`Last message ${formatDateTime(status?.last_message_at)}`} icon={Mailbox} />
        <MetricCard title="Sync Mailboxes" value={status?.sync_enabled_mailboxes_count ?? 0} detail={`${status?.healthy_mailboxes_count ?? 0} healthy`} icon={RefreshCw} />
        <MetricCard title="Scheduler" value={status?.scheduler_status.status ?? "unknown"} detail={status?.scheduler_status.detail ?? "No scheduler status"} icon={AlertCircle} />
      </div>

      {syncMessage ? (
        <SurfaceCard className="border-green-200 bg-green-50/70 px-4 py-3 text-sm text-green-800">{syncMessage}</SurfaceCard>
      ) : null}
      {syncError ? (
        <SurfaceCard className="border-red-200 bg-red-50/70 px-4 py-3 text-sm text-red-800">{syncError}</SurfaceCard>
      ) : null}

      <div className="grid gap-6 xl:grid-cols-[320px_minmax(0,1fr)]">
        <SurfaceCard className="space-y-4 p-4">
          <div>
            <h2 className="text-sm font-semibold uppercase tracking-[0.18em] text-slate-500">Sync Health</h2>
            <p className="mt-2 text-sm text-slate-600">{status?.worker_status.detail}</p>
            <p className="mt-1 text-sm text-slate-600">{status?.scheduler_status.detail}</p>
          </div>

          <div className="space-y-2">
            <label className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">Mailbox</label>
            <select
              value={mailboxFilter}
              onChange={(event) => setMailboxFilter(event.target.value)}
              className="w-full rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm text-slate-900"
            >
              <option value="all">All mailboxes</option>
              {(status?.mailboxes ?? []).map((mailbox) => (
                <option key={mailbox.id} value={mailbox.id}>
                  {mailbox.email}
                </option>
              ))}
            </select>
          </div>

          <label className="flex items-center justify-between rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 text-sm text-slate-700">
            <span>Show unread only</span>
            <input type="checkbox" checked={showUnreadOnly} onChange={(event) => setShowUnreadOnly(event.target.checked)} />
          </label>

          <div className="space-y-2">
            <label className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">Search threads</label>
            <div className="relative">
              <Search size={15} className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
              <input
                value={search}
                onChange={(event) => setSearch(event.target.value)}
                placeholder="Search subject or sender"
                className="w-full rounded-xl border border-slate-200 bg-white py-2 pl-9 pr-3 text-sm text-slate-900"
              />
            </div>
          </div>

          <div className="space-y-2 border-t border-slate-200 pt-4">
            <h3 className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">Mailbox Sync Status</h3>
            <div className="space-y-2">
              {(status?.mailboxes ?? []).map((mailbox) => (
                <div key={mailbox.id} className="rounded-xl border border-slate-200 bg-white px-3 py-2">
                  <div className="flex items-center justify-between gap-3">
                    <div className="min-w-0">
                      <p className="truncate text-sm font-medium text-slate-900">{mailbox.email}</p>
                      <p className="text-xs text-slate-500">{mailbox.inbox_sync_status}</p>
                    </div>
                    <span className={`rounded-full px-2 py-1 text-[11px] font-semibold ${
                      mailbox.inbox_sync_status === "healthy"
                        ? "bg-green-100 text-green-700"
                        : mailbox.inbox_sync_status === "failing"
                          ? "bg-red-100 text-red-700"
                          : "bg-slate-100 text-slate-600"
                    }`}>
                      {mailbox.inbox_sync_status}
                    </span>
                  </div>
                  <p className="mt-2 text-xs text-slate-500">
                    Last sync: {formatDateTime(mailbox.inbox_last_synced_at)}
                  </p>
                  {mailbox.inbox_last_error ? (
                    <p className="mt-1 text-xs text-red-600">{mailbox.inbox_last_error}</p>
                  ) : null}
                </div>
              ))}
            </div>
          </div>
        </SurfaceCard>

        {!hasThreads ? (
          <EmptyState
            icon={InboxIcon}
            title="No inbox threads yet"
            description={
              blockers.length > 0
                ? blockers.map((blocker) => blocker.message).join(" ")
                : "Inbox sync is healthy, but no replies or conversations have been ingested yet."
            }
          />
        ) : (
          <div className="grid gap-6 xl:grid-cols-[360px_minmax(0,1fr)]">
            <SurfaceCard className="overflow-hidden p-0">
              <div className="flex items-center justify-between border-b border-slate-200 px-4 py-3">
                <h2 className="text-sm font-semibold uppercase tracking-[0.18em] text-slate-500">Threads</h2>
                <span className="rounded-full bg-slate-100 px-2.5 py-1 text-xs font-semibold text-slate-700">
                  {threads.length} visible
                </span>
              </div>
              <div className="divide-y divide-slate-100">
                {threads.map((thread) => (
                  <button
                    key={thread.id}
                    type="button"
                    onClick={() => setSelectedThreadId(thread.id)}
                    className={`flex w-full flex-col gap-2 px-4 py-4 text-left transition-colors ${selectedThreadId === thread.id ? "bg-slate-50" : "hover:bg-slate-50/70"}`}
                  >
                    <div className="flex items-start justify-between gap-3">
                      <div className="min-w-0">
                        <p className="truncate text-sm font-semibold text-slate-900">{thread.subject || "No subject"}</p>
                        <p className="truncate text-sm text-slate-600">{thread.contact_email || "Unknown sender"}</p>
                      </div>
                      <div className="text-right">
                        <p className="text-xs text-slate-500">{formatDateTime(thread.last_message_at)}</p>
                        {thread.unread ? (
                          <span className="mt-1 inline-flex rounded-full bg-blue-100 px-2 py-1 text-[11px] font-semibold text-blue-700">
                            {thread.unread_count ?? 1} unread
                          </span>
                        ) : null}
                      </div>
                    </div>
                    <p className="line-clamp-2 text-sm text-slate-600">{thread.last_message_preview || thread.snippet || "No preview available."}</p>
                    <div className="flex flex-wrap items-center gap-2 text-xs text-slate-500">
                      <span>{thread.mailbox_email}</span>
                      <span>•</span>
                      <span>{thread.linkage_status === "linked" ? (thread.campaign_name ? `Campaign: ${thread.campaign_name}` : "Linked contact") : "Unlinked reply"}</span>
                    </div>
                  </button>
                ))}
              </div>
            </SurfaceCard>

            <SurfaceCard className="p-0">
              {selectedThread ? (
                <div className="flex h-full flex-col">
                  <div className="border-b border-slate-200 px-5 py-4">
                    <h2 className="text-xl font-semibold text-slate-900">{selectedThread.subject || "No subject"}</h2>
                    <div className="mt-2 flex flex-wrap items-center gap-2 text-sm text-slate-600">
                      <span>{selectedThread.contact_email || "Unknown sender"}</span>
                      <span>•</span>
                      <span>{selectedThread.mailbox_email}</span>
                      {selectedThread.campaign_name ? (
                        <>
                          <span>•</span>
                          <span>{selectedThread.campaign_name}</span>
                        </>
                      ) : null}
                    </div>
                  </div>
                  <div className="space-y-4 p-5">
                    {selectedThread.messages.map((message) => (
                      <div key={message.id} className={`rounded-2xl border px-4 py-3 ${
                        message.direction === "inbound" ? "border-slate-200 bg-white" : "border-blue-100 bg-blue-50/70"
                      }`}>
                        <div className="flex flex-wrap items-center justify-between gap-2 text-xs text-slate-500">
                          <span>{message.direction === "inbound" ? message.from_address : message.to_address}</span>
                          <span>{formatDateTime(message.sent_at)}</span>
                        </div>
                        <p className="mt-3 whitespace-pre-wrap text-sm leading-6 text-slate-800">{message.body_text || "No plain-text body available."}</p>
                      </div>
                    ))}
                  </div>
                </div>
              ) : (
                <div className="flex min-h-[24rem] items-center justify-center">
                  <EmptyState icon={InboxIcon} title="Select a thread" description="Choose a conversation from the left to inspect the full message history." />
                </div>
              )}
            </SurfaceCard>
          </div>
        )}
      </div>
    </div>
  );
}
