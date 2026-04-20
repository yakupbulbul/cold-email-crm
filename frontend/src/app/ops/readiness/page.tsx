"use client";

import { useEffect, useState } from "react";
import { useApi } from "@/hooks/useApi";
import { CheckCircle2, ShieldAlert, AlertTriangle, Cpu, HardDrive, ShieldCheck } from "lucide-react";
import Spinner from "@/components/ui/Spinner";

type ReadinessCheck = {
    category: string;
    check: string;
    detail: string;
    status: string;
};

type ReadinessResponse = {
    checklist?: ReadinessCheck[];
};

export default function ReadinessDashboard() {
    const { request, loading } = useApi();
    const [readiness, setReadiness] = useState<ReadinessResponse | null>(null);

    useEffect(() => {
        const fetchReadiness = async () => {
            const data = await request<ReadinessResponse>("/ops/readiness");
            if (data) setReadiness(data);
        };
        fetchReadiness();
    }, [request]);

    const getStatusIcon = (status: string) => {
        if (status === "pass") return <CheckCircle2 className="text-emerald-500" size={20} />;
        if (status === "warning") return <AlertTriangle className="text-amber-500" size={20} />;
        return <ShieldAlert className="text-red-500" size={20} />;
    };

    return (
        <div className="space-y-6 animate-fade-in relative min-h-screen pb-12">
            <h1 className="text-3xl font-bold text-slate-800 tracking-tight flex items-center gap-3">
                <Cpu className="text-blue-500" size={32} /> Production Readiness & Backups
            </h1>
            <p className="text-slate-500 font-medium max-w-2xl">
                Verify critical operational bounds securing your Cold Email cluster before initiating high-volume outreach sequences.
            </p>

            {loading ? <Spinner size="lg" /> : readiness && (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-8 mt-8">
                    
                    {/* Environmental Checklist Panel */}
                    <div className="bg-white rounded-2xl border border-slate-200 shadow-sm p-6">
                        <h3 className="text-lg font-bold text-slate-800 mb-6 flex items-center gap-2">
                            <ShieldCheck className="text-emerald-500" /> Environment Guardrails
                        </h3>
                        <div className="space-y-4">
                            {readiness.checklist?.map((check, i) => (
                                <div key={i} className="flex items-start justify-between p-4 bg-slate-50 rounded-xl border border-slate-100">
                                    <div>
                                        <div className="text-xs font-bold text-slate-400 uppercase tracking-widest">{check.category}</div>
                                        <div className="font-bold text-slate-800 mt-1">{check.check}</div>
                                        <div className="text-sm text-slate-500 mt-1">{check.detail}</div>
                                    </div>
                                    <div className="ml-4">{getStatusIcon(check.status)}</div>
                                </div>
                            ))}
                        </div>
                    </div>

                    {/* Operational Backup Strategy Panel */}
                    <div className="bg-white rounded-2xl border border-slate-200 shadow-sm p-6 h-fit bg-gradient-to-b from-white to-slate-50">
                        <h3 className="text-lg font-bold text-slate-800 mb-6 flex items-center gap-2">
                            <HardDrive className="text-purple-500" /> Operational Backup Strategy
                        </h3>
                        <div className="prose prose-sm text-slate-600">
                            <p className="font-bold text-slate-700">Database Persistence Rules:</p>
                            <ul>
                                <li>The PostgreSQL container volume <code>db_data</code> contains all Campaigns, Contacts, and Core Telemetry.</li>
                                <li>We recommend automated nightly `pg_dump` schedules routed asynchronously to an Amazon S3 bucket.</li>
                                <li>Redis workloads do not require active backups as Queue payloads are strictly transient.</li>
                            </ul>
                            
                            <p className="font-bold text-slate-700 mt-6">Restoration Procedure:</p>
                            <ul>
                                <li>Perform <code>docker-compose down</code> halting background celery tasks.</li>
                                <li>Run <code>pg_restore</code> resolving the target dump file physically.</li>
                                <li>Redeploy services safely. Data consistency will resume natively.</li>
                            </ul>

                            <div className="mt-6 p-4 bg-amber-50 border border-amber-200 rounded-xl text-amber-800 text-sm font-medium">
                                <AlertTriangle className="inline-block mr-2 text-amber-500" size={16}/> 
                                Always ensure <strong>Mailcow SMTP bounds</strong> are detached during restoration to prevent duplicate backlogged message deliveries.
                            </div>
                        </div>
                    </div>

                </div>
            )}
        </div>
    );
}
