"use client";

import Link from "next/link";
import { useCallback, useEffect, useMemo, useState } from "react";
import { Activity, AlertTriangle, CheckCircle2, ClipboardList, History, PlayCircle, RefreshCcw, ShieldCheck, TimerReset } from "lucide-react";

import { AlertBanner, EmptyState, MetricCard, PageHeader, SectionTitle, StatusBadge, SurfaceCard } from "@/components/ui/primitives";
import { useApiService } from "@/services/api";
import type { QualityCenterSummary, QualityCheckResult, QualityCheckRun } from "@/types/models";

function toneForStatus(status?: string): "success" | "warning" | "danger" | "info" | "neutral" {
  if (status === "ready" || status === "passed") return "success";
  if (status === "blocked" || status === "failed") return "danger";
  if (status === "warning" || status === "skipped" || status === "unknown") return "warning";
  return "neutral";
}

function formatDateTime(value?: string | null) {
  if (!value) return "Never";
  const parsed = new Date(value.endsWith("Z") ? value : `${value}Z`);
  return Number.isNaN(parsed.getTime()) ? "Unknown" : parsed.toLocaleString();
}

function statusLabel(status?: string) {
  return (status || "unknown").replaceAll("_", " ");
}

function ResultRow({
  result,
  onCreateTask,
  taskPending,
}: {
  result: QualityCheckResult;
  onCreateTask?: (result: QualityCheckResult) => void;
  taskPending?: boolean;
}) {
  return (
    <div className="rounded-2xl border border-slate-200 bg-white px-4 py-3">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <StatusBadge tone={toneForStatus(result.status)}>{statusLabel(result.status)}</StatusBadge>
            <span className="text-xs font-semibold uppercase tracking-wide text-slate-400">{result.category.replaceAll("_", " ")}</span>
          </div>
          <div className="mt-2 text-sm font-semibold text-slate-950">{result.name}</div>
          <p className="mt-1 text-sm leading-6 text-slate-600">{result.message}</p>
          <div className="mt-2 text-xs text-slate-400">Checked {formatDateTime(result.checked_at)}</div>
        </div>
        <div className="flex shrink-0 flex-wrap items-center gap-2">
          {result.href ? (
            <Link href={result.href} className="rounded-xl border border-slate-200 px-3 py-2 text-xs font-semibold text-slate-700 hover:bg-slate-50">
              Open context
            </Link>
          ) : null}
          {onCreateTask && ["failed", "blocked", "warning"].includes(result.status) ? (
            <button
              type="button"
              disabled={taskPending}
              onClick={() => onCreateTask(result)}
              className="rounded-xl border border-slate-200 px-3 py-2 text-xs font-semibold text-slate-700 hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-50"
            >
              Create task
            </button>
          ) : null}
        </div>
      </div>
    </div>
  );
}

function RunCard({ title, run }: { title: string; run?: QualityCheckRun | null }) {
  return (
    <SurfaceCard className="p-5">
      <div className="flex items-start justify-between gap-4">
        <div>
          <div className="text-sm font-semibold text-slate-950">{title}</div>
          <div className="mt-2 text-sm leading-6 text-slate-600">{run?.summary || "No run has been recorded yet."}</div>
        </div>
        <StatusBadge tone={toneForStatus(run?.status)}>{statusLabel(run?.status)}</StatusBadge>
      </div>
      <div className="mt-4 text-xs text-slate-500">Last completed: {formatDateTime(run?.completed_at)}</div>
    </SurfaceCard>
  );
}

export default function QualityCenterPage() {
  const {
    getQualitySummary,
    runQualitySmoke,
    runQualityReleaseReadiness,
    createOperatorTask,
  } = useApiService();
  const [summary, setSummary] = useState<QualityCenterSummary | null>(null);
  const [pageError, setPageError] = useState<string | null>(null);
  const [actionMessage, setActionMessage] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [running, setRunning] = useState<"smoke" | "release" | null>(null);
  const [taskPendingId, setTaskPendingId] = useState<string | null>(null);

  const loadSummary = useCallback(async () => {
    setPageError(null);
    try {
      const data = await getQualitySummary();
      setSummary(data);
    } catch (error) {
      setSummary(null);
      setPageError(error instanceof Error ? error.message : "Quality Center summary could not be loaded.");
    } finally {
      setLoading(false);
    }
  }, [getQualitySummary]);

  useEffect(() => {
    loadSummary();
  }, [loadSummary]);

  const runCheck = async (type: "smoke" | "release") => {
    setRunning(type);
    setActionMessage(null);
    setPageError(null);
    try {
      const run = type === "smoke" ? await runQualitySmoke() : await runQualityReleaseReadiness();
      setActionMessage(`${type === "smoke" ? "Smoke" : "Release readiness"} run completed with status ${run.status}.`);
      await loadSummary();
    } catch (error) {
      setPageError(error instanceof Error ? error.message : "Quality run failed.");
    } finally {
      setRunning(null);
    }
  };

  const createTaskFromResult = async (result: QualityCheckResult) => {
    const pendingKey = result.id || `${result.category}:${result.name}`;
    setTaskPendingId(pendingKey);
    setActionMessage(null);
    try {
      await createOperatorTask({
        title: `Fix quality issue: ${result.name}`,
        description: `${result.message}${result.href ? `\nContext: ${result.href}` : ""}`,
        status: "todo",
        priority: result.status === "blocked" || result.status === "failed" ? "high" : "normal",
        category: "system",
        related_entity_type: result.entity_type || null,
        related_entity_id: result.entity_id || null,
        metadata: {
          source: "quality_center",
          quality_category: result.category,
          quality_status: result.status,
          href: result.href,
        },
      });
      setActionMessage("Operator task created in Command Center.");
    } catch (error) {
      setPageError(error instanceof Error ? error.message : "Could not create operator task.");
    } finally {
      setTaskPendingId(null);
    }
  };

  const failingAndStale = useMemo(() => [...(summary?.failing_checks || []), ...(summary?.stale_checks || [])], [summary]);

  return (
    <div className="space-y-6 pb-12">
      <PageHeader
        eyebrow="Internal quality"
        title="Quality Center"
        description="Run structured internal validation, inspect runtime consistency, and turn quality failures into operator tasks."
        actions={(
          <>
            <button type="button" onClick={() => void loadSummary()} className="btn-secondary">
              <RefreshCcw size={16} /> Refresh Runtime Status
            </button>
            <button type="button" disabled={Boolean(running)} onClick={() => void runCheck("smoke")} className="btn-secondary disabled:opacity-60">
              <PlayCircle size={16} /> {running === "smoke" ? "Running..." : "Run Smoke Check"}
            </button>
            <button type="button" disabled={Boolean(running)} onClick={() => void runCheck("release")} className="btn-primary disabled:opacity-60">
              <ShieldCheck size={16} /> {running === "release" ? "Running..." : "Run Release Readiness"}
            </button>
          </>
        )}
      />

      {pageError ? <AlertBanner tone="danger" title="Quality Center unavailable">{pageError}</AlertBanner> : null}
      {actionMessage ? <AlertBanner tone="success" title="Quality action completed">{actionMessage}</AlertBanner> : null}

      {loading && !summary ? (
        <SurfaceCard className="flex h-64 items-center justify-center text-sm font-medium text-slate-500">Loading quality state...</SurfaceCard>
      ) : !summary ? (
        <EmptyState icon={ShieldCheck} title="No quality state available" description="The backend did not return a Quality Center summary. Check API health and authentication." />
      ) : (
        <>
          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
            <MetricCard title="Overall quality" value={statusLabel(summary.overall_status)} detail={`Generated ${formatDateTime(summary.generated_at)}`} icon={ShieldCheck} tone={toneForStatus(summary.overall_status)} />
            <MetricCard title="Failing checks" value={summary.stats.failing_checks ?? summary.failing_checks.length} detail="Failed or blocked quality checks" icon={AlertTriangle} tone={summary.failing_checks.length ? "danger" : "success"} />
            <MetricCard title="Stale checks" value={summary.stats.stale_checks ?? summary.stale_checks.length} detail="Checks that need a fresh run" icon={TimerReset} tone={summary.stale_checks.length ? "warning" : "success"} />
            <MetricCard title="Recent runs" value={summary.stats.recent_runs ?? summary.recent_runs.length} detail="Persisted quality history" icon={History} tone="info" />
          </div>

          <div className="grid gap-4 lg:grid-cols-2">
            <RunCard title="Last smoke run" run={summary.last_smoke_run} />
            <RunCard title="Last release readiness run" run={summary.last_release_run} />
          </div>

          <SurfaceCard className="p-5">
            <SectionTitle title="Recommended next fixes" description="Prioritized from failed, blocked, and stale quality checks." />
            <div className="space-y-2">
              {summary.recommended_next_fixes.map((fix, index) => (
                <div key={`${fix}-${index}`} className="flex items-start gap-3 rounded-xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-700">
                  <span className="rounded-full bg-white px-2 py-0.5 text-xs font-semibold text-slate-950 ring-1 ring-slate-200">{index + 1}</span>
                  <span>{fix}</span>
                </div>
              ))}
            </div>
          </SurfaceCard>

          <div className="grid gap-6 xl:grid-cols-2">
            <SurfaceCard className="p-5">
              <SectionTitle title="Runtime checks" description="Live checks from backend health, readiness, deliverability, and quality history." />
              <div className="space-y-3">
                {summary.runtime_checks.map((result) => (
                  <ResultRow key={`${result.category}-${result.name}`} result={result} onCreateTask={createTaskFromResult} taskPending={taskPendingId === (result.id || `${result.category}:${result.name}`)} />
                ))}
              </div>
            </SurfaceCard>

            <SurfaceCard className="p-5">
              <SectionTitle title="Data integrity checks" description="Consistency checks for campaigns, jobs, mailboxes, domains, inbox, warm-up, and notifications." />
              <div className="space-y-3">
                {summary.integrity_checks.map((result, index) => (
                  <ResultRow key={`${result.category}-${result.entity_id || result.name}-${index}`} result={result} onCreateTask={createTaskFromResult} taskPending={taskPendingId === (result.id || `${result.category}:${result.name}`)} />
                ))}
              </div>
            </SurfaceCard>
          </div>

          <SurfaceCard className="p-5">
            <SectionTitle title="Failures and stale checks" description="Items that should be resolved or refreshed before important product changes." />
            {failingAndStale.length === 0 ? (
              <div className="rounded-xl border border-emerald-100 bg-emerald-50 px-4 py-3 text-sm font-medium text-emerald-800">
                No failed, blocked, or stale quality checks are currently known.
              </div>
            ) : (
              <div className="space-y-3">
                {failingAndStale.map((result, index) => (
                  <ResultRow key={`issue-${result.id || index}`} result={result} onCreateTask={createTaskFromResult} taskPending={taskPendingId === (result.id || `${result.category}:${result.name}`)} />
                ))}
              </div>
            )}
          </SurfaceCard>

          <SurfaceCard className="overflow-hidden">
            <div className="border-b border-slate-200 px-5 py-4">
              <div className="flex items-center gap-2 text-base font-semibold text-slate-950">
                <Activity size={18} className="text-sky-600" />
                Recent quality runs
              </div>
            </div>
            {summary.recent_runs.length === 0 ? (
              <div className="p-5 text-sm text-slate-600">No quality runs have been recorded yet. Run a smoke check to create the first quality record.</div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full min-w-[720px] text-left">
                  <thead className="border-b border-slate-200 bg-slate-50 text-xs font-semibold uppercase tracking-wide text-slate-500">
                    <tr>
                      <th className="px-5 py-3">Run</th>
                      <th className="px-5 py-3">Status</th>
                      <th className="px-5 py-3">Summary</th>
                      <th className="px-5 py-3">Completed</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {summary.recent_runs.map((run) => (
                      <tr key={run.id}>
                        <td className="px-5 py-4 text-sm font-semibold text-slate-900">{run.run_type.replaceAll("_", " ")}</td>
                        <td className="px-5 py-4"><StatusBadge tone={toneForStatus(run.status)}>{statusLabel(run.status)}</StatusBadge></td>
                        <td className="max-w-xl px-5 py-4 text-sm text-slate-600">{run.summary || "No summary recorded."}</td>
                        <td className="px-5 py-4 text-sm text-slate-500">{formatDateTime(run.completed_at)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </SurfaceCard>

          <SurfaceCard className="p-5">
            <div className="flex items-start gap-3">
              <CheckCircle2 size={18} className="mt-0.5 text-emerald-600" />
              <div>
                <div className="font-semibold text-slate-950">Structured quality evidence</div>
                <p className="mt-1 text-sm leading-6 text-slate-600">
                  Quality Center stores structured results, not raw terminal logs. It complements existing smoke scripts, release docs, Command Center logs, and header notifications.
                </p>
                <Link href="/command-center" className="mt-3 inline-flex items-center gap-2 text-sm font-semibold text-slate-700 hover:text-slate-950">
                  <ClipboardList size={15} /> Open Command Center
                </Link>
              </div>
            </div>
          </SurfaceCard>
        </>
      )}
    </div>
  );
}

