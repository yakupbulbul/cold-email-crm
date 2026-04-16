"use client";

import { useCallback, useEffect, useState } from "react";
import { useApiService } from "@/services/api";
import { useAuth } from "@/context/AuthContext";
import { MailProviderType, SettingsSummary } from "@/types/models";
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
import { PageHeader, SurfaceCard } from "@/components/ui/primitives";

async function loadSettingsWithRetry(fetchSummary: () => Promise<SettingsSummary | null>, attempts: number = 5) {
    for (let index = 0; index < attempts; index += 1) {
        const data = await fetchSummary();
        if (data) {
            return data;
        }
        if (index < attempts - 1) {
            await new Promise((resolve) => window.setTimeout(resolve, 200));
        }
    }
    return null;
}

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
            : "Mailcow integration is configured and reachable with mutation mode enabled.";
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
    const { user } = useAuth();
    const { getSettingsSummary, updateProviderSettings, loading, error } = useApiService();
    const [summary, setSummary] = useState<SettingsSummary | null>(null);
    const [refreshing, setRefreshing] = useState(false);
    const [providerSaving, setProviderSaving] = useState<MailProviderType | "default" | null>(null);
    const [providerError, setProviderError] = useState<string | null>(null);

    const loadSummary = useCallback(async () => {
        setRefreshing(true);
        const data = await loadSettingsWithRetry(getSettingsSummary);
        if (data) {
            setSummary(data);
        }
        setRefreshing(false);
    }, [getSettingsSummary]);

    const handleProviderToggle = useCallback(async (provider: MailProviderType, enabled: boolean) => {
        setProviderSaving(provider);
        setProviderError(null);
        try {
            const updated = await updateProviderSettings(
                provider === "mailcow"
                    ? { mailcow_enabled: enabled }
                    : { google_workspace_enabled: enabled },
            );
            setSummary(updated);
        } catch (err) {
            setProviderError(err instanceof Error ? err.message : "Provider settings update failed.");
        } finally {
            setProviderSaving(null);
        }
    }, [updateProviderSettings]);

    const handleDefaultProvider = useCallback(async (provider: MailProviderType) => {
        setProviderSaving("default");
        setProviderError(null);
        try {
            const updated = await updateProviderSettings({ default_provider: provider });
            setSummary(updated);
        } catch (err) {
            setProviderError(err instanceof Error ? err.message : "Default provider update failed.");
        } finally {
            setProviderSaving(null);
        }
    }, [updateProviderSettings]);

    useEffect(() => {
        let isMounted = true;

        const fetchInitialSummary = async () => {
            const data = await loadSettingsWithRetry(getSettingsSummary);
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
                <PageHeader
                    eyebrow="Configuration"
                    title="System settings"
                    description="Review backend runtime state, worker mode, and integration posture without exposing secrets."
                />
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
                <PageHeader
                    eyebrow="Configuration"
                    title="System settings"
                    description="Review backend runtime state, worker mode, and integration posture without exposing secrets."
                />
                <SurfaceCard className="flex min-h-[320px] items-center justify-center">
                    <Spinner size="lg" />
                </SurfaceCard>
            </div>
        );
    }

    if (!summary) {
        const apiBase = process.env.NEXT_PUBLIC_API_URL || "/api/v1";
        const backendUrl = apiBase.startsWith("http") ? apiBase.replace(/\/api\/v1\/?$/, "") : "http://127.0.0.1:8060";
        return (
            <div className="space-y-6 animate-fade-in">
                <PageHeader
                    eyebrow="Configuration"
                    title="System settings"
                    description="Review backend runtime state, worker mode, and integration posture without exposing secrets."
                />
                <div className="rounded-2xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-800">
                    The backend settings summary is temporarily unavailable. This page is showing degraded local runtime context while it retries.
                </div>
                <div className="grid grid-cols-1 gap-6 xl:grid-cols-2">
                    <SettingCard
                        title="Application Environment"
                        subtitle="Fallback runtime context while the backend summary is unavailable."
                        icon={<Server size={20} />}
                    >
                        <DetailRow label="Backend URL" value={backendUrl} />
                        <DetailRow label="Frontend API Path" value={apiBase} />
                        <DetailRow label="Readiness" value={<StatusBadge value="unknown" />} />
                    </SettingCard>
                    <SettingCard
                        title="Mailcow Integration"
                        subtitle="Backend summary is unavailable, so provider detail could not be refreshed."
                        icon={<Mail size={20} />}
                    >
                        <DetailRow label="Status" value={<StatusBadge value="unknown" />} />
                        <DetailRow label="Mode" value="Read only" />
                    </SettingCard>
                    <SettingCard
                        title="Worker / Queue Mode"
                        subtitle="Worker detail is unavailable until the backend settings summary returns."
                        icon={<Cpu size={20} />}
                    >
                        <DetailRow label="Current mode" value="Unknown" />
                        <DetailRow label="Workers available" value="Unknown" />
                    </SettingCard>
                    <SettingCard
                        title="Auth / Session"
                        subtitle="Current operator information from the authenticated client session."
                        icon={<UserCircle2 size={20} />}
                    >
                        <DetailRow label="Signed-in user" value={user?.email || "Unknown"} />
                        <DetailRow label="Display name" value={user?.full_name || "Bootstrap Admin"} />
                        <DetailRow label="Role" value={user?.is_admin ? "Admin" : "User"} />
                    </SettingCard>
                </div>
            </div>
        );
    }

    return (
        <div className="space-y-6 animate-fade-in">
            <PageHeader
                eyebrow="Configuration"
                title="System settings"
                description="Review real runtime state for the app, infrastructure, worker mode, and backend-only Mailcow integration."
                actions={(
                <button
                    type="button"
                    onClick={() => void loadSummary()}
                    disabled={refreshing}
                    className="btn-secondary"
                >
                    <RefreshCw size={16} className={refreshing ? "animate-spin" : ""} />
                    {refreshing ? "Refreshing..." : "Refresh Status"}
                </button>
                )}
            />

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

            {providerError ? (
                <div className="rounded-2xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
                    {providerError}
                </div>
            ) : null}

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
                    title="Mail Providers"
                    subtitle="Enable or disable mailbox providers globally, inspect provider health, and control the default provider for new mailboxes."
                    icon={<Mail size={20} />}
                >
                    <div className="space-y-4">
                        {(["mailcow", "google_workspace"] as MailProviderType[]).map((provider) => {
                            const providerSummary = summary.providers[provider];
                            const checked = providerSummary?.enabled ?? false;
                            return (
                                <div key={provider} className="rounded-xl border border-slate-200 bg-slate-50 p-4">
                                    <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
                                        <div>
                                            <div className="text-sm font-bold text-slate-900">{provider === "mailcow" ? "Mailcow" : "Google Workspace"}</div>
                                            <div className="mt-1 text-sm text-slate-600">{providerSummary?.detail || "No provider detail available."}</div>
                                            <div className="mt-2 flex flex-wrap items-center gap-2">
                                                <StatusBadge value={providerSummary?.status || "unknown"} />
                                                <span className="rounded-full border border-slate-200 bg-white px-3 py-1 text-xs font-semibold text-slate-700">
                                                    {providerSummary?.configured ? "Configured" : "Not configured"}
                                                </span>
                                                {provider === "google_workspace" ? (
                                                    <span className="rounded-full border border-slate-200 bg-white px-3 py-1 text-xs font-semibold text-slate-700">
                                                        OAuth {providerSummary?.oauth_connection_status?.replaceAll("_", " ") || "not connected"}
                                                    </span>
                                                ) : null}
                                            </div>
                                        </div>
                                        <label className="flex items-center gap-3 rounded-full border border-slate-200 bg-white px-4 py-2 text-sm font-semibold text-slate-800">
                                            <span>{checked ? "Enabled" : "Disabled"}</span>
                                            <input
                                                type="checkbox"
                                                checked={checked}
                                                onChange={(event) => void handleProviderToggle(provider, event.target.checked)}
                                                disabled={providerSaving === provider}
                                            />
                                        </label>
                                    </div>
                                </div>
                            );
                        })}
                        <div className="rounded-xl border border-slate-200 bg-white p-4">
                            <div className="text-sm font-bold text-slate-900">Default provider</div>
                            <div className="mt-1 text-sm text-slate-600">New mailbox setup defaults to this provider unless the operator chooses another one.</div>
                            <div className="mt-3 flex flex-wrap gap-2">
                                {(["mailcow", "google_workspace"] as MailProviderType[]).map((provider) => (
                                    <button
                                        key={provider}
                                        type="button"
                                        onClick={() => void handleDefaultProvider(provider)}
                                        disabled={providerSaving === "default"}
                                        className={`rounded-xl border px-4 py-2 text-sm font-semibold transition-colors ${
                                            summary.default_provider === provider
                                                ? "border-slate-900 bg-slate-900 text-white"
                                                : "border-slate-200 bg-white text-slate-700 hover:bg-slate-50"
                                        }`}
                                    >
                                        {provider === "mailcow" ? "Mailcow" : "Google Workspace"}
                                    </button>
                                ))}
                            </div>
                        </div>
                    </div>
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
                                : "Background workers are disabled in lean development mode. Warmup execution and campaign sending require worker availability. Restart with make dev or make dev-full to process queued work."}
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
}
