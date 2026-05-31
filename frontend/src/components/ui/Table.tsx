"use client";

interface TableProps {
    columns: string[];
    children: React.ReactNode;
}

export default function Table({ columns, children }: TableProps) {
    return (
        <div className="overflow-x-auto rounded-2xl border border-[var(--border)] bg-[var(--surface)]">
            <table className="w-full text-left border-collapse">
                <thead>
                    <tr className="bg-[var(--surface-muted)] border-b border-[var(--border)]">
                        {columns.map((col, i) => (
                            <th key={i} className="px-6 py-4 text-xs font-bold text-[var(--muted-foreground)] uppercase tracking-wider">
                                {col}
                            </th>
                        ))}
                    </tr>
                </thead>
                <tbody className="divide-y divide-[var(--surface-muted)]">
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
    return <tr className={`border-b border-[var(--surface-muted)] last:border-0 hover:bg-[var(--surface-muted)] transition-colors ${className}`}>{children}</tr>;
}

interface TableCellProps {
    children: React.ReactNode;
    className?: string;
    colSpan?: number;
}
export function TableCell({ children, className = "", colSpan }: TableCellProps) {
    return <td colSpan={colSpan} className={`px-6 py-4 text-sm ${className}`}>{children}</td>;
}
