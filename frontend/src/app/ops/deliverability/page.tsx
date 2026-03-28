"use client";

import { useEffect, useState } from "react";
import { useApi } from "@/hooks/useApi";
import { BarChart3, TrendingUp, Inbox, ShieldAlert, XCircle } from "lucide-react";
import Table, { TableRow, TableCell } from "@/components/ui/Table";

export default function DeliverabilityDashboard() {
    const { request, loading } = useApi();
    const [summary, setSummary] = useState<any>({});
    const [mailboxes, setMailboxes] = useState<any[]>([]);

    useEffect(() => {
        const fetchStats = async () => {
            const sum = await request("/ops/deliverability/summary");
            if (sum) setSummary(sum);
            const mbox = await request("/ops/deliverability/mailboxes");
            if (mbox) setMailboxes(mbox);
        };
        fetchStats();
    }, [request]);

    const StatCard = ({ title, value, icon, bg }: { title: string, value: number, icon: any, bg: string }) => (
        <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm flex items-center justify-between">
            <div>
                <div className="text-sm font-bold text-slate-500 mb-1">{title}</div>
                <div className="text-3xl font-black text-slate-800">{value || 0}</div>
            </div>
            <div className={`p-4 rounded-xl ${bg}`}>{icon}</div>
        </div>
    );

    return (
        <div className="space-y-6 animate-fade-in relative min-h-screen pb-12">
            <h1 className="text-3xl font-bold text-slate-800 tracking-tight flex items-center gap-3">
                <BarChart3 className="text-blue-500" size={32} /> Deliverability Matrix
            </h1>

            <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mt-6">
                <StatCard title="Total Sends" value={summary.sent || 0} icon={<TrendingUp className="text-blue-600"/>} bg="bg-blue-50" />
                <StatCard title="Replies" value={summary.replied || 0} icon={<Inbox className="text-emerald-600"/>} bg="bg-emerald-50" />
                <StatCard title="Bounced" value={summary.bounced || 0} icon={<XCircle className="text-red-600"/>} bg="bg-red-50" />
                <StatCard title="Suppressed/Blocked" value={summary.suppressed || 0} icon={<ShieldAlert className="text-amber-600"/>} bg="bg-amber-50" />
            </div>

            <div className="bg-white rounded-2xl border border-slate-200 shadow-sm p-6 mt-8">
                <h3 className="font-bold text-slate-800 mb-6 flex items-center gap-2">Mailbox Leaderboard</h3>
                <Table columns={["Mailbox Domain", "Total Sends", "Replies", "Bounces", "Health Status"]}>
                    {mailboxes.map((box, i) => {
                        const bounceRate = ((box.bounced || 0) / ((box.sent || 1) + (box.bounced || 0))) * 100;
                        return (
                            <TableRow key={i}>
                                <TableCell className="font-bold text-slate-800">{box.mailbox}</TableCell>
                                <TableCell className="font-medium text-slate-600">{box.sent || 0}</TableCell>
                                <TableCell className="text-emerald-600 font-bold">{box.replied || 0}</TableCell>
                                <TableCell className="text-red-600 font-bold">{box.bounced || 0}</TableCell>
                                <TableCell>
                                    {bounceRate > 5 ? (
                                        <span className="px-2 py-1 bg-red-100 text-red-700 font-bold rounded-lg text-xs">High Risk ({bounceRate.toFixed(1)}%)</span>
                                    ) : (
                                        <span className="px-2 py-1 bg-green-100 text-green-700 font-bold rounded-lg text-xs">Healthy</span>
                                    )}
                                </TableCell>
                            </TableRow>
                        );
                    })}
                </Table>
            </div>
        </div>
    );
}
