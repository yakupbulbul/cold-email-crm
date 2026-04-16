"use client";

import { useEffect, useState } from "react";
import { CheckCircle2, LoaderCircle, MailCheck, Send } from "lucide-react";

import Spinner from "@/components/ui/Spinner";
import { useApiService } from "@/services/api";
import { Mailbox, SMTPDiagnosticResult, SendEmailLog, SendEmailResult } from "@/types/models";
import { AlertBanner, EmptyState, MetricCard, PageHeader, SectionTitle, SurfaceCard } from "@/components/ui/primitives";

function parseRecipients(raw: string): string[] {
  return raw
    .split(",")
    .map((value) => value.trim())
    .filter(Boolean);
}

function buildSenderPreview(mailbox: Mailbox | null): string {
  if (!mailbox) return "";
  const displayName = mailbox.display_name?.trim();
  return displayName ? `${displayName} <${mailbox.email}>` : mailbox.email;
}

export default function SendEmailPage() {
  const { getMailboxes, sendEmail, getSendEmailLogs, checkMailboxSmtp } = useApiService();
  const [mailboxes, setMailboxes] = useState<Mailbox[]>([]);
  const [logs, setLogs] = useState<SendEmailLog[]>([]);
  const [mailboxId, setMailboxId] = useState("");
  const [to, setTo] = useState("");
  const [cc, setCc] = useState("");
  const [bcc, setBcc] = useState("");
  const [subject, setSubject] = useState("Test email");
  const [textBody, setTextBody] = useState("Hello from the app");
  const [htmlBody, setHtmlBody] = useState("");
  const [loadingPage, setLoadingPage] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [pageError, setPageError] = useState<string | null>(null);
  const [result, setResult] = useState<SendEmailResult | null>(null);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [smtpDiagnostic, setSmtpDiagnostic] = useState<SMTPDiagnosticResult | null>(null);

  useEffect(() => {
    const load = async () => {
      setLoadingPage(true);
      setPageError(null);
      const [mailboxData, logData] = await Promise.all([getMailboxes(), getSendEmailLogs()]);
      if (!mailboxData) {
        setPageError("Failed to load mailboxes for direct send.");
        setLoadingPage(false);
        return;
      }
      setMailboxes(mailboxData);
      setMailboxId(mailboxData[0]?.id || "");
      setLogs(logData || []);
      setLoadingPage(false);
    };
    void load();
  }, [getMailboxes, getSendEmailLogs]);

  const refreshLogs = async () => {
    const refreshed = await getSendEmailLogs();
    if (refreshed) setLogs(refreshed);
  };

  const selectedMailbox = mailboxes.find((mailbox) => mailbox.id === mailboxId) || null;

  const handleCheckSelectedMailbox = async () => {
    if (!mailboxId) return;
    setSubmitError(null);
    try {
      const diagnostic = await checkMailboxSmtp(mailboxId);
      setSmtpDiagnostic(diagnostic);
      const refreshed = await getMailboxes();
      if (refreshed) setMailboxes(refreshed);
    } catch (error) {
      setSubmitError(error instanceof Error ? error.message : "SMTP check failed.");
    }
  };

  const handleSend = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setResult(null);
    setSubmitError(null);

    const toRecipients = parseRecipients(to);
    if (!mailboxId || toRecipients.length === 0 || !subject.trim() || !textBody.trim()) {
      setSubmitError("Sender mailbox, at least one recipient, subject, and text body are required.");
      return;
    }

    setSubmitting(true);
    try {
      const response = await sendEmail({
        mailbox_id: mailboxId,
        to: toRecipients,
        cc: parseRecipients(cc),
        bcc: parseRecipients(bcc),
        subject: subject.trim(),
        text_body: textBody.trim(),
        html_body: htmlBody.trim() || null,
      });
      setResult(response);
      await refreshLogs();
    } catch (error) {
      setSubmitError(error instanceof Error ? error.message : "Direct send failed.");
    } finally {
      setSubmitting(false);
    }
  };

  if (loadingPage) {
    return (
      <SurfaceCard className="flex min-h-[50vh] items-center justify-center">
        <Spinner size="lg" />
      </SurfaceCard>
    );
  }

  return (
    <div className="space-y-6 animate-fade-in">
      <PageHeader
        eyebrow="Testing"
        title="Send Email"
        description="Send one real email immediately through the backend mail provider integration and inspect the result without campaigns or worker timing."
      />

      <div className="grid gap-4 md:grid-cols-3">
        <MetricCard title="Sender mailboxes" value={mailboxes.length} detail="Mailboxes available for direct testing." icon={MailCheck} />
        <MetricCard title="Recent attempts" value={logs.length} detail="Persisted send attempts shown below." icon={Send} tone="info" />
        <MetricCard title="Selected sender" value={selectedMailbox ? selectedMailbox.email : "None"} detail={selectedMailbox ? buildSenderPreview(selectedMailbox) : "Choose a mailbox to preview sender identity."} icon={CheckCircle2} tone="success" />
      </div>

      {pageError ? <AlertBanner tone="danger" title="Failed to load direct-send data">{pageError}</AlertBanner> : null}

      <SurfaceCard className="p-5">
      <form onSubmit={handleSend} className="grid gap-4 md:grid-cols-2">
        <div>
          <label htmlFor="send-email-mailbox" className="mb-2 block text-sm font-semibold text-slate-700">Sender Mailbox</label>
          <select id="send-email-mailbox" value={mailboxId} onChange={(event) => setMailboxId(event.target.value)} className="form-input">
            <option value="">Select a mailbox</option>
            {mailboxes.map((mailbox) => (
              <option key={mailbox.id} value={mailbox.id}>
                {mailbox.email} {mailbox.status !== "active" ? `(status: ${mailbox.status})` : ""}
              </option>
            ))}
          </select>
        </div>
        <div>
          <label htmlFor="send-email-to" className="mb-2 block text-sm font-semibold text-slate-700">To</label>
          <input id="send-email-to" value={to} onChange={(event) => setTo(event.target.value)} placeholder="recipient@example.com" className="form-input" />
        </div>
        <div>
          <label htmlFor="send-email-cc" className="mb-2 block text-sm font-semibold text-slate-700">CC</label>
          <input id="send-email-cc" value={cc} onChange={(event) => setCc(event.target.value)} placeholder="Optional, comma separated" className="form-input" />
        </div>
        <div>
          <label htmlFor="send-email-bcc" className="mb-2 block text-sm font-semibold text-slate-700">BCC</label>
          <input id="send-email-bcc" value={bcc} onChange={(event) => setBcc(event.target.value)} placeholder="Optional, comma separated" className="form-input" />
        </div>
        <div className="md:col-span-2">
          <label htmlFor="send-email-subject" className="mb-2 block text-sm font-semibold text-slate-700">Subject</label>
          <input id="send-email-subject" value={subject} onChange={(event) => setSubject(event.target.value)} className="form-input" />
        </div>
        <div className="md:col-span-2">
          <label htmlFor="send-email-text-body" className="mb-2 block text-sm font-semibold text-slate-700">Text Body</label>
          <textarea id="send-email-text-body" value={textBody} onChange={(event) => setTextBody(event.target.value)} rows={6} className="form-input" />
        </div>
        <div className="md:col-span-2">
          <label htmlFor="send-email-html-body" className="mb-2 block text-sm font-semibold text-slate-700">HTML Body</label>
          <textarea id="send-email-html-body" value={htmlBody} onChange={(event) => setHtmlBody(event.target.value)} rows={4} placeholder="<p>Hello from the app</p>" className="form-input font-mono text-sm" />
        </div>
        <div className="md:col-span-2 flex items-center justify-between gap-4">
          <div className="text-sm text-slate-500">Direct send uses the backend SMTP integration only. It bypasses campaign lists, workers, and preflight.</div>
          <div className="flex items-center gap-3">
            <button data-testid="check-smtp-button" type="button" onClick={() => void handleCheckSelectedMailbox()} disabled={!mailboxId || submitting} className="btn-secondary">
              <MailCheck size={16} />
              Check SMTP
            </button>
            <button type="submit" disabled={submitting || mailboxes.length === 0} className="btn-primary">
              {submitting ? <LoaderCircle size={18} className="animate-spin" /> : <Send size={18} />}
              {submitting ? "Sending..." : "Send Email"}
            </button>
          </div>
        </div>
      </form>
      </SurfaceCard>

      {selectedMailbox ? (
        <SurfaceCard className="px-5 py-4">
          <div className="text-sm font-semibold text-slate-700">Selected mailbox transport</div>
          <div className="mt-2 text-sm font-medium text-slate-700">
            From preview: <span className="break-all text-slate-800">{buildSenderPreview(selectedMailbox)}</span>
          </div>
          <div className="mt-2 text-sm text-slate-600">
            {selectedMailbox.email} via {(selectedMailbox.provider_type || "mailcow").replaceAll("_", " ")} on {selectedMailbox.smtp_host}:{selectedMailbox.smtp_port} using {selectedMailbox.smtp_security_mode.toUpperCase()}
          </div>
          <div className="mt-2 text-sm text-slate-600">
            Provider state: {(selectedMailbox.provider_status || "active").replaceAll("_", " ")} · OAuth {(selectedMailbox.oauth_connection_status || "not_connected").replaceAll("_", " ")}
          </div>
          <div className={`mt-2 text-sm font-medium ${(smtpDiagnostic?.status || selectedMailbox.smtp_last_check_status) === 'healthy' ? 'text-emerald-700' : 'text-slate-600'}`}>
            {smtpDiagnostic?.message || selectedMailbox.last_provider_check_message || selectedMailbox.smtp_last_check_message || 'Provider diagnostics have not been checked yet for this mailbox.'}
          </div>
        </SurfaceCard>
      ) : null}

      {result ? <AlertBanner tone="success" title={`Email sent through ${result.provider}.`}>Message ID: <span className="font-mono" data-testid="send-result-message-id">{result.message_id}</span></AlertBanner> : null}

      {submitError ? <AlertBanner tone="danger" title="Send failed">{submitError}</AlertBanner> : null}

      <SurfaceCard className="p-5">
        <SectionTitle title="Recent send attempts" description="Operational history for direct SMTP tests." />
        {logs.length === 0 ? (
          <EmptyState icon={MailCheck} title="No send attempts logged yet" description="Direct test sends will appear here with real message IDs and results." />
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left">
              <thead>
                <tr className="border-b border-slate-200 text-xs uppercase tracking-wide text-slate-500">
                  <th className="px-2 py-3">When</th>
                  <th className="px-2 py-3">To</th>
                  <th className="px-2 py-3">Subject</th>
                    <th className="px-2 py-3">Status</th>
                    <th className="px-2 py-3">Message ID</th>
                    <th className="px-2 py-3">Response</th>
                </tr>
              </thead>
              <tbody>
                {logs.map((log) => (
                  <tr key={log.id} className="border-b border-slate-100 text-sm text-slate-700">
                    <td className="px-2 py-3">{log.created_at ? new Date(log.created_at).toLocaleString() : "Unknown"}</td>
                    <td className="px-2 py-3">{log.target_email}</td>
                    <td className="px-2 py-3">{log.subject || "-"}</td>
                    <td className="px-2 py-3">
                      <span className={`rounded-full px-3 py-1 text-xs font-bold ${log.delivery_status === "success" ? "bg-emerald-50 text-emerald-700" : "bg-red-50 text-red-700"}`}>
                        {log.delivery_status}
                      </span>
                    </td>
                    <td className="px-2 py-3 text-xs font-mono text-slate-500">{log.provider_message_id || "-"}</td>
                    <td className="px-2 py-3 text-xs text-slate-500">{log.smtp_response || "-"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </SurfaceCard>
    </div>
  );
}
