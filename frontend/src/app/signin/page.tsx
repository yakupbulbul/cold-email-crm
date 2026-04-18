"use client";

import React, { useEffect, useRef, useState } from "react";
import { useAuth } from "@/context/AuthContext";
import Image from "next/image";
import Link from "next/link";
import { Mail, Lock, LogIn, ShieldCheck, Activity, Send, Eye, EyeOff, ArrowRight } from "lucide-react";
import Spinner from "@/components/ui/Spinner";
import { AlertBanner, FieldGroup } from "@/components/ui/primitives";
import { useRouter } from "next/navigation";

export default function SignInPage() {
    const { login, token, isLoading } = useAuth();
    const router = useRouter();
    const [email, setEmail] = useState("");
    const [password, setPassword] = useState("");
    const [error, setError] = useState<string | null>(null);
    const [emailError, setEmailError] = useState<string | null>(null);
    const [passwordError, setPasswordError] = useState<string | null>(null);
    const [loading, setLoading] = useState(false);
    const [showPassword, setShowPassword] = useState(false);
    const isMountedRef = useRef(true);

    useEffect(() => {
        return () => {
            isMountedRef.current = false;
        };
    }, []);

    useEffect(() => {
        if (!isLoading && token) {
            router.replace("/dashboard");
        }
    }, [isLoading, router, token]);

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setError(null);
        const normalizedEmail = email.trim();
        let hasError = false;

        if (!normalizedEmail) {
            setEmailError("Enter the email address for your workspace account.");
            hasError = true;
        } else {
            setEmailError(null);
        }

        if (!password) {
            setPasswordError("Enter your password to continue.");
            hasError = true;
        } else {
            setPasswordError(null);
        }

        if (hasError) {
            return;
        }

        setLoading(true);

        try {
            const API_URL = process.env.NEXT_PUBLIC_API_URL || "/api/v1";
            const res = await fetch(`${API_URL}/auth/login`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ email: normalizedEmail, password }),
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
        <div className="min-h-screen bg-[linear-gradient(180deg,#f8fbff_0%,#edf3ff_52%,#f4f7fb_100%)] px-4 py-5 sm:px-6 sm:py-6">
            <div className="mx-auto flex min-h-[calc(100vh-2.5rem)] w-full max-w-6xl flex-col">
                <header className="flex items-center justify-between gap-4 rounded-[1.9rem] border border-white/80 bg-white/82 px-5 py-4 shadow-[0_18px_48px_rgba(15,23,42,0.07)] backdrop-blur sm:px-6">
                    <Link href="/" className="flex items-center gap-3">
                        <div className="rounded-2xl bg-slate-950 px-4 py-3">
                            <Image src="/crm-logo.png" alt="Campaign Manager" width={78} height={40} className="h-auto w-[78px]" priority />
                        </div>
                        <div>
                            <div className="text-sm font-semibold text-slate-950">Campaign Manager</div>
                            <div className="text-xs text-slate-500">Outreach operations workspace</div>
                        </div>
                    </Link>
                    <div className="flex items-center gap-3">
                        <Link href="/" className="hidden text-sm font-medium text-slate-600 hover:text-slate-900 sm:inline-flex">
                            Back to product overview
                        </Link>
                        <Link href="/" className="btn-secondary px-4 py-2.5 text-sm">
                            View landing page
                        </Link>
                    </div>
                </header>

                <div className="mx-auto grid w-full flex-1 items-center gap-8 py-8 lg:grid-cols-[1.08fr,0.92fr] lg:gap-10 lg:py-12">
                <div className="hidden lg:block">
                    <div className="max-w-xl">
                        <div className="inline-flex items-center gap-2 rounded-full border border-sky-200 bg-sky-50 px-3 py-1 text-xs font-semibold uppercase tracking-[0.18em] text-sky-700">
                            Secure sign-in
                        </div>
                        <h1 className="mt-6 text-5xl font-semibold leading-[1.02] tracking-[-0.055em] text-slate-950">
                            Sign in to the workspace that runs your cold email system.
                        </h1>
                        <p className="mt-5 max-w-lg text-base leading-7 text-[var(--muted-foreground)]">
                            Access domains, mailboxes, campaigns, inbox replies, warm-up, and operational health from one product surface with backend-backed status instead of placeholder UI.
                        </p>
                        <div className="mt-10 grid gap-4 sm:grid-cols-3">
                            <FeatureCard icon={Send} title="Campaign control" detail="Start, pause, and inspect real execution without losing clarity." />
                            <FeatureCard icon={Activity} title="Operational visibility" detail="See what is healthy, blocked, and ready right away." />
                            <FeatureCard icon={ShieldCheck} title="Sender safety" detail="Keep suppression, verification, and compliance visible." />
                        </div>
                    </div>
                </div>
                <div className="mx-auto w-full max-w-md">
                    <div className="surface-card animate-fade-in overflow-hidden rounded-[2rem] p-8 sm:p-10">
                        <div className="mb-8 flex items-start justify-between gap-4">
                            <div>
                                <div className="text-xs font-semibold uppercase tracking-[0.24em] text-[var(--muted-foreground)]">
                                    Operator access
                                </div>
                                <h2 className="mt-2 text-3xl font-semibold tracking-[-0.045em] text-slate-950">Sign in</h2>
                                <p className="mt-2 max-w-sm text-sm leading-6 text-[var(--muted-foreground)]">
                                    Use your workspace credentials to access infrastructure, campaigns, inbox, and delivery controls.
                                </p>
                            </div>
                            <div className="inline-flex h-12 w-12 shrink-0 items-center justify-center rounded-2xl bg-slate-950 text-white shadow-lg">
                                <LogIn size={20} />
                            </div>
                        </div>

                        <form onSubmit={handleSubmit} className="space-y-5">
                            {error ? (
                                <AlertBanner tone="danger" title="Authentication failed">
                                    {error}
                                </AlertBanner>
                            ) : null}

                            <FieldGroup
                                label="Email address"
                                hint="Use the operator email assigned to your workspace."
                                error={emailError}
                            >
                                <div className="relative">
                                    <Mail size={18} className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-400" />
                                    <input
                                        data-testid="email-input"
                                        type="email"
                                        required
                                        value={email}
                                        onChange={(e) => {
                                            setEmail(e.target.value);
                                            if (emailError) setEmailError(null);
                                        }}
                                        className="form-input pl-12"
                                        placeholder="name@company.com"
                                        autoComplete="email"
                                    />
                                </div>
                            </FieldGroup>

                            <FieldGroup
                                label="Password"
                                hint="Your credentials stay within the existing backend auth flow."
                                error={passwordError}
                            >
                                <div className="relative">
                                    <Lock size={18} className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-400" />
                                    <input
                                        data-testid="password-input"
                                        type={showPassword ? "text" : "password"}
                                        required
                                        value={password}
                                        onChange={(e) => {
                                            setPassword(e.target.value);
                                            if (passwordError) setPasswordError(null);
                                        }}
                                        className="form-input pl-12 pr-12"
                                        placeholder="••••••••"
                                        autoComplete="current-password"
                                    />
                                    <button
                                        type="button"
                                        onClick={() => setShowPassword((current) => !current)}
                                        className="absolute right-3 top-1/2 inline-flex h-9 w-9 -translate-y-1/2 items-center justify-center rounded-xl text-slate-400 hover:bg-slate-100 hover:text-slate-700"
                                        aria-label={showPassword ? "Hide password" : "Show password"}
                                    >
                                        {showPassword ? <EyeOff size={17} /> : <Eye size={17} />}
                                    </button>
                                </div>
                            </FieldGroup>

                            <button
                                data-testid="login-button"
                                type="submit"
                                disabled={loading}
                                className="btn-primary mt-3 w-full rounded-2xl py-4 text-base"
                            >
                                {loading ? <Spinner size="sm" /> : (
                                    <>
                                        Sign in to workspace
                                        <ArrowRight size={16} />
                                    </>
                                )}
                            </button>
                        </form>

                        <div className="mt-8 border-t border-slate-100 pt-6">
                            <div className="text-xs uppercase tracking-[0.18em] text-[var(--muted-foreground)]">
                                Backend-backed control for senders, audiences, and campaigns
                            </div>
                            <div className="mt-3 text-sm text-slate-500">
                                Need product context first? <Link href="/" className="font-medium text-slate-900 hover:text-slate-700">Review the landing page</Link>.
                            </div>
                        </div>
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
