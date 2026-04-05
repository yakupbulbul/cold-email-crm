"use client";

import { useEffect, useState } from "react";
import { useApiService } from "@/services/api";
import { Domain } from "@/types/models";
import { ServerCrash, Globe } from "lucide-react";
import Spinner from "@/components/ui/Spinner";

export default function DomainsPage() {
    const { getDomains, loading, error } = useApiService();
    const [domains, setDomains] = useState<Domain[]>([]);

    useEffect(() => {
        const fetchDomains = async () => {
            const data = await getDomains();
            if (data) setDomains(data);
        };
        fetchDomains();
    }, [getDomains]);

    return (
        <div className="p-8 animate-fade-in relative min-h-[50vh]">
            <h1 className="text-3xl font-bold text-slate-800 tracking-tight mb-6">Domain Infrastructure</h1>
            
            {error ? (
                <div className="bg-white rounded-2xl border border-slate-200 shadow-sm flex flex-col items-center justify-center p-16 text-center">
                    <div className="w-16 h-16 bg-red-50 rounded-full flex items-center justify-center mb-4 border border-red-100">
                        <ServerCrash className="text-red-500" size={28} />
                    </div>
                    <h3 className="text-lg font-bold text-slate-800 mb-2">Backend Endpoint Missing</h3>
                    <p className="text-sm text-slate-500 max-w-sm mb-2">The REST API for querying domains is not yet connected or available.</p>
                    <p className="text-xs text-red-600 font-medium bg-red-50 px-3 py-1 rounded">Error: {error}</p>
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
