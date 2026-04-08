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
    email: string;
    display_name: string;
    status: string;
    daily_send_limit: number;
    current_warmup_stage: number;
    warmup_enabled: boolean;
    created_at: string;
}

export interface Campaign {
    id: string;
    name: string;
    status: string; // draft, active, paused, completed, etc.
    template_subject: string;
    template_body: string;
    daily_limit: number;
    created_at: string;
    // Computed fields for UI
    sent_count?: number;
    lead_count?: number;
    reply_rate?: string | number;
}

export interface Contact {
    id: string;
    email: string;
    first_name: string | null;
    last_name: string | null;
    company: string | null;
    verification_score: number | null;
    is_suppressed: boolean;
    source?: string;
    created_at: string;
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
}

export interface SystemHealth {
    status: "healthy" | "degraded" | "failed";
    components: Record<string, HealthComponent>;
    timestamp: string;
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
