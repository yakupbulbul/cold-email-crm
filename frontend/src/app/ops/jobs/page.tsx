"use client";

import { useEffect, useState } from "react";
import { useApi } from "@/hooks/useApi";
import Table, { TableRow, TableCell } from "@/components/ui/Table";
import Spinner from "@/components/ui/Spinner";
import { Network, RefreshCw, XCircle, AlertTriangle } from "lucide-react";

type JobItem = {
    id: string;
    job_id: string;
    job_type: string;
    status: string;
    retry_count: number;
    started_at?: string | null;
    finished_at?: string | null;
};

type QueueStats = {
    queued?: number;
    running?: number;
    failed?: number;
    dead_letter?: number;
};

export default function JobQueueDashboard() {
    const { request, loading } = useApi();
    const [jobs, setJobs] = useState<JobItem[]>([]);
    const [stats, setStats] = useState<QueueStats>({});
    const [filter, setFilter] = useState("all");

    useEffect(() => {
        const fetchJobs = async () => {
            const data = await request<JobItem[]>(`/ops/jobs?status=${filter}`);
            if (data) setJobs(data);
            const sq = await request<QueueStats>("/ops/jobs/queue-stats");
            if (sq) setStats(sq);
        };
        fetchJobs();
    }, [request, filter]);

    const handleRetry = async (jobId: string) => {
        await request(`/ops/jobs/${jobId}/retry`, { method: "POST" });
        setJobs(jobs.map(j => j.job_id === jobId ? { ...j, status: "queued", retry_count: j.retry_count + 1 } : j));
    };

    const handleCancel = async (jobId: string) => {
        await request(`/ops/jobs/${jobId}/cancel`, { method: "POST" });
        setJobs(jobs.map(j => j.job_id === jobId ? { ...j, status: "cancelled" } : j));
    };

    const getStatusBadge = (status: string) => {
        switch (status) {
            case "completed": return <span className="px-2 py-1 bg-green-100 text-green-700 font-bold rounded-lg text-xs">Completed</span>;
            case "failed": return <span className="px-2 py-1 bg-red-100 text-red-700 font-bold rounded-lg text-xs">Failed</span>;
            case "dead_letter": return <span className="px-2 py-1 bg-slate-800 text-white font-bold rounded-lg text-xs flex items-center gap-1 w-fit"><AlertTriangle size={12}/> Dead Letter</span>;
            case "queued": return <span className="px-2 py-1 bg-amber-100 text-amber-700 font-bold rounded-lg text-xs">Queued</span>;
            case "running": return <span className="px-2 py-1 bg-blue-100 text-blue-700 font-bold rounded-lg text-xs animate-pulse">Running</span>;
            default: return <span className="px-2 py-1 bg-slate-100 text-slate-700 font-bold rounded-lg text-xs">{status}</span>;
        }
    };

    return (
        <div className="space-y-6 animate-fade-in relative min-h-screen pb-12">
            <h1 className="text-3xl font-bold text-slate-800 tracking-tight flex items-center gap-3">
                <Network className="text-purple-500" size={32} /> Background Worker State
            </h1>

            <div className="grid grid-cols-4 gap-4 mt-6">
                <div className="bg-white p-5 rounded-2xl border border-slate-200">
                    <div className="text-sm font-bold text-slate-500">Queued</div>
                    <div className="text-2xl font-black text-amber-600">{stats.queued || 0}</div>
                </div>
                <div className="bg-white p-5 rounded-2xl border border-slate-200">
                    <div className="text-sm font-bold text-slate-500">Running</div>
                    <div className="text-2xl font-black text-blue-600">{stats.running || 0}</div>
                </div>
                <div className="bg-white p-5 rounded-2xl border border-slate-200">
                    <div className="text-sm font-bold text-slate-500">Failed / Dead Letter</div>
                    <div className="text-2xl font-black text-red-600">{(stats.failed || 0) + (stats.dead_letter || 0)}</div>
                </div>
            </div>

            <div className="bg-white rounded-2xl border border-slate-200 shadow-sm p-6 mt-8">
                <div className="flex gap-2 mb-6 border-b border-slate-100 pb-4">
                    {["all", "queued", "running", "failed", "dead_letter"].map(f => (
                        <button key={f} onClick={() => setFilter(f)} className={`px-4 py-2 font-bold rounded-lg text-sm transition-colors ${filter === f ? "bg-slate-900 text-white" : "bg-slate-50 text-slate-600 hover:bg-slate-100"}`}>
                            {f.replace("_", " ").toUpperCase()}
                        </button>
                    ))}
                </div>

                {loading ? <Spinner size="lg" /> : (
                    <Table columns={["Job ID", "Task Target", "Status", "Retries", "Duration", "Controls"]}>
                        {jobs.map(job => (
                            <TableRow key={job.id}>
                                <TableCell className="font-mono text-xs font-bold text-slate-500">{job.job_id?.substring(0,8)}</TableCell>
                                <TableCell className="font-bold text-slate-800">{job.job_type}</TableCell>
                                <TableCell>{getStatusBadge(job.status)}</TableCell>
                                <TableCell className="font-bold text-slate-600">{job.retry_count}</TableCell>
                                <TableCell className="text-slate-500 font-medium">
                                    {job.started_at && job.finished_at ? 
                                        ((new Date(job.finished_at).getTime() - new Date(job.started_at).getTime()) / 1000).toFixed(2) + "s" 
                                        : "-"
                                    }
                                </TableCell>
                                <TableCell>
                                    <div className="flex gap-2">
                                        {(job.status === "failed" || job.status === "dead_letter") && (
                                            <button onClick={() => handleRetry(job.job_id)} className="p-2 bg-blue-50 text-blue-600 hover:bg-blue-100 rounded-lg transition-colors" title="Retry Job">
                                                <RefreshCw size={16} />
                                            </button>
                                        )}
                                        {job.status === "queued" && (
                                            <button onClick={() => handleCancel(job.job_id)} className="p-2 bg-red-50 text-red-600 hover:bg-red-100 rounded-lg transition-colors" title="Cancel Job">
                                                <XCircle size={16} />
                                            </button>
                                        )}
                                    </div>
                                </TableCell>
                            </TableRow>
                        ))}
                    </Table>
                )}
            </div>
        </div>
    );
}
