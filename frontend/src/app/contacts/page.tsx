"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import {
  AlertCircle,
  CheckCircle2,
  Download,
  ListPlus,
  LoaderCircle,
  MailCheck,
  ShieldAlert,
  ShieldX,
  Sparkles,
  Upload,
  Tags,
} from "lucide-react";

import Table, { TableCell, TableRow } from "@/components/ui/Table";
import Spinner from "@/components/ui/Spinner";
import { useApiService } from "@/services/api";
import { Contact, LeadList, LeadVerificationResult } from "@/types/models";

type BulkState = {
  jobId: string;
  status: string;
  requestedCount: number;
  processedCount: number;
  error?: string | null;
};

const STATUS_STYLES: Record<string, string> = {
  unverified: "bg-slate-100 text-slate-700",
  valid: "bg-green-100 text-green-700",
  risky: "bg-yellow-100 text-yellow-700",
  invalid: "bg-red-100 text-red-700",
  no_mx: "bg-orange-100 text-orange-700",
  disposable: "bg-amber-100 text-amber-700",
  role_based: "bg-indigo-100 text-indigo-700",
  duplicate: "bg-purple-100 text-purple-700",
  suppressed: "bg-red-100 text-red-700",
};

const INTEGRITY_STYLES: Record<string, string> = {
  high: "bg-emerald-50 text-emerald-700",
  medium: "bg-yellow-50 text-yellow-700",
  low: "bg-rose-50 text-rose-700",
};

function applyVerificationResult(lead: Contact, result: LeadVerificationResult): Contact {
  if (lead.id !== result.lead_id) {
    return lead;
  }
  return {
    ...lead,
    email: result.email,
    email_status: result.status,
    verification_score: result.score,
    verification_integrity: result.integrity,
    last_verified_at: result.checked_at,
    is_disposable: result.is_disposable,
    is_role_based: result.is_role_based,
    is_suppressed: result.is_suppressed,
    verification_reasons: result.reasons,
  };
}

function formatStatus(status: string) {
  return status.replace(/_/g, " ");
}

function statusBadge(status: string) {
  const style = STATUS_STYLES[status] || STATUS_STYLES.unverified;
  const icon =
    status === "valid" ? <CheckCircle2 size={14} /> :
    status === "suppressed" ? <ShieldX size={14} /> :
    status === "risky" ? <ShieldAlert size={14} /> :
    status === "unverified" ? <AlertCircle size={14} /> :
    <MailCheck size={14} />;

  return (
    <span className={`inline-flex items-center gap-1.5 rounded-lg px-3 py-1 text-xs font-bold tracking-wide ${style}`}>
      {icon}
      {formatStatus(status)}
    </span>
  );
}

function scoreBadge(score: number | null) {
  if (score === null || score === undefined) {
    return <span className="rounded-lg bg-slate-100 px-3 py-1 text-xs font-bold text-slate-600">Not scored</span>;
  }

  const style = score >= 90 ? "bg-green-50 text-green-700" : score >= 70 ? "bg-yellow-50 text-yellow-700" : "bg-red-50 text-red-700";
  return <span className={`rounded-lg px-3 py-1 text-xs font-bold ${style}`}>{score}</span>;
}

function integrityBadge(integrity: Contact["verification_integrity"]) {
  if (!integrity) {
    return <span className="rounded-lg bg-slate-100 px-3 py-1 text-xs font-bold text-slate-600">Not checked</span>;
  }

  return (
    <span className={`rounded-lg px-3 py-1 text-xs font-bold ${INTEGRITY_STYLES[integrity] || "bg-slate-100 text-slate-700"}`}>
      {integrity}
    </span>
  );
}

export default function ContactsPage() {
  const searchParams = useSearchParams();
  const sourceJobId = searchParams.get("source_job");
  const {
    getLeads,
    getLists,
    updateLead,
    updateLeadContactTypeBulk,
    addLeadToList,
    addLeadsToListBulk,
    verifyLead,
    verifyLeadsBulk,
    getLeadVerificationJob,
    assignLeadTagsBulk,
    suppressLeadsBulk,
    loading,
    error,
  } = useApiService();

  const [leads, setLeads] = useState<Contact[]>([]);
  const [lists, setLists] = useState<LeadList[]>([]);
  const [search, setSearch] = useState("");
  const [listFilterId, setListFilterId] = useState("all");
  const [contactTypeFilter, setContactTypeFilter] = useState("all");
  const [consentFilter, setConsentFilter] = useState("all");
  const [unsubscribeFilter, setUnsubscribeFilter] = useState("all");
  const [selectedLeadIds, setSelectedLeadIds] = useState<string[]>([]);
  const [expandedLeadId, setExpandedLeadId] = useState<string | null>(null);
  const [verifyingLeadId, setVerifyingLeadId] = useState<string | null>(null);
  const [addingLeadId, setAddingLeadId] = useState<string | null>(null);
  const [bulkListTargetId, setBulkListTargetId] = useState("");
  const [bulkTags, setBulkTags] = useState("");
  const [bulkContactType, setBulkContactType] = useState<"b2b" | "b2c" | "mixed">("mixed");
  const [rowListTargets, setRowListTargets] = useState<Record<string, string>>({});
  const [bulkState, setBulkState] = useState<BulkState | null>(null);
  const [banner, setBanner] = useState<string | null>(sourceJobId ? "Imported leads are unverified until you run verification." : null);
  const [contactTypeDraft, setContactTypeDraft] = useState<"b2b" | "b2c" | "mixed">("mixed");
  const [updatingLeadId, setUpdatingLeadId] = useState<string | null>(null);

  useEffect(() => {
    let ignore = false;
    Promise.all([getLeads(), getLists()]).then(([leadData, listData]) => {
      if (!ignore && leadData) {
        setLeads(leadData);
      }
      if (!ignore && listData) {
        setLists(listData);
        setBulkListTargetId((current) => current || listData[0]?.id || "");
      }
    });
    return () => {
      ignore = true;
    };
  }, [getLeads, getLists]);

  useEffect(() => {
    if (!bulkState || bulkState.status === "completed" || bulkState.status === "failed") {
      return undefined;
    }

    const intervalId = window.setInterval(async () => {
      const data = await getLeadVerificationJob(bulkState.jobId);
      if (!data) {
        return;
      }

      setBulkState({
        jobId: data.job_id,
        status: data.status,
        requestedCount: data.requested_count,
        processedCount: data.processed_count,
        error: data.error,
      });

      if (data.results?.length) {
        setLeads((current) => current.map((lead) => {
          const result = data.results.find((item) => item.lead_id === lead.id);
          return result ? applyVerificationResult(lead, result) : lead;
        }));
      }

      if (data.status === "completed") {
        setBanner(`Verified ${data.processed_count} lead${data.processed_count === 1 ? "" : "s"}.`);
        setSelectedLeadIds([]);
        window.clearInterval(intervalId);
      }

      if (data.status === "failed") {
        setBanner(data.error || "Bulk verification failed.");
        window.clearInterval(intervalId);
      }
    }, 1500);

    return () => window.clearInterval(intervalId);
  }, [bulkState, getLeadVerificationJob]);

  const filteredLeads = useMemo(() => {
    const normalizedSearch = search.trim().toLowerCase();
    return leads.filter((lead) => {
      if (sourceJobId && lead.source_import_job_id !== sourceJobId) {
        return false;
      }
      if (listFilterId !== "all" && !(lead.list_ids || []).includes(listFilterId)) {
        return false;
      }
      if (contactTypeFilter !== "all") {
        const normalizedType = lead.contact_type || "mixed";
        if (normalizedType !== contactTypeFilter) {
          return false;
        }
      }
      if (consentFilter !== "all" && (lead.consent_status || "unknown") !== consentFilter) {
        return false;
      }
      if (unsubscribeFilter !== "all" && (lead.unsubscribe_status || "subscribed") !== unsubscribeFilter) {
        return false;
      }
      if (!normalizedSearch) {
        return true;
      }
      return [lead.email, lead.first_name, lead.last_name, lead.company, lead.persona, lead.industry, ...(lead.tags || [])]
        .filter(Boolean)
        .some((value) => String(value).toLowerCase().includes(normalizedSearch));
    });
  }, [leads, search, sourceJobId, listFilterId, contactTypeFilter, consentFilter, unsubscribeFilter]);

  const expandedLead = leads.find((lead) => lead.id === expandedLeadId) || null;
  const allVisibleSelected = filteredLeads.length > 0 && filteredLeads.every((lead) => selectedLeadIds.includes(lead.id));

  useEffect(() => {
    if (!expandedLead) return;
    setContactTypeDraft((expandedLead.contact_type || "mixed") as "b2b" | "b2c" | "mixed");
  }, [expandedLead]);

  const toggleLead = (leadId: string) => {
    setSelectedLeadIds((current) =>
      current.includes(leadId) ? current.filter((id) => id !== leadId) : [...current, leadId],
    );
  };

  const toggleAllVisible = () => {
    if (allVisibleSelected) {
      setSelectedLeadIds((current) => current.filter((id) => !filteredLeads.some((lead) => lead.id === id)));
      return;
    }
    setSelectedLeadIds((current) => Array.from(new Set([...current, ...filteredLeads.map((lead) => lead.id)])));
  };

  const handleVerifyOne = async (leadId: string) => {
    setVerifyingLeadId(leadId);
    const result = await verifyLead(leadId);
    if (result) {
      setLeads((current) => current.map((lead) => applyVerificationResult(lead, result)));
      setBanner(`Verified ${result.email}.`);
      if (expandedLeadId === leadId) {
        setExpandedLeadId(leadId);
      }
    }
    setVerifyingLeadId(null);
  };

  const handleBulkVerify = async (leadIds: string[]) => {
    if (!leadIds.length) {
      return;
    }
    setBulkState({ jobId: "pending", status: "queued", requestedCount: leadIds.length, processedCount: 0 });
    const response = await verifyLeadsBulk(leadIds);
    if (!response) {
      setBulkState(null);
      return;
    }
    setBulkState({
      jobId: response.job_id,
      status: response.status,
      requestedCount: response.requested_count,
      processedCount: response.status === "completed" ? response.requested_count : 0,
    });
    if (response.status === "completed") {
      const data = await getLeadVerificationJob(response.job_id);
      if (data?.results?.length) {
        setLeads((current) => current.map((lead) => {
          const result = data.results.find((item) => item.lead_id === lead.id);
          return result ? applyVerificationResult(lead, result) : lead;
        }));
      }
      setBanner(`Verified ${response.requested_count} lead${response.requested_count === 1 ? "" : "s"}.`);
      setSelectedLeadIds([]);
    }
  };

  const handleAddLeadToList = async (leadId: string) => {
    const listId = rowListTargets[leadId];
    if (!listId) {
      setBanner("Select a target list first.");
      return;
    }
    setAddingLeadId(leadId);
    try {
      await addLeadToList(listId, leadId);
      const refreshedLeads = await getLeads();
      const refreshedLists = await getLists();
      if (refreshedLeads) setLeads(refreshedLeads);
      if (refreshedLists) setLists(refreshedLists);
      setBanner("Lead added to list.");
    } catch (err) {
      setBanner(err instanceof Error ? err.message : "Lead add failed.");
    } finally {
      setAddingLeadId(null);
    }
  };

  const handleBulkAddToList = async () => {
    if (!bulkListTargetId || !selectedLeadIds.length) {
      setBanner("Select one or more leads and choose a target list.");
      return;
    }
    setAddingLeadId("__bulk__");
    try {
      await addLeadsToListBulk(bulkListTargetId, selectedLeadIds);
      const refreshedLeads = await getLeads();
      const refreshedLists = await getLists();
      if (refreshedLeads) setLeads(refreshedLeads);
      if (refreshedLists) setLists(refreshedLists);
      setSelectedLeadIds([]);
      setBanner("Selected leads added to list.");
    } catch (err) {
      setBanner(err instanceof Error ? err.message : "Bulk add failed.");
    } finally {
      setAddingLeadId(null);
    }
  };

  const handleBulkTagAssign = async () => {
    const tags = bulkTags.split(",").map((value) => value.trim()).filter(Boolean);
    if (!selectedLeadIds.length || !tags.length) {
      setBanner("Select leads and enter one or more tags.");
      return;
    }
    setAddingLeadId("__bulk_tags__");
    try {
      await assignLeadTagsBulk(selectedLeadIds, tags);
      const refreshedLeads = await getLeads();
      if (refreshedLeads) setLeads(refreshedLeads);
      setBulkTags("");
      setSelectedLeadIds([]);
      setBanner("Tags assigned to selected leads.");
    } catch (err) {
      setBanner(err instanceof Error ? err.message : "Bulk tag assignment failed.");
    } finally {
      setAddingLeadId(null);
    }
  };

  const handleBulkContactTypeAssign = async () => {
    if (!selectedLeadIds.length) {
      setBanner("Select one or more leads to update contact type.");
      return;
    }
    setAddingLeadId("__bulk_contact_type__");
    try {
      const result = await updateLeadContactTypeBulk({
        lead_ids: selectedLeadIds,
        contact_type: bulkContactType,
      });
      const refreshedLeads = await getLeads();
      if (refreshedLeads) setLeads(refreshedLeads);
      setSelectedLeadIds([]);
      setBanner(`Updated ${result.lead_count} lead${result.lead_count === 1 ? "" : "s"} to ${result.contact_type || "mixed"}.`);
    } catch (err) {
      setBanner(err instanceof Error ? err.message : "Bulk contact type update failed.");
    } finally {
      setAddingLeadId(null);
    }
  };

  const handleBulkSuppress = async () => {
    if (!selectedLeadIds.length) {
      setBanner("Select one or more leads to suppress.");
      return;
    }
    setAddingLeadId("__bulk_suppress__");
    try {
      await suppressLeadsBulk(selectedLeadIds, "bulk_contact_action");
      const refreshedLeads = await getLeads();
      if (refreshedLeads) setLeads(refreshedLeads);
      setSelectedLeadIds([]);
      setBanner("Selected leads suppressed.");
    } catch (err) {
      setBanner(err instanceof Error ? err.message : "Bulk suppression failed.");
    } finally {
      setAddingLeadId(null);
    }
  };

  const handleExportFiltered = () => {
    const rows = [
      ["Email", "Name", "Company", "Contact Type", "Consent", "Unsubscribe", "Status", "Score", "Quality Tier", "Tags"],
      ...filteredLeads.map((lead) => [
        lead.email,
        [lead.first_name, lead.last_name].filter(Boolean).join(" "),
        lead.company || "",
        lead.contact_type || "mixed",
        lead.consent_status || "unknown",
        lead.unsubscribe_status || "subscribed",
        lead.email_status || "unverified",
        String(lead.verification_score ?? ""),
        lead.contact_quality_tier || "",
        (lead.tags || []).join("|"),
      ]),
    ];
    const csv = rows.map((row) => row.map((value) => `"${String(value).replaceAll('"', '""')}"`).join(",")).join("\n");
    const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = "filtered_contacts.csv";
    anchor.click();
    URL.revokeObjectURL(url);
  };

  const handleUpdateContactType = async () => {
    if (!expandedLead) return;
    setUpdatingLeadId(expandedLead.id);
    try {
      const updated = await updateLead(expandedLead.id, { contact_type: contactTypeDraft });
      setLeads((current) => current.map((lead) => lead.id === updated.id ? updated : lead));
      setBanner(`Updated ${updated.email} contact type to ${updated.contact_type || "mixed"}.`);
    } catch (err) {
      setBanner(err instanceof Error ? err.message : "Contact type update failed.");
    } finally {
      setUpdatingLeadId(null);
    }
  };

  return (
    <div className="relative min-h-screen space-y-6 pb-12 animate-fade-in">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight text-slate-800">Lead Directory</h1>
          <p className="mt-2 text-sm font-medium text-slate-500">
            Verify individual leads or run bulk checks. Unverified means the email has not been checked yet.
          </p>
        </div>
        <div className="flex items-center gap-3">
          <button onClick={handleExportFiltered} className="flex items-center gap-2 rounded-xl border border-slate-200 bg-white px-5 py-2.5 font-bold text-slate-700 shadow-sm transition-all active:scale-95 hover:bg-slate-50">
            <Download size={18} /> Export CSV
          </button>
          <Link href="/contacts/import" className="flex items-center gap-2 rounded-xl bg-blue-600 px-5 py-2.5 font-bold text-white shadow-lg shadow-blue-600/30 transition-all active:scale-95 hover:bg-blue-700">
            <Upload size={18} /> Bulk Import Leads
          </Link>
        </div>
      </div>

      {banner && (
        <div className="flex items-start justify-between rounded-2xl border border-blue-100 bg-blue-50 px-5 py-4 text-sm font-medium text-blue-700">
          <span>{banner}</span>
          <button className="text-blue-500 hover:text-blue-700" onClick={() => setBanner(null)}>Dismiss</button>
        </div>
      )}

      <div className="flex flex-wrap items-center justify-between gap-4 rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
        <input
          type="text"
          value={search}
          onChange={(event) => setSearch(event.target.value)}
          placeholder="Search by email, name, or company..."
          className="w-full rounded-xl bg-slate-50 px-5 py-3 font-medium text-slate-700 outline-none ring-0 focus:ring-2 focus:ring-blue-500 md:w-[420px]"
        />
        <div className="flex flex-wrap items-center gap-3">
          <select
            value={listFilterId}
            onChange={(event) => setListFilterId(event.target.value)}
            className="rounded-xl border border-slate-200 bg-slate-50 px-4 py-2.5 text-sm font-medium text-slate-700"
          >
            <option value="all">All lists</option>
            {lists.map((list) => (
              <option key={list.id} value={list.id}>{list.name}</option>
            ))}
          </select>
          <select value={contactTypeFilter} onChange={(event) => setContactTypeFilter(event.target.value)} className="rounded-xl border border-slate-200 bg-slate-50 px-4 py-2.5 text-sm font-medium text-slate-700">
            <option value="all">All contact types</option>
            <option value="b2b">B2B</option>
            <option value="b2c">B2C</option>
            <option value="mixed">Mixed / imported</option>
          </select>
          <select value={consentFilter} onChange={(event) => setConsentFilter(event.target.value)} className="rounded-xl border border-slate-200 bg-slate-50 px-4 py-2.5 text-sm font-medium text-slate-700">
            <option value="all">All consent states</option>
            <option value="granted">Granted</option>
            <option value="unknown">Unknown</option>
            <option value="revoked">Revoked</option>
            <option value="not_required">Not required</option>
          </select>
          <select value={unsubscribeFilter} onChange={(event) => setUnsubscribeFilter(event.target.value)} className="rounded-xl border border-slate-200 bg-slate-50 px-4 py-2.5 text-sm font-medium text-slate-700">
            <option value="all">All subscription states</option>
            <option value="subscribed">Subscribed</option>
            <option value="unsubscribed">Unsubscribed</option>
            <option value="suppressed">Suppressed</option>
          </select>
          <button
            type="button"
            disabled={!selectedLeadIds.length || !!bulkState && ["queued", "running"].includes(bulkState.status)}
            onClick={() => void handleBulkVerify(selectedLeadIds)}
            className="inline-flex items-center gap-2 rounded-xl bg-slate-900 px-4 py-2.5 text-sm font-bold text-white transition disabled:cursor-not-allowed disabled:bg-slate-300"
          >
            {bulkState && ["queued", "running"].includes(bulkState.status) ? <LoaderCircle size={16} className="animate-spin" /> : <Sparkles size={16} />}
            Verify selected
          </button>
          <select
            value={bulkContactType}
            onChange={(event) => setBulkContactType(event.target.value as "b2b" | "b2c" | "mixed")}
            aria-label="Bulk contact type"
            className="rounded-xl border border-slate-200 bg-slate-50 px-4 py-2.5 text-sm font-medium text-slate-700"
          >
            <option value="b2b">B2B</option>
            <option value="b2c">B2C</option>
            <option value="mixed">Mixed</option>
          </select>
          <button
            type="button"
            disabled={!selectedLeadIds.length || addingLeadId === "__bulk_contact_type__"}
            onClick={() => void handleBulkContactTypeAssign()}
            className="inline-flex items-center gap-2 rounded-xl border border-slate-200 bg-white px-4 py-2.5 text-sm font-bold text-slate-700 transition disabled:cursor-not-allowed disabled:border-slate-200 disabled:bg-slate-100 disabled:text-slate-400"
          >
            {addingLeadId === "__bulk_contact_type__" ? <LoaderCircle size={16} className="animate-spin" /> : null}
            Set contact type
          </button>
          <select
            value={bulkListTargetId}
            onChange={(event) => setBulkListTargetId(event.target.value)}
            className="rounded-xl border border-slate-200 bg-slate-50 px-4 py-2.5 text-sm font-medium text-slate-700"
          >
            <option value="">Choose list</option>
            {lists.map((list) => (
              <option key={list.id} value={list.id}>{list.name}</option>
            ))}
          </select>
          <button
            type="button"
            disabled={!selectedLeadIds.length || !bulkListTargetId || addingLeadId === "__bulk__"}
            onClick={() => void handleBulkAddToList()}
            className="inline-flex items-center gap-2 rounded-xl border border-blue-200 bg-blue-50 px-4 py-2.5 text-sm font-bold text-blue-700 transition disabled:cursor-not-allowed disabled:border-slate-200 disabled:bg-slate-100 disabled:text-slate-400"
          >
            {addingLeadId === "__bulk__" ? <LoaderCircle size={16} className="animate-spin" /> : <ListPlus size={16} />}
            Add selected to list
          </button>
          <input
            value={bulkTags}
            onChange={(event) => setBulkTags(event.target.value)}
            placeholder="vip, newsletter"
            className="rounded-xl border border-slate-200 bg-slate-50 px-4 py-2.5 text-sm font-medium text-slate-700"
          />
          <button
            type="button"
            disabled={!selectedLeadIds.length || addingLeadId === "__bulk_tags__"}
            onClick={() => void handleBulkTagAssign()}
            className="inline-flex items-center gap-2 rounded-xl border border-indigo-200 bg-indigo-50 px-4 py-2.5 text-sm font-bold text-indigo-700 transition disabled:cursor-not-allowed disabled:border-slate-200 disabled:bg-slate-100 disabled:text-slate-400"
          >
            <Tags size={16} />
            Assign tags
          </button>
          <button
            type="button"
            disabled={!selectedLeadIds.length || addingLeadId === "__bulk_suppress__"}
            onClick={() => void handleBulkSuppress()}
            className="inline-flex items-center gap-2 rounded-xl border border-red-200 bg-red-50 px-4 py-2.5 text-sm font-bold text-red-700 transition disabled:cursor-not-allowed disabled:border-slate-200 disabled:bg-slate-100 disabled:text-slate-400"
          >
            <ShieldX size={16} />
            Suppress selected
          </button>
          {sourceJobId && filteredLeads.length > 0 && (
            <button
              type="button"
              onClick={() => void handleBulkVerify(filteredLeads.map((lead) => lead.id))}
              className="inline-flex items-center gap-2 rounded-xl border border-blue-200 bg-blue-50 px-4 py-2.5 text-sm font-bold text-blue-700 transition hover:bg-blue-100"
            >
              <MailCheck size={16} />
              Verify imported leads
            </button>
          )}
        </div>
      </div>

      {bulkState && (
        <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
          <div className="flex items-center justify-between gap-3">
            <div>
              <div className="text-sm font-bold text-slate-700">Bulk verification</div>
              <div className="text-sm text-slate-500">
                {bulkState.status === "completed"
                  ? `Completed ${bulkState.processedCount} of ${bulkState.requestedCount} leads.`
                  : bulkState.status === "failed"
                    ? bulkState.error || "Verification job failed."
                    : `Processed ${bulkState.processedCount} of ${bulkState.requestedCount} leads.`}
              </div>
            </div>
            <span className={`rounded-lg px-3 py-1 text-xs font-bold ${bulkState.status === "completed" ? "bg-green-100 text-green-700" : bulkState.status === "failed" ? "bg-red-100 text-red-700" : "bg-yellow-100 text-yellow-700"}`}>
              {bulkState.status}
            </span>
          </div>
        </div>
      )}

      {error && leads.length === 0 ? (
        <div className="flex flex-col items-center justify-center rounded-2xl border border-red-200 bg-red-50 py-16 text-center text-red-700 shadow-sm">
          <AlertCircle className="mb-4 text-red-500" size={32} />
          <span className="mb-2 font-bold">Failed to Load Contacts</span>
          <span className="text-sm">{error}</span>
        </div>
      ) : loading && leads.length === 0 ? (
        <div className="flex h-64 items-center justify-center rounded-2xl border border-slate-200 bg-white shadow-sm">
          <Spinner size="lg" />
        </div>
      ) : (
        <>
          <Table columns={["", "Email Address", "Profile", "Audience", "Lists", "Status", "Score", "Integrity", "Last verified", "Actions"]}>
            {filteredLeads.map((lead) => {
              const isSelected = selectedLeadIds.includes(lead.id);
              const isVerifying = verifyingLeadId === lead.id;
              const rowListTarget = rowListTargets[lead.id] || "";
              return (
                <TableRow key={lead.id}>
                  <TableCell className="w-12">
                    <input
                      type="checkbox"
                      aria-label={`Select ${lead.email}`}
                      checked={isSelected}
                      onChange={() => toggleLead(lead.id)}
                      className="h-4 w-4 rounded border-slate-300 text-blue-600 focus:ring-blue-500"
                    />
                  </TableCell>
                  <TableCell className="font-bold text-slate-800">{lead.email}</TableCell>
                  <TableCell className="font-medium text-slate-600">
                    <div>{[lead.first_name, lead.last_name].filter(Boolean).join(" ") || "-"}</div>
                    <div className="text-xs text-slate-400">{lead.company || "No company"}{lead.persona ? ` • ${lead.persona}` : ""}</div>
                  </TableCell>
                  <TableCell className="text-slate-600">
                    <div className="flex flex-wrap gap-1">
                      <span className="rounded-lg bg-slate-100 px-2 py-1 text-xs font-semibold text-slate-700">{lead.contact_type || "mixed"}</span>
                      <span className="rounded-lg bg-blue-50 px-2 py-1 text-xs font-semibold text-blue-700">{lead.consent_status || "unknown"}</span>
                      <span className={`rounded-lg px-2 py-1 text-xs font-semibold ${(lead.unsubscribe_status || "subscribed") === "subscribed" ? "bg-emerald-50 text-emerald-700" : "bg-rose-50 text-rose-700"}`}>{lead.unsubscribe_status || "subscribed"}</span>
                      <span className={`rounded-lg px-2 py-1 text-xs font-semibold ${(lead.contact_quality_tier || "low") === "high" ? "bg-emerald-50 text-emerald-700" : (lead.contact_quality_tier || "low") === "medium" ? "bg-amber-50 text-amber-700" : "bg-slate-100 text-slate-700"}`}>{lead.contact_quality_tier || "low"} quality</span>
                    </div>
                  </TableCell>
                  <TableCell>
                    <div className="flex max-w-[180px] flex-wrap gap-1">
                      {(lead.list_names || []).length ? (
                        lead.list_names?.map((listName) => (
                          <span key={`${lead.id}-${listName}`} className="rounded-lg bg-slate-100 px-2 py-1 text-xs font-semibold text-slate-700">
                            {listName}
                          </span>
                        ))
                      ) : (
                        <span className="text-xs text-slate-400">No lists</span>
                      )}
                    </div>
                  </TableCell>
                  <TableCell>{statusBadge(lead.email_status || "unverified")}</TableCell>
                  <TableCell>{scoreBadge(lead.verification_score)}</TableCell>
                  <TableCell>{integrityBadge(lead.verification_integrity)}</TableCell>
                  <TableCell className="text-slate-500">{lead.last_verified_at ? new Date(lead.last_verified_at).toLocaleString() : "Not checked"}</TableCell>
                  <TableCell>
                    <div className="flex flex-wrap items-center gap-2">
                      <button
                        type="button"
                        onClick={() => void handleVerifyOne(lead.id)}
                        disabled={isVerifying}
                        className="inline-flex items-center gap-2 rounded-lg bg-blue-600 px-3 py-2 text-xs font-bold text-white transition disabled:bg-blue-300"
                      >
                        {isVerifying ? <LoaderCircle size={14} className="animate-spin" /> : <MailCheck size={14} />}
                        Verify
                      </button>
                      <select
                        value={rowListTarget}
                        onChange={(event) => setRowListTargets((current) => ({ ...current, [lead.id]: event.target.value }))}
                        className="rounded-lg border border-slate-200 px-2 py-2 text-xs font-medium text-slate-700"
                      >
                        <option value="">Choose list</option>
                        {lists
                          .filter((list) => !(lead.list_ids || []).includes(list.id))
                          .map((list) => (
                            <option key={list.id} value={list.id}>{list.name}</option>
                          ))}
                      </select>
                      <button
                        type="button"
                        onClick={() => void handleAddLeadToList(lead.id)}
                        disabled={!rowListTarget || addingLeadId === lead.id}
                        className="inline-flex items-center gap-2 rounded-lg border border-blue-200 px-3 py-2 text-xs font-bold text-blue-700 transition disabled:cursor-not-allowed disabled:border-slate-200 disabled:text-slate-400"
                      >
                        {addingLeadId === lead.id ? <LoaderCircle size={14} className="animate-spin" /> : <ListPlus size={14} />}
                        Add to list
                      </button>
                      <button
                        type="button"
                        onClick={() => setExpandedLeadId(expandedLeadId === lead.id ? null : lead.id)}
                        className="rounded-lg border border-slate-200 px-3 py-2 text-xs font-bold text-slate-700 transition hover:bg-slate-50"
                      >
                        {expandedLeadId === lead.id ? "Hide" : "Details"}
                      </button>
                    </div>
                  </TableCell>
                </TableRow>
              );
            })}
            {filteredLeads.length === 0 && (
              <TableRow>
                <TableCell className="py-12 text-center" colSpan={10}>
                  <div className="space-y-2">
                    <div className="text-lg font-bold text-slate-500">No leads available</div>
                    <div className="text-sm text-slate-400">
                      Import leads or create them through your workflow, then verify them here.
                    </div>
                  </div>
                </TableCell>
              </TableRow>
            )}
          </Table>

          {filteredLeads.length > 0 && (
            <div className="flex items-center gap-3">
              <input
                type="checkbox"
                aria-label="Select all visible leads"
                checked={allVisibleSelected}
                onChange={toggleAllVisible}
                className="h-4 w-4 rounded border-slate-300 text-blue-600 focus:ring-blue-500"
              />
              <span className="text-sm font-medium text-slate-600">
                Select all visible leads ({filteredLeads.length})
              </span>
            </div>
          )}

          {expandedLead && (
            <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
              <div className="mb-4 flex items-start justify-between gap-4">
                <div>
                  <h2 className="text-xl font-bold text-slate-800">{expandedLead.email}</h2>
                  <p className="mt-1 text-sm text-slate-500">
                    Latest verification state for this lead.
                  </p>
                </div>
                {statusBadge(expandedLead.email_status || "unverified")}
              </div>

              <div className="grid gap-4 md:grid-cols-3">
                <DetailCard label="Score">{scoreBadge(expandedLead.verification_score)}</DetailCard>
                <DetailCard label="Integrity">{integrityBadge(expandedLead.verification_integrity)}</DetailCard>
                <DetailCard label="Last checked">
                  <span className="text-sm font-medium text-slate-700">
                    {expandedLead.last_verified_at ? new Date(expandedLead.last_verified_at).toLocaleString() : "Not checked yet"}
                  </span>
                </DetailCard>
              </div>

              <div className="mt-6 grid gap-4 md:grid-cols-4">
                <FlagBadge label="Disposable" value={expandedLead.is_disposable} />
                <FlagBadge label="Role-based" value={expandedLead.is_role_based} />
                <FlagBadge label="Suppressed" value={expandedLead.is_suppressed} />
                <FlagBadge label="Source" value={expandedLead.source || "Manual"} positive />
              </div>

              <div className="mt-6 grid gap-4 md:grid-cols-4">
                <DetailCard label="Contact type">
                  <div className="space-y-3">
                    <select
                      value={contactTypeDraft}
                      onChange={(event) => setContactTypeDraft(event.target.value as "b2b" | "b2c" | "mixed")}
                      className="w-full rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm font-medium text-slate-700"
                      disabled={updatingLeadId === expandedLead.id}
                    >
                      <option value="b2b">B2B</option>
                      <option value="b2c">B2C</option>
                      <option value="mixed">Mixed</option>
                    </select>
                    <button
                      type="button"
                      onClick={() => void handleUpdateContactType()}
                      disabled={updatingLeadId === expandedLead.id || contactTypeDraft === (expandedLead.contact_type || "mixed")}
                      className="inline-flex items-center gap-2 rounded-xl border border-slate-200 px-3 py-2 text-sm font-bold text-slate-700 disabled:cursor-not-allowed disabled:opacity-50"
                    >
                      {updatingLeadId === expandedLead.id ? <LoaderCircle size={14} className="animate-spin" /> : null}
                      Save
                    </button>
                  </div>
                </DetailCard>
                <DetailCard label="Consent"><span className="text-sm font-medium text-slate-700">{expandedLead.consent_status || "unknown"}</span></DetailCard>
                <DetailCard label="Subscription"><span className="text-sm font-medium text-slate-700">{expandedLead.unsubscribe_status || "subscribed"}</span></DetailCard>
                <DetailCard label="Engagement"><span className="text-sm font-medium text-slate-700">{expandedLead.engagement_score ?? 0}</span></DetailCard>
              </div>

              <div className="mt-6">
                <div className="mb-2 text-sm font-bold uppercase tracking-wide text-slate-500">Tags</div>
                {(expandedLead.tags || []).length ? (
                  <div className="flex flex-wrap gap-2">
                    {expandedLead.tags?.map((tag) => (
                      <span key={`${expandedLead.id}-${tag}`} className="rounded-xl bg-indigo-50 px-3 py-2 text-sm font-semibold text-indigo-700">{tag}</span>
                    ))}
                  </div>
                ) : (
                  <div className="rounded-xl bg-slate-50 px-4 py-3 text-sm text-slate-500">No tags assigned yet.</div>
                )}
              </div>

              <div className="mt-6">
                <div className="mb-2 text-sm font-bold uppercase tracking-wide text-slate-500">List membership</div>
                {(expandedLead.list_names || []).length ? (
                  <div className="flex flex-wrap gap-2">
                    {expandedLead.list_names?.map((listName) => (
                      <span key={`${expandedLead.id}-${listName}`} className="rounded-xl bg-slate-100 px-3 py-2 text-sm font-semibold text-slate-700">
                        {listName}
                      </span>
                    ))}
                  </div>
                ) : (
                  <div className="rounded-xl bg-slate-50 px-4 py-3 text-sm text-slate-500">
                    This lead is not assigned to any reusable list yet.
                  </div>
                )}
              </div>

              <div className="mt-6">
                <div className="mb-2 text-sm font-bold uppercase tracking-wide text-slate-500">Verification reasons</div>
                {expandedLead.verification_reasons?.length ? (
                  <ul className="space-y-2 text-sm text-slate-700">
                    {expandedLead.verification_reasons.map((reason) => (
                      <li key={reason} className="rounded-xl bg-slate-50 px-4 py-3">{reason}</li>
                    ))}
                  </ul>
                ) : (
                  <div className="rounded-xl bg-slate-50 px-4 py-3 text-sm text-slate-500">
                    This lead has not been checked yet. Run verification to populate reasons.
                  </div>
                )}
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}

function DetailCard({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
      <div className="mb-2 text-xs font-bold uppercase tracking-wide text-slate-500">{label}</div>
      {children}
    </div>
  );
}

function FlagBadge({ label, value, positive = false }: { label: string; value: boolean | string; positive?: boolean }) {
  const isTrue = typeof value === "boolean" ? value : Boolean(value);
  const display = typeof value === "boolean" ? (value ? "Yes" : "No") : value;
  const style = positive
    ? "bg-blue-50 text-blue-700"
    : isTrue
      ? "bg-red-50 text-red-700"
      : "bg-emerald-50 text-emerald-700";

  return (
    <div className={`rounded-2xl px-4 py-3 ${style}`}>
      <div className="text-xs font-bold uppercase tracking-wide">{label}</div>
      <div className="mt-1 text-sm font-semibold">{display}</div>
    </div>
  );
}
