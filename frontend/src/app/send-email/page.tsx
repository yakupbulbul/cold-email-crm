"use client";

import { useEffect, useState } from "react";
import { AlertCircle, CheckCircle2, LoaderCircle, MailCheck, Send } from "lucide-react";

import Spinner from "@/components/ui/Spinner";
import { useApiService } from "@/services/api";
import { Mailbox, SendEmailLog, SendEmailResult } from "@/types/models";

function parseRecipients(raw: string): string[] {
  return raw
    .split(",")
    .map((value) => value.trim())
    .filter(Boolean);
}

export default function SendEmailPage() {
  const { getMailboxes, sendEmail, getSendEmailLogs } = useApiService();
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
      <div className="flex min-h-[50vh] items-center justify-center rounded-2xl border border-slate-200 bg-white">
        <Spinner size="lg" />
      </div>
    );
  }

  return (
    <div className="space-y-6 animate-fade-in">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold tracking-tight text-slate-800">Send Email</h1>
      </div>

      {pageError ? (
        <div className="rounded-2xl border border-red-200 bg-red-50 px-5 py-4 text-sm font-medium text-red-700">
          {pageError}
        </div>
      ) : null}

      <form onSubmit={handleSend} className="grid gap-4 rounded-2xl border border-slate-200 bg-white p-5 shadow-sm md:grid-cols-2">
        <div>
          <label htmlFor="send-email-mailbox" className="mb-2 block text-sm font-semibold text-slate-700">Sender Mailbox</label>
          <select id="send-email-mailbox" value={mailboxId} onChange={(event) => setMailboxId(event.target.value)} className="w-full rounded-xl border border-slate-200 px-4 py-3 text-slate-900 outline-none focus:border-blue-500 focus:ring-4 focus:ring-blue-100">
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
          <input id="send-email-to" value={to} onChange={(event) => setTo(event.target.value)} placeholder="recipient@example.com" className="w-full rounded-xl border border-slate-200 px-4 py-3 text-slate-900 outline-none focus:border-blue-500 focus:ring-4 focus:ring-blue-100" />
        </div>
        <div>
          <label htmlFor="send-email-cc" className="mb-2 block text-sm font-semibold text-slate-700">CC</label>
          <input id="send-email-cc" value={cc} onChange={(event) => setCc(event.target.value)} placeholder="Optional, comma separated" className="w-full rounded-xl border border-slate-200 px-4 py-3 text-slate-900 outline-none focus:border-blue-500 focus:ring-4 focus:ring-blue-100" />
        </div>
        <div>
          <label htmlFor="send-email-bcc" className="mb-2 block text-sm font-semibold text-slate-700">BCC</label>
          <input id="send-email-bcc" value={bcc} onChange={(event) => setBcc(event.target.value)} placeholder="Optional, comma separated" className="w-full rounded-xl border border-slate-200 px-4 py-3 text-slate-900 outline-none focus:border-blue-500 focus:ring-4 focus:ring-blue-100" />
        </div>
        <div className="md:col-span-2">
          <label htmlFor="send-email-subject" className="mb-2 block text-sm font-semibold text-slate-700">Subject</label>
          <input id="send-email-subject" value={subject} onChange={(event) => setSubject(event.target.value)} className="w-full rounded-xl border border-slate-200 px-4 py-3 text-slate-900 outline-none focus:border-blue-500 focus:ring-4 focus:ring-blue-100" />
        </div>
        <div className="md:col-span-2">
          <label htmlFor="send-email-text-body" className="mb-2 block text-sm font-semibold text-slate-700">Text Body</label>
          <textarea id="send-email-text-body" value={textBody} onChange={(event) => setTextBody(event.target.value)} rows={6} className="w-full rounded-xl border border-slate-200 px-4 py-3 text-slate-900 outline-none focus:border-blue-500 focus:ring-4 focus:ring-blue-100" />
        </div>
        <div className="md:col-span-2">
          <label htmlFor="send-email-html-body" className="mb-2 block text-sm font-semibold text-slate-700">HTML Body</label>
          <textarea id="send-email-html-body" value={htmlBody} onChange={(event) => setHtmlBody(event.target.value)} rows={4} placeholder="<p>Hello from the app</p>" className="w-full rounded-xl border border-slate-200 px-4 py-3 font-mono text-sm text-slate-900 outline-none focus:border-blue-500 focus:ring-4 focus:ring-blue-100" />
        </div>
        <div className="md:col-span-2 flex items-center justify-between gap-4">
          <div className="text-sm text-slate-500">Direct send uses the backend SMTP integration only. It bypasses campaign lists, workers, and preflight.</div>
          <button type="submit" disabled={submitting || mailboxes.length === 0} className="inline-flex items-center gap-2 rounded-xl bg-slate-900 px-5 py-3 font-bold text-white shadow-lg shadow-slate-900/20 transition-colors hover:bg-slate-800 disabled:cursor-not-allowed disabled:opacity-50">
            {submitting ? <LoaderCircle size={18} className="animate-spin" /> : <Send size={18} />}
            {submitting ? "Sending..." : "Send Email"}
          </button>
        </div>
      </form>

      {result ? (
        <div className="rounded-2xl border border-emerald-200 bg-emerald-50 px-5 py-4 text-sm text-emerald-700">
          <div className="flex items-center gap-2 font-semibold">
            <CheckCircle2 size={18} />
            Email sent through {result.provider}.
          </div>
          <div className="mt-2">Message ID: <span className="font-mono">{result.message_id}</span></div>
        </div>
      ) : null}

      {submitError ? (
        <div className="rounded-2xl border border-red-200 bg-red-50 px-5 py-4 text-sm text-red-700">
          <div className="flex items-center gap-2 font-semibold">
            <AlertCircle size={18} />
            Send failed
          </div>
          <div className="mt-2">{submitError}</div>
        </div>
      ) : null}

      <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
        <div className="mb-4 flex items-center gap-2">
          <MailCheck size={18} className="text-slate-500" />
          <h2 className="text-lg font-bold text-slate-800">Recent Send Attempts</h2>
        </div>
        {logs.length === 0 ? (
          <div className="rounded-xl border border-slate-200 bg-slate-50 px-4 py-6 text-sm text-slate-500">
            No send attempts logged yet.
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left">
              <thead>
                <tr className="border-b border-slate-200 text-xs uppercase tracking-wide text-slate-500">
                  <th className="px-2 py-3">When</th>
                  <th className="px-2 py-3">To</th>
                  <th className="px-2 py-3">Subject</th>
                  <th className="px-2 py-3">Status</th>
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
                    <td className="px-2 py-3 text-xs text-slate-500">{log.smtp_response || "-"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  );
}
