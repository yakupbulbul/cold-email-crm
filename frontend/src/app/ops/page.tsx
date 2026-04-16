"use client";

import { useApiService } from "@/services/api";
import { ReactNode, useEffect, useState } from "react";
import { SystemHealth, Alert, DeliverabilitySummary, HealthComponent, SettingsSummary } from "@/types/models";
import { Database, Server, ServerCrash, CheckCircle2, AlertTriangle, XCircle, MailWarning, Network, Mail } from "lucide-react";
import Link from "next/link";
import { PageHeader, SurfaceCard } from "@/components/ui/primitives";

function getStatusIcon(status: string) {
    if (status === "healthy") return <CheckCircle2 className="text-emerald-500" size={24} />;
    if (status === "degraded") return <AlertTriangle className="text-amber-500" size={24} />;
    return <XCircle className="text-red-500" size={24} />;
}

function StatusCard({ title, icon, data }: { title: string; icon: ReactNode; data?: HealthComponent | null }) {
    return (
        <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm flex flex-col justify-between hover:shadow-md transition-shadow h-full">
            <div className="flex items-center justify-between mb-4">
                <div className="flex items-center gap-3">
                    <div className="p-2.5 bg-slate-50 rounded-xl text-slate-600">{icon}</div>
                    <span className="font-bold text-slate-800 tracking-tight">{title}</span>
                </div>
                {data ? getStatusIcon(data.status) : <div className="w-6 h-6 bg-slate-100 rounded-full animate-pulse" />}
            </div>

            <div className="space-y-2 mt-2 flex-grow">
                {data?.status === "failed" && (
                    <div className="text-xs font-bold text-red-600 bg-red-50 p-2 rounded-lg">Error details available in logs.</div>
                )}
                {data?.active_count !== undefined && (
                    <div className="flex justify-between text-sm mt-auto">
                        <span className="text-slate-500 font-medium">Active Nodes</span>
                        <span className="font-bold text-slate-800">{data.active_count} / {data.total_registered}</span>
                    </div>
                )}
                {data?.latency_ms !== undefined && (
                    <div className="flex justify-between text-sm mt-auto">
                        <span className="text-slate-500 font-medium">Ping Latency</span>
                        <span className="font-bold text-slate-800">{data.latency_ms}ms</span>
                    </div>
                )}
                {data?.status === "healthy" && data?.active_count === undefined && data?.latency_ms === undefined && (
                    <div className="text-xs font-bold text-emerald-600 bg-emerald-50 p-2 rounded-lg mt-auto">Component Online.</div>
                )}
            </div>
        </div>
    );
}

export default function OpsDashboard() {
    const { getHealth, getAlerts, getDeliverabilitySummary, getSettingsSummary, loading } = useApiService();
    const [health, setHealth] = useState<SystemHealth | null>(null);
    const [alerts, setAlerts] = useState<Alert[]>([]);
    const [deliverability, setDeliverability] = useState<DeliverabilitySummary | null>(null);
    const [settingsSummary, setSettingsSummary] = useState<SettingsSummary | null>(null);

    useEffect(() => {
        const fetchDashboardData = async () => {
            const h = await getHealth();
            if (h) setHealth(h);
            const a = await getAlerts();
            if (a) setAlerts(a);
            const d = await getDeliverabilitySummary();
            if (d) setDeliverability(d);
            const s = await getSettingsSummary();
            if (s) setSettingsSummary(s);
        };
        fetchDashboardData();
    }, [getHealth, getAlerts, getDeliverabilitySummary, getSettingsSummary]);

    const liveMetrics = [
        { label: "Valid Contacts", value: deliverability?.valid_contacts ?? 0, tone: "text-emerald-600" },
        { label: "Suppressed Contacts", value: deliverability?.suppressed_contacts ?? 0, tone: "text-amber-600" },
        { label: "Unsubscribed Contacts", value: deliverability?.unsubscribed_contacts ?? 0, tone: "text-rose-600" },
        { label: "B2C Campaigns", value: deliverability?.b2c_campaigns ?? 0, tone: "text-violet-600" },
    ];

    return (
        <div className="space-y-6 animate-fade-in relative min-h-screen pb-12">
            <PageHeader
                eyebrow="Operations"
                title="Ops command center"
                description="Inspect backend, worker, alert, and deliverability posture with backend-driven readiness and blocker visibility."
                actions={(
                <div className="flex items-center gap-3">
                    <Link href="/ops/jobs" className="px-5 py-2.5 bg-white border border-slate-200 hover:bg-slate-50 text-slate-700 font-bold rounded-xl transition-all shadow-sm active:scale-95">
                        Worker Queues
                    </Link>
                    <Link href="/ops/alerts" className="px-5 py-2.5 bg-slate-900 hover:bg-black text-white font-bold rounded-xl transition-all shadow-lg active:scale-95">
                        System Alerts
                    </Link>
                </div>
                )}
            />

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mt-8 items-stretch">
                <StatusCard title="Core Database" icon={<Database/>} data={health?.components?.postgres} />
                <StatusCard title="Redis Backplane" icon={<Server/>} data={health?.components?.redis} />
                <StatusCard title="Background Workers" icon={<Network/>} data={health?.components?.workers} />
                <StatusCard title="SMTP/IMAP Infrastructure" icon={<ServerCrash/>} data={health?.components?.smtp_engine} />
            </div>

            {/* Live Action Feed Panel */}
            <div className="grid grid-cols-3 gap-6 mt-8">
                <SurfaceCard className="col-span-2 p-6 overflow-y-auto h-96">
                    <h3 className="font-bold text-slate-800 mb-6 flex items-center gap-2 sticky top-0 bg-white z-10 pb-2 border-b border-slate-100">
                        <MailWarning size={20} className="text-amber-500" /> Recent System Alerts & Blockers
                    </h3>
                    <div className="space-y-4">
                        {loading && alerts.length === 0 ? (
                           <div className="flex justify-center p-8"><span className="animate-pulse text-slate-400">Loading alerts...</span></div>
                        ) : alerts.length === 0 ? (
                            <div className="p-8 text-center text-slate-400">No active system alerts detected. Systems are stable.</div>
                        ) : (
                            alerts.map((alert) => (
                                <div key={alert.id} className={`p-3 border-l-4 ${alert.severity === 'critical' ? 'border-red-500 bg-red-50 text-red-800' : 'border-amber-500 bg-amber-50 text-amber-800'} text-sm font-bold rounded-r-lg`}>
                                    <p className="font-black mb-1">{alert.title}</p>
                                    <p className="font-medium text-xs">{alert.message}</p>
                                </div>
                            ))
                        )}
                    </div>
                </SurfaceCard>
                
                <SurfaceCard className="col-span-1 p-6 overflow-hidden">
                    <h3 className="font-bold text-slate-800 mb-6">Live Pulse</h3>
                    <div className="flex flex-col gap-4">
                        <div className="flex justify-between items-center bg-slate-50 p-3 rounded-lg">
                            <span className="text-slate-500 font-bold text-xs uppercase">Emails Sent Today</span>
                            <span className="text-blue-600 font-black text-xl">{deliverability?.sent || 0}</span>
                        </div>
                        <div className="flex justify-between items-center bg-slate-50 p-3 rounded-lg">
                            <span className="text-slate-500 font-bold text-xs uppercase">Bounces Blocked</span>
                            <span className="text-amber-600 font-black text-xl">{deliverability?.suppressed || 0}</span>
                        </div>
                        {liveMetrics.map((metric) => (
                            <div key={metric.label} className="flex justify-between items-center bg-slate-50 p-3 rounded-lg">
                                <span className="text-slate-500 font-bold text-xs uppercase">{metric.label}</span>
                                <span className={`${metric.tone} font-black text-xl`}>{metric.value}</span>
                            </div>
                        ))}
                    </div>
                </SurfaceCard>
            </div>

            {settingsSummary ? (
                <div className="grid grid-cols-1 gap-6 md:grid-cols-2 mt-8">
                    {(["mailcow", "google_workspace"] as const).map((provider) => {
                        const item = settingsSummary.providers[provider];
                        return (
                            <SurfaceCard key={provider} className="p-6">
                                <div className="flex items-center justify-between">
                                    <div>
                                        <div className="text-xs font-bold uppercase tracking-[0.18em] text-slate-500">Provider</div>
                                        <div className="mt-2 text-xl font-extrabold text-slate-900">{provider === "mailcow" ? "Mailcow" : "Google Workspace"}</div>
                                    </div>
                                    <div className="rounded-xl border border-slate-200 bg-slate-50 p-3 text-slate-700">
                                        <Mail size={18} />
                                    </div>
                                </div>
                                <div className="mt-4 flex flex-wrap gap-2">
                                    <span className="rounded-full border border-slate-200 bg-white px-3 py-1 text-xs font-semibold text-slate-700">
                                        {item.enabled ? "Enabled" : "Disabled"}
                                    </span>
                                    <span className="rounded-full border border-slate-200 bg-white px-3 py-1 text-xs font-semibold text-slate-700">
                                        {item.configured ? "Configured" : "Not configured"}
                                    </span>
                                    <span className="rounded-full border border-slate-200 bg-white px-3 py-1 text-xs font-semibold text-slate-700">
                                        {item.status}
                                    </span>
                                </div>
                                <div className="mt-4 text-sm text-slate-600">{item.detail || "No provider detail available."}</div>
                            </SurfaceCard>
                        );
                    })}
                </div>
            ) : null}

        </div>
    );
}
