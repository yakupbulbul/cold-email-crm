"use client";

import { useEffect, useState } from "react";
import { useApiService } from "@/services/api";
import { Domain } from "@/types/models";
import { ServerCrash, Globe, Plus, AlertCircle } from "lucide-react";
import Spinner from "@/components/ui/Spinner";

export default function DomainsPage() {
    const { getDomains, createDomain, loading, error } = useApiService();
    const [domains, setDomains] = useState<Domain[]>([]);
    const [domainName, setDomainName] = useState("");
    const [submitError, setSubmitError] = useState<string | null>(null);
    const [submitSuccess, setSubmitSuccess] = useState<string | null>(null);
    const [isSubmitting, setIsSubmitting] = useState(false);

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

    return (
        <div className="p-8 animate-fade-in relative min-h-[50vh]">
            <div className="flex flex-col gap-6 mb-6">
                <div className="flex items-center justify-between gap-4">
                    <div>
                        <h1 className="text-3xl font-bold text-slate-800 tracking-tight">Domain Infrastructure</h1>
                        <p className="text-sm text-slate-500 mt-2 max-w-2xl">
                            Add domains to the local app database. In safe mode this does not provision or mutate Mailcow remotely.
                        </p>
                    </div>
                </div>

                <form onSubmit={handleCreateDomain} className="bg-white rounded-2xl border border-slate-200 shadow-sm p-5 flex flex-col gap-4 md:flex-row md:items-end">
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
                            className="w-full rounded-xl border border-slate-200 px-4 py-3 text-slate-900 outline-none focus:border-blue-500 focus:ring-4 focus:ring-blue-100 transition-all"
                        />
                    </div>
                    <button
                        data-testid="create-domain-button"
                        type="submit"
                        disabled={isSubmitting}
                        className="inline-flex items-center justify-center gap-2 rounded-xl bg-slate-900 px-5 py-3 font-bold text-white shadow-lg shadow-slate-900/20 transition-colors hover:bg-slate-800 disabled:cursor-not-allowed disabled:opacity-50"
                    >
                        <Plus size={18} />
                        {isSubmitting ? "Adding..." : "Add Domain"}
                    </button>
                </form>

                {submitError && (
                    <div className="flex items-center gap-3 rounded-2xl border border-red-100 bg-red-50 px-4 py-3 text-sm font-medium text-red-700">
                        <AlertCircle size={18} />
                        <span>{submitError}</span>
                    </div>
                )}

                {submitSuccess && (
                    <div className="rounded-2xl border border-green-100 bg-green-50 px-4 py-3 text-sm font-medium text-green-700">
                        {submitSuccess}
                    </div>
                )}
            </div>
            
            {error ? (
                <div className="bg-white rounded-2xl border border-slate-200 shadow-sm flex flex-col items-center justify-center p-16 text-center">
                    <div className="w-16 h-16 bg-red-50 rounded-full flex items-center justify-center mb-4 border border-red-100">
                        <ServerCrash className="text-red-500" size={28} />
                    </div>
                    <h3 className="text-lg font-bold text-slate-800 mb-2">Failed to Load Domains</h3>
                    <p className="text-sm text-slate-500 max-w-sm mb-2">Something went wrong while fetching your domain infrastructure.</p>
                    <p className="text-xs text-red-600 font-medium bg-red-50 px-3 py-1 rounded">{error}</p>
                </div>
            ) : loading ? (
                 <div className="flex justify-center items-center py-16 bg-white rounded-2xl border border-slate-200 shadow-sm">
                    <Spinner size="lg" />
                 </div>
            ) : domains.length === 0 ? (
                 <div className="bg-white rounded-2xl border border-slate-200 shadow-sm flex flex-col items-center justify-center p-16 text-center">
                    <div className="w-16 h-16 bg-slate-50 rounded-full flex items-center justify-center mb-4 border border-slate-100">
                        <Globe className="text-slate-400" size={28} />
                    </div>
                    <h3 className="text-lg font-bold text-slate-800 mb-2">No Domains Active</h3>
                    <p className="text-sm text-slate-500 max-w-sm mb-6">You have no active domains routed into the CRM platform yet.</p>
                 </div>
            ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                     {domains.map((d) => (
                         <div key={d.id} className="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm font-bold text-slate-800">
                             {d.name}
                         </div>
                     ))}
                </div>
            )}
        </div>
    );
}
