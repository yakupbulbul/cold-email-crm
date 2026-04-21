import { useApi } from "@/hooks/useApi";
import { useCallback } from "react";
import { 
    Domain, Mailbox, Campaign, Contact, SuppressionEntry, 
    SystemHealth, Alert, JobLog, DeliverabilitySummary, Thread, Message, SettingsSummary,
    LeadVerificationJob,
    LeadVerificationResult,
    CampaignActionResult,
    CampaignDryRunResult,
    CampaignExecutionDetail,
    CampaignPreflightResult,
    CampaignSequenceStep,
    CampaignListSummary,
    EmailTemplate,
    LeadList,
    LeadListLeadResponse,
    SendEmailLog,
    SendEmailPayload,
    SendEmailResult,
    SMTPDiagnosticResult,
    WarmupLog,
    WarmupPair,
    WarmupStatus,
    InboxStatus,
    InboxSyncResult,
    MailProviderType,
    DeliverabilityEntity,
    DeliverabilityOverview,
    CommandCenterSummary,
    DailyNote,
    NotificationSummary,
    OperatorActionLog,
    OperatorTask,
    OperatorTaskCategory,
    OperatorTaskPriority,
    OperatorTaskStatus,
    Runbook,
    RunbookStep,
} from "@/types/models";
type MailboxCreatePayload = {
    domain_id: string;
    email: string;
    display_name: string;
    provider_type?: MailProviderType;
    smtp_host?: string;
    smtp_port?: number;
    smtp_username?: string;
    smtp_security_mode?: "starttls" | "ssl" | "plain";
    smtp_password?: string;
    imap_host?: string;
    imap_port?: number;
    imap_username?: string;
    imap_password?: string;
    imap_security_mode?: "starttls" | "ssl" | "plain";
    oauth_enabled?: boolean;
    daily_send_limit?: number;
};

type MailboxUpdatePayload = {
    display_name: string;
    daily_send_limit: number;
    status: string;
    smtp_security_mode?: "starttls" | "ssl" | "plain";
    provider_type?: MailProviderType;
    oauth_enabled?: boolean;
};

type MailboxWarmupPayload = {
    warmup_enabled: boolean;
};

type ProviderSettingsUpdatePayload = {
    mailcow_enabled?: boolean;
    google_workspace_enabled?: boolean;
    default_provider?: MailProviderType;
    allow_existing_disabled_provider_mailboxes?: boolean;
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

type EmailTemplatePayload = {
    name: string;
    subject: string;
    body: string;
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

type LeadBulkContactTypePayload = {
    lead_ids: string[];
    contact_type: "b2b" | "b2c" | "mixed" | null;
};

type OperatorTaskCreatePayload = {
    title: string;
    description?: string | null;
    status?: OperatorTaskStatus;
    priority?: OperatorTaskPriority;
    category?: OperatorTaskCategory;
    due_at?: string | null;
    related_entity_type?: string | null;
    related_entity_id?: string | null;
    metadata?: Record<string, unknown>;
};

type OperatorTaskUpdatePayload = Partial<OperatorTaskCreatePayload>;

type RunbookPayload = {
    name: string;
    description?: string | null;
    category?: OperatorTaskCategory;
    is_active?: boolean;
    steps?: RunbookStep[];
};

/**
 * Service API wrapping backend endpoints. Provides typed data fetching abstractions.
 */
export function useApiService() {
    const { request, requestOrThrow, loading, error } = useApi();

    // ── OPS / METRICS ──
    const getHealth = useCallback(() => request<SystemHealth>("/ops/health"), [request]);
    const getSettingsSummary = useCallback(() => request<SettingsSummary>("/settings/summary"), [request]);
    const updateProviderSettings = useCallback((data: ProviderSettingsUpdatePayload) => requestOrThrow<SettingsSummary>("/settings/providers", { method: "PATCH", body: data }), [requestOrThrow]);
    const getAlerts = useCallback(() => request<Alert[]>("/ops/alerts"), [request]);
    const getJobs = useCallback(() => request<JobLog[]>("/ops/jobs"), [request]);
    const getDeliverabilitySummary = useCallback(() => request<DeliverabilitySummary>("/ops/deliverability/summary"), [request]);
    const getDeliverabilityOverview = useCallback(() => request<DeliverabilityOverview>("/deliverability/overview"), [request]);
    const getDeliverabilityOverviewOrThrow = useCallback(() => requestOrThrow<DeliverabilityOverview>("/deliverability/overview"), [requestOrThrow]);
    const getDeliverabilityDomains = useCallback(() => request<{ status: string; summary: Record<string, number>; items: DeliverabilityEntity[]; blockers: unknown[]; warnings: unknown[]; next_actions: string[] }>("/deliverability/domains"), [request]);
    const getDeliverabilityMailboxes = useCallback(() => request<{ status: string; summary: Record<string, number>; items: DeliverabilityEntity[]; blockers: unknown[]; warnings: unknown[]; next_actions: string[] }>("/deliverability/mailboxes"), [request]);
    const getCampaignDeliverability = useCallback((id: string) => request<DeliverabilityEntity & { audience?: Record<string, unknown>; eligible_leads?: number }>("/deliverability/campaigns/" + id), [request]);

    // ── COMMAND CENTER ──
    const getCommandCenterSummary = useCallback(() => request<CommandCenterSummary>("/command-center/summary"), [request]);
    const getOperatorTasks = useCallback((query: string = "") => request<OperatorTask[]>(`/command-center/tasks${query ? `?${query}` : ""}`), [request]);
    const createOperatorTask = useCallback((data: OperatorTaskCreatePayload) => requestOrThrow<OperatorTask>("/command-center/tasks", { method: "POST", body: data }), [requestOrThrow]);
    const updateOperatorTask = useCallback((id: string, data: OperatorTaskUpdatePayload) => requestOrThrow<OperatorTask>(`/command-center/tasks/${id}`, { method: "PATCH", body: data }), [requestOrThrow]);
    const getOperatorActions = useCallback((query: string = "") => request<OperatorActionLog[]>(`/command-center/actions${query ? `?${query}` : ""}`), [request]);
    const getDailyNotes = useCallback((limit: number = 30) => request<DailyNote[]>(`/command-center/daily-notes?limit=${limit}`), [request]);
    const upsertDailyNote = useCallback((note_date: string, content: string) => requestOrThrow<DailyNote>("/command-center/daily-notes", { method: "POST", body: { note_date, content } }), [requestOrThrow]);
    const getRunbooks = useCallback(() => request<Runbook[]>("/command-center/runbooks"), [request]);
    const createRunbook = useCallback((data: RunbookPayload) => requestOrThrow<Runbook>("/command-center/runbooks", { method: "POST", body: data }), [requestOrThrow]);
    const updateRunbook = useCallback((id: string, data: RunbookPayload) => requestOrThrow<Runbook>(`/command-center/runbooks/${id}`, { method: "PATCH", body: data }), [requestOrThrow]);
    const startRunbook = useCallback((id: string) => requestOrThrow<OperatorTask[]>(`/command-center/runbooks/${id}/start`, { method: "POST" }), [requestOrThrow]);

    // ── HEADER NOTIFICATIONS ──
    const getNotificationSummary = useCallback((limit: number = 20) => request<NotificationSummary>(`/notifications/summary?limit=${limit}`), [request]);
    const markNotificationRead = useCallback((id: string) => requestOrThrow<{ status: string; id: string }>(`/notifications/${encodeURIComponent(id)}/read`, { method: "POST" }), [requestOrThrow]);
    const markAllNotificationsRead = useCallback(() => requestOrThrow<{ status: string; count: number }>("/notifications/read-all", { method: "POST" }), [requestOrThrow]);

    // ── CAMPAIGNS ──
    const getCampaigns = useCallback(() => request<Campaign[]>("/campaigns"), [request]);
    const getCampaignById = useCallback((id: string) => request<Campaign>(`/campaigns/${id}`), [request]);
    const createCampaign = useCallback((data: CampaignCreatePayload) => request<Campaign>("/campaigns", { method: "POST", body: data }), [request]);
    const updateCampaign = useCallback((id: string, data: CampaignUpdatePayload) => requestOrThrow<Campaign>(`/campaigns/${id}`, { method: "PUT", body: data }), [requestOrThrow]);
    const deleteCampaign = useCallback((id: string) => requestOrThrow<{ status: string; id: string }>(`/campaigns/${id}`, { method: "DELETE" }), [requestOrThrow]);
    const archiveCampaign = useCallback((id: string) => requestOrThrow<{ status: string; id: string; campaign?: string }>(`/campaigns/${id}/archive`, { method: "POST" }), [requestOrThrow]);
    const unarchiveCampaign = useCallback((id: string) => requestOrThrow<{ status: string; id: string; campaign?: string }>(`/campaigns/${id}/unarchive`, { method: "POST" }), [requestOrThrow]);
    const startCampaign = useCallback((id: string) => requestOrThrow<CampaignActionResult>(`/campaigns/${id}/start`, { method: "POST" }), [requestOrThrow]);
    const retryCampaign = useCallback((id: string) => requestOrThrow<CampaignActionResult>(`/campaigns/${id}/retry`, { method: "POST" }), [requestOrThrow]);
    const dryRunCampaign = useCallback((id: string) => requestOrThrow<CampaignDryRunResult>(`/campaigns/${id}/dry-run`, { method: "POST" }), [requestOrThrow]);
    const getCampaignExecution = useCallback((id: string) => request<CampaignExecutionDetail>(`/campaigns/${id}/execution`), [request]);
    const pauseCampaign = useCallback((id: string) => requestOrThrow<CampaignActionResult>(`/campaigns/${id}/pause`, { method: "POST" }), [requestOrThrow]);
    const runPreflight = useCallback((id: string) => requestOrThrow<CampaignPreflightResult>(`/campaigns/${id}/preflight`, { method: "POST" }), [requestOrThrow]);
    const getCampaignTemplates = useCallback(() => request<EmailTemplate[]>("/campaigns/templates"), [request]);
    const createCampaignTemplate = useCallback((data: EmailTemplatePayload) => requestOrThrow<EmailTemplate>("/campaigns/templates", { method: "POST", body: data }), [requestOrThrow]);
    const updateCampaignTemplate = useCallback((id: string, data: EmailTemplatePayload) => requestOrThrow<EmailTemplate>(`/campaigns/templates/${id}`, { method: "PUT", body: data }), [requestOrThrow]);
    const deleteCampaignTemplate = useCallback((id: string) => requestOrThrow<{ status: string; id: string }>(`/campaigns/templates/${id}`, { method: "DELETE" }), [requestOrThrow]);
    const getCampaignSequence = useCallback((id: string) => request<CampaignSequenceStep[]>(`/campaigns/${id}/sequence`), [request]);
    const updateCampaignSequence = useCallback((id: string, steps: CampaignSequenceStep[]) => requestOrThrow<CampaignSequenceStep[]>(`/campaigns/${id}/sequence`, { method: "PUT", body: steps }), [requestOrThrow]);

    // ── LEADS / CONTACTS ──
    const getLeads = useCallback(() => request<Contact[]>("/leads"), [request]);
    const getLeadsWithFilters = useCallback((query: string) => request<Contact[]>(`/leads${query ? `?${query}` : ""}`), [request]);
    const updateLead = useCallback((leadId: string, data: LeadUpdatePayload) => requestOrThrow<Contact>(`/leads/${leadId}`, { method: "PATCH", body: data }), [requestOrThrow]);
    const updateLeadContactTypeBulk = useCallback((data: LeadBulkContactTypePayload) => requestOrThrow<{ status: string; lead_count: number; contact_type: "b2b" | "b2c" | null }>(`/leads/bulk/contact-type`, { method: "PATCH", body: data }), [requestOrThrow]);
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
    const getWarmupPairs = useCallback(() => request<WarmupPair[]>("/warmup/pairs"), [request]);
    const getWarmupLogs = useCallback((limit: number = 50) => request<WarmupLog[]>(`/warmup/logs?limit=${limit}`), [request]);
    const startWarmup = useCallback(() => requestOrThrow<{ status: string; detail: string; job_queued?: boolean; job_id?: string | null }>("/warmup/start", { method: "POST" }), [requestOrThrow]);
    const pauseWarmup = useCallback(() => requestOrThrow<{ status: string; detail: string }>("/warmup/pause", { method: "POST" }), [requestOrThrow]);
    const runWarmupNow = useCallback(() => requestOrThrow<{ status: string; detail: string; job_queued?: boolean; job_id?: string | null }>("/warmup/run-now", { method: "POST" }), [requestOrThrow]);

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
    const updateMailboxWarmup = useCallback((id: string, data: MailboxWarmupPayload) => requestOrThrow<Mailbox>(`/mailboxes/${id}/warmup`, { method: "PATCH", body: data }), [requestOrThrow]);
    const deleteMailbox = useCallback((id: string) => request<{ status: string; id: string }>(`/mailboxes/${id}`, { method: "DELETE" }), [request]);
    const checkMailboxSmtp = useCallback((id: string) => requestOrThrow<SMTPDiagnosticResult>(`/mailboxes/${id}/smtp-check`, { method: "POST" }), [requestOrThrow]);
    const checkMailboxProvider = useCallback((id: string) => requestOrThrow<{
        provider_type: MailProviderType;
        status: string;
        smtp: { status: string; category: string; message: string };
        imap: { status: string; category: string; message: string };
        oauth?: {
            oauth_connection_status?: string | null;
            oauth_last_checked_at?: string | null;
            oauth_last_error?: string | null;
            oauth_last_refreshed_at?: string | null;
            oauth_token_expires_at?: string | null;
            external_account_email?: string | null;
            scopes?: string[];
        } | null;
    }>(`/mailboxes/${id}/provider-check`, { method: "POST" }), [requestOrThrow]);
    const getMailboxOAuthStatus = useCallback((id: string) => requestOrThrow<{
        oauth_enabled: boolean;
        oauth_provider?: string | null;
        oauth_connection_status?: string | null;
        oauth_last_checked_at?: string | null;
        oauth_last_error?: string | null;
        oauth_last_refreshed_at?: string | null;
        oauth_token_expires_at?: string | null;
        external_account_email?: string | null;
        scopes?: string[];
    }>(`/mailboxes/${id}/oauth-status`), [requestOrThrow]);
    const startMailboxOAuth = useCallback((id: string) => requestOrThrow<{ status: string; authorization_url: string }>(`/mailboxes/${id}/google-workspace/connect`, { method: "POST" }), [requestOrThrow]);
    const disconnectMailboxOAuth = useCallback((id: string) => requestOrThrow<Mailbox>(`/mailboxes/${id}/google-workspace/disconnect`, { method: "POST" }), [requestOrThrow]);
    const sendEmail = useCallback((data: SendEmailPayload) => requestOrThrow<SendEmailResult>("/send-email", { method: "POST", body: data }), [requestOrThrow]);
    const getSendEmailLogs = useCallback((limit: number = 20) => request<SendEmailLog[]>(`/send-email/logs?limit=${limit}`), [request]);

    // ── INBOX & THREADS ──
    const getInboxStatus = useCallback(() => request<InboxStatus>("/inbox/status"), [request]);
    const syncInbox = useCallback((mailboxId?: string) => requestOrThrow<InboxSyncResult>(`/inbox/sync${mailboxId ? `?mailbox_id=${mailboxId}` : ""}`, { method: "POST" }), [requestOrThrow]);
    const syncMailboxInbox = useCallback((mailboxId: string) => requestOrThrow<InboxSyncResult>(`/inbox/mailboxes/${mailboxId}/sync`, { method: "POST" }), [requestOrThrow]);
    const getThreads = useCallback((query: string = "") => request<Thread[]>(`/inbox/threads${query ? `?${query}` : ""}`), [request]);
    const getThread = useCallback((threadId: string) => request<Thread & { messages: Message[] }>(`/inbox/threads/${threadId}`), [request]);
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
        updateProviderSettings,
        getAlerts,
        getJobs,
        getDeliverabilitySummary,
        getDeliverabilityOverview,
        getDeliverabilityOverviewOrThrow,
        getDeliverabilityDomains,
        getDeliverabilityMailboxes,
        getCampaignDeliverability,
        getCommandCenterSummary,
        getOperatorTasks,
        createOperatorTask,
        updateOperatorTask,
        getOperatorActions,
        getDailyNotes,
        upsertDailyNote,
        getRunbooks,
        createRunbook,
        updateRunbook,
        startRunbook,
        getNotificationSummary,
        markNotificationRead,
        markAllNotificationsRead,
        getCampaigns,
        getCampaignById,
        createCampaign,
        updateCampaign,
        deleteCampaign,
        archiveCampaign,
        unarchiveCampaign,
        startCampaign,
        retryCampaign,
        dryRunCampaign,
        getCampaignExecution,
        pauseCampaign,
        runPreflight,
        getCampaignTemplates,
        createCampaignTemplate,
        updateCampaignTemplate,
        deleteCampaignTemplate,
        getCampaignSequence,
        updateCampaignSequence,
        getLeads,
        getLeadsWithFilters,
        updateLead,
        updateLeadContactTypeBulk,
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
        getWarmupPairs,
        getWarmupLogs,
        startWarmup,
        pauseWarmup,
        runWarmupNow,
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
        updateMailboxWarmup,
        deleteMailbox,
        checkMailboxSmtp,
        checkMailboxProvider,
        getMailboxOAuthStatus,
        startMailboxOAuth,
        disconnectMailboxOAuth,
        sendEmail,
        getSendEmailLogs,
        getInboxStatus,
        syncInbox,
        syncMailboxInbox,
        getThreads,
        getThread,
        getMessages
    };
}
