"use client";

import { AlertCircle, CheckCircle2, Info, LucideIcon, TriangleAlert } from "lucide-react";

import { cn } from "@/lib/utils";

export function PageHeader({
  eyebrow,
  title,
  description,
  actions,
}: {
  eyebrow?: string;
  title: string;
  description?: string;
  actions?: React.ReactNode;
}) {
  return (
    <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
      <div className="min-w-0">
        {eyebrow ? (
          <div className="text-xs font-semibold uppercase tracking-[0.24em] text-[var(--muted-foreground)]">
            {eyebrow}
          </div>
        ) : null}
        <h1 className="mt-2 text-3xl font-semibold tracking-[-0.03em] text-[var(--foreground)] sm:text-4xl">
          {title}
        </h1>
        {description ? (
          <p className="mt-3 max-w-3xl text-sm leading-6 text-[var(--muted-foreground)] sm:text-[15px]">
            {description}
          </p>
        ) : null}
      </div>
      {actions ? <div className="flex flex-wrap items-center gap-3">{actions}</div> : null}
    </div>
  );
}

export function SurfaceCard({
  className,
  children,
}: {
  className?: string;
  children: React.ReactNode;
}) {
  return <section className={cn("surface-card", className)}>{children}</section>;
}

export function SectionTitle({
  title,
  description,
  action,
}: {
  title: string;
  description?: string;
  action?: React.ReactNode;
}) {
  return (
    <div className="mb-5 flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
      <div>
        <h2 className="text-lg font-semibold tracking-[-0.02em] text-[var(--foreground)]">{title}</h2>
        {description ? <p className="mt-1 text-sm text-[var(--muted-foreground)]">{description}</p> : null}
      </div>
      {action}
    </div>
  );
}

export function MetricCard({
  title,
  value,
  detail,
  icon: Icon,
  tone = "neutral",
}: {
  title: string;
  value: string | number;
  detail?: string;
  icon?: LucideIcon;
  tone?: "neutral" | "success" | "warning" | "danger" | "info";
}) {
  const toneClasses = {
    neutral: "bg-[var(--accent)] text-[var(--foreground)]",
    success: "bg-emerald-50 text-emerald-700",
    warning: "bg-amber-50 text-amber-700",
    danger: "bg-rose-50 text-rose-700",
    info: "bg-sky-50 text-sky-700",
  } as const;

  return (
    <SurfaceCard className="p-5">
      <div className="flex items-start justify-between gap-4">
        <div>
          <div className="text-sm font-medium text-[var(--muted-foreground)]">{title}</div>
          <div className="mt-3 text-3xl font-semibold tracking-[-0.04em] text-[var(--foreground)]">{value}</div>
          {detail ? <div className="mt-2 text-sm text-[var(--muted-foreground)]">{detail}</div> : null}
        </div>
        {Icon ? (
          <div className={cn("rounded-2xl p-3", toneClasses[tone])}>
            <Icon size={20} />
          </div>
        ) : null}
      </div>
    </SurfaceCard>
  );
}

export function StatusBadge({
  children,
  tone = "neutral",
  className,
}: {
  children: React.ReactNode;
  tone?: "neutral" | "success" | "warning" | "danger" | "info";
  className?: string;
}) {
  const toneClasses = {
    neutral: "border-slate-200 bg-slate-100 text-slate-700",
    success: "border-emerald-200 bg-emerald-50 text-emerald-700",
    warning: "border-amber-200 bg-amber-50 text-amber-700",
    danger: "border-rose-200 bg-rose-50 text-rose-700",
    info: "border-sky-200 bg-sky-50 text-sky-700",
  } as const;

  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 rounded-full border px-3 py-1 text-xs font-semibold capitalize",
        toneClasses[tone],
        className,
      )}
    >
      {children}
    </span>
  );
}

export function AlertBanner({
  tone = "info",
  title,
  children,
}: {
  tone?: "info" | "success" | "warning" | "danger";
  title?: string;
  children: React.ReactNode;
}) {
  const config = {
    info: {
      icon: Info,
      className: "border-sky-200 bg-sky-50 text-sky-800",
    },
    success: {
      icon: CheckCircle2,
      className: "border-emerald-200 bg-emerald-50 text-emerald-800",
    },
    warning: {
      icon: TriangleAlert,
      className: "border-amber-200 bg-amber-50 text-amber-900",
    },
    danger: {
      icon: AlertCircle,
      className: "border-rose-200 bg-rose-50 text-rose-900",
    },
  } as const;

  const Icon = config[tone].icon;

  return (
    <div className={cn("rounded-2xl border px-4 py-4", config[tone].className)}>
      <div className="flex items-start gap-3">
        <Icon size={18} className="mt-0.5 shrink-0" />
        <div className="min-w-0">
          {title ? <div className="font-semibold">{title}</div> : null}
          <div className={cn("text-sm", title ? "mt-1" : "")}>{children}</div>
        </div>
      </div>
    </div>
  );
}

export function EmptyState({
  title,
  description,
  action,
  icon: Icon = Info,
}: {
  title: string;
  description: string;
  action?: React.ReactNode;
  icon?: LucideIcon;
}) {
  return (
    <SurfaceCard className="flex min-h-[260px] flex-col items-center justify-center p-8 text-center">
      <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4 text-slate-500">
        <Icon size={24} />
      </div>
      <h3 className="mt-5 text-lg font-semibold text-[var(--foreground)]">{title}</h3>
      <p className="mt-2 max-w-md text-sm leading-6 text-[var(--muted-foreground)]">{description}</p>
      {action ? <div className="mt-6">{action}</div> : null}
    </SurfaceCard>
  );
}

export function FieldGroup({
  label,
  hint,
  error,
  children,
}: {
  label: string;
  hint?: string;
  error?: string | null;
  children: React.ReactNode;
}) {
  return (
    <label className="block space-y-2">
      <span className="text-sm font-medium text-[var(--foreground)]">{label}</span>
      {children}
      {error ? (
        <span className="text-sm text-rose-700">{error}</span>
      ) : hint ? (
        <span className="text-xs text-[var(--muted-foreground)]">{hint}</span>
      ) : null}
    </label>
  );
}

export function DetailItem({
  label,
  value,
}: {
  label: string;
  value: React.ReactNode;
}) {
  return (
    <div className="flex items-start justify-between gap-4 border-b border-slate-100 py-3 last:border-b-0 last:pb-0 first:pt-0">
      <div className="text-sm text-[var(--muted-foreground)]">{label}</div>
      <div className="text-right text-sm font-medium text-[var(--foreground)]">{value}</div>
    </div>
  );
}
