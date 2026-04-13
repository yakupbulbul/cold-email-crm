"use client";

import React, { useEffect, useRef, useState } from "react";
import { useAuth } from "@/context/AuthContext";
import Image from "next/image";
import { Mail, Lock, LogIn, ShieldCheck, Activity, Send } from "lucide-react";
import Spinner from "@/components/ui/Spinner";
import { AlertBanner } from "@/components/ui/primitives";

export default function SignInPage() {
    const { login } = useAuth();
    const [email, setEmail] = useState("");
    const [password, setPassword] = useState("");
    const [error, setError] = useState<string | null>(null);
    const [loading, setLoading] = useState(false);
    const isMountedRef = useRef(true);

    useEffect(() => {
        return () => {
            isMountedRef.current = false;
        };
    }, []);

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setError(null);
        setLoading(true);

        try {
            const API_URL = process.env.NEXT_PUBLIC_API_URL || "/api/v1";
            const res = await fetch(`${API_URL}/auth/login`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ email, password }),
            });

            if (!res.ok) {
                const data = await res.json().catch(() => ({}));
                throw new Error(data.detail || "Authentication failed");
            }

            const { access_token } = await res.json();
            await login(access_token);
        } catch (err: unknown) {
            if (isMountedRef.current) {
                setError(err instanceof Error ? err.message : "An unexpected error occurred");
            }
        } finally {
            if (isMountedRef.current) {
                setLoading(false);
            }
        }
    };

    return (
        <div className="min-h-screen bg-[radial-gradient(circle_at_top_left,_rgba(37,99,235,0.12),_transparent_32%),radial-gradient(circle_at_bottom_right,_rgba(14,165,233,0.12),_transparent_28%),_var(--background)] px-4 py-8">
            <div className="mx-auto grid min-h-[calc(100vh-4rem)] w-full max-w-6xl items-center gap-10 lg:grid-cols-[1.15fr,0.85fr]">
                <div className="hidden lg:block">
                    <div className="max-w-xl">
                        <div className="mb-8 flex items-center gap-4">
                            <div className="rounded-[1.75rem] bg-white px-5 py-4 shadow-[var(--shadow-soft)]">
                                <Image src="/crm-logo.png" alt="Campaign Manager" width={108} height={54} className="h-auto w-[108px]" priority />
                            </div>
                            <div>
                                <div className="text-sm font-semibold uppercase tracking-[0.24em] text-[var(--muted-foreground)]">
                                    Campaign Manager
                                </div>
                                <div className="mt-1 text-sm text-[var(--muted-foreground)]">
                                    Unified outreach operations for infrastructure, campaigns, warm-up, and compliance.
                                </div>
                            </div>
                        </div>
                        <h1 className="text-5xl font-semibold leading-[1.02] tracking-[-0.05em] text-slate-950">
                            Operate B2B and B2C email systems with less friction.
                        </h1>
                        <p className="mt-5 max-w-lg text-base leading-7 text-[var(--muted-foreground)]">
                            This console keeps campaigns, mailboxes, warm-up, audience quality, and delivery health in one place, with backend-backed truth instead of placeholder dashboards.
                        </p>
                        <div className="mt-10 grid gap-4 sm:grid-cols-3">
                            <FeatureCard icon={Send} title="Campaign control" detail="Start, pause, and inspect real execution without losing clarity." />
                            <FeatureCard icon={Activity} title="Operational visibility" detail="See what is healthy, blocked, and ready right away." />
                            <FeatureCard icon={ShieldCheck} title="Sender safety" detail="Keep suppression, verification, and compliance visible." />
                        </div>
                    </div>
                </div>
                <div className="mx-auto w-full max-w-md">
                    <div className="surface-card animate-fade-in p-8 sm:p-10">
                        <div className="mb-8 flex items-center justify-between">
                            <div>
                                <div className="text-xs font-semibold uppercase tracking-[0.24em] text-[var(--muted-foreground)]">
                                    Secure access
                                </div>
                                <h2 className="mt-2 text-3xl font-semibold tracking-[-0.04em] text-slate-950">Sign in</h2>
                                <p className="mt-2 text-sm text-[var(--muted-foreground)]">
                                    Use your operator credentials to access infrastructure, campaigns, and delivery controls.
                                </p>
                            </div>
                            <div className="inline-flex h-14 w-14 items-center justify-center rounded-3xl bg-slate-900 text-white shadow-lg">
                                <LogIn size={24} />
                            </div>
                        </div>

                        <form onSubmit={handleSubmit} className="space-y-5">
                            {error ? (
                                <AlertBanner tone="danger" title="Authentication failed">
                                    {error}
                                </AlertBanner>
                            ) : null}

                            <label className="block space-y-2">
                                <span className="text-sm font-medium text-slate-800">Email address</span>
                                <div className="relative">
                                    <Mail size={18} className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-400" />
                                    <input
                                        data-testid="email-input"
                                        type="email"
                                        required
                                        value={email}
                                        onChange={(e) => setEmail(e.target.value)}
                                        className="form-input pl-12"
                                        placeholder="name@company.com"
                                        autoComplete="email"
                                    />
                                </div>
                            </label>

                            <label className="block space-y-2">
                                <span className="text-sm font-medium text-slate-800">Password</span>
                                <div className="relative">
                                    <Lock size={18} className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-400" />
                                    <input
                                        data-testid="password-input"
                                        type="password"
                                        required
                                        value={password}
                                        onChange={(e) => setPassword(e.target.value)}
                                        className="form-input pl-12"
                                        placeholder="••••••••"
                                        autoComplete="current-password"
                                    />
                                </div>
                            </label>

                            <button
                                data-testid="login-button"
                                type="submit"
                                disabled={loading}
                                className="btn-primary mt-3 w-full rounded-2xl py-4 text-base"
                            >
                                {loading ? <Spinner size="sm" /> : "Sign in to platform"}
                            </button>
                        </form>

                        <div className="mt-8 border-t border-slate-100 pt-6 text-xs uppercase tracking-[0.18em] text-[var(--muted-foreground)]">
                            Backend-backed control for senders, audiences, and campaigns
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
}

function FeatureCard({
    icon: Icon,
    title,
    detail,
}: {
    icon: typeof Send;
    title: string;
    detail: string;
}) {
    return (
        <div className="surface-card p-5">
            <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-white text-slate-900 shadow-sm">
                <Icon size={18} />
            </div>
            <div className="mt-4 text-base font-semibold text-slate-950">{title}</div>
            <div className="mt-2 text-sm leading-6 text-[var(--muted-foreground)]">{detail}</div>
        </div>
    );
}
