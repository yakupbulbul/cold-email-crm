"use client";

import { useEffect, useState } from "react";
import { useApi } from "@/hooks/useApi";
import Table, { TableRow, TableCell } from "@/components/ui/Table";
import { Bell, ShieldAlert, CheckCircle, Info, Activity } from "lucide-react";
import Spinner from "@/components/ui/Spinner";

type AlertItem = {
    id: string;
    severity: string;
    title: string;
    alert_type: string;
    message: string;
    created_at: string;
    is_acknowledged: boolean;
};

export default function AlertsDashboard() {
    const { request, loading } = useApi();
    const [alerts, setAlerts] = useState<AlertItem[]>([]);

    useEffect(() => {
        const fetchAlerts = async () => {
            const data = await request<AlertItem[]>("/ops/alerts");
            if (data) setAlerts(data);
        };
        fetchAlerts();
    }, [request]);

    const handleAcknowledge = async (id: string) => {
        await request(`/ops/alerts/${id}/acknowledge`, { method: "POST" });
        setAlerts(alerts.map(a => a.id === id ? { ...a, is_acknowledged: true } : a));
    };

    const handleResolve = async (id: string) => {
        await request(`/ops/alerts/${id}/resolve`, { method: "POST" });
        setAlerts(alerts.filter(a => a.id !== id));
    };

    const getSeverityIcon = (sev: string) => {
        if (sev === "critical") return <ShieldAlert className="text-red-600" size={24} />;
        if (sev === "warning") return <Activity className="text-amber-500" size={24} />;
        return <Info className="text-[var(--primary)]" size={24} />;
    };

    return (
        <div className="space-y-6 animate-fade-in relative min-h-screen pb-12">
            <h1 className="text-3xl font-bold text-[var(--foreground)] tracking-tight flex items-center gap-3">
                <Bell className="text-red-500" size={32} /> Incident Management & Alerts
            </h1>

            {loading ? (
                <div className="flex justify-center py-20"><Spinner size="lg" /></div>
            ) : alerts.length === 0 ? (
                <div className="bg-[var(--surface)] border-2 border-dashed border-[var(--border)] rounded-2xl p-16 flex flex-col items-center justify-center text-center mt-8">
                    <CheckCircle className="text-emerald-500 mb-4" size={48} />
                    <h3 className="text-xl font-bold text-[var(--foreground)]">All Systems Nominal</h3>
                    <p className="text-[var(--muted-foreground)] font-medium">There are no active alerts or incidents tracked in the cluster.</p>
                </div>
            ) : (
                <div className="bg-[var(--surface)] rounded-2xl border border-[var(--border)] shadow-sm p-6 mt-8">
                    <Table columns={["Severity", "Alert Rule Data", "Message", "Timestamp", "Actions"]}>
                        {alerts.map(alert => (
                            <TableRow key={alert.id} className={!alert.is_acknowledged ? "bg-red-50/50" : ""}>
                                <TableCell>
                                    <div className="flex items-center gap-2">
                                        {getSeverityIcon(alert.severity)}
                                        <span className="font-bold text-[var(--foreground)] capitalize w-20">{alert.severity}</span>
                                    </div>
                                </TableCell>
                                <TableCell>
                                    <div className="font-bold text-[var(--foreground)]">{alert.title}</div>
                                    <div className="text-xs text-[var(--muted-foreground)] font-mono mt-1">{alert.alert_type}</div>
                                </TableCell>
                                <TableCell className="max-w-md">
                                    <span className="text-[var(--muted-foreground)] font-medium text-sm drop-shadow-sm">{alert.message}</span>
                                </TableCell>
                                <TableCell className="text-[var(--muted-foreground)] text-xs font-mono">
                                    {new Date(alert.created_at).toLocaleString()}
                                </TableCell>
                                <TableCell>
                                    <div className="flex items-center gap-3">
                                        {!alert.is_acknowledged && (
                                            <button onClick={() => handleAcknowledge(alert.id)} className="text-xs font-bold px-3 py-1.5 bg-[var(--surface)] border border-[var(--border)] shadow-sm rounded-lg hover:bg-[var(--surface-muted)] transition-colors text-[var(--foreground)]">
                                                Acknowledge
                                            </button>
                                        )}
                                        <button onClick={() => handleResolve(alert.id)} className="text-xs font-bold px-3 py-1.5 bg-emerald-100 text-emerald-800 rounded-lg hover:bg-emerald-200 transition-colors">
                                            Resolve
                                        </button>
                                    </div>
                                </TableCell>
                            </TableRow>
                        ))}
                    </Table>
                </div>
            )}
        </div>
    );
}
