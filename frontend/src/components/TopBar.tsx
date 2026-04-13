import { Bell, User } from "lucide-react";

import { useAuth } from "@/context/AuthContext";

export default function TopBar({
  title,
  description,
  menuButton,
}: {
  title: string;
  description: string;
  menuButton?: React.ReactNode;
}) {
  const { user } = useAuth();

  return (
    <header className="sticky top-0 z-30 border-b border-slate-200/80 bg-[rgba(244,247,251,0.9)] backdrop-blur">
      <div className="page-container flex flex-col gap-4 px-4 py-4 sm:px-6 lg:px-8">
        <div className="flex items-start justify-between gap-4">
          <div className="flex min-w-0 items-start gap-3">
            <div className="lg:hidden">{menuButton}</div>
            <div className="min-w-0">
              <div className="text-xs font-semibold uppercase tracking-[0.24em] text-[var(--muted-foreground)]">
                Operations Platform
              </div>
              <div className="mt-1 text-2xl font-semibold tracking-[-0.03em] text-[var(--foreground)] sm:text-[2rem]">
                {title}
              </div>
              <p className="mt-1 max-w-2xl text-sm leading-6 text-[var(--muted-foreground)]">
                {description}
              </p>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <button className="relative inline-flex h-11 w-11 items-center justify-center rounded-2xl border border-slate-200 bg-white text-slate-600 shadow-sm hover:bg-slate-50">
              <Bell size={18} />
              <span className="absolute right-3 top-3 h-2.5 w-2.5 rounded-full bg-rose-500 ring-2 ring-white"></span>
            </button>
            <div className="hidden items-center gap-3 rounded-2xl border border-slate-200 bg-white px-3 py-2 shadow-sm sm:flex">
              <div className="flex h-10 w-10 items-center justify-center rounded-2xl bg-slate-900 text-white">
                <User size={16} />
              </div>
              <div className="min-w-0">
                <div className="truncate text-sm font-semibold text-slate-900">{user?.full_name || "Admin"}</div>
                <div className="text-xs text-[var(--muted-foreground)]">{user?.email || "Authenticated session"}</div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </header>
  );
}
