"use client";

import { useEffect, useState } from "react";
import { useApi } from "@/hooks/useApi";
import { Activity, Database, Server, ServerCrash, CheckCircle2, AlertTriangle, XCircle, MailWarning, Network } from "lucide-react";
import Link from "next/link";

export default function OpsDashboard() {
    const { request, loading } = useApi();
    const [health, setHealth] = useState<any>(null);

    useEffect(() => {
        const fetchHealth = async () => {
            const data = await request("/ops/health");
            if (data) setHealth(data);
        };
        fetchHealth();
    }, [request]);

    const getStatusIcon = (status: string) => {
        if (status === "healthy") return <CheckCircle2 className="text-emerald-500" size={24} />;
        if (status === "degraded") return <AlertTriangle className="text-amber-500" size={24} />;
        return <XCircle className="text-red-500" size={24} />;
    };

    const StatusCard = ({ title, icon, data }: { title: string, icon: any, data: any }) => (
        <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm flex flex-col justify-between hover:shadow-md transition-shadow">
            <div className="flex items-center justify-between mb-4">
                <div className="flex items-center gap-3">
                    <div className="p-2.5 bg-slate-50 rounded-xl text-slate-600">{icon}</div>
                    <span className="font-bold text-slate-800 tracking-tight">{title}</span>
                </div>
                {data ? getStatusIcon(data.status) : <div className="w-6 h-6 bg-slate-100 rounded-full animate-pulse"/>}
            </div>
            
            <div className="space-y-2 mt-2">
                {data?.status === "failed" && (
                    <div className="text-xs font-bold text-red-600 bg-red-50 p-2 rounded-lg">Error details available in logs.</div>
                )}
                {data?.active_count !== undefined && (
                    <div className="flex justify-between text-sm">
                        <span className="text-slate-500 font-medium">Active Nodes</span>
                        <span className="font-bold text-slate-800">{data.active_count} / {data.total_registered}</span>
                    </div>
                )}
                {data?.latency_ms !== undefined && (
                    <div className="flex justify-between text-sm">
                        <span className="text-slate-500 font-medium">Ping Latency</span>
                        <span className="font-bold text-slate-800">{data.latency_ms}ms</span>
                    </div>
                )}
            </div>
        </div>
    );

    return (
        <div className="space-y-6 animate-fade-in relative min-h-screen pb-12">
            <div className="flex items-center justify-between">
                <div>
                    <h1 className="text-3xl font-bold text-slate-800 tracking-tight flex items-center gap-3">
                        <Activity className="text-blue-500" size={32} /> Ops Command Center
                    </h1>
                    <p className="text-slate-500 mt-2 text-sm font-medium">
                        Real-time Telemetry, Observability, and Delivery Infrastructure monitoring arrays.
                    </p>
                </div>
                <div className="flex items-center gap-3">
                    <Link href="/ops/jobs" className="px-5 py-2.5 bg-white border border-slate-200 hover:bg-slate-50 text-slate-700 font-bold rounded-xl transition-all shadow-sm active:scale-95">
                        Worker Queues
                    </Link>
                    <Link href="/ops/alerts" className="px-5 py-2.5 bg-slate-900 hover:bg-black text-white font-bold rounded-xl transition-all shadow-lg active:scale-95">
                        System Alerts
                    </Link>
                </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mt-8">
                <StatusCard title="Core Database" icon={<Database/>} data={health?.components?.postgres} />
                <StatusCard title="Redis Backplane" icon={<Server/>} data={health?.components?.redis} />
                <StatusCard title="Background Workers" icon={<Network/>} data={health?.components?.workers} />
                <StatusCard title="SMTP/IMAP Infrastructure" icon={<ServerCrash/>} data={health?.components?.smtp_engine} />
            </div>

            {/* Simulated Live Action Feed Panel */}
            <div className="grid grid-cols-3 gap-6 mt-8">
                <div className="col-span-2 bg-white rounded-2xl border border-slate-200 shadow-sm p-6 line-clamp-none h-96">
                    <h3 className="font-bold text-slate-800 mb-6 flex items-center gap-2">
                        <MailWarning size={20} className="text-amber-500" /> Recent Preflight & Delivery Blockers
                    </h3>
                    <div className="space-y-4">
                        <div className="p-3 border-l-4 border-red-500 bg-red-50 text-sm font-bold text-red-800 rounded-r-lg">
                            Campaign "Q3 SaaS Reachout" halted. Preflight validation failed: 40% leads identified as Disposable.
                        </div>
                        <div className="p-3 border-l-4 border-amber-500 bg-amber-50 text-sm font-bold text-amber-800 rounded-r-lg">
                            Mailbox "dev@example.com" Daily Limit (50/50) exceeded. Jobs deferred to queue.
                        </div>
                    </div>
                </div>
                
                <div className="col-span-1 bg-white rounded-2xl border border-slate-200 shadow-sm p-6 overflow-hidden">
                    <h3 className="font-bold text-slate-800 mb-6">Live Pulse</h3>
                    <div className="flex flex-col gap-4">
                        <div className="flex justify-between items-center bg-slate-50 p-3 rounded-lg">
                            <span className="text-slate-500 font-bold text-xs uppercase">Emails Sent Today</span>
                            <span className="text-blue-600 font-black text-xl">14,203</span>
                        </div>
                        <div className="flex justify-between items-center bg-slate-50 p-3 rounded-lg">
                            <span className="text-slate-500 font-bold text-xs uppercase">Bounces Blocked</span>
                            <span className="text-amber-600 font-black text-xl">412</span>
                        </div>
                        <div className="flex justify-between items-center bg-slate-50 p-3 rounded-lg">
                            <span className="text-slate-500 font-bold text-xs uppercase">Queue Backlog</span>
                            <span className="text-slate-700 font-black text-xl">0</span>
                        </div>
                    </div>
                </div>
            </div>

        </div>
    );
}
