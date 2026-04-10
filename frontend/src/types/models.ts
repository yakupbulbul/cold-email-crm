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
    verification_summary?: Record<string, unknown>;
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
    smtp_host?: string;
    smtp_port?: number;
    smtp_security_mode: "starttls" | "ssl" | "plain";
    smtp_last_checked_at?: string | null;
    smtp_last_check_status?: string | null;
    smtp_last_check_category?: string | null;
    smtp_last_check_message?: string | null;
    status: string;
    daily_send_limit: number;
    current_warmup_stage: number;
    warmup_enabled: boolean;
    remote_mailcow_provisioned: boolean;
    provisioning_mode: "local_only" | "mailcow_synced";
    created_at: string;
}

export interface Campaign {
    id: string;
    name: string;
    status: string; // draft, active, paused, completed, etc.
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
        state: "idle" | "queued" | "running" | "waiting_for_beat";
        job_id?: string | null;
        job_created_at?: string | null;
        job_started_at?: string | null;
        last_completed_at?: string | null;
        next_dispatch_at?: string | null;
        beat_interval_seconds?: number;
        detail?: string | null;
    };
}

export interface CampaignActionResult {
    status: string;
    campaign?: string;
    eligible_leads?: number;
    blocked_leads?: Record<string, number>;
    job_queued?: boolean;
    job_id?: string | null;
}

export interface CampaignPreflightResult {
    status: string;
    blocked: boolean;
    audience_summary?: CampaignListSummary;
    checks: Array<{
        name: string;
        status: string;
        message: string;
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
    auth_enabled: boolean;
    session_healthy: boolean;
    current_user: SettingsUserSummary;
    health: Record<string, SettingsHealthItem>;
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
    provider: string;
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

export interface Thread {
    id: string;
    subject: string;
    contact_email: string;
    contact_name?: string;
    status: string;
    last_message_at: string;
    snippet?: string;
    unread: boolean;
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
    sent_at: string;
}
