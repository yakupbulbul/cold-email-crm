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
    created_at: string;
    // Computed fields for UI
    sent_count?: number;
    lead_count?: number;
    reply_rate?: string | number;
    lists_summary?: CampaignListSummary;
}

export interface CampaignActionResult {
    status: string;
    campaign?: string;
    eligible_leads?: number;
    job_queued?: boolean;
    job_id?: string | null;
}

export interface CampaignPreflightResult {
    status: string;
    blocked: boolean;
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
    email_status: string;
    verification_score: number | null;
    verification_integrity: "high" | "medium" | "low" | null;
    last_verified_at: string | null;
    is_disposable: boolean;
    is_role_based: boolean;
    is_suppressed: boolean;
    verification_reasons: string[] | null;
    source?: string;
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
    status_counts: Record<string, number>;
}

export interface LeadListLeadResponse {
    list: LeadList;
    leads: Contact[];
}

export interface CampaignListSummary {
    lead_count: number;
    reachable_count: number;
    risky_count: number;
    invalid_count: number;
    suppressed_count: number;
    status_counts: Record<string, number>;
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

export interface DeliverabilitySummary {
    sent?: number;
    bounced?: number;
    replied?: number;
    suppressed?: number;
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
