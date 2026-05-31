"use client";

import Link from "next/link";
import Image from "next/image";
import { useAuth } from "@/context/AuthContext";
import {
  ArrowRight,
  Globe,
  Inbox,
  MailPlus,
  Network,
  Send,
  Sparkles,
  Users,
} from "lucide-react";

const MODULES = [
  { title: "Domains", href: "/signin", icon: Globe },
  { title: "Mailboxes", href: "/signin", icon: MailPlus },
  { title: "Campaigns", href: "/signin", icon: Send },
  { title: "Contacts", href: "/signin", icon: Users },
  { title: "Inbox", href: "/signin", icon: Inbox },
  { title: "Warm-up & Ops", href: "/signin", icon: Network },
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
    <div className="min-h-screen bg-[linear-gradient(180deg,#faf8f5_0%,#f0ebe4_45%,#faf8f5_100%)] text-[var(--foreground)]">
      <div className="mx-auto max-w-7xl px-4 py-5 sm:px-6 lg:px-8">
        <header className="flex items-center justify-between gap-4 rounded-[2rem] border border-white/80 bg-[var(--surface)]/80 px-5 py-4 shadow-[0_20px_50px_rgba(45,31,20,0.07)] backdrop-blur sm:px-6">
          <Link href="/" className="flex items-center gap-3">
            <div className="rounded-2xl bg-[var(--sidebar)] px-4 py-3">
              <Image src="/crm-logo.png" alt="Campaign Manager" width={78} height={38} className="h-auto w-[78px]" priority />
            </div>
            <div>
              <div className="text-sm font-semibold tracking-[-0.02em] text-[var(--foreground)]">Campaign Manager</div>
              <div className="text-xs text-[var(--muted-foreground)]">Cold email CRM and operator workspace</div>
            </div>
          </Link>
          <div className="flex items-center gap-3">
            <Link href={primaryHref} className="btn-secondary px-4 py-2.5 text-sm">
              {token ? "Open workspace" : "Sign in"}
            </Link>
            <a href="#product" className="hidden text-sm font-medium text-[var(--muted-foreground)] hover:text-[var(--foreground)] sm:inline-flex">
              Explore product
            </a>
          </div>
        </header>

        <main className="space-y-8 py-8 sm:space-y-12 sm:py-12">
          <section className="rounded-[2rem] border border-white/70 bg-[var(--surface)]/88 p-6 shadow-[0_28px_70px_rgba(45,31,20,0.08)] backdrop-blur sm:p-8 lg:p-10">
            <div className="max-w-2xl">
              <div className="inline-flex items-center gap-2 rounded-full border border-[#b8d4b6] bg-[#d4e4d3] px-3 py-1 text-xs font-semibold uppercase tracking-[0.18em] text-[#2d6a4f]">
                <Sparkles size={14} />
                Outreach operations
              </div>
              <h1 className="mt-5 text-4xl font-semibold tracking-[-0.06em] text-[var(--foreground)] sm:text-5xl lg:text-[3.7rem] lg:leading-[0.95]">
                Cold email campaigns, inbox, and warm-up — one workspace.
              </h1>
              <p className="mt-5 max-w-xl text-base leading-7 text-[var(--muted-foreground)] sm:text-lg">
                Manage domains, mailboxes, contacts, and replies without switching tools.
              </p>
              <div className="mt-7 flex flex-col gap-3 sm:flex-row">
                <Link href={primaryHref} className="btn-primary px-5 py-3 text-sm sm:text-base">
                  {primaryLabel}
                  <ArrowRight size={16} />
                </Link>
                <a href="#workflow" className="btn-secondary px-5 py-3 text-sm sm:text-base">
                  How it works
                </a>
              </div>
            </div>
          </section>

          <section id="product">
            <h2 className="text-2xl font-semibold tracking-[-0.04em] text-[var(--foreground)]">
              One surface for your entire outbound stack.
            </h2>
            <div className="mt-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
              {MODULES.map((module) => (
                <Link key={module.title} href={token ? "/dashboard" : module.href} className="flex items-center gap-4 rounded-[1.75rem] border border-[var(--border)] bg-[var(--surface)] p-5 shadow-[var(--shadow-soft)] transition-shadow hover:shadow-md">
                  <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-2xl bg-[var(--sidebar)] text-white">
                    <module.icon size={18} />
                  </div>
                  <h3 className="text-base font-semibold tracking-[-0.02em] text-[var(--foreground)]">{module.title}</h3>
                </Link>
              ))}
            </div>
          </section>

          <section id="workflow" className="rounded-[2rem] border border-[#3d2e22] bg-[var(--sidebar)] p-6 text-[#faf8f5] shadow-[0_28px_60px_rgba(45,31,20,0.2)] sm:p-8">
            <div className="text-xs font-semibold uppercase tracking-[0.22em] text-[#8b7e74]">How it works</div>
            <h2 className="mt-3 text-2xl font-semibold tracking-[-0.04em]">
              From setup to replies in five steps.
            </h2>
            <div className="mt-6 space-y-3">
              {WORKFLOW.map((step, index) => (
                <div key={step} className="flex items-start gap-4 rounded-2xl border border-white/10 bg-[var(--surface)]/5 px-4 py-3">
                  <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-[var(--surface)] text-xs font-semibold text-[var(--foreground)]">
                    {index + 1}
                  </div>
                  <div className="text-sm leading-6 text-[#d4c9bc]">{step}</div>
                </div>
              ))}
            </div>
            <div className="mt-7">
              <Link href={primaryHref} className="btn-primary px-5 py-3 text-sm">
                {primaryLabel}
                <ArrowRight size={16} />
              </Link>
            </div>
          </section>
        </main>
      </div>
    </div>
  );
}
