import Image from 'next/image';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { LayoutDashboard, Globe, Send, Inbox, Activity, Server, Users, Settings, ShieldX, TrendingUp, Network, Bell, Cpu, ListChecks, MailPlus, X, ClipboardList } from 'lucide-react';
import { cn } from '@/lib/utils';

const NAV_GROUPS = [
  {
    title: "Overview",
    items: [
      { href: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
      { href: "/command-center", label: "Command Center", icon: ClipboardList },
    ],
  },
  {
    title: "Infrastructure",
    items: [
      { href: "/domains", label: "Domains", icon: Server },
      { href: "/mailboxes", label: "Mailboxes", icon: Globe },
      { href: "/warmup", label: "Warm-up", icon: Activity },
    ],
  },
  {
    title: "Audience & Sending",
    items: [
      { href: "/campaigns", label: "Campaigns", icon: Send },
      { href: "/send-email", label: "Send Email", icon: MailPlus },
      { href: "/contacts", label: "Contacts", icon: Users },
      { href: "/lists", label: "Lists", icon: ListChecks },
      { href: "/inbox", label: "Inbox", icon: Inbox },
      { href: "/suppression", label: "Suppression", icon: ShieldX },
    ],
  },
  {
    title: "Operations",
    items: [
      { href: "/ops", label: "System Health", icon: Activity },
      { href: "/ops/deliverability", label: "Deliverability", icon: TrendingUp },
      { href: "/ops/jobs", label: "Worker Queues", icon: Network },
      { href: "/ops/alerts", label: "System Alerts", icon: Bell },
      { href: "/ops/readiness", label: "Prod Readiness", icon: Cpu },
      { href: "/settings", label: "Settings", icon: Settings },
    ],
  },
] as const;

export default function Sidebar({
  mobileOpen = false,
  onClose,
}: {
  mobileOpen?: boolean;
  onClose?: () => void;
}) {
  const pathname = usePathname();

  return (
    <>
      <div
        className={cn(
          "fixed inset-0 z-40 bg-slate-950/45 backdrop-blur-sm transition-opacity lg:hidden",
          mobileOpen ? "opacity-100" : "pointer-events-none opacity-0",
        )}
        onClick={onClose}
      />
      <aside
        className={cn(
          "fixed inset-y-0 left-0 z-50 flex h-screen w-[18rem] flex-col border-r border-slate-800 bg-[var(--sidebar)] text-[var(--sidebar-foreground)] transition-transform lg:z-20 lg:translate-x-0",
          mobileOpen ? "translate-x-0" : "-translate-x-full",
        )}
      >
      <div className="border-b border-slate-800 px-5 py-5">
        <div className="mb-4 flex items-center justify-between lg:hidden">
          <div className="text-xs font-semibold uppercase tracking-[0.24em] text-slate-500">Navigation</div>
          <button
            type="button"
            onClick={onClose}
            className="inline-flex h-10 w-10 items-center justify-center rounded-2xl border border-slate-700 text-slate-300"
            aria-label="Close navigation"
          >
            <X size={18} />
          </button>
        </div>
        <Link href="/dashboard" className="flex items-center gap-4" onClick={onClose}>
          <div className="rounded-2xl bg-white px-4 py-3">
            <Image
              src="/crm-logo.png"
              alt="Campaign Manager"
              width={78}
              height={40}
              priority
              className="h-auto w-full max-w-[78px]"
            />
          </div>
          <div>
            <div className="text-sm font-semibold text-white">Campaign Manager</div>
            <div className="text-xs text-slate-400">B2B + B2C outreach ops</div>
          </div>
        </Link>
      </div>
      <nav className="flex-1 space-y-7 overflow-y-auto px-4 py-6 pb-8">
        {NAV_GROUPS.map((group) => (
          <div key={group.title}>
            <div className="px-3 text-[11px] font-semibold uppercase tracking-[0.22em] text-slate-500">
              {group.title}
            </div>
            <div className="mt-3 space-y-1.5">
              {group.items.map((item) => {
                const isActive = item.href === "/ops"
                  ? pathname === "/ops" || pathname.startsWith("/ops/")
                  : item.href === "/contacts"
                    ? pathname === "/contacts" || pathname.startsWith("/contacts/")
                    : pathname === item.href;
                const Icon = item.icon;
                return (
                  <Link
                    key={item.href}
                    href={item.href}
                    onClick={onClose}
                    className={cn(
                      "group flex items-center gap-3 rounded-2xl px-3 py-3 text-sm font-medium transition-all",
                      isActive
                        ? "bg-white text-slate-900 shadow-sm"
                        : "text-slate-300 hover:bg-slate-800 hover:text-white",
                    )}
                  >
                    <div className={cn("rounded-xl p-2", isActive ? "bg-slate-100 text-slate-700" : "bg-slate-800 text-slate-400 group-hover:bg-slate-700 group-hover:text-slate-200")}>
                      <Icon size={16} />
                    </div>
                    <span>{item.label}</span>
                  </Link>
                );
              })}
            </div>
          </div>
        ))}
      </nav>
    </aside>
    </>
  );
}
