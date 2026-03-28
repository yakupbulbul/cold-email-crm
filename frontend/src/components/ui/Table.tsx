"use client";

interface TableProps {
    columns: string[];
    children: React.ReactNode;
}

export default function Table({ columns, children }: TableProps) {
    return (
        <div className="overflow-x-auto rounded-2xl border border-slate-200 bg-white">
            <table className="w-full text-left border-collapse">
                <thead>
                    <tr className="bg-slate-50 border-b border-slate-200">
                        {columns.map((col, i) => (
                            <th key={i} className="px-6 py-4 text-xs font-bold text-slate-500 uppercase tracking-wider">
                                {col}
                            </th>
                        ))}
                    </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                    {children}
                </tbody>
            </table>
        </div>
    );
}

export function TableRow({ children }: { children: React.ReactNode }) {
    return <tr className="hover:bg-slate-50/80 transition-colors">{children}</tr>;
}

export function TableCell({ children, className = "" }: { children: React.ReactNode, className?: string }) {
    return <td className={`px-6 py-4 text-sm text-slate-700 ${className}`}>{children}</td>;
}
