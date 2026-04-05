import { useApi } from "@/hooks/useApi";
import { useCallback } from "react";
import { 
    Domain, Mailbox, Campaign, Contact, SuppressionEntry, 
    SystemHealth, Alert, JobLog, DeliverabilitySummary, Thread, Message 
} from "@/types/models";

/**
 * Service API wrapping backend endpoints. Provides typed data fetching abstractions.
 */
export function useApiService() {
    const { request, loading, error } = useApi();

    // ── OPS / METRICS ──
    const getHealth = useCallback(() => request<SystemHealth>("/ops/health"), [request]);
    const getAlerts = useCallback(() => request<Alert[]>("/ops/alerts"), [request]);
    const getJobs = useCallback(() => request<JobLog[]>("/ops/jobs"), [request]);
    const getDeliverabilitySummary = useCallback(() => request<DeliverabilitySummary>("/ops/deliverability/summary"), [request]);

    // ── CAMPAIGNS ──
    const getCampaigns = useCallback(() => request<Campaign[]>("/campaigns"), [request]);
    const getCampaignById = useCallback((id: string) => request<Campaign>(`/campaigns/${id}`), [request]);
    const runPreflight = useCallback((id: string) => request(`/campaigns/${id}/preflight`, { method: "POST" }), [request]);

    // ── LEADS / CONTACTS ──
    const getLeads = useCallback(() => request<Contact[]>("/leads"), [request]);

    // ── SUPPRESSION ──
    const getSuppressionList = useCallback(() => request<SuppressionEntry[]>("/suppression"), [request]);
    const addSuppression = useCallback((email: string, reason: string) => request<SuppressionEntry>("/suppression", { method: "POST", body: { email, reason } }), [request]);
    const deleteSuppression = useCallback((id: string) => request(`/suppression/${id}`, { method: "DELETE" }), [request]);

    // ── WARMUP ──
    const getWarmupStatus = useCallback(() => request<{ active_pairs: any[]; global_health?: number; total_sent?: number }>("/warmup/status"), [request]);
    const startWarmup = useCallback((mailbox_id: string) => request("/warmup/start", { method: "POST", body: { mailbox_id } }), [request]);
    const stopWarmup = useCallback((mailbox_id: string) => request("/warmup/stop", { method: "POST", body: { mailbox_id } }), [request]);

    // ── DOMAINS ──
    const getDomains = useCallback(() => request<Domain[]>("/domains"), [request]);
    const createDomain = useCallback((name: string) => request<Domain>("/domains", { method: "POST", body: { name } }), [request]);

    // ── MAILBOXES ──
    const getMailboxes = useCallback(() => request<Mailbox[]>("/mailboxes"), [request]);
    const createMailbox = useCallback((data: any) => request<Mailbox>("/mailboxes", { method: "POST", body: data }), [request]);

    // ── INBOX & THREADS (Missing Backend - Graceful Fallback) ──
    const getThreads = useCallback(() => request<Thread[]>("/inbox/threads"), [request]);
    const getMessages = useCallback((threadId: string) => request<Message[]>(`/inbox/threads/${threadId}/messages`), [request]);

    return {
        loading,
        error,
        getHealth,
        getAlerts,
        getJobs,
        getDeliverabilitySummary,
        getCampaigns,
        getCampaignById,
        runPreflight,
        getLeads,
        getSuppressionList,
        addSuppression,
        deleteSuppression,
        getWarmupStatus,
        startWarmup,
        stopWarmup,
        getDomains,
        createDomain,
        getMailboxes,
        createMailbox,
        getThreads,
        getMessages
    };
}
