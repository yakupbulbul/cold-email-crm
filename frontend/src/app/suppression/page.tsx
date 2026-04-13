"use client";

import { useEffect, useState } from "react";
import { useApiService } from "@/services/api";
import { SuppressionEntry } from "@/types/models";
import Table, { TableRow, TableCell } from "@/components/ui/Table";
import Spinner from "@/components/ui/Spinner";
import { Trash2, AlertCircle, Plus } from "lucide-react";
import { AlertBanner, PageHeader, SurfaceCard } from "@/components/ui/primitives";

export default function SuppressionPage() {
    const { getSuppressionList, addSuppression, deleteSuppression, loading, error } = useApiService();
    const [list, setList] = useState<SuppressionEntry[]>([]);
    const [email, setEmail] = useState("");
    const [reason, setReason] = useState("manual");
    const [submitError, setSubmitError] = useState<string | null>(null);
    const [isSubmitting, setIsSubmitting] = useState(false);

    useEffect(() => {
        const fetchList = async () => {
            const data = await getSuppressionList();
            if (data) setList(data);
        };
        fetchList();
    }, [getSuppressionList]);

    const performDelete = async (id: string) => {
        await deleteSuppression(id);
        setList(list.filter(item => item.id !== id));
    };

    const handleCreate = async (event: React.FormEvent<HTMLFormElement>) => {
        event.preventDefault();
        setSubmitError(null);
        const normalizedEmail = email.trim().toLowerCase();
        if (!normalizedEmail) {
            setSubmitError("Enter an email address to suppress.");
            return;
        }
        setIsSubmitting(true);
        const created = await addSuppression(normalizedEmail, reason.trim() || "manual");
        setIsSubmitting(false);
        if (!created) {
            setSubmitError("Suppression create failed. Check the backend response and try again.");
            return;
        }
        setEmail("");
        const refreshed = await getSuppressionList();
        if (refreshed) {
            setList(refreshed);
        }
    };

    return (
        <div className="space-y-6 animate-fade-in relative min-h-screen">
            <PageHeader
                eyebrow="Safety"
                title="Global Suppression Log"
                description="Keep blocked addresses visible, persistent, and infrastructure-wide so suppressed emails never re-enter outbound traffic."
            />

            <SurfaceCard className="p-5">
            <form onSubmit={handleCreate} className="flex flex-col gap-4 md:flex-row md:items-end">
                <div className="flex-1">
                    <label htmlFor="suppression-email" className="block text-sm font-semibold text-slate-700 mb-2">
                        Email Address
                    </label>
                    <input
                        id="suppression-email"
                        data-testid="suppression-email-input"
                        type="email"
                        value={email}
                        onChange={(event) => setEmail(event.target.value)}
                        placeholder="blocked@example.com"
                        className="form-input"
                    />
                </div>
                <div className="md:w-64">
                    <label htmlFor="suppression-reason" className="block text-sm font-semibold text-slate-700 mb-2">
                        Reason
                    </label>
                    <input
                        id="suppression-reason"
                        data-testid="suppression-reason-input"
                        type="text"
                        value={reason}
                        onChange={(event) => setReason(event.target.value)}
                        placeholder="bounce"
                        className="form-input"
                    />
                </div>
                <button
                    data-testid="create-suppression-button"
                    type="submit"
                    disabled={isSubmitting}
                    className="btn-primary"
                >
                    <Plus size={18} />
                    {isSubmitting ? "Adding..." : "Add Suppression"}
                </button>
            </form>
            </SurfaceCard>

            {submitError ? <AlertBanner tone="danger" title="Suppression create failed">{submitError}</AlertBanner> : null}

            <div className="bg-white rounded-2xl border border-red-100 shadow-sm p-8 mt-8 flex flex-col items-center justify-center max-w-full">
                {error && list.length === 0 ? (
                    <div className="p-6 text-red-700 flex flex-col items-center justify-center py-12 text-center w-full">
                        <AlertCircle className="mb-4 text-red-500" size={32} />
                        <span className="font-bold mb-2">Error Loading Suspensions</span>
                        <span className="text-sm">{error}</span>
                    </div>
                ) : loading ? (
                    <Spinner size="lg" />
                ) : (
                    <div className="w-full">
                        <Table columns={["Blocked Address", "Penalty Reason", "Detection Source", "Blocked On", "Actions"]}>
                            {list.map((item) => (
                                <TableRow key={item.id}>
                                    <TableCell className="font-bold text-slate-800">{item.email}</TableCell>
                                    <TableCell className="text-red-600 font-bold">{item.reason}</TableCell>
                                    <TableCell className="text-slate-500 font-bold uppercase text-xs">{item.source}</TableCell>
                                    <TableCell className="text-slate-600 font-medium">{new Date(item.created_at).toLocaleDateString()}</TableCell>
                                    <TableCell>
                                        <button onClick={() => performDelete(item.id)} className="text-slate-400 hover:text-red-500 transition-colors p-2 hover:bg-red-50 rounded-xl">
                                            <Trash2 size={18} />
                                        </button>
                                    </TableCell>
                                </TableRow>
                            ))}
                            {list.length === 0 && (
                                <TableRow>
                                    <TableCell colSpan={5} className="text-center py-12">
                                        <span className="text-slate-400 font-bold text-lg">No suppression entries yet.</span>
                                    </TableCell>
                                </TableRow>
                            )}
                        </Table>
                    </div>
                )}
            </div>
        </div>
    );
}
