"use client";

import { useEffect, useState } from "react";
import { useApiService } from "@/services/api";
import { Domain } from "@/types/models";
import { ServerCrash, Globe, Plus, RefreshCw, ShieldCheck, ShieldAlert, ChevronDown, ChevronUp, Trash2 } from "lucide-react";
import Spinner from "@/components/ui/Spinner";
import { AlertBanner, EmptyState, PageHeader, SurfaceCard } from "@/components/ui/primitives";

const statusTone: Record<string, string> = {
    ready: "bg-green-50 text-green-700 border-green-200",
    dns_partial: "bg-amber-50 text-amber-700 border-amber-200",
    mailcow_verified: "bg-blue-50 text-blue-700 border-blue-200",
    local_only: "bg-slate-100 text-slate-700 border-slate-200",
    blocked: "bg-red-50 text-red-700 border-red-200",
    failed: "bg-red-50 text-red-700 border-red-200",
    pending: "bg-slate-100 text-slate-700 border-slate-200",
    verified: "bg-green-50 text-green-700 border-green-200",
    missing: "bg-amber-50 text-amber-700 border-amber-200",
};

function StatusBadge({ label, value }: { label: string; value: string }) {
    const tone = statusTone[value] ?? "bg-slate-100 text-slate-700 border-slate-200";
    return (
        <div className={`inline-flex items-center gap-2 rounded-full border px-3 py-1 text-xs font-semibold ${tone}`}>
            <span>{label}</span>
            <span className="uppercase tracking-wide">{value.replaceAll("_", " ")}</span>
        </div>
    );
}

function GuidanceRow({ title, host, type, expectedValue, explanation }: { title: string; host?: string; type?: string; expectedValue?: string; explanation?: string }) {
    return (
        <div className="rounded-xl border border-slate-200 p-3">
            <div className="font-semibold text-slate-800">{title}</div>
            {host ? <div className="mt-2 text-xs uppercase tracking-wide text-slate-500">Host: {host}</div> : null}
            {type ? <div className="mt-1 text-xs uppercase tracking-wide text-slate-500">Type: {type}</div> : null}
            {expectedValue ? <div className="mt-2 break-all rounded-lg bg-slate-50 px-3 py-2 text-sm text-slate-700">{expectedValue}</div> : null}
            {explanation ? <div className="mt-2 text-sm text-slate-600">{explanation}</div> : null}
        </div>
    );
}

export default function DomainsPage() {
    const { getDomains, createDomain, deleteDomain, verifyDomain, refreshDomain, loading, error } = useApiService();
    const [domains, setDomains] = useState<Domain[]>([]);
    const [domainName, setDomainName] = useState("");
    const [submitError, setSubmitError] = useState<string | null>(null);
    const [submitSuccess, setSubmitSuccess] = useState<string | null>(null);
    const [isSubmitting, setIsSubmitting] = useState(false);
    const [activeDetailsId, setActiveDetailsId] = useState<string | null>(null);
    const [busyDomainId, setBusyDomainId] = useState<string | null>(null);

    useEffect(() => {
        let isMounted = true;

        void getDomains().then((data) => {
            if (isMounted && data) {
                setDomains(data);
            }
        });

        return () => {
            isMounted = false;
        };
    }, [getDomains]);

    const handleCreateDomain = async (event: React.FormEvent<HTMLFormElement>) => {
        event.preventDefault();
        setSubmitError(null);
        setSubmitSuccess(null);

        const normalizedDomain = domainName.trim().toLowerCase();
        if (!normalizedDomain) {
            setSubmitError("Enter a domain name.");
            return;
        }

        if (!/^[a-z0-9-]+(\.[a-z0-9-]+)+$/.test(normalizedDomain)) {
            setSubmitError("Enter a valid domain such as example.com.");
            return;
        }

        setIsSubmitting(true);
        const created = await createDomain(normalizedDomain);
        setIsSubmitting(false);

        if (!created) {
            setSubmitError("Domain creation failed. Check the backend response and try again.");
            return;
        }

        setDomainName("");
        setSubmitSuccess(`Added ${created.name}`);
        const refreshed = await getDomains();
        if (refreshed) {
            setDomains(refreshed);
        }
    };

    const handleDomainAction = async (domainId: string, action: "verify" | "refresh" | "delete") => {
        setBusyDomainId(domainId);
        setSubmitError(null);
        setSubmitSuccess(null);

        if (action === "delete") {
            const deleted = await deleteDomain(domainId);
            setBusyDomainId(null);

            if (!deleted) {
                setSubmitError("Domain delete failed. Check the backend response and try again.");
                return;
            }

            setDomains((current) => current.filter((domain) => domain.id !== domainId));
            setActiveDetailsId((current) => (current === domainId ? null : current));
            setSubmitSuccess("Domain removed.");
            return;
        }

        const result = action === "verify"
            ? await verifyDomain(domainId)
            : await refreshDomain(domainId);

        setBusyDomainId(null);

        if (!result) {
            setSubmitError(`Domain ${action} failed. Check the backend response and try again.`);
            return;
        }

        setDomains((current) => current.map((domain) => (domain.id === domainId ? result : domain)));
        setActiveDetailsId(domainId);
    };

    return (
        <div className="space-y-6 animate-fade-in relative min-h-[50vh]">
            <PageHeader
                eyebrow="Infrastructure"
                title="Domain Infrastructure"
                description="Add domains, verify readiness, and inspect DNS plus Mailcow state from one operational surface."
            />

            <SurfaceCard className="p-5">
                <form onSubmit={handleCreateDomain} className="flex flex-col gap-4 md:flex-row md:items-end">
                    <div className="flex-1">
                        <label htmlFor="domain-name" className="block text-sm font-semibold text-slate-700 mb-2">
                            Domain Name
                        </label>
                        <input
                            id="domain-name"
                            data-testid="domain-name-input"
                            type="text"
                            value={domainName}
                            onChange={(event) => setDomainName(event.target.value)}
                            placeholder="example.com"
                            className="form-input"
                        />
                    </div>
                    <button
                        data-testid="create-domain-button"
                        type="submit"
                        disabled={isSubmitting}
                        className="btn-primary"
                    >
                        <Plus size={18} />
                        {isSubmitting ? "Adding..." : "Add Domain"}
                    </button>
                </form>
            </SurfaceCard>

            {submitError ? <AlertBanner tone="danger" title="Domain action failed">{submitError}</AlertBanner> : null}
            {submitSuccess ? <AlertBanner tone="success">{submitSuccess}</AlertBanner> : null}
            
            {error ? (
                <SurfaceCard className="flex flex-col items-center justify-center p-16 text-center">
                    <div className="w-16 h-16 bg-red-50 rounded-full flex items-center justify-center mb-4 border border-red-100">
                        <ServerCrash className="text-red-500" size={28} />
                    </div>
                    <h3 className="text-lg font-bold text-slate-800 mb-2">Failed to Load Domains</h3>
                    <p className="text-sm text-slate-500 max-w-sm mb-2">Something went wrong while fetching your domain infrastructure.</p>
                    <p className="text-xs text-red-600 font-medium bg-red-50 px-3 py-1 rounded">{error}</p>
                </SurfaceCard>
            ) : loading ? (
                 <SurfaceCard className="flex justify-center items-center py-16">
                    <Spinner size="lg" />
                 </SurfaceCard>
            ) : domains.length === 0 ? (
                 <EmptyState
                    icon={Globe}
                    title="No domains added yet"
                    description="Add a domain to inspect Mailcow visibility and MX, SPF, DKIM, and DMARC readiness."
                 />
            ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                     {domains.map((d) => (
                         <SurfaceCard key={d.id} className="p-6 text-slate-800">
                             <div className="flex flex-col gap-4">
                                 <div className="flex items-start justify-between gap-4">
                                     <div>
                                         <div className="text-lg font-bold">{d.name}</div>
                                         <div className="mt-2 flex flex-wrap gap-2">
                                             <StatusBadge label="Overall" value={d.status} />
                                             <StatusBadge label="Mailcow" value={d.mailcow_status} />
                                         </div>
                                     </div>
                                     <button
                                         type="button"
                                         onClick={() => setActiveDetailsId(activeDetailsId === d.id ? null : d.id)}
                                         className="inline-flex items-center gap-2 rounded-lg border border-slate-200 px-3 py-2 text-sm font-semibold text-slate-600 hover:bg-slate-50"
                                     >
                                         Details
                                         {activeDetailsId === d.id ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
                                     </button>
                                 </div>

                                 <div className="grid grid-cols-2 gap-2 text-sm md:grid-cols-4">
                                     <StatusBadge label="MX" value={d.mx_status} />
                                     <StatusBadge label="SPF" value={d.spf_status} />
                                     <StatusBadge label="DKIM" value={d.dkim_status} />
                                     <StatusBadge label="DMARC" value={d.dmarc_status} />
                                 </div>

                                 <div className="rounded-xl border border-slate-100 bg-slate-50 px-4 py-3 text-sm text-slate-600">
                                     <div className="font-semibold text-slate-700">Readiness summary</div>
                                     <div className="mt-1">{d.mailcow_detail || "Mailcow verification has not run yet."}</div>
                                     <div className="mt-2 text-xs text-slate-500">
                                         Last checked: {d.last_checked_at ? new Date(d.last_checked_at).toLocaleString() : "Never"}
                                     </div>
                                 </div>

                                 <div className="flex flex-wrap gap-3">
                                     <button
                                         type="button"
                                         onClick={() => void handleDomainAction(d.id, "verify")}
                                         disabled={busyDomainId === d.id}
                                         className="inline-flex items-center gap-2 rounded-xl bg-slate-900 px-4 py-2 text-sm font-bold text-white hover:bg-slate-800 disabled:cursor-not-allowed disabled:opacity-50"
                                     >
                                         <ShieldCheck size={16} />
                                         {busyDomainId === d.id ? "Verifying..." : "Verify"}
                                     </button>
                                     <button
                                         type="button"
                                         onClick={() => void handleDomainAction(d.id, "refresh")}
                                         disabled={busyDomainId === d.id}
                                         className="inline-flex items-center gap-2 rounded-xl border border-slate-200 px-4 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-50"
                                     >
                                         <RefreshCw size={16} />
                                         Refresh
                                     </button>
                                     <button
                                         type="button"
                                         data-testid={`delete-domain-${d.id}`}
                                         onClick={() => void handleDomainAction(d.id, "delete")}
                                         disabled={busyDomainId === d.id}
                                         className="inline-flex items-center gap-2 rounded-xl border border-red-200 px-4 py-2 text-sm font-semibold text-red-700 hover:bg-red-50 disabled:cursor-not-allowed disabled:opacity-50"
                                     >
                                         <Trash2 size={16} />
                                         {busyDomainId === d.id ? "Removing..." : "Remove"}
                                     </button>
                                 </div>

                                 {activeDetailsId === d.id && (
                                     <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4 text-sm text-slate-700">
                                         <div className="flex items-center gap-2 font-semibold text-slate-800">
                                             {d.status === "ready" ? <ShieldCheck size={16} className="text-green-600" /> : <ShieldAlert size={16} className="text-amber-600" />}
                                             Domain Details
                                         </div>
                                         <div className="mt-3 grid gap-3 md:grid-cols-2">
                                             <div className="rounded-xl bg-white p-4 border border-slate-200">
                                                 <div className="font-semibold text-slate-800">Local Record</div>
                                                 <div className="mt-2">Status: {d.status.replaceAll("_", " ")}</div>
                                                 <div>Created: {new Date(d.created_at).toLocaleString()}</div>
                                                 <div>Last checked: {d.last_checked_at ? new Date(d.last_checked_at).toLocaleString() : "Never"}</div>
                                             </div>
                                             <div className="rounded-xl bg-white p-4 border border-slate-200">
                                                 <div className="font-semibold text-slate-800">Mailcow Verification</div>
                                                 <div className="mt-2">Status: {d.mailcow_status.replaceAll("_", " ")}</div>
                                                 <div>{d.mailcow_detail || "No Mailcow verification detail available."}</div>
                                             </div>
                                         </div>

                                         <div className="mt-3 rounded-xl bg-white p-4 border border-slate-200">
                                             <div className="font-semibold text-slate-800">DNS Checks</div>
                                             <div className="mt-3 grid gap-3 md:grid-cols-2">
                                                 {(["mx", "spf", "dkim", "dmarc"] as const).map((key) => {
                                                     const result = d.dns_results?.[key];
                                                     return (
                                                         <div key={key} className="rounded-xl border border-slate-200 p-3">
                                                             <div className="flex items-center justify-between gap-2">
                                                                 <span className="font-semibold uppercase tracking-wide text-xs text-slate-500">{key}</span>
                                                                 <StatusBadge label="Status" value={result?.status || "pending"} />
                                                             </div>
                                                             <div className="mt-2 text-sm text-slate-600">{result?.detail || "No result available yet."}</div>
                                                             {result?.records?.length ? (
                                                                 <div className="mt-2 text-xs text-slate-500 break-all">
                                                                     {result.records.join(" | ")}
                                                                 </div>
                                                             ) : null}
                                                         </div>
                                                     );
                                                 })}
                                             </div>
                                         </div>

                                         <div className="mt-3 rounded-xl bg-white p-4 border border-slate-200">
                                             <div className="font-semibold text-slate-800">Missing Requirements</div>
                                             {d.missing_requirements?.length ? (
                                                 <ul className="mt-2 list-disc pl-5 text-sm text-slate-600">
                                                     {d.missing_requirements.map((item) => (
                                                         <li key={item}>{item}</li>
                                                     ))}
                                                 </ul>
                                             ) : (
                                                 <div className="mt-2 text-sm text-slate-600">No missing requirements. This domain is mail-ready.</div>
                                             )}
                                         </div>

                                         <div className="mt-3 rounded-xl bg-white p-4 border border-slate-200">
                                             <div className="font-semibold text-slate-800">How To Fix</div>
                                             <div className="mt-3 grid gap-3 md:grid-cols-2">
                                                 <GuidanceRow
                                                     title="Mailcow"
                                                     host={d.verification_summary?.remediation?.mailcow?.mailcow_host as string | undefined}
                                                     expectedValue={d.verification_summary?.remediation?.mailcow?.action as string | undefined}
                                                     explanation={d.verification_summary?.remediation?.mailcow?.detail as string | undefined}
                                                 />
                                                 {(["mx", "spf", "dkim", "dmarc"] as const).map((key) => {
                                                     const guidance = d.verification_summary?.remediation?.dns?.[key] as {
                                                         host?: string;
                                                         type?: string;
                                                         expected_value?: string;
                                                         explanation?: string;
                                                     } | undefined;
                                                     return (
                                                         <GuidanceRow
                                                             key={key}
                                                             title={key.toUpperCase()}
                                                             host={guidance?.host}
                                                             type={guidance?.type}
                                                             expectedValue={guidance?.expected_value}
                                                             explanation={guidance?.explanation}
                                                         />
                                                     );
                                                 })}
                                             </div>
                                         </div>
                                     </div>
                                 )}
                             </div>
                         </SurfaceCard>
                     ))}
                </div>
            )}
        </div>
    );
}
