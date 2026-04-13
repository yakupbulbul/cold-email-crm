"use client";

import { useAuth } from "@/context/AuthContext";
import { usePathname } from "next/navigation";
import { Menu } from "lucide-react";
import { useMemo, useState } from "react";

import Sidebar from "@/components/Sidebar";
import TopBar from "@/components/TopBar";
import Spinner from "@/components/ui/Spinner";

const PAGE_META: Record<string, { title: string; description: string }> = {
    "/": {
        title: "Dashboard",
        description: "Track infrastructure health, audience quality, and the next operational action across the product.",
    },
    "/domains": {
        title: "Domains",
        description: "Manage domain readiness, Mailcow visibility, and DNS verification without leaving the app.",
    },
    "/mailboxes": {
        title: "Mailboxes",
        description: "Configure sender identities, SMTP posture, and warm-up participation from one place.",
    },
    "/warmup": {
        title: "Warm-up",
        description: "Operate worker-backed warm-up safely with clear blockers, participating mailboxes, and recent activity.",
    },
    "/campaigns": {
        title: "Campaigns",
        description: "Create, monitor, and control reusable B2B and B2C campaigns with list-based execution.",
    },
    "/send-email": {
        title: "Send Email",
        description: "Validate real SMTP delivery directly, outside campaigns, using the same backend send pipeline.",
    },
    "/contacts": {
        title: "Contacts",
        description: "Manage audience quality, verification state, compliance posture, and bulk actions at scale.",
    },
    "/lists": {
        title: "Lists",
        description: "Build reusable audience groups and attach them across multiple campaigns without losing persistence.",
    },
    "/inbox": {
        title: "Inbox",
        description: "Review threads, understand replies, and keep operator attention on active conversations.",
    },
    "/suppression": {
        title: "Suppression",
        description: "Keep global suppression explicit and operationally visible so blocked addresses never re-enter sends.",
    },
    "/ops": {
        title: "Operations",
        description: "Inspect backend readiness, worker health, deliverability, jobs, and blockers from one command center.",
    },
    "/settings": {
        title: "Settings",
        description: "Review backend runtime state, worker mode, and Mailcow configuration without exposing secrets.",
    },
};

export default function AppLayout({ children }: { children: React.ReactNode }) {
    const { token, isLoading } = useAuth();
    const pathname = usePathname();
    const [mobileNavOpen, setMobileNavOpen] = useState(false);

    const isAuthRoute = pathname === "/signin" || pathname === "/login";
    const pageMeta = useMemo(() => {
        if (!pathname) return PAGE_META["/"];
        if (pathname.startsWith("/ops")) {
            return PAGE_META["/ops"];
        }
        if (pathname.startsWith("/contacts")) {
            return PAGE_META["/contacts"];
        }
        return PAGE_META[pathname] || {
            title: "Campaign Manager",
            description: "Operational control for outreach, inbox health, infrastructure, and sender safety.",
        };
    }, [pathname]);

    if (isAuthRoute) {
        return <div className="w-full">{children}</div>;
    }

    if (isLoading) {
        return (
            <div className="min-h-screen flex items-center justify-center bg-slate-50 w-full font-bold text-slate-400">
                <div className="flex flex-col items-center gap-4">
                    <Spinner size="lg" />
                    <span>Hydrating Secure Session...</span>
                </div>
            </div>
        );
    }

    if (!token) {
        return null; // AuthContext handles the redirect to /signin
    }

    return (
        <div className="flex min-h-screen w-full bg-[var(--background)] text-[var(--foreground)]">
            <Sidebar mobileOpen={mobileNavOpen} onClose={() => setMobileNavOpen(false)} />
            <div className="flex min-h-screen min-w-0 flex-1 flex-col lg:ml-72">
                <TopBar
                    title={pageMeta.title}
                    menuButton={(
                        <button
                            type="button"
                            onClick={() => setMobileNavOpen(true)}
                            className="inline-flex h-11 w-11 items-center justify-center rounded-2xl border border-slate-200 bg-white text-slate-700 shadow-sm lg:hidden"
                            aria-label="Open navigation"
                        >
                            <Menu size={20} />
                        </button>
                    )}
                />
                <main className="flex-1 overflow-y-auto px-4 pb-8 pt-4 sm:px-6 lg:px-8">
                    <div className="page-container">
                    {children}
                    </div>
                </main>
            </div>
        </div>
    );
}
