"use client";

import { useEffect, useState } from "react";
import { useApi } from "@/hooks/useApi";
import Table, { TableRow, TableCell } from "@/components/ui/Table";
import Spinner from "@/components/ui/Spinner";
import { ShieldX, Trash2 } from "lucide-react";

export default function SuppressionPage() {
    const { request, loading } = useApi();
    const [list, setList] = useState<any[]>([]);

    useEffect(() => {
        const fetchList = async () => {
            const data = await request("/suppression");
            if (data) setList(data);
        };
        fetchList();
    }, [request]);

    const performDelete = async (id: string) => {
        await request(`/suppression/${id}`, { method: "DELETE" });
        setList(list.filter(item => item.id !== id));
    };

    return (
        <div className="space-y-6 animate-fade-in relative min-h-screen">
            <div className="flex items-center justify-between">
                <div>
                    <h1 className="text-3xl font-bold text-slate-800 tracking-tight flex items-center gap-3">
                        <ShieldX className="text-red-500" size={32} /> Global Suppression Log
                    </h1>
                    <p className="text-slate-500 mt-2 text-sm font-medium max-w-2xl">
                        Emails on this list are definitively blocked infrastructure-wide from receiving any outbound campaign messages protecting the SMTP Domain sender reputations heavily.
                    </p>
                </div>
            </div>

            <div className="bg-white rounded-2xl border border-red-100 shadow-sm p-8 mt-8 flex flex-col items-center justify-center max-w-full">
                {loading ? (
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
                                        <span className="text-slate-400 font-bold text-lg">Infrastructure Clear. No Penalties Detected.</span>
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
