"use client";

import Link from "next/link";
import { Send, Globe, Inbox, AlertCircle, ArrowRight, Users } from 'lucide-react';
import { useApiService } from '@/services/api';
import { useEffect, useState } from 'react';
import Spinner from '@/components/ui/Spinner';
import { DeliverabilitySummary } from '@/types/models';
import { AlertBanner, EmptyState, MetricCard, PageHeader, SectionTitle, StatusBadge, SurfaceCard } from "@/components/ui/primitives";

export default function Dashboard() {
  const { getDeliverabilitySummary, getMailboxes, loading, error } = useApiService();
  const [stats, setStats] = useState<DeliverabilitySummary | null>(null);
  const [mailboxCount, setMailboxCount] = useState<number>(0);

  useEffect(() => {
    const fetchDashboardStats = async () => {
      // In a real load we would do Promise.all, but we handle missing endpoints gracefully
      const res = await getDeliverabilitySummary();
      if (res) setStats(res);
      
      const boxes = await getMailboxes();
      if (boxes) setMailboxCount(boxes.length);
    };
    fetchDashboardStats();
  }, [getDeliverabilitySummary, getMailboxes]);

  return (
    <div className="space-y-8 animate-fade-in">
      <PageHeader
        eyebrow="Overview"
        title="Dashboard Overview"
        description="See infrastructure readiness, audience quality, and the next action your operators should take."
        actions={(
          <div className="flex flex-wrap items-center gap-3">
            <Link href="/campaigns" className="btn-primary">
              New campaign
            </Link>
            <Link href="/send-email" className="btn-secondary">
              Test direct send
            </Link>
          </div>
        )}
      />
      
      {error && !stats ? (
        <AlertBanner tone="danger" title="Backend connection error">
          {error}
        </AlertBanner>
      ) : loading && !stats ? (
        <SurfaceCard className="flex h-64 items-center justify-center">
          <Spinner size="lg" />
        </SurfaceCard>
      ) : !stats ? (
        <EmptyState
          icon={AlertCircle}
          title="No operational summary available"
          description="The backend did not return dashboard summary data yet. Refresh after the API becomes available."
        />
      ) : (
        <>
          <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
            <MetricCard title="Total contacts" value={stats.total_contacts || 0} icon={Users} detail="Unified B2B and B2C audience base." />
            <MetricCard title="Active mailboxes" value={stats.mailbox_count || mailboxCount} icon={Globe} detail="Configured senders across domains." tone="info" />
            <MetricCard title="B2B campaigns" value={stats.b2b_campaigns || 0} icon={Send} detail="Mailbox-driven outreach programs." />
            <MetricCard title="B2C campaigns" value={stats.b2c_campaigns || 0} icon={Inbox} detail="Consent-aware audience campaigns." tone="success" />
          </div>

          <div className="grid gap-6 xl:grid-cols-[1.4fr,0.9fr]">
            <SurfaceCard className="p-6">
              <SectionTitle
                title="Audience quality"
                description="Keep deliverable, risky, and blocked inventory obvious before operators start sending."
              />
              <div className="grid gap-4 md:grid-cols-3">
                <MiniMetric label="Valid" value={stats.valid_contacts || 0} tone="success" />
                <MiniMetric label="Risky" value={stats.risky_contacts || 0} tone="warning" />
                <MiniMetric label="Invalid or blocked" value={(stats.invalid_contacts || 0) + (stats.suppressed_contacts || 0)} tone="danger" />
              </div>
            </SurfaceCard>

            <SurfaceCard className="p-6">
              <SectionTitle
                title="Operator priorities"
                description="Use these counts to decide whether the next step is quality cleanup, suppression review, or campaign execution."
              />
              <div className="space-y-3">
                <PriorityRow label="Unsubscribed contacts" value={stats.unsubscribed_contacts || 0} tone="warning" />
                <PriorityRow label="Suppressed contacts" value={stats.suppressed_contacts || 0} tone="danger" />
                <PriorityRow label="Active campaigns" value={stats.active_campaigns || 0} tone="info" />
              </div>
            </SurfaceCard>
          </div>

          <div className="grid gap-6 xl:grid-cols-[1.1fr,0.9fr]">
            <SurfaceCard className="p-6">
              <SectionTitle
                title="Next steps"
                description="The product should tell non-technical operators what to do next without sending them digging across pages."
              />
              <div className="grid gap-3">
                <ActionRow
                  title="Verify audience quality before launch"
                  detail="Review contacts with risky or blocked status before you start list-based sends."
                  href="/contacts"
                />
                <ActionRow
                  title="Check mailbox SMTP health"
                  detail="Confirm senders are active and transport checks pass before warm-up or campaigns run."
                  href="/mailboxes?focus=smtp"
                />
                <ActionRow
                  title="Inspect warm-up readiness"
                  detail="Make sure scheduler, workers, and participating mailboxes are all healthy."
                  href="/warmup"
                />
              </div>
            </SurfaceCard>

            <SurfaceCard className="p-6">
              <SectionTitle
                title="Operational posture"
                description="A quick explanation of the current database-backed state, without decorative filler."
              />
              <div className="space-y-4">
                <div className="flex items-center justify-between rounded-2xl border border-slate-200 bg-slate-50 px-4 py-4">
                  <div>
                    <div className="text-sm font-medium text-slate-900">Audience mix</div>
                    <div className="mt-1 text-sm text-[var(--muted-foreground)]">B2B and B2C counts come from the backend deliverability summary.</div>
                  </div>
                  <StatusBadge tone="info">Live data</StatusBadge>
                </div>
                <div className="flex items-center justify-between rounded-2xl border border-slate-200 bg-slate-50 px-4 py-4">
                  <div>
                    <div className="text-sm font-medium text-slate-900">Suppression safety</div>
                    <div className="mt-1 text-sm text-[var(--muted-foreground)]">Suppressed and unsubscribed contacts remain visible as blockers.</div>
                  </div>
                  <StatusBadge tone={(stats.suppressed_contacts || 0) > 0 ? "warning" : "success"}>
                    {(stats.suppressed_contacts || 0) > 0 ? "Needs review" : "Healthy"}
                  </StatusBadge>
                </div>
                <div className="flex items-center justify-between rounded-2xl border border-slate-200 bg-slate-50 px-4 py-4">
                  <div>
                    <div className="text-sm font-medium text-slate-900">Campaign workload</div>
                    <div className="mt-1 text-sm text-[var(--muted-foreground)]">Use the campaigns page to inspect preflight, lists, and real execution timing.</div>
                  </div>
                  <StatusBadge tone="neutral">{stats.active_campaigns || 0} active</StatusBadge>
                </div>
              </div>
            </SurfaceCard>
          </div>
        </>
      )}
    </div>
  );
}

function MiniMetric({ label, value, tone }: { label: string; value: number; tone: "success" | "warning" | "danger" }) {
  const classes = {
    success: "border-emerald-200 bg-emerald-50 text-emerald-800",
    warning: "border-amber-200 bg-amber-50 text-amber-900",
    danger: "border-rose-200 bg-rose-50 text-rose-900",
  } as const;
  return (
    <div className={`rounded-3xl border p-5 ${classes[tone]}`}>
      <div className="text-sm font-medium">{label}</div>
      <div className="mt-3 text-4xl font-semibold tracking-[-0.04em]">{value}</div>
    </div>
  );
}

function PriorityRow({ label, value, tone }: { label: string; value: number; tone: "warning" | "danger" | "info" }) {
  const toneClasses = {
    warning: "bg-amber-50 text-amber-900 border-amber-200",
    danger: "bg-rose-50 text-rose-900 border-rose-200",
    info: "bg-sky-50 text-sky-900 border-sky-200",
  } as const;
  return (
    <div className={`flex items-center justify-between rounded-2xl border px-4 py-4 ${toneClasses[tone]}`}>
      <div className="text-sm font-medium">{label}</div>
      <div className="text-2xl font-semibold tracking-[-0.04em]">{value}</div>
    </div>
  );
}

function ActionRow({ title, detail, href }: { title: string; detail: string; href: string }) {
  return (
    <Link href={href} className="group flex items-start justify-between gap-4 rounded-2xl border border-slate-200 bg-slate-50 px-4 py-4 transition-colors hover:bg-white">
      <div>
        <div className="text-sm font-semibold text-slate-900">{title}</div>
        <div className="mt-1 text-sm text-[var(--muted-foreground)]">{detail}</div>
      </div>
      <div className="mt-1 rounded-full bg-white p-2 text-slate-500 transition-colors group-hover:text-slate-900">
        <ArrowRight size={16} />
      </div>
    </Link>
  );
}
