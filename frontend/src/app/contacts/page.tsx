"use client";

import { useEffect, useState } from "react";
import { useApiService } from "@/services/api";
import { Contact } from "@/types/models";
import Link from "next/link";
import Table, { TableRow, TableCell } from "@/components/ui/Table";
import Spinner from "@/components/ui/Spinner";
import { Download, Upload, ShieldX, CheckCircle, ShieldAlert, AlertCircle } from "lucide-react";

export default function ContactsPage() {
    const { getLeads, loading, error } = useApiService();
    const [leads, setLeads] = useState<Contact[]>([]);

    useEffect(() => {
        const fetchLeads = async () => {
             const data = await getLeads();
             if (data) setLeads(data);
        };
        fetchLeads();
    }, [getLeads]);

    const getVerificationBadge = (score: number | null, is_suppressed: boolean) => {
        if (is_suppressed) return <span className="inline-flex items-center gap-1.5 px-3 py-1 bg-red-100 text-red-700 rounded-lg text-xs font-bold tracking-wide"><ShieldX size={14} /> Suppressed</span>;
        if (score === null || score === undefined) return <span className="inline-flex items-center gap-1.5 px-3 py-1 bg-slate-100 text-slate-700 rounded-lg text-xs font-bold tracking-wide"><AlertCircle size={14} /> Unknown</span>;
        if (score === 100) return <span className="inline-flex items-center gap-1.5 px-3 py-1 bg-green-100 text-green-700 rounded-lg text-xs font-bold tracking-wide"><CheckCircle size={14} /> Verified</span>;
        if (score >= 80) return <span className="inline-flex items-center gap-1.5 px-3 py-1 bg-yellow-100 text-yellow-700 rounded-lg text-xs font-bold tracking-wide"><ShieldAlert size={14} /> Risky</span>;
        return <span className="inline-flex items-center gap-1.5 px-3 py-1 bg-slate-100 text-slate-700 rounded-lg text-xs font-bold tracking-wide">Unverified</span>;
    };

    return (
        <div className="space-y-6 animate-fade-in relative min-h-screen pb-12">
            <div className="flex items-center justify-between">
                <div>
                    <h1 className="text-3xl font-bold text-slate-800 tracking-tight">Lead Directory</h1>
                    <p className="text-slate-500 mt-2 text-sm font-medium">Manage your 10,000+ imported contacts globally mapped against bounce suppression layers.</p>
                </div>
                <div className="flex items-center gap-3">
                    <button className="flex items-center gap-2 bg-white hover:bg-slate-50 text-slate-700 border border-slate-200 px-5 py-2.5 rounded-xl font-bold transition-all shadow-sm active:scale-95">
                        <Download size={18} /> Export CSV
                    </button>
                    <Link href="/contacts/import" className="flex items-center gap-2 bg-blue-600 hover:bg-blue-700 text-white px-5 py-2.5 rounded-xl font-bold transition-all shadow-lg shadow-blue-600/30 active:scale-95">
                        <Upload size={18} /> Bulk Import Leads
                    </Link>
                </div>
            </div>

            <div className="bg-white rounded-2xl border border-slate-200 shadow-sm p-4 mt-8 flex items-center justify-between">
                <input 
                    type="text" 
                    placeholder="Search precisely by email, name, or company domain..." 
                    className="w-[400px] border-none bg-slate-50 px-5 py-3 rounded-xl focus:ring-2 focus:ring-blue-500 outline-none text-slate-700 font-medium" 
                />
                <div className="flex gap-2">
                    <select className="bg-slate-50 border border-slate-100 rounded-xl px-4 py-2 text-sm font-bold text-slate-600 outline-none">
                        <option>Status: All</option>
                        <option>Verified (100)</option>
                        <option>Risky (&gt;= 80)</option>
                        <option>Suppressed</option>
                    </select>
                </div>
            </div>

            {error && leads.length === 0 ? (
                <div className="p-6 bg-red-50 border border-red-200 text-red-700 rounded-2xl flex flex-col items-center justify-center py-16 shadow-sm text-center">
                    <AlertCircle className="mb-4 text-red-500" size={32} />
                    <span className="font-bold mb-2">Failed to Load Contacts</span>
                    <span className="text-sm">{error}</span>
                </div>
            ) : loading ? (
                <div className="h-64 flex items-center justify-center bg-white rounded-2xl border border-slate-200 shadow-sm">
                    <Spinner size="lg" />
                </div>
            ) : (
                <Table columns={["Email Address", "Name", "Company", "Verification Integrity", "Activity Status"]}>
                    {leads.map((lead) => (
                        <TableRow key={lead.id}>
                            <TableCell className="font-bold text-slate-800">{lead.email}</TableCell>
                            <TableCell className="text-slate-600 font-medium">{lead.first_name} {lead.last_name}</TableCell>
                            <TableCell className="text-slate-600">{lead.company || "-"}</TableCell>
                            <TableCell>{getVerificationBadge(lead.verification_score, lead.is_suppressed)}</TableCell>
                            <TableCell>
                                <span className="bg-blue-50 text-blue-600 font-bold px-3 py-1 rounded-full text-xs">New Lead</span>
                            </TableCell>
                        </TableRow>
                    ))}
                    {leads.length === 0 && (
                        <TableRow>
                            <TableCell className="text-center py-12" colSpan={5}>
                                <span className="text-slate-400 font-bold text-lg">No Lead Data Found</span>
                            </TableCell>
                        </TableRow>
                    )}
                </Table>
            )}
        </div>
    );
}
