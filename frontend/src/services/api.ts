import { useApi } from "@/hooks/useApi";
import { useCallback } from "react";
import { 
    Domain, Mailbox, Campaign, Contact, SuppressionEntry, 
    SystemHealth, Alert, JobLog, DeliverabilitySummary, Thread, Message, SettingsSummary,
    LeadVerificationJob,
    LeadVerificationResult,
    CampaignActionResult,
    CampaignPreflightResult,
} from "@/types/models";

type WarmupStatus = { active_pairs: unknown[]; global_health?: number; total_sent?: number };
type MailboxCreatePayload = {
    domain_id: string;
    email: string;
    display_name: string;
    smtp_host?: string;
    smtp_port?: number;
    smtp_username?: string;
    smtp_password: string;
    imap_host?: string;
    imap_port?: number;
    imap_username?: string;
    imap_password: string;
    daily_send_limit?: number;
};

type MailboxUpdatePayload = {
    display_name: string;
    daily_send_limit: number;
    status: string;
};

type CampaignCreatePayload = {
    name: string;
    mailbox_id: string;
    template_subject: string;
    template_body: string;
    daily_limit?: number;
};

/**
 * Service API wrapping backend endpoints. Provides typed data fetching abstractions.
 */
export function useApiService() {
    const { request, requestOrThrow, loading, error } = useApi();

    // ── OPS / METRICS ──
    const getHealth = useCallback(() => request<SystemHealth>("/ops/health"), [request]);
    const getSettingsSummary = useCallback(() => request<SettingsSummary>("/settings/summary"), [request]);
    const getAlerts = useCallback(() => request<Alert[]>("/ops/alerts"), [request]);
    const getJobs = useCallback(() => request<JobLog[]>("/ops/jobs"), [request]);
    const getDeliverabilitySummary = useCallback(() => request<DeliverabilitySummary>("/ops/deliverability/summary"), [request]);

    // ── CAMPAIGNS ──
    const getCampaigns = useCallback(() => request<Campaign[]>("/campaigns"), [request]);
    const getCampaignById = useCallback((id: string) => request<Campaign>(`/campaigns/${id}`), [request]);
    const createCampaign = useCallback((data: CampaignCreatePayload) => request<Campaign>("/campaigns", { method: "POST", body: data }), [request]);
    const startCampaign = useCallback((id: string) => requestOrThrow<CampaignActionResult>(`/campaigns/${id}/start`, { method: "POST" }), [requestOrThrow]);
    const pauseCampaign = useCallback((id: string) => requestOrThrow<CampaignActionResult>(`/campaigns/${id}/pause`, { method: "POST" }), [requestOrThrow]);
    const runPreflight = useCallback((id: string) => requestOrThrow<CampaignPreflightResult>(`/campaigns/${id}/preflight`, { method: "POST" }), [requestOrThrow]);

    // ── LEADS / CONTACTS ──
    const getLeads = useCallback(() => request<Contact[]>("/leads"), [request]);
    const verifyLead = useCallback((lead_id: string) => request<LeadVerificationResult>("/leads/verify", { method: "POST", body: { lead_id } }), [request]);
    const verifyLeadsBulk = useCallback((lead_ids: string[]) => request<{ job_id: string; status: string; requested_count: number; worker_mode: "lean" | "full" }>("/leads/verify/bulk", { method: "POST", body: { lead_ids } }), [request]);
    const getLeadVerificationJob = useCallback((jobId: string) => request<LeadVerificationJob>(`/leads/verify/${jobId}`), [request]);

    // ── SUPPRESSION ──
    const getSuppressionList = useCallback(() => request<SuppressionEntry[]>("/suppression"), [request]);
    const addSuppression = useCallback((email: string, reason: string) => request<SuppressionEntry>("/suppression", { method: "POST", body: { email, reason } }), [request]);
    const deleteSuppression = useCallback((id: string) => request(`/suppression/${id}`, { method: "DELETE" }), [request]);

    // ── WARMUP ──
    const getWarmupStatus = useCallback(() => request<WarmupStatus>("/warmup/status"), [request]);
    const startWarmup = useCallback((mailbox_id: string) => request("/warmup/start", { method: "POST", body: { mailbox_id } }), [request]);
    const stopWarmup = useCallback((mailbox_id: string) => request("/warmup/stop", { method: "POST", body: { mailbox_id } }), [request]);

    // ── DOMAINS ──
    const getDomains = useCallback(() => request<Domain[]>("/domains"), [request]);
    const getDomainById = useCallback((id: string) => request<Domain>(`/domains/${id}`), [request]);
    const createDomain = useCallback((name: string) => request<Domain>("/domains", { method: "POST", body: { name } }), [request]);
    const deleteDomain = useCallback((id: string) => request<{ status: string; id: string }>(`/domains/${id}`, { method: "DELETE" }), [request]);
    const verifyDomain = useCallback((id: string) => request<Domain>(`/domains/${id}/verify`, { method: "POST" }), [request]);
    const refreshDomain = useCallback((id: string) => request<Domain>(`/domains/${id}/refresh`, { method: "POST" }), [request]);
    const getDomainStatus = useCallback((id: string) => request(`/domains/${id}/status`), [request]);

    // ── MAILBOXES ──
    const getMailboxes = useCallback(() => request<Mailbox[]>("/mailboxes"), [request]);
    const createMailbox = useCallback((data: MailboxCreatePayload) => request<Mailbox>("/mailboxes", { method: "POST", body: data }), [request]);
    const updateMailbox = useCallback((id: string, data: MailboxUpdatePayload) => request<Mailbox>(`/mailboxes/${id}`, { method: "PUT", body: data }), [request]);
    const deleteMailbox = useCallback((id: string) => request<{ status: string; id: string }>(`/mailboxes/${id}`, { method: "DELETE" }), [request]);

    // ── INBOX & THREADS (Missing Backend - Graceful Fallback) ──
    const getThreads = useCallback(() => request<Thread[]>("/inbox/threads"), [request]);
    const getMessages = useCallback((threadId: string) => request<Message[]>(`/inbox/threads/${threadId}/messages`), [request]);

    return {
        loading,
        error,
        getHealth,
        getSettingsSummary,
        getAlerts,
        getJobs,
        getDeliverabilitySummary,
        getCampaigns,
        getCampaignById,
        createCampaign,
        startCampaign,
        pauseCampaign,
        runPreflight,
        getLeads,
        verifyLead,
        verifyLeadsBulk,
        getLeadVerificationJob,
        getSuppressionList,
        addSuppression,
        deleteSuppression,
        getWarmupStatus,
        startWarmup,
        stopWarmup,
        getDomains,
        getDomainById,
        createDomain,
        deleteDomain,
        verifyDomain,
        refreshDomain,
        getDomainStatus,
        getMailboxes,
        createMailbox,
        updateMailbox,
        deleteMailbox,
        getThreads,
        getMessages
    };
}
