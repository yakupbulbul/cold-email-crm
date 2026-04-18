"use client";

import Link from "next/link";
import Image from "next/image";
import { useAuth } from "@/context/AuthContext";
import {
  ArrowRight,
  BadgeCheck,
  Globe,
  Inbox,
  MailPlus,
  Network,
  Send,
  ShieldCheck,
  Sparkles,
  Users,
} from "lucide-react";

const MODULES = [
  {
    title: "Domains",
    description: "Set up sender domains, verify readiness, and keep infrastructure visible before campaigns go live.",
    href: "/signin",
    icon: Globe,
  },
  {
    title: "Mailboxes",
    description: "Connect mailboxes, validate transport health, and manage sender identity from one workspace.",
    href: "/signin",
    icon: MailPlus,
  },
  {
    title: "Campaigns",
    description: "Create reusable campaigns, attach lists, and control execution with operational clarity.",
    href: "/signin",
    icon: Send,
  },
  {
    title: "Contacts",
    description: "Organize leads, review verification posture, and keep audience quality obvious before sending.",
    href: "/signin",
    icon: Users,
  },
  {
    title: "Inbox",
    description: "Track real replies, review threads, and keep operators focused on active conversations.",
    href: "/signin",
    icon: Inbox,
  },
  {
    title: "Warm-up & Ops",
    description: "Monitor warm-up, worker health, queue state, and runtime blockers from the same product surface.",
    href: "/signin",
    icon: Network,
  },
] as const;

const WORKFLOW = [
  "Add and verify a sending domain",
  "Connect a mailbox and confirm provider health",
  "Import contacts and organize them into lists",
  "Launch campaigns and track reply activity",
  "Review inbox, warm-up, and operational health in one place",
] as const;

export default function LandingPage() {
  const { token } = useAuth();
  const primaryHref = token ? "/dashboard" : "/signin";
  const primaryLabel = token ? "Open workspace" : "Sign in to workspace";

  return (
    <div className="min-h-screen bg-[linear-gradient(180deg,#f7f9fc_0%,#eef4ff_45%,#f4f7fb_100%)] text-slate-950">
      <div className="mx-auto max-w-7xl px-4 py-5 sm:px-6 lg:px-8">
        <header className="flex items-center justify-between gap-4 rounded-[2rem] border border-white/80 bg-white/80 px-5 py-4 shadow-[0_20px_50px_rgba(15,23,42,0.07)] backdrop-blur sm:px-6">
          <Link href="/" className="flex items-center gap-3">
            <div className="rounded-2xl bg-slate-950 px-4 py-3">
              <Image src="/crm-logo.png" alt="Campaign Manager" width={78} height={38} className="h-auto w-[78px]" priority />
            </div>
            <div>
              <div className="text-sm font-semibold tracking-[-0.02em] text-slate-950">Campaign Manager</div>
              <div className="text-xs text-slate-500">Cold email CRM and operator workspace</div>
            </div>
          </Link>
          <div className="flex items-center gap-3">
            <Link href={primaryHref} className="btn-secondary px-4 py-2.5 text-sm">
              {token ? "Open workspace" : "Sign in"}
            </Link>
            <a href="#product" className="hidden text-sm font-medium text-slate-600 hover:text-slate-900 sm:inline-flex">
              Explore product
            </a>
          </div>
        </header>

        <main className="space-y-8 py-8 sm:space-y-12 sm:py-12">
          <section className="grid gap-8 rounded-[2rem] border border-white/70 bg-white/88 p-6 shadow-[0_28px_70px_rgba(15,23,42,0.08)] backdrop-blur sm:p-8 lg:grid-cols-[1.15fr,0.85fr] lg:items-center lg:p-10">
            <div className="max-w-2xl">
              <div className="inline-flex items-center gap-2 rounded-full border border-sky-200 bg-sky-50 px-3 py-1 text-xs font-semibold uppercase tracking-[0.18em] text-sky-700">
                <Sparkles size={14} />
                Unified outreach operations
              </div>
              <h1 className="mt-5 text-4xl font-semibold tracking-[-0.06em] text-slate-950 sm:text-5xl lg:text-[3.7rem] lg:leading-[0.95]">
                Run cold email infrastructure, campaigns, inbox, and warm-up from one product.
              </h1>
              <p className="mt-5 max-w-xl text-base leading-7 text-slate-600 sm:text-lg">
                Campaign Manager keeps domain setup, mailbox control, contacts, replies, warm-up, and operational health in one workspace so teams can run outbound systems without losing clarity.
              </p>
              <div className="mt-7 flex flex-col gap-3 sm:flex-row">
                <Link href={primaryHref} className="btn-primary px-5 py-3 text-sm sm:text-base">
                  {primaryLabel}
                  <ArrowRight size={16} />
                </Link>
                <a href="#workflow" className="btn-secondary px-5 py-3 text-sm sm:text-base">
                  Learn how it works
                </a>
              </div>
            </div>

            <div className="grid gap-4 sm:grid-cols-2">
              <LandingMetric
                title="Domains and senders"
                detail="Keep readiness, provider health, and sender posture visible before any campaign starts."
                icon={Globe}
              />
              <LandingMetric
                title="Campaign execution"
                detail="Launch and monitor campaigns with clear list, compliance, and delivery context."
                icon={Send}
              />
              <LandingMetric
                title="Reply operations"
                detail="Track inbox threads and operator follow-up without leaving the product."
                icon={Inbox}
              />
              <LandingMetric
                title="Warm-up and health"
                detail="Understand worker state, scheduler posture, and provider blockers in one place."
                icon={ShieldCheck}
              />
            </div>
          </section>

          <section id="product" className="grid gap-6 lg:grid-cols-[0.8fr,1.2fr]">
            <div className="rounded-[2rem] border border-slate-200 bg-white p-6 shadow-[var(--shadow-soft)] sm:p-7">
              <div className="text-xs font-semibold uppercase tracking-[0.22em] text-slate-500">Product overview</div>
              <h2 className="mt-3 text-2xl font-semibold tracking-[-0.04em] text-slate-950">
                Built for teams that need one operational surface instead of scattered tools.
              </h2>
              <p className="mt-4 text-sm leading-7 text-slate-600">
                The product brings together sender infrastructure, mailbox connectivity, campaign execution, contact quality, reply monitoring, warm-up, and runtime health so operators can see what is ready, blocked, or failing without guessing.
              </p>
              <div className="mt-6 space-y-3">
                <ValuePoint label="Public-safe overview" detail="The landing page explains the product without exposing internal metrics or private runtime state." />
                <ValuePoint label="One workspace" detail="The signed-in product keeps campaigns, inbox, and health views in a single operator console." />
                <ValuePoint label="Operational clarity" detail="The app is built around readiness, blockers, and next actions instead of decorative dashboards." />
              </div>
            </div>

            <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
              {MODULES.map((module) => (
                <article key={module.title} className="rounded-[1.75rem] border border-slate-200 bg-white p-5 shadow-[var(--shadow-soft)]">
                  <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-slate-900 text-white">
                    <module.icon size={18} />
                  </div>
                  <h3 className="mt-4 text-lg font-semibold tracking-[-0.03em] text-slate-950">{module.title}</h3>
                  <p className="mt-2 text-sm leading-6 text-slate-600">{module.description}</p>
                  <Link href={token ? "/dashboard" : module.href} className="mt-4 inline-flex items-center gap-2 text-sm font-semibold text-slate-900 hover:text-slate-700">
                    {token ? "Open workspace" : "Open in workspace"}
                    <ArrowRight size={15} />
                  </Link>
                </article>
              ))}
            </div>
          </section>

          <section id="workflow" className="grid gap-6 lg:grid-cols-[1.1fr,0.9fr]">
            <div className="rounded-[2rem] border border-slate-200 bg-slate-950 p-6 text-white shadow-[0_28px_60px_rgba(15,23,42,0.2)] sm:p-8">
              <div className="text-xs font-semibold uppercase tracking-[0.22em] text-slate-400">How it works</div>
              <h2 className="mt-3 text-2xl font-semibold tracking-[-0.04em]">
                A straightforward workflow from infrastructure to replies.
              </h2>
              <div className="mt-6 space-y-4">
                {WORKFLOW.map((step, index) => (
                  <div key={step} className="flex items-start gap-4 rounded-2xl border border-white/10 bg-white/5 px-4 py-4">
                    <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-white text-xs font-semibold text-slate-950">
                      {index + 1}
                    </div>
                    <div className="text-sm leading-6 text-slate-200">{step}</div>
                  </div>
                ))}
              </div>
            </div>

            <div className="rounded-[2rem] border border-slate-200 bg-white p-6 shadow-[var(--shadow-soft)] sm:p-8">
              <div className="text-xs font-semibold uppercase tracking-[0.22em] text-slate-500">Get started</div>
              <h2 className="mt-3 text-2xl font-semibold tracking-[-0.04em] text-slate-950">
                Use the product as a guided workspace, not a collection of disconnected pages.
              </h2>
              <p className="mt-4 text-sm leading-7 text-slate-600">
                Start with sender setup, move into mailbox and contact preparation, then use campaigns, inbox, and warm-up to operate with clear system feedback.
              </p>
              <div className="mt-6 grid gap-3">
                {[
                  "Set up a domain and mailbox",
                  "Import contacts and organize lists",
                  "Launch campaigns and inspect replies",
                  "Monitor warm-up and operations",
                ].map((item) => (
                  <div key={item} className="flex items-center gap-3 rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-700">
                    <BadgeCheck size={16} className="text-slate-900" />
                    {item}
                  </div>
                ))}
              </div>
              <div className="mt-8 flex flex-col gap-3 sm:flex-row">
                <Link href={primaryHref} className="btn-primary px-5 py-3 text-sm">
                  {token ? "Open workspace" : "Sign in"}
                </Link>
                <a href="#product" className="btn-secondary px-5 py-3 text-sm">
                  Explore sections
                </a>
              </div>
            </div>
          </section>
        </main>
      </div>
    </div>
  );
}

function LandingMetric({
  title,
  detail,
  icon: Icon,
}: {
  title: string;
  detail: string;
  icon: typeof Globe;
}) {
  return (
    <div className="rounded-[1.6rem] border border-slate-200 bg-slate-50/85 p-5">
      <div className="flex h-10 w-10 items-center justify-center rounded-2xl bg-white text-slate-900 shadow-sm">
        <Icon size={18} />
      </div>
      <div className="mt-4 text-base font-semibold tracking-[-0.02em] text-slate-950">{title}</div>
      <div className="mt-2 text-sm leading-6 text-slate-600">{detail}</div>
    </div>
  );
}

function ValuePoint({ label, detail }: { label: string; detail: string }) {
  return (
    <div className="rounded-2xl border border-slate-200 bg-slate-50 px-4 py-4">
      <div className="text-sm font-semibold text-slate-950">{label}</div>
      <div className="mt-1 text-sm leading-6 text-slate-600">{detail}</div>
    </div>
  );
}
