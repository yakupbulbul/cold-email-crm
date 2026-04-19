"use client";

import { useEffect, useState } from "react";
import { AlertTriangle, CheckCircle2, Globe2, Mailbox, Radar, ShieldAlert, Sparkles, Users, Zap } from "lucide-react";

import { AlertBanner, EmptyState, MetricCard, PageHeader, StatusBadge, SurfaceCard } from "@/components/ui/primitives";
import { useApiService } from "@/services/api";
import { DeliverabilityEntity, DeliverabilityIssue, DeliverabilityOverview, DeliverabilityStatus } from "@/types/models";

function toneForStatus(status?: string): "success" | "warning" | "danger" | "info" | "neutral" {
  if (status === "ready" || status === "pass" || status === "healthy") return "success";
  if (status === "blocked" || status === "fail" || status === "failed") return "danger";
  if (status === "degraded" || status === "warning") return "warning";
  return "neutral";
}

function formatDateTime(value?: string | null): string {
  if (!value) return "Not checked";
  const parsed = new Date(value.endsWith("Z") ? value : `${value}Z`);
  return Number.isNaN(parsed.getTime()) ? "Not checked" : parsed.toLocaleString();
}

function issueLabel(issue: DeliverabilityIssue) {
  return [issue.entity, issue.message].filter(Boolean).join(": ");
}

function StatusPill({ status }: { status: DeliverabilityStatus | string }) {
  return <StatusBadge tone={toneForStatus(status)}>{status.replaceAll("_", " ")}</StatusBadge>;
}

function IssueList({ title, issues, empty }: { title: string; issues: DeliverabilityIssue[]; empty: string }) {
  return (
    <SurfaceCard className="p-5">
      <div className="flex items-center justify-between gap-3">
        <h2 className="text-base font-semibold text-slate-950">{title}</h2>
        <StatusBadge tone={issues.length ? "warning" : "success"}>{issues.length}</StatusBadge>
      </div>
      <div className="mt-4 space-y-3">
        {issues.length === 0 ? (
          <div className="rounded-xl border border-emerald-100 bg-emerald-50 px-4 py-3 text-sm font-medium text-emerald-800">{empty}</div>
        ) : (
          issues.map((issue, index) => (
            <div key={`${issue.code}-${index}`} className="rounded-xl border border-slate-200 bg-white px-4 py-3">
              <div className="flex items-start gap-3">
                <ShieldAlert className={issue.severity === "critical" ? "mt-0.5 text-rose-600" : "mt-0.5 text-amber-600"} size={17} />
                <div className="min-w-0">
                  <div className="text-sm font-semibold text-slate-900">{issueLabel(issue)}</div>
                  {issue.next_action ? <div className="mt-1 text-xs leading-5 text-slate-600">Next action: {issue.next_action}</div> : null}
                </div>
              </div>
            </div>
          ))
        )}
      </div>
    </SurfaceCard>
  );
}

function ReadinessTable({ title, items, kind }: { title: string; items: DeliverabilityEntity[]; kind: "domain" | "mailbox" }) {
  return (
    <SurfaceCard className="overflow-hidden">
      <div className="border-b border-slate-200 px-5 py-4">
        <h2 className="text-base font-semibold text-slate-950">{title}</h2>
      </div>
      {items.length === 0 ? (
        <div className="p-5 text-sm text-slate-600">No {kind === "domain" ? "domains" : "mailboxes"} exist yet.</div>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full min-w-[760px] text-left">
            <thead className="border-b border-slate-200 bg-slate-50 text-xs font-semibold uppercase tracking-wide text-slate-500">
              <tr>
                <th className="px-5 py-3">{kind === "domain" ? "Domain" : "Mailbox"}</th>
                <th className="px-5 py-3">Status</th>
                <th className="px-5 py-3">Provider</th>
                <th className="px-5 py-3">Primary issue</th>
                <th className="px-5 py-3">Last checked</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {items.map((item) => {
                const issue = item.blockers[0] || item.warnings[0];
                return (
                  <tr key={item.id || item.email || item.name} className="align-top">
                    <td className="px-5 py-4">
                      <div className="font-semibold text-slate-900">{item.email || item.name}</div>
                      {kind === "mailbox" ? <div className="mt-1 text-xs text-slate-500">{item.domain}</div> : null}
                    </td>
                    <td className="px-5 py-4"><StatusPill status={item.status} /></td>
                    <td className="px-5 py-4 text-sm text-slate-600">{item.provider_type?.replaceAll("_", " ") || "Domain DNS"}</td>
                    <td className="max-w-md px-5 py-4 text-sm text-slate-600">{issue ? issue.message : "No deliverability issue detected."}</td>
                    <td className="px-5 py-4 text-sm text-slate-500">{formatDateTime(item.last_checked_at)}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </SurfaceCard>
  );
}

export default function DeliverabilityDashboard() {
  const { getDeliverabilityOverviewOrThrow, loading } = useApiService();
  const [overview, setOverview] = useState<DeliverabilityOverview | null>(null);
  const [pageError, setPageError] = useState<string | null>(null);

  useEffect(() => {
    const fetchOverview = async () => {
      setPageError(null);
      try {
        const data = await getDeliverabilityOverviewOrThrow();
        setOverview(data);
      } catch (error) {
        setOverview(null);
        setPageError(error instanceof Error ? error.message : "Deliverability overview could not be loaded from the backend.");
      }
    };
    fetchOverview();
  }, [getDeliverabilityOverviewOrThrow]);

  const audience = overview?.summary.audience || {};
  const warmup = overview?.summary.warmup || {};
  const domains = overview?.summary.domains || {};
  const mailboxes = overview?.summary.mailboxes || {};

  return (
    <div className="space-y-6 pb-12">
      <PageHeader
        eyebrow="Operations"
        title="Deliverability control center"
        description="Real readiness across domains, mailboxes, providers, audience hygiene, warm-up, and campaign posture. Unchecked or failing systems are shown honestly instead of marked healthy."
      />

      {pageError ? <AlertBanner tone="danger" title="Deliverability unavailable">{pageError}</AlertBanner> : null}

      {loading && !overview ? (
        <SurfaceCard className="flex h-64 items-center justify-center text-sm font-medium text-slate-500">Loading deliverability truth...</SurfaceCard>
      ) : !overview ? (
        <EmptyState icon={Radar} title="No deliverability data loaded" description="The backend did not return a deliverability overview. Check API health and authentication." />
      ) : (
        <>
          <SurfaceCard className="p-5">
            <div className="flex flex-col gap-5 lg:flex-row lg:items-center lg:justify-between">
              <div>
                <div className="flex flex-wrap items-center gap-3">
                  <StatusPill status={overview.status} />
                  <span className="text-sm text-slate-500">Generated {formatDateTime(overview.generated_at)}</span>
                </div>
                <h2 className="mt-3 text-xl font-semibold tracking-[-0.03em] text-slate-950">
                  Overall readiness is {overview.status}.
                </h2>
                <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-600">
                  This status is derived from persisted DNS verification, provider availability, SMTP/IMAP diagnostics, warm-up activity, send logs, and contact verification fields.
                </p>
              </div>
              <div className="rounded-2xl border border-slate-200 bg-slate-50 px-5 py-4 text-right">
                <div className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">Derived score</div>
                <div className="mt-1 text-3xl font-semibold tracking-[-0.04em] text-slate-950">{overview.score ?? "N/A"}</div>
              </div>
            </div>
          </SurfaceCard>

          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
            <MetricCard title="Domains ready" value={`${domains.ready ?? 0}/${domains.domain_count ?? 0}`} detail={`${domains.blocked ?? 0} blocked, ${domains.degraded ?? 0} degraded`} icon={Globe2} tone={domains.blocked ? "danger" : domains.degraded ? "warning" : "success"} />
            <MetricCard title="Mailboxes ready" value={`${mailboxes.ready ?? 0}/${mailboxes.mailbox_count ?? 0}`} detail={`${mailboxes.blocked ?? 0} blocked, ${mailboxes.degraded ?? 0} degraded`} icon={Mailbox} tone={mailboxes.blocked ? "danger" : mailboxes.degraded ? "warning" : "success"} />
            <MetricCard title="Reachable contacts" value={String(audience.reachable_count ?? 0)} detail={`${audience.invalid_count ?? 0} invalid, ${audience.suppressed_count ?? 0} suppressed`} icon={Users} tone={(audience.invalid_count as number) > 0 ? "warning" : "success"} />
            <MetricCard title="Warm-up today" value={String(warmup.successful_sends_today ?? 0)} detail={`${warmup.failed_sends_today ?? 0} failed, ${warmup.active_pairs ?? 0} active pairs`} icon={Zap} tone={(warmup.failed_sends_today as number) > 0 ? "warning" : "info"} />
          </div>

          <div className="grid gap-6 xl:grid-cols-2">
            <IssueList title="Blocking issues" issues={overview.blockers} empty="No blocking deliverability issues are currently known." />
            <IssueList title="Warnings and next fixes" issues={overview.warnings} empty="No warning-level deliverability issues are currently known." />
          </div>

          {overview.next_actions.length > 0 ? (
            <SurfaceCard className="p-5">
              <div className="flex items-center gap-2 text-base font-semibold text-slate-950">
                <Sparkles size={18} className="text-sky-600" />
                Recommended fix order
              </div>
              <div className="mt-4 grid gap-3 md:grid-cols-2">
                {overview.next_actions.map((action, index) => (
                  <div key={action} className="rounded-xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-700">
                    <span className="mr-2 font-semibold text-slate-950">{index + 1}.</span>
                    {action}
                  </div>
                ))}
              </div>
            </SurfaceCard>
          ) : null}

          <div className="grid gap-6 xl:grid-cols-2">
            <ReadinessTable title="Domain readiness" items={overview.domains} kind="domain" />
            <ReadinessTable title="Mailbox readiness" items={overview.mailboxes} kind="mailbox" />
          </div>

          <div className="grid gap-6 xl:grid-cols-2">
            <SurfaceCard className="p-5">
              <div className="flex items-center justify-between gap-3">
                <h2 className="text-base font-semibold text-slate-950">Provider posture</h2>
                <AlertTriangle size={18} className={overview.providers.some((provider) => provider.status === "blocked") ? "text-rose-600" : "text-slate-400"} />
              </div>
              <div className="mt-4 space-y-3">
                {overview.providers.map((provider) => (
                  <div key={provider.provider_type} className="rounded-xl border border-slate-200 px-4 py-3">
                    <div className="flex flex-wrap items-center justify-between gap-3">
                      <div className="font-semibold capitalize text-slate-900">{provider.provider_type.replaceAll("_", " ")}</div>
                      <StatusPill status={provider.status} />
                    </div>
                    <div className="mt-2 text-sm text-slate-600">{provider.detail || "No provider detail available."}</div>
                    <div className="mt-2 text-xs text-slate-500">{provider.mailbox_count} mailbox(es), {provider.enabled ? "enabled" : "disabled"}, {provider.configured ? "configured" : "not configured"}</div>
                  </div>
                ))}
              </div>
            </SurfaceCard>

            <SurfaceCard className="p-5">
              <div className="flex items-center gap-2 text-base font-semibold text-slate-950">
                <CheckCircle2 size={18} className="text-emerald-600" />
                Campaign posture
              </div>
              <div className="mt-4 grid grid-cols-3 gap-3">
                <div className="rounded-xl bg-slate-50 p-3">
                  <div className="text-xs font-semibold uppercase text-slate-500">Active</div>
                  <div className="mt-1 text-2xl font-semibold text-slate-950">{overview.campaigns.summary.active ?? 0}</div>
                </div>
                <div className="rounded-xl bg-slate-50 p-3">
                  <div className="text-xs font-semibold uppercase text-slate-500">Paused</div>
                  <div className="mt-1 text-2xl font-semibold text-slate-950">{overview.campaigns.summary.paused ?? 0}</div>
                </div>
                <div className="rounded-xl bg-slate-50 p-3">
                  <div className="text-xs font-semibold uppercase text-slate-500">Checked</div>
                  <div className="mt-1 text-2xl font-semibold text-slate-950">{overview.campaigns.summary.checked_campaigns ?? 0}</div>
                </div>
              </div>
              <div className="mt-4 space-y-3">
                {overview.campaigns.items.length === 0 ? (
                  <div className="rounded-xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-600">No active or paused campaigns need deliverability review right now.</div>
                ) : (
                  overview.campaigns.items.slice(0, 5).map((campaign) => (
                    <div key={campaign.id} className="flex items-center justify-between gap-3 rounded-xl border border-slate-200 px-4 py-3">
                      <div className="min-w-0">
                        <div className="truncate text-sm font-semibold text-slate-900">{campaign.name}</div>
                        <div className="truncate text-xs text-slate-500">{campaign.blockers[0]?.message || campaign.warnings[0]?.message || "No known campaign deliverability issue."}</div>
                      </div>
                      <StatusPill status={campaign.status} />
                    </div>
                  ))
                )}
              </div>
            </SurfaceCard>
          </div>
        </>
      )}
    </div>
  );
}
