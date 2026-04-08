"use client";

import { useAuth } from "@/context/AuthContext";
import { usePathname } from "next/navigation";
import Sidebar from "@/components/Sidebar";
import TopBar from "@/components/TopBar";
import Spinner from "@/components/ui/Spinner";

export default function AppLayout({ children }: { children: React.ReactNode }) {
    const { token, isLoading } = useAuth();
    const pathname = usePathname();

    const isAuthRoute = pathname === "/signin" || pathname === "/login";

    if (isAuthRoute) {
        return <div className="w-full">{children}</div>;
    }

    if (isLoading) {
        return (
            <div className="min-h-screen flex items-center justify-center bg-slate-50 w-full font-bold text-slate-400">
                <div className="flex flex-col items-center gap-4">
                    <Spinner size="lg" />
                    <span>Hydrating Secure Session...</span>
                </div>
            </div>
        );
    }

    if (!token) {
        return null; // AuthContext handles the redirect to /signin
    }

    return (
        <div className="bg-slate-50 text-slate-900 flex min-h-screen overflow-hidden w-full">
            <Sidebar />
            <div className="flex-1 flex flex-col ml-64 min-h-screen bg-slate-50/50 overflow-hidden">
                <TopBar />
                <main className="flex-1 overflow-y-auto p-10">
                    {children}
                </main>
            </div>
        </div>
    );
}
