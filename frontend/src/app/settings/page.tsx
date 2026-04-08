"use client";

import { useCallback, useEffect, useState } from "react";
import { useApiService } from "@/services/api";
import { SettingsSummary } from "@/types/models";
import {
    AlertCircle,
    CheckCircle2,
    Cpu,
    Database,
    Mail,
    RefreshCw,
    Server,
    Shield,
    ShieldAlert,
    UserCircle2,
    XCircle,
} from "lucide-react";
import Spinner from "@/components/ui/Spinner";

const toneMap: Record<string, string> = {
    healthy: "bg-emerald-50 text-emerald-700 border-emerald-200",
    degraded: "bg-amber-50 text-amber-700 border-amber-200",
    failed: "bg-red-50 text-red-700 border-red-200",
    disabled: "bg-slate-100 text-slate-700 border-slate-200",
    unknown: "bg-slate-100 text-slate-700 border-slate-200",
};

function StatusBadge({ value }: { value: string }) {
    const tone = toneMap[value] ?? toneMap.unknown;
    return (
        <span className={`inline-flex items-center rounded-full border px-3 py-1 text-xs font-bold uppercase tracking-wide ${tone}`}>
            {value.replaceAll("_", " ")}
        </span>
    );
}

function statusIcon(status: string) {
    if (status === "healthy") return <CheckCircle2 className="text-emerald-500" size={18} />;
    if (status === "degraded") return <AlertCircle className="text-amber-500" size={18} />;
    if (status === "disabled") return <ShieldAlert className="text-slate-500" size={18} />;
    return <XCircle className="text-red-500" size={18} />;
}

function SettingCard({
    title,
    subtitle,
    icon,
    children,
}: {
    title: string;
    subtitle: string;
    icon: React.ReactNode;
    children: React.ReactNode;
}) {
    return (
        <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
            <div className="mb-5 flex items-start justify-between gap-4">
                <div>
                    <h2 className="text-lg font-bold text-slate-800">{title}</h2>
                    <p className="mt-1 text-sm text-slate-500">{subtitle}</p>
                </div>
                <div className="rounded-2xl bg-slate-50 p-3 text-slate-600">{icon}</div>
            </div>
            {children}
        </section>
    );
}

function DetailRow({ label, value }: { label: string; value: React.ReactNode }) {
    return (
        <div className="flex items-start justify-between gap-4 border-b border-slate-100 py-3 last:border-b-0 last:pb-0 first:pt-0">
            <span className="text-sm font-medium text-slate-500">{label}</span>
            <div className="text-right text-sm font-semibold text-slate-800">{value}</div>
        </div>
    );
}

function formatMessage(summary: SettingsSummary) {
    if (!summary.mailcow_configured) {
        return "Mailcow integration is not configured on the backend.";
    }

    if (summary.mailcow_status === "healthy") {
        return summary.safe_mode
            ? "Mailcow integration is configured and reachable in read-only safe mode."
            : "Mailcow integration is configured and mutation-enabled.";
    }

    if (summary.mailcow_reason === "unauthorized") {
        return "Mailcow integration is configured but the backend credentials are unauthorized.";
    }

    if (summary.mailcow_reason === "unreachable") {
        return "Mailcow integration is configured but the backend cannot reach Mailcow right now.";
    }

    return summary.mailcow_detail || "Mailcow integration is not healthy.";
}

export default function SettingsPage() {
    const { getSettingsSummary, loading, error } = useApiService();
    const [summary, setSummary] = useState<SettingsSummary | null>(null);
    const [refreshing, setRefreshing] = useState(false);

    const loadSummary = useCallback(async () => {
        setRefreshing(true);
        const data = await getSettingsSummary();
        if (data) {
            setSummary(data);
        }
        setRefreshing(false);
    }, [getSettingsSummary]);

    useEffect(() => {
        let isMounted = true;

        const fetchInitialSummary = async () => {
            const data = await getSettingsSummary();
            if (isMounted && data) {
                setSummary(data);
            }
        };

        void fetchInitialSummary();

        return () => {
            isMounted = false;
        };
    }, [getSettingsSummary]);

    if (error && !summary) {
        return (
            <div className="space-y-6 animate-fade-in">
                <div>
                    <h1 className="text-3xl font-bold tracking-tight text-slate-800">System Settings</h1>
                    <p className="mt-2 max-w-2xl text-sm text-slate-500">
                        Runtime and integration settings are loaded from the backend. This view never exposes raw secrets.
                    </p>
                </div>
                <div className="rounded-2xl border border-red-200 bg-red-50 p-8 text-center shadow-sm">
                    <div className="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-full border border-red-200 bg-white">
                        <AlertCircle className="text-red-500" size={26} />
                    </div>
                    <h2 className="text-lg font-bold text-red-900">Failed to load system settings</h2>
                    <p className="mt-2 text-sm text-red-700">{error}</p>
                </div>
            </div>
        );
    }

    if (loading && !summary) {
        return (
            <div className="space-y-6 animate-fade-in">
                <div>
                    <h1 className="text-3xl font-bold tracking-tight text-slate-800">System Settings</h1>
                    <p className="mt-2 max-w-2xl text-sm text-slate-500">
                        Runtime and integration settings are loaded from the backend. This view never exposes raw secrets.
                    </p>
                </div>
                <div className="flex min-h-[320px] items-center justify-center rounded-2xl border border-slate-200 bg-white shadow-sm">
                    <Spinner size="lg" />
                </div>
            </div>
        );
    }

    if (!summary) {
        return (
            <div className="space-y-6 animate-fade-in">
                <div>
                    <h1 className="text-3xl font-bold tracking-tight text-slate-800">System Settings</h1>
                    <p className="mt-2 max-w-2xl text-sm text-slate-500">
                        Runtime and integration settings are loaded from the backend. This view never exposes raw secrets.
                    </p>
                </div>
                <div className="rounded-2xl border border-slate-200 bg-white p-8 text-center shadow-sm">
                    <p className="text-sm font-medium text-slate-600">No settings data is available yet.</p>
                </div>
            </div>
        );
    }

    return (
        <div className="space-y-6 animate-fade-in">
            <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
                <div>
                    <h1 className="text-3xl font-bold tracking-tight text-slate-800">System Settings</h1>
                    <p className="mt-2 max-w-3xl text-sm text-slate-500">
                        Real runtime state for the local app, infrastructure, worker mode, and backend-only Mailcow integration.
                    </p>
                </div>
                <button
                    type="button"
                    onClick={() => void loadSummary()}
                    disabled={refreshing}
                    className="inline-flex items-center justify-center gap-2 rounded-xl border border-slate-200 bg-white px-4 py-3 text-sm font-bold text-slate-700 shadow-sm transition-colors hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-50"
                >
                    <RefreshCw size={16} className={refreshing ? "animate-spin" : ""} />
                    {refreshing ? "Refreshing..." : "Refresh Status"}
                </button>
            </div>

            <div className="grid grid-cols-1 gap-4 xl:grid-cols-3">
                <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
                    <div className="text-xs font-bold uppercase tracking-[0.2em] text-slate-500">System Overview</div>
                    <div className="mt-3 flex items-center gap-3">
                        {statusIcon(summary.readiness_status)}
                        <div>
                            <div className="text-2xl font-extrabold text-slate-800">{summary.app_env}</div>
                            <div className="text-sm text-slate-500">Environment</div>
                        </div>
                    </div>
                    <div className="mt-4">
                        <StatusBadge value={summary.readiness_status} />
                    </div>
                </div>
                <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
                    <div className="text-xs font-bold uppercase tracking-[0.2em] text-slate-500">Worker Mode</div>
                    <div className="mt-3 text-2xl font-extrabold text-slate-800">{summary.worker_mode}</div>
                    <div className="mt-2 text-sm text-slate-500">
                        {summary.worker_available
                            ? "Worker-backed flows are available."
                            : summary.worker_detail || "Background workers are not available."}
                    </div>
                    <div className="mt-4">
                        <StatusBadge value={summary.health.workers?.status || "unknown"} />
                    </div>
                </div>
                <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
                    <div className="text-xs font-bold uppercase tracking-[0.2em] text-slate-500">Mailcow Mode</div>
                    <div className="mt-3 text-2xl font-extrabold text-slate-800">
                        {summary.mailcow_mutations_enabled ? "Mutation Enabled" : "Read Only"}
                    </div>
                    <div className="mt-2 text-sm text-slate-500">{formatMessage(summary)}</div>
                    <div className="mt-4">
                        <StatusBadge value={summary.mailcow_status} />
                    </div>
                </div>
            </div>

            <div className="grid grid-cols-1 gap-6 xl:grid-cols-2">
                <SettingCard
                    title="Application Environment"
                    subtitle="Safe runtime metadata from the backend."
                    icon={<Server size={20} />}
                >
                    <DetailRow label="Project" value={summary.project_name} />
                    <DetailRow label="Environment" value={summary.app_env} />
                    <DetailRow label="Backend URL" value={summary.backend_url} />
                    <DetailRow label="Frontend API Path" value={summary.frontend_api_path} />
                    <DetailRow label="API Base Path" value={summary.api_base_path} />
                    <DetailRow label="Readiness" value={<StatusBadge value={summary.readiness_status} />} />
                </SettingCard>

                <SettingCard
                    title="Auth / Session"
                    subtitle="Current authenticated operator and session posture."
                    icon={<UserCircle2 size={20} />}
                >
                    <DetailRow label="Signed-in user" value={summary.current_user.email} />
                    <DetailRow label="Display name" value={summary.current_user.full_name || "Not set"} />
                    <DetailRow label="Role" value={summary.current_user.is_admin ? "Admin" : "User"} />
                    <DetailRow label="Session health" value={<StatusBadge value={summary.session_healthy ? "healthy" : "failed"} />} />
                    <DetailRow label="User active" value={summary.current_user.is_active ? "Yes" : "No"} />
                </SettingCard>

                <SettingCard
                    title="Infrastructure"
                    subtitle="Live backend component status pulled from the health services."
                    icon={<Database size={20} />}
                >
                    <DetailRow label="Backend" value={<StatusBadge value={summary.health.backend?.status || "unknown"} />} />
                    <DetailRow label="Database" value={<StatusBadge value={summary.health.database?.status || "unknown"} />} />
                    <DetailRow label="Redis" value={<StatusBadge value={summary.health.redis?.status || "unknown"} />} />
                    <DetailRow label="Workers" value={<StatusBadge value={summary.health.workers?.status || "unknown"} />} />
                    {summary.health.workers?.detail ? (
                        <div className="mt-4 rounded-xl border border-slate-200 bg-slate-50 p-4 text-sm text-slate-600">
                            {summary.health.workers.detail}
                        </div>
                    ) : null}
                </SettingCard>

                <SettingCard
                    title="Mailcow Integration"
                    subtitle="Backend-only Mailcow visibility. The frontend never talks to Mailcow directly."
                    icon={<Mail size={20} />}
                >
                    <DetailRow label="Configured" value={summary.mailcow_configured ? "Yes" : "No"} />
                    <DetailRow label="Status" value={<StatusBadge value={summary.mailcow_status} />} />
                    <DetailRow label="Reason" value={summary.mailcow_reason ? summary.mailcow_reason.replaceAll("_", " ") : "None"} />
                    <DetailRow label="Mode" value={summary.mailcow_mutations_enabled ? "Mutation enabled" : "Read only"} />
                    <DetailRow label="Frontend direct access" value={summary.frontend_mailcow_direct_access ? "Enabled" : "Disabled"} />
                    <div className="mt-4 rounded-xl border border-slate-200 bg-slate-50 p-4 text-sm text-slate-600">
                        {summary.mailcow_detail || formatMessage(summary)}
                    </div>
                </SettingCard>

                <SettingCard
                    title="Worker / Queue Mode"
                    subtitle="Whether background execution is available for warmup and campaigns."
                    icon={<Cpu size={20} />}
                >
                    <DetailRow label="Current mode" value={summary.worker_mode} />
                    <DetailRow label="Workers available" value={summary.worker_available ? "Yes" : "No"} />
                    <DetailRow
                        label="Warmup execution"
                        value={summary.worker_available ? "Available" : "Run make dev or make dev-full"}
                    />
                    <DetailRow
                        label="Campaign execution"
                        value={summary.worker_available ? "Available" : "Run make dev or make dev-full"}
                    />
                    <div className="mt-4 rounded-xl border border-slate-200 bg-slate-50 p-4 text-sm text-slate-600">
                        {summary.worker_available
                            ? "Worker-backed flows are active in this runtime."
                            : summary.worker_detail || "Low-RAM mode keeps worker-backed flows unavailable until you restart with make dev or make dev-full."}
                    </div>
                </SettingCard>

                <SettingCard
                    title="Feature Flags / Safe Mode"
                    subtitle="Safe operational posture for local and validation work."
                    icon={<Shield size={20} />}
                >
                    <DetailRow label="Safe mode" value={summary.safe_mode ? "Enabled" : "Disabled"} />
                    <DetailRow
                        label="Mailcow mutations"
                        value={summary.mailcow_mutations_enabled ? "Enabled" : "Disabled"}
                    />
                    <DetailRow label="Auth enabled" value={summary.auth_enabled ? "Yes" : "No"} />
                    <div className="mt-4 rounded-xl border border-blue-100 bg-blue-50 p-4 text-sm text-blue-700">
                        {summary.safe_mode
                            ? "This environment is protecting Mailcow by default. Domain checks are read-only, mailbox provisioning stays local-only, and worker-backed actions may require full mode."
                            : "Mutation mode is enabled. Review Mailcow-facing operations carefully."}
                    </div>
                    {error ? (
                        <div className="mt-3 rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-700">
                            Latest refresh error: {error}
                        </div>
                    ) : null}
                </SettingCard>
            </div>

            <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
                <h2 className="text-lg font-bold text-slate-800">Troubleshooting Guidance</h2>
                <div className="mt-4 grid gap-4 md:grid-cols-2">
                    <div className="rounded-xl border border-slate-200 bg-slate-50 p-4 text-sm text-slate-600">
                        <div className="font-semibold text-slate-800">Mailcow Verification</div>
                        <div className="mt-2">
                            {formatMessage(summary)}
                        </div>
                    </div>
                    <div className="rounded-xl border border-slate-200 bg-slate-50 p-4 text-sm text-slate-600">
                        <div className="font-semibold text-slate-800">Worker-backed Flows</div>
                        <div className="mt-2">
                            {summary.worker_available
                                ? "Warmup and campaign execution can be processed in this runtime."
                                : "Warmup execution and campaign sending require worker availability. Restart with make dev or make dev-full to process queued work."}
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
}
