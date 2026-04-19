export type MailProviderType = "mailcow" | "google_workspace";

export interface DomainVerificationSummary {
    remediation?: {
        mailcow?: {
            mailcow_host?: string;
            action?: string;
            detail?: string;
        };
        dns?: Record<string, {
            host?: string;
            type?: string;
            expected_value?: string;
            explanation?: string;
            observed_records?: string[];
        }>;
    };
    [key: string]: unknown;
}

export interface Domain {
    id: string;
    name: string;
    status: string;
    mailcow_status: string;
    mailcow_detail?: string | null;
    spf_status: string;
    dkim_status: string;
    dmarc_status: string;
    mx_status: string;
    dns_results?: Record<string, { status: string; detail: string; records?: string[] }>;
    missing_requirements?: string[];
    verification_summary?: DomainVerificationSummary;
    verification_error?: string | null;
    last_checked_at?: string | null;
    mailcow_last_checked_at?: string | null;
    dns_last_checked_at?: string | null;
    created_at: string;
    updated_at?: string;
}

export interface Mailbox {
    id: string;
    domain_id?: string;
    email: string;
    display_name: string;
    provider_type: MailProviderType;
    provider_status: string;
    provider_mailbox_id?: string | null;
    provider_domain_id?: string | null;
    provider_config_status?: string;
    last_provider_check_at?: string | null;
    last_provider_check_status?: string | null;
    last_provider_check_message?: string | null;
    smtp_host?: string;
    smtp_port?: number;
    smtp_security_mode: "starttls" | "ssl" | "plain";
    imap_host?: string;
    imap_port?: number;
    imap_security_mode?: "starttls" | "ssl" | "plain";
    oauth_enabled?: boolean;
    oauth_provider?: string | null;
    oauth_connection_status?: string | null;
    oauth_last_checked_at?: string | null;
    oauth_last_error?: string | null;
    oauth_last_refreshed_at?: string | null;
    oauth_token_expires_at?: string | null;
    external_account_email?: string | null;
    smtp_last_checked_at?: string | null;
    smtp_last_check_status?: string | null;
    smtp_last_check_category?: string | null;
    smtp_last_check_message?: string | null;
    status: string;
    daily_send_limit: number;
    current_warmup_stage: number;
    warmup_enabled: boolean;
    warmup_status?: string | null;
    warmup_last_checked_at?: string | null;
    warmup_last_result?: string | null;
    warmup_block_reason?: string | null;
    warmup_recommendation?: string | null;
    inbox_sync_enabled?: boolean;
    inbox_sync_status?: string | null;
    inbox_last_synced_at?: string | null;
    inbox_last_success_at?: string | null;
    inbox_last_error?: string | null;
    remote_mailcow_provisioned: boolean;
    provisioning_mode: "local_only" | "mailcow_synced";
    created_at: string;
}

export interface Campaign {
    id: string;
    name: string;
    status: string; // draft, active, paused, completed, archived, etc.
    mailbox_id?: string | null;
    template_subject: string;
    template_body: string;
    daily_limit: number;
    campaign_type: "b2b" | "b2c";
    channel_type: string;
    goal_type: string;
    list_strategy: string;
    compliance_mode: string;
    schedule_window?: Record<string, unknown> | null;
    send_window_timezone?: string | null;
    created_at: string;
    // Computed fields for UI
    sent_count?: number;
    lead_count?: number;
    reply_rate?: string | number;
    lists_summary?: CampaignListSummary;
    execution_summary?: {
        state: "idle" | "queued" | "running" | "waiting_for_beat" | "archived";
        job_id?: string | null;
        job_created_at?: string | null;
        job_started_at?: string | null;
        last_completed_at?: string | null;
        next_dispatch_at?: string | null;
        beat_interval_seconds?: number;
        detail?: string | null;
        current_blocker?: CampaignExecutionBlocker | null;
        next_send_decision?: string | null;
        last_job_queued_at?: string | null;
        last_job_started_at?: string | null;
        last_job_completed_at?: string | null;
        last_job_failed_at?: string | null;
        last_job_error?: string | null;
        eligible_leads?: number;
        scheduled_leads?: number;
        blocked_leads?: Record<string, number>;
        next_eligible_lead?: CampaignNextEligibleLead | null;
        job_history?: CampaignJobHistoryItem[];
        last_delivery_attempt_at?: string | null;
        last_delivery_status?: "success" | "failed" | null;
        last_delivery_target_email?: string | null;
        last_delivery_error?: string | null;
    };
}

export interface CampaignExecutionBlocker {
    code: string;
    message: string;
}

export interface CampaignNextEligibleLead {
    campaign_lead_id: string;
    contact_id: string;
    email: string;
    scheduled_at?: string | null;
    warning_reason?: string | null;
}

export interface CampaignJobHistoryItem {
    job_id: string;
    status: string;
    created_at?: string | null;
    started_at?: string | null;
    finished_at?: string | null;
    error_message?: string | null;
    retry_count?: number;
    payload_summary?: Record<string, unknown>;
}

export interface CampaignDryRunResult {
    campaign_id: string;
    campaign: string;
    campaign_status: string;
    mailbox_id?: string | null;
    mailbox_email?: string | null;
    sender_identity?: string | null;
    eligible_leads: number;
    scheduled_leads: number;
    blocked_leads: Record<string, number>;
    next_eligible_lead?: CampaignNextEligibleLead | null;
    sent_today: number;
    daily_limit: number;
    remaining_today: number;
    schedule_allows_now: boolean;
    schedule_detail: string;
    next_send_at?: string | null;
    deliverability_status: string;
    would_queue: boolean;
    blockers: CampaignExecutionBlocker[];
    warnings: CampaignExecutionBlocker[];
}

export interface CampaignExecutionDetail {
    campaign_id: string;
    campaign: string;
    summary: NonNullable<Campaign["execution_summary"]>;
    dry_run: CampaignDryRunResult;
    job_history: CampaignJobHistoryItem[];
    next_eligible_lead?: CampaignNextEligibleLead | null;
    current_blocker?: CampaignExecutionBlocker | null;
    next_send_decision?: string | null;
}

export interface CampaignActionResult {
    status: string;
    campaign?: string;
    eligible_leads?: number;
    blocked_leads?: Record<string, number>;
    job_queued?: boolean;
    job_id?: string | null;
    execution?: CampaignExecutionDetail;
}

export interface CampaignPreflightResult {
    status: string;
    blocked: boolean;
    audience_summary?: CampaignListSummary;
    checks: Array<{
        name: string;
        status: string;
        message: string;
        severity?: string;
        metadata?: unknown;
    }>;
}

export interface Contact {
    id: string;
    email: string;
    first_name: string | null;
    last_name: string | null;
    company: string | null;
    job_title?: string | null;
    website?: string | null;
    country?: string | null;
    industry?: string | null;
    persona?: string | null;
    contact_type?: "b2b" | "b2c" | "mixed" | null;
    consent_status?: "unknown" | "granted" | "revoked" | "not_required";
    unsubscribe_status?: "subscribed" | "unsubscribed" | "suppressed";
    engagement_score?: number;
    contact_status?: string;
    email_status: string;
    verification_score: number | null;
    verification_integrity: "high" | "medium" | "low" | null;
    contact_quality_tier?: "high" | "medium" | "low";
    last_verified_at: string | null;
    last_contacted_at?: string | null;
    last_replied_at?: string | null;
    is_disposable: boolean;
    is_role_based: boolean;
    is_suppressed: boolean;
    verification_reasons: string[] | null;
    source?: string;
    source_file_name?: string | null;
    tags?: string[];
    source_import_job_id?: string | null;
    list_ids?: string[];
    list_names?: string[];
    created_at: string;
}

export interface LeadList {
    id: string;
    name: string;
    description?: string | null;
    type: "static" | "smart";
    filter_definition?: Record<string, unknown> | null;
    created_at: string;
    updated_at?: string | null;
    lead_count: number;
    reachable_count: number;
    risky_count: number;
    invalid_count: number;
    suppressed_count: number;
    unsubscribed_count?: number;
    consent_unknown_count?: number;
    type_mismatch_count?: number;
    status_counts: Record<string, number>;
    contact_type_counts?: Record<string, number>;
    consent_counts?: Record<string, number>;
    unsubscribe_counts?: Record<string, number>;
    quality_tier_counts?: Record<string, number>;
    high_quality_count?: number;
    medium_quality_count?: number;
    low_quality_count?: number;
}

export interface LeadListLeadResponse {
    list: LeadList;
    leads: Contact[];
}

export interface CampaignListSummary {
    lead_count: number;
    deduped_count?: number;
    reachable_count: number;
    risky_count: number;
    invalid_count: number;
    suppressed_count: number;
    unsubscribed_count?: number;
    consent_unknown_count?: number;
    type_mismatch_count?: number;
    status_counts: Record<string, number>;
    contact_type_counts?: Record<string, number>;
    consent_counts?: Record<string, number>;
    unsubscribe_counts?: Record<string, number>;
    quality_tier_counts?: Record<string, number>;
    blocked_breakdown?: Record<string, number>;
    high_quality_count?: number;
    medium_quality_count?: number;
    low_quality_count?: number;
    industry_counts?: Record<string, number>;
    persona_counts?: Record<string, number>;
    lists: LeadList[];
}

export interface LeadVerificationResult {
    lead_id: string;
    email: string;
    status: string;
    score: number;
    integrity: "high" | "medium" | "low";
    reasons: string[];
    checked_at: string;
    syntax_valid: boolean;
    domain_valid: boolean;
    mx_valid: boolean;
    is_disposable: boolean;
    is_role_based: boolean;
    is_duplicate: boolean;
    is_suppressed: boolean;
}

export interface LeadVerificationJob {
    job_id: string;
    status: string;
    requested_count: number;
    processed_count: number;
    results: LeadVerificationResult[];
    error?: string | null;
    started_at?: string | null;
    finished_at?: string | null;
}

export interface SuppressionEntry {
    id: string;
    email: string;
    reason: string;
    source?: string;
    created_at: string;
}

export interface HealthComponent {
    status: "healthy" | "degraded" | "failed" | "unknown";
    service?: string;
    latency_ms?: number;
    active_count?: number;
    total_registered?: number;
    detail?: string | null;
}

export interface SystemHealth {
    status: "healthy" | "degraded" | "failed";
    components: Record<string, HealthComponent>;
    timestamp: string;
}

export interface SettingsUserSummary {
    email: string;
    full_name?: string | null;
    is_admin: boolean;
    is_active: boolean;
}

export interface SettingsHealthItem {
    status: string;
    detail?: string | null;
}

export interface ProviderStatusItem {
    enabled: boolean;
    configured: boolean;
    status: string;
    detail?: string | null;
    reason?: string | null;
    checked_at?: string | null;
    oauth_connection_status?: string | null;
    safe_mode?: boolean | null;
}

export interface SettingsSummary {
    app_env: string;
    project_name: string;
    api_base_path: string;
    backend_url: string;
    frontend_api_path: string;
    worker_mode: "lean" | "full";
    worker_available: boolean;
    worker_detail?: string | null;
    readiness_status: "healthy" | "degraded" | "failed" | "unknown";
    safe_mode: boolean;
    mailcow_mutations_enabled: boolean;
    mailcow_configured: boolean;
    mailcow_status: string;
    mailcow_reason?: string | null;
    mailcow_detail?: string | null;
    frontend_mailcow_direct_access: boolean;
    default_provider: MailProviderType;
    enabled_providers: MailProviderType[];
    allow_existing_disabled_provider_mailboxes: boolean;
    providers: Record<MailProviderType, ProviderStatusItem>;
    auth_enabled: boolean;
    session_healthy: boolean;
    current_user: SettingsUserSummary;
    health: Record<string, SettingsHealthItem>;
}

export interface WarmupMailboxStatus {
    id: string;
    email: string;
    display_name: string;
    provider_type?: MailProviderType;
    warmup_enabled: boolean;
    warmup_status: string;
    warmup_last_checked_at?: string | null;
    warmup_last_result?: string | null;
    warmup_block_reason?: string | null;
    warmup_recommendation?: string | null;
    smtp_last_check_status?: string | null;
    smtp_last_check_message?: string | null;
    status: string;
    current_warmup_stage: number;
}

export interface WarmupBlocker {
    code: string;
    message: string;
}

export interface WarmupPair {
    id: string;
    sender_mailbox_id: string;
    recipient_mailbox_id: string;
    sender_email: string;
    recipient_email: string;
    state: string;
    last_send_at?: string | null;
    next_scheduled_at?: string | null;
    last_result?: string | null;
    last_error?: string | null;
    daily_sent_count: number;
    daily_limit: number;
}

export interface WarmupLog {
    id: string;
    pair_id?: string | null;
    sender_mailbox_id: string;
    recipient_mailbox_id?: string | null;
    sender_email?: string | null;
    recipient_email?: string | null;
    timestamp?: string | null;
    event_type: string;
    status: string;
    error_category?: string | null;
    result_detail?: string | null;
    target_email: string;
    subject?: string | null;
    scheduled_for?: string | null;
    sent_at?: string | null;
}

export interface WarmupStatus {
    global_status: "enabled" | "paused";
    worker_status: HealthComponent & { enabled?: boolean };
    scheduler_status: {
        status: string;
        detail?: string | null;
        last_seen_at?: string | null;
    };
    inboxes_warming_count: number;
    eligible_mailboxes_count: number;
    active_pairs_count: number;
    successful_sends_today: number;
    failed_sends_today: number;
    health_percent?: number | null;
    blockers: WarmupBlocker[];
    next_action?: string | null;
    last_run_at?: string | null;
    next_run_at?: string | null;
    mailboxes: WarmupMailboxStatus[];
}

export interface Alert {
    id: string;
    alert_type: string;
    severity: "info" | "warning" | "critical";
    title: string;
    message: string;
    is_active: boolean;
    created_at: string;
}

export interface JobLog {
    id: string;
    job_id: string;
    job_type: string;
    status: string;
    error_message?: string;
    retry_count: number;
    created_at: string;
}

export interface SendEmailPayload {
    mailbox_id: string;
    to: string[];
    cc?: string[];
    bcc?: string[];
    subject: string;
    text_body: string;
    html_body?: string | null;
}

export interface SendEmailResult {
    success: boolean;
    status: string;
    message_id: string;
    provider: MailProviderType | string;
    log_id?: string | null;
}

export interface SMTPDiagnosticResult {
    status: string;
    category: string;
    message: string;
    host: string;
    port: number;
    security_mode: "starttls" | "ssl" | "plain";
    dns_resolved: boolean;
    connected: boolean;
    tls_negotiated: boolean;
    auth_succeeded: boolean;
}

export interface SendEmailLog {
    id: string;
    mailbox_id?: string | null;
    campaign_id?: string | null;
    contact_id?: string | null;
    target_email: string;
    subject?: string | null;
    delivery_status: string;
    provider_message_id?: string | null;
    smtp_response?: string | null;
    created_at?: string | null;
}

export interface DeliverabilitySummary {
    sent?: number;
    bounced?: number;
    replied?: number;
    suppressed?: number;
    total_contacts?: number;
    valid_contacts?: number;
    risky_contacts?: number;
    invalid_contacts?: number;
    suppressed_contacts?: number;
    unsubscribed_contacts?: number;
    b2b_campaigns?: number;
    b2c_campaigns?: number;
    active_campaigns?: number;
    mailbox_count?: number;
    domain_count?: number;
    [key: string]: number | undefined;
}

export type DeliverabilityStatus = "ready" | "warning" | "degraded" | "blocked" | "unknown";

export interface DeliverabilityIssue {
    code: string;
    severity: string;
    message: string;
    next_action?: string | null;
    source?: string | null;
    entity?: string | null;
    priority?: number;
}

export interface DeliverabilityCheck {
    code: string;
    label: string;
    status: "pass" | "warning" | "fail" | string;
    severity: string;
    detail: string;
    next_action?: string | null;
    checked_at?: string | null;
    metadata?: unknown;
}

export interface DeliverabilityEntity {
    id?: string;
    type?: string;
    name?: string;
    email?: string;
    domain?: string;
    provider_type?: MailProviderType | string;
    status: DeliverabilityStatus;
    score?: number | null;
    last_checked_at?: string | null;
    blockers: DeliverabilityIssue[];
    warnings: DeliverabilityIssue[];
    next_actions: string[];
    checks: DeliverabilityCheck[];
    recent_sends?: {
        success_7d: number;
        failed_7d: number;
        success_30d: number;
        failed_30d: number;
        last_status?: string | null;
        last_error?: string | null;
        last_sent_at?: string | null;
    };
    warmup?: {
        enabled: boolean;
        status?: string | null;
        last_result?: string | null;
        block_reason?: string | null;
    };
}

export interface DeliverabilityOverview {
    status: DeliverabilityStatus;
    score?: number | null;
    generated_at: string;
    blockers: DeliverabilityIssue[];
    warnings: DeliverabilityIssue[];
    fix_priority?: DeliverabilityIssue[];
    next_actions: string[];
    summary: {
        domains: Record<string, number>;
        mailboxes: Record<string, number>;
        audience: Record<string, unknown>;
        warmup: Record<string, unknown>;
        providers: Record<string, unknown>;
        campaigns: Record<string, number>;
    };
    domains: DeliverabilityEntity[];
    mailboxes: DeliverabilityEntity[];
    audience: {
        status: DeliverabilityStatus;
        summary: Record<string, unknown>;
        blockers: DeliverabilityIssue[];
        warnings: DeliverabilityIssue[];
        next_actions: string[];
    };
    warmup: {
        status: DeliverabilityStatus;
        summary: Record<string, unknown>;
        blockers: DeliverabilityIssue[];
        warnings: DeliverabilityIssue[];
        next_actions: string[];
    };
    providers: Array<{
        provider_type: MailProviderType | string;
        enabled: boolean;
        configured: boolean;
        status: DeliverabilityStatus;
        health_status?: string | null;
        detail?: string | null;
        reason?: string | null;
        mailbox_count: number;
        checked_at?: string | null;
    }>;
    campaigns: {
        status: DeliverabilityStatus;
        summary: Record<string, number>;
        items: DeliverabilityEntity[];
        blockers: DeliverabilityIssue[];
        warnings: DeliverabilityIssue[];
    };
}

export interface Thread {
    id: string;
    subject: string;
    mailbox_id: string;
    mailbox_email?: string | null;
    mailbox_provider?: MailProviderType | null;
    contact_email: string;
    contact_name?: string;
    campaign_id?: string | null;
    campaign_name?: string | null;
    contact_id?: string | null;
    linkage_status?: string | null;
    participants?: string[];
    status: string;
    last_message_at: string;
    snippet?: string;
    unread: boolean;
    unread_count?: number;
    last_message_direction?: string | null;
    last_message_preview?: string | null;
}

export interface Message {
    id: string;
    thread_id: string;
    direction: "inbound" | "outbound";
    subject: string;
    body_text: string;
    body_html?: string;
    from_address: string;
    to_address: string;
    cc_address?: string;
    is_read?: boolean;
    sent_at: string;
}

export interface InboxStatusMailbox {
    id: string;
    email: string;
    display_name: string;
    status: string;
    provider_type?: MailProviderType;
    oauth_connection_status?: string | null;
    inbox_sync_enabled: boolean;
    inbox_sync_status: string;
    inbox_last_synced_at?: string | null;
    inbox_last_success_at?: string | null;
    inbox_last_error?: string | null;
    inbox_block_reason?: string | null;
    imap_health?: string | null;
    imap_health_detail?: string | null;
    smtp_last_check_status?: string | null;
    imap_host?: string | null;
    imap_port?: number | null;
}

export interface InboxStatus {
    sync_enabled: boolean;
    workers_enabled: boolean;
    worker_status: {
        status: string;
        detail?: string | null;
        last_seen_at?: string | null;
    };
    scheduler_status: {
        status: string;
        detail?: string | null;
        last_seen_at?: string | null;
        next_run_at?: string | null;
    };
    mailboxes: InboxStatusMailbox[];
    configured_mailboxes_count: number;
    sync_enabled_mailboxes_count: number;
    healthy_mailboxes_count: number;
    threads_count: number;
    unread_threads_count: number;
    messages_received_today: number;
    last_sync_at?: string | null;
    last_message_at?: string | null;
    blockers: Array<{ code: string; message: string }>;
}

export interface InboxSyncResult {
    status: string;
    mailboxes_processed: number;
    results: Array<{
        mailbox_id: string;
        mailbox_email: string;
        status: string;
        detail: string;
        fetched_count: number;
        imported_count: number;
        duplicate_count: number;
        thread_count: number;
        last_synced_at?: string | null;
    }>;
}
