"use client";

import { useCallback, useEffect, useState } from "react";
import { Activity, AlertCircle, Clock3, Mailbox, Pause, Play, RefreshCcw, ShieldAlert, Zap } from "lucide-react";

import Spinner from "@/components/ui/Spinner";
import { useApiService } from "@/services/api";
import { WarmupLog, WarmupPair, WarmupStatus } from "@/types/models";

function formatDateTime(value?: string | null): string {
  if (!value) return "Not available";
  const parsed = new Date(/[zZ]|[+-]\d{2}:\d{2}$/.test(value) ? value : `${value}Z`);
  return Number.isNaN(parsed.getTime()) ? "Not available" : parsed.toLocaleString();
}

export default function WarmupPage() {
  const {
    getWarmupStatus,
    getWarmupPairs,
    getWarmupLogs,
    startWarmup,
    pauseWarmup,
    updateMailboxWarmup,
  } = useApiService();

  const [status, setStatus] = useState<WarmupStatus | null>(null);
  const [pairs, setPairs] = useState<WarmupPair[]>([]);
  const [logs, setLogs] = useState<WarmupLog[]>([]);
  const [pageLoading, setPageLoading] = useState(true);
  const [pageError, setPageError] = useState<string | null>(null);
  const [banner, setBanner] = useState<{ tone: "success" | "error"; message: string } | null>(null);
  const [actionState, setActionState] = useState<{ type: "start" | "pause" | "toggle"; id?: string } | null>(null);

  const loadWarmup = useCallback(async () => {
    setPageLoading(true);
    setPageError(null);
    const [statusResult, pairResult, logResult] = await Promise.all([
      getWarmupStatus(),
      getWarmupPairs(),
      getWarmupLogs(50),
    ]);
    if (!statusResult || !pairResult || !logResult) {
      setPageError("Failed to load warm-up status, pairs, or recent activity.");
      setPageLoading(false);
      return;
    }
    setStatus(statusResult);
    setPairs(pairResult);
    setLogs(logResult);
    setPageLoading(false);
  }, [getWarmupLogs, getWarmupPairs, getWarmupStatus]);

  useEffect(() => {
    void loadWarmup();
  }, [loadWarmup]);

  const handleStart = async () => {
    setBanner(null);
    setActionState({ type: "start" });
    try {
      const result = await startWarmup();
      await loadWarmup();
      setBanner({ tone: "success", message: result.detail });
    } catch (err) {
      const message = err instanceof Error ? err.message : "Warm-up start failed.";
      setBanner({ tone: "error", message });
    } finally {
      setActionState(null);
    }
  };

  const handlePause = async () => {
    setBanner(null);
    setActionState({ type: "pause" });
    try {
      const result = await pauseWarmup();
      await loadWarmup();
      setBanner({ tone: "success", message: result.detail });
    } catch (err) {
      const message = err instanceof Error ? err.message : "Warm-up pause failed.";
      setBanner({ tone: "error", message });
    } finally {
      setActionState(null);
    }
  };

  const handleToggleMailbox = async (mailboxId: string, warmupEnabled: boolean) => {
    setBanner(null);
    setActionState({ type: "toggle", id: mailboxId });
    try {
      await updateMailboxWarmup(mailboxId, { warmup_enabled: warmupEnabled });
      await loadWarmup();
      setBanner({
        tone: "success",
        message: warmupEnabled ? "Mailbox added to warm-up participation." : "Mailbox removed from warm-up participation.",
      });
    } catch (err) {
      const message = err instanceof Error ? err.message : "Mailbox warm-up update failed.";
      setBanner({ tone: "error", message });
    } finally {
      setActionState(null);
    }
  };

  const blockers = status?.blockers || [];
  const activeAction = actionState?.type;

  return (
    <div className="space-y-6 animate-fade-in relative min-h-[50vh]">
      <div className="flex flex-col gap-4 md:flex-row md:items-start md:justify-between">
        <div>
          <h1 className="text-3xl font-bold text-slate-800 tracking-tight">Warm-up Engine</h1>
          <p className="mt-2 text-sm font-medium text-slate-500">
            Warm-up is worker-backed, separate from campaign sending, and depends on healthy participating mailboxes.
          </p>
        </div>
        <div className="flex flex-wrap gap-3">
          <button
            type="button"
            onClick={() => void handlePause()}
            disabled={pageLoading || activeAction === "start" || activeAction === "pause"}
            className="inline-flex items-center gap-2 rounded-xl border border-slate-200 bg-white px-5 py-2.5 font-medium text-slate-700 transition-colors hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-50"
          >
            {activeAction === "pause" ? <Spinner size="sm" /> : <Pause size={18} />}
            Pause All
          </button>
          <button
            type="button"
            onClick={() => void handleStart()}
            disabled={pageLoading || activeAction === "start" || activeAction === "pause"}
            className="inline-flex items-center gap-2 rounded-xl bg-blue-600 px-5 py-2.5 font-bold text-white transition-colors hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-50"
          >
            {activeAction === "start" ? <Spinner size="sm" /> : <Play size={18} fill="currentColor" />}
            Start Warm-up
          </button>
          <button
            type="button"
            onClick={() => void loadWarmup()}
            disabled={pageLoading}
            className="inline-flex items-center gap-2 rounded-xl border border-slate-200 bg-white px-5 py-2.5 font-medium text-slate-700 transition-colors hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-50"
          >
            <RefreshCcw size={18} />
            Refresh
          </button>
        </div>
      </div>

      {banner ? (
        <div className={`rounded-2xl border px-5 py-4 text-sm font-medium ${
          banner.tone === "success"
            ? "border-emerald-200 bg-emerald-50 text-emerald-700"
            : "border-red-200 bg-red-50 text-red-700"
        }`}>
          {banner.message}
        </div>
      ) : null}

      {pageError ? (
        <div className="flex h-64 flex-col items-center justify-center rounded-2xl border border-red-200 bg-red-50 p-6 text-center text-red-700 shadow-sm">
          <AlertCircle className="mb-4 text-red-500" size={32} />
          <span className="mb-2 font-bold">Failed to load Warm-up data</span>
          <span className="text-sm">{pageError}</span>
        </div>
      ) : pageLoading ? (
        <div className="flex h-64 items-center justify-center rounded-2xl border border-slate-200 bg-white shadow-sm">
          <Spinner size="lg" />
        </div>
      ) : status ? (
        <>
          <div className="grid grid-cols-1 gap-6 md:grid-cols-4">
            <SummaryCard
              title="Global Health"
              value={status.health_percent == null ? "N/A" : `${status.health_percent}%`}
              detail={status.global_status === "enabled" ? "Warm-up is enabled globally." : "Warm-up is paused globally."}
              icon={<ShieldAlert size={26} />}
              tone="emerald"
            />
            <SummaryCard
              title="Total Sent Today"
              value={String(status.successful_sends_today)}
              detail={`${status.failed_sends_today} failed`}
              icon={<Activity size={26} />}
              tone="blue"
            />
            <SummaryCard
              title="Inboxes Warming"
              value={String(status.inboxes_warming_count)}
              detail={`${status.eligible_mailboxes_count} eligible now`}
              icon={<Mailbox size={26} />}
              tone="violet"
            />
            <SummaryCard
              title="Active Pairs"
              value={String(status.active_pairs_count)}
              detail={status.next_run_at ? `Next run ${formatDateTime(status.next_run_at)}` : "Not schedulable right now"}
              icon={<Zap size={26} />}
              tone="amber"
            />
          </div>

          <div className="grid gap-6 lg:grid-cols-[1.2fr,0.8fr]">
            <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
              <div className="mb-4 flex items-center gap-2 text-lg font-bold text-slate-800">
                <Clock3 size={18} />
                Runtime status
              </div>
              <div className="grid gap-3 sm:grid-cols-2">
                <DetailCard label="Global status" value={status.global_status} />
                <DetailCard label="Worker status" value={status.worker_status.status} detail={status.worker_status.detail || undefined} />
                <DetailCard label="Scheduler status" value={status.scheduler_status.status} detail={status.scheduler_status.detail || undefined} />
                <DetailCard label="Last run" value={formatDateTime(status.last_run_at)} />
              </div>
              <div className="mt-4 space-y-2">
                {blockers.length > 0 ? blockers.map((blocker) => (
                  <div key={blocker.code} className="rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm font-medium text-amber-800">
                    {blocker.message}
                  </div>
                )) : (
                  <div className="rounded-xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm font-medium text-emerald-700">
                    No warm-up blockers are active right now.
                  </div>
                )}
              </div>
            </section>

            <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
              <div className="mb-4 text-lg font-bold text-slate-800">Mailbox participation</div>
              <div className="space-y-3">
                {status.mailboxes.length === 0 ? (
                  <div className="rounded-xl border border-slate-200 bg-slate-50 px-4 py-4 text-sm text-slate-600">
                    No mailboxes exist yet. Create at least two healthy mailboxes before warm-up can run.
                  </div>
                ) : status.mailboxes.map((mailbox) => (
                  <div key={mailbox.id} className="rounded-xl border border-slate-200 bg-slate-50 px-4 py-4">
                    <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
                      <div>
                        <div className="font-semibold text-slate-800">{mailbox.email}</div>
                        <div className="mt-1 text-xs font-medium uppercase tracking-wide text-slate-500">
                          {mailbox.warmup_status}
                        </div>
                        <div className="mt-2 text-sm text-slate-600">
                          Last result: <span className="font-medium text-slate-800">{mailbox.warmup_last_result || "never_run"}</span>
                        </div>
                        {mailbox.warmup_block_reason ? (
                          <div className="mt-1 text-sm text-amber-700">{mailbox.warmup_block_reason}</div>
                        ) : null}
                      </div>
                      <button
                        type="button"
                        onClick={() => void handleToggleMailbox(mailbox.id, !mailbox.warmup_enabled)}
                        disabled={activeAction === "toggle" && actionState?.id === mailbox.id}
                        className={`inline-flex items-center justify-center rounded-xl px-4 py-2.5 text-sm font-bold transition-colors disabled:cursor-not-allowed disabled:opacity-50 ${
                          mailbox.warmup_enabled
                            ? "border border-slate-200 bg-white text-slate-700 hover:bg-slate-50"
                            : "bg-blue-600 text-white hover:bg-blue-700"
                        }`}
                      >
                        {activeAction === "toggle" && actionState?.id === mailbox.id ? (
                          <Spinner size="sm" />
                        ) : mailbox.warmup_enabled ? "Disable warm-up" : "Enable warm-up"}
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            </section>
          </div>

          <section className="rounded-2xl border border-slate-200 bg-white shadow-sm overflow-hidden">
            <div className="border-b border-slate-100 p-6">
              <h2 className="text-lg font-bold text-slate-800">Active warm-up pairs</h2>
            </div>
            {pairs.length === 0 ? (
              <div className="p-10 text-center text-slate-500">
                <Zap className="mx-auto mb-4 opacity-50" size={42} />
                <div className="font-semibold text-slate-700">No active warm-up pairs</div>
                <div className="mt-2 text-sm">
                  {blockers.length > 0 ? blockers[0].message : "Enable at least two SMTP-healthy mailboxes to generate warm-up pairs."}
                </div>
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="min-w-full text-left">
                  <thead className="bg-slate-50 text-xs uppercase tracking-wide text-slate-500">
                    <tr>
                      <th className="px-6 py-4">Sender</th>
                      <th className="px-6 py-4">Recipient</th>
                      <th className="px-6 py-4">State</th>
                      <th className="px-6 py-4">Last send</th>
                      <th className="px-6 py-4">Next send</th>
                      <th className="px-6 py-4">Last result</th>
                      <th className="px-6 py-4">Daily progress</th>
                    </tr>
                  </thead>
                  <tbody>
                    {pairs.map((pair) => (
                      <tr key={pair.id} className="border-t border-slate-100 align-top">
                        <td className="px-6 py-4 font-medium text-slate-800">{pair.sender_email}</td>
                        <td className="px-6 py-4 font-medium text-slate-800">{pair.recipient_email}</td>
                        <td className="px-6 py-4 text-sm text-slate-600">{pair.state}</td>
                        <td className="px-6 py-4 text-sm text-slate-600">{formatDateTime(pair.last_send_at)}</td>
                        <td className="px-6 py-4 text-sm text-slate-600">{formatDateTime(pair.next_scheduled_at)}</td>
                        <td className="px-6 py-4 text-sm text-slate-600">
                          <div>{pair.last_result || "Not run yet"}</div>
                          {pair.last_error ? <div className="mt-1 text-amber-700">{pair.last_error}</div> : null}
                        </td>
                        <td className="px-6 py-4 text-sm text-slate-600">
                          {pair.daily_sent_count} / {pair.daily_limit}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </section>

          <section className="rounded-2xl border border-slate-200 bg-white shadow-sm overflow-hidden">
            <div className="border-b border-slate-100 p-6">
              <h2 className="text-lg font-bold text-slate-800">Recent warm-up activity</h2>
            </div>
            {logs.length === 0 ? (
              <div className="p-10 text-center text-slate-500">
                <Activity className="mx-auto mb-4 opacity-50" size={42} />
                <div className="font-semibold text-slate-700">No recent warm-up activity</div>
                <div className="mt-2 text-sm">Recent send, failure, and skipped warm-up events will appear here.</div>
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="min-w-full text-left">
                  <thead className="bg-slate-50 text-xs uppercase tracking-wide text-slate-500">
                    <tr>
                      <th className="px-6 py-4">Timestamp</th>
                      <th className="px-6 py-4">Sender</th>
                      <th className="px-6 py-4">Recipient</th>
                      <th className="px-6 py-4">Result</th>
                      <th className="px-6 py-4">Detail</th>
                    </tr>
                  </thead>
                  <tbody>
                    {logs.map((log) => (
                      <tr key={log.id} className="border-t border-slate-100 align-top">
                        <td className="px-6 py-4 text-sm text-slate-600">{formatDateTime(log.timestamp)}</td>
                        <td className="px-6 py-4 text-sm text-slate-700">{log.sender_email || "Unknown sender"}</td>
                        <td className="px-6 py-4 text-sm text-slate-700">{log.recipient_email || log.target_email}</td>
                        <td className="px-6 py-4 text-sm font-medium text-slate-800">{log.status}</td>
                        <td className="px-6 py-4 text-sm text-slate-600">
                          {log.result_detail || "No detail recorded."}
                          {log.error_category ? <div className="mt-1 text-amber-700">Category: {log.error_category}</div> : null}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </section>
        </>
      ) : null}
    </div>
  );
}

function SummaryCard({
  title,
  value,
  detail,
  icon,
  tone,
}: {
  title: string;
  value: string;
  detail: string;
  icon: React.ReactNode;
  tone: "emerald" | "blue" | "violet" | "amber";
}) {
  const tones = {
    emerald: "bg-emerald-100 text-emerald-700",
    blue: "bg-blue-100 text-blue-700",
    violet: "bg-violet-100 text-violet-700",
    amber: "bg-amber-100 text-amber-700",
  };

  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
      <div className="flex items-center justify-between">
        <div>
          <div className="text-sm font-semibold uppercase tracking-wider text-slate-500">{title}</div>
          <div className="mt-1 text-4xl font-extrabold text-slate-800">{value}</div>
          <div className="mt-2 text-sm text-slate-500">{detail}</div>
        </div>
        <div className={`rounded-2xl p-4 shadow-sm ${tones[tone]}`}>{icon}</div>
      </div>
    </div>
  );
}

function DetailCard({ label, value, detail }: { label: string; value: string; detail?: string }) {
  return (
    <div className="rounded-xl border border-slate-200 bg-slate-50 px-4 py-4">
      <div className="text-xs font-bold uppercase tracking-wide text-slate-500">{label}</div>
      <div className="mt-2 text-sm font-semibold text-slate-800">{value}</div>
      {detail ? <div className="mt-1 text-sm text-slate-600">{detail}</div> : null}
    </div>
  );
}
