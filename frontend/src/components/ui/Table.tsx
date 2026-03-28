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

interface TableRowProps {
    children: React.ReactNode;
    className?: string;
}

export function TableRow({ children, className = "" }: TableRowProps) {
    return <tr className={`border-b border-slate-100 last:border-0 hover:bg-slate-50 transition-colors ${className}`}>{children}</tr>;
}

interface TableCellProps {
    children: React.ReactNode;
    className?: string;
    colSpan?: number;
}
export function TableCell({ children, className = "", colSpan }: TableCellProps) {
    return <td colSpan={colSpan} className={`px-6 py-4 text-sm ${className}`}>{children}</td>;
}
