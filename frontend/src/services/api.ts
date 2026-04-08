import { useApi } from "@/hooks/useApi";
import { useCallback } from "react";
import { 
    Domain, Mailbox, Campaign, Contact, SuppressionEntry, 
    SystemHealth, Alert, JobLog, DeliverabilitySummary, Thread, Message, SettingsSummary,
    LeadVerificationJob,
    LeadVerificationResult,
    CampaignActionResult,
    CampaignPreflightResult,
    LeadList,
    LeadListLeadResponse,
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
    campaign_type?: string;
    channel_type?: string;
    goal_type?: string;
    list_strategy?: string;
    compliance_mode?: string;
    schedule_window?: Record<string, unknown> | null;
    send_window_timezone?: string | null;
};

type CampaignUpdatePayload = {
    name: string;
    mailbox_id: string;
    template_subject: string;
    template_body: string;
    daily_limit: number;
    campaign_type?: string;
    channel_type?: string;
    goal_type?: string;
    list_strategy?: string;
    compliance_mode?: string;
    schedule_window?: Record<string, unknown> | null;
    send_window_timezone?: string | null;
};

type LeadListCreatePayload = {
    name: string;
    description?: string;
};

type LeadListUpdatePayload = {
    name?: string;
    description?: string;
};

type LeadUpdatePayload = {
    contact_type: "b2b" | "b2c" | "mixed" | null;
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
    const updateCampaign = useCallback((id: string, data: CampaignUpdatePayload) => requestOrThrow<Campaign>(`/campaigns/${id}`, { method: "PUT", body: data }), [requestOrThrow]);
    const deleteCampaign = useCallback((id: string) => requestOrThrow<{ status: string; id: string }>(`/campaigns/${id}`, { method: "DELETE" }), [requestOrThrow]);
    const startCampaign = useCallback((id: string) => requestOrThrow<CampaignActionResult>(`/campaigns/${id}/start`, { method: "POST" }), [requestOrThrow]);
    const pauseCampaign = useCallback((id: string) => requestOrThrow<CampaignActionResult>(`/campaigns/${id}/pause`, { method: "POST" }), [requestOrThrow]);
    const runPreflight = useCallback((id: string) => requestOrThrow<CampaignPreflightResult>(`/campaigns/${id}/preflight`, { method: "POST" }), [requestOrThrow]);

    // ── LEADS / CONTACTS ──
    const getLeads = useCallback(() => request<Contact[]>("/leads"), [request]);
    const getLeadsWithFilters = useCallback((query: string) => request<Contact[]>(`/leads${query ? `?${query}` : ""}`), [request]);
    const updateLead = useCallback((leadId: string, data: LeadUpdatePayload) => requestOrThrow<Contact>(`/leads/${leadId}`, { method: "PATCH", body: data }), [requestOrThrow]);
    const verifyLead = useCallback((lead_id: string) => request<LeadVerificationResult>("/leads/verify", { method: "POST", body: { lead_id } }), [request]);
    const verifyLeadsBulk = useCallback((lead_ids: string[]) => request<{ job_id: string; status: string; requested_count: number; worker_mode: "lean" | "full" }>("/leads/verify/bulk", { method: "POST", body: { lead_ids } }), [request]);
    const getLeadVerificationJob = useCallback((jobId: string) => request<LeadVerificationJob>(`/leads/verify/${jobId}`), [request]);
    const assignLeadTagsBulk = useCallback((lead_ids: string[], tags: string[]) => requestOrThrow<{ status: string; lead_count: number; tags: string[] }>("/leads/bulk/tags", { method: "PATCH", body: { lead_ids, tags } }), [requestOrThrow]);
    const suppressLeadsBulk = useCallback((lead_ids: string[], reason: string) => requestOrThrow<{ status: string; lead_count: number }>("/leads/bulk/suppress", { method: "POST", body: { lead_ids, reason } }), [requestOrThrow]);

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
    const createMailbox = useCallback((data: MailboxCreatePayload) => requestOrThrow<Mailbox>("/mailboxes", { method: "POST", body: data }), [requestOrThrow]);
    const updateMailbox = useCallback((id: string, data: MailboxUpdatePayload) => request<Mailbox>(`/mailboxes/${id}`, { method: "PUT", body: data }), [request]);
    const deleteMailbox = useCallback((id: string) => request<{ status: string; id: string }>(`/mailboxes/${id}`, { method: "DELETE" }), [request]);

    // ── INBOX & THREADS (Missing Backend - Graceful Fallback) ──
    const getThreads = useCallback(() => request<Thread[]>("/inbox/threads"), [request]);
    const getMessages = useCallback((threadId: string) => request<Message[]>(`/inbox/threads/${threadId}/messages`), [request]);

    // ── LISTS ──
    const getLists = useCallback(() => request<LeadList[]>("/lists"), [request]);
    const getListById = useCallback((id: string) => request<LeadList>(`/lists/${id}`), [request]);
    const getListLeads = useCallback((id: string) => request<LeadListLeadResponse>(`/lists/${id}/leads`), [request]);
    const createList = useCallback((data: LeadListCreatePayload) => requestOrThrow<LeadList>("/lists", { method: "POST", body: data }), [requestOrThrow]);
    const updateList = useCallback((id: string, data: LeadListUpdatePayload) => requestOrThrow<LeadList>(`/lists/${id}`, { method: "PATCH", body: data }), [requestOrThrow]);
    const deleteList = useCallback((id: string) => requestOrThrow<{ status: string; id: string }>(`/lists/${id}`, { method: "DELETE" }), [requestOrThrow]);
    const addLeadToList = useCallback((listId: string, leadId: string) => requestOrThrow<LeadList>(`/lists/${listId}/leads`, { method: "POST", body: { lead_id: leadId } }), [requestOrThrow]);
    const addLeadsToListBulk = useCallback((listId: string, leadIds: string[]) => requestOrThrow<LeadList>(`/lists/${listId}/leads/bulk`, { method: "POST", body: { lead_ids: leadIds } }), [requestOrThrow]);
    const removeLeadFromList = useCallback((listId: string, leadId: string) => requestOrThrow<{ status: string; list_id: string; lead_id: string }>(`/lists/${listId}/leads/${leadId}`, { method: "DELETE" }), [requestOrThrow]);
    const getCampaignLists = useCallback((campaignId: string) => request<CampaignListSummary>(`/campaigns/${campaignId}/lists`), [request]);
    const attachListToCampaign = useCallback((campaignId: string, listId: string) => requestOrThrow<CampaignListSummary>(`/campaigns/${campaignId}/lists`, { method: "POST", body: { list_id: listId } }), [requestOrThrow]);
    const removeListFromCampaign = useCallback((campaignId: string, listId: string) => requestOrThrow<CampaignListSummary>(`/campaigns/${campaignId}/lists/${listId}`, { method: "DELETE" }), [requestOrThrow]);

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
        updateCampaign,
        deleteCampaign,
        startCampaign,
        pauseCampaign,
        runPreflight,
        getLeads,
        getLeadsWithFilters,
        updateLead,
        verifyLead,
        verifyLeadsBulk,
        getLeadVerificationJob,
        assignLeadTagsBulk,
        suppressLeadsBulk,
        getLists,
        getListById,
        getListLeads,
        createList,
        updateList,
        deleteList,
        addLeadToList,
        addLeadsToListBulk,
        removeLeadFromList,
        getCampaignLists,
        attachListToCampaign,
        removeListFromCampaign,
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
