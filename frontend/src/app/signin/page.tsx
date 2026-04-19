"use client";

import React, { useEffect, useRef, useState } from "react";
import { useAuth } from "@/context/AuthContext";
import Image from "next/image";
import Link from "next/link";
import { Mail, Lock, ShieldCheck, Activity, Send, Eye, EyeOff, ArrowRight } from "lucide-react";
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
        <div className="min-h-screen bg-[radial-gradient(circle_at_top_left,_rgba(37,99,235,0.10),_transparent_34%),linear-gradient(180deg,#f8fbff_0%,#eef4ff_48%,#f5f7fb_100%)] px-4 py-6 sm:px-6 lg:px-8">
            <main className="mx-auto flex min-h-[calc(100vh-3rem)] w-full max-w-6xl items-center justify-center">
                <section className="grid w-full overflow-hidden rounded-[2rem] border border-white/80 bg-white/90 shadow-[0_30px_80px_rgba(15,23,42,0.12)] backdrop-blur lg:grid-cols-[0.95fr,1.05fr]">
                    <div className="relative hidden min-h-[620px] flex-col justify-between overflow-hidden bg-slate-950 p-8 text-white lg:flex xl:p-10">
                        <div className="absolute inset-0 bg-[radial-gradient(circle_at_20%_20%,rgba(56,189,248,0.20),transparent_30%),radial-gradient(circle_at_85%_10%,rgba(37,99,235,0.18),transparent_28%)]" />
                        <div className="relative">
                            <Link href="/" className="inline-flex items-center gap-3">
                                <div className="rounded-2xl bg-white px-4 py-3">
                                    <Image src="/crm-logo.png" alt="Campaign Manager" width={78} height={40} className="h-auto w-[78px]" priority />
                                </div>
                                <div>
                                    <div className="text-sm font-semibold text-white">Campaign Manager</div>
                                    <div className="text-xs text-slate-400">Outreach operations workspace</div>
                                </div>
                            </Link>
                        </div>
                        <div className="relative max-w-md">
                            <div className="inline-flex rounded-full border border-white/10 bg-white/10 px-3 py-1 text-xs font-semibold uppercase tracking-[0.18em] text-sky-100">
                                Secure workspace access
                            </div>
                            <h1 className="mt-5 text-4xl font-semibold leading-[1.02] tracking-[-0.055em] xl:text-5xl">
                                Operate cold email with one clear control surface.
                            </h1>
                            <p className="mt-5 text-sm leading-7 text-slate-300 xl:text-base">
                                Sign in to manage domains, mailboxes, campaigns, replies, warm-up, and operational health from a single backend-backed workspace.
                            </p>
                        </div>
                        <div className="relative grid gap-3">
                            <ValuePoint icon={Send} title="Campaign control" detail="Launch, pause, and inspect real execution." />
                            <ValuePoint icon={Activity} title="Operational visibility" detail="See readiness, blockers, and worker-backed state." />
                            <ValuePoint icon={ShieldCheck} title="Sender safety" detail="Keep verification, suppression, and compliance visible." />
                        </div>
                    </div>

                    <div className="flex min-h-[620px] items-center justify-center px-5 py-8 sm:px-8 lg:px-10">
                        <div className="w-full max-w-md">
                            <div className="mb-7 flex items-center justify-between gap-4 lg:hidden">
                                <Link href="/" className="flex items-center gap-3">
                                    <div className="rounded-2xl bg-slate-950 px-4 py-3">
                                        <Image src="/crm-logo.png" alt="Campaign Manager" width={74} height={38} className="h-auto w-[74px]" priority />
                                    </div>
                                    <div>
                                        <div className="text-sm font-semibold text-slate-950">Campaign Manager</div>
                                        <div className="text-xs text-slate-500">Workspace access</div>
                                    </div>
                                </Link>
                                <Link href="/" className="text-sm font-medium text-slate-500 hover:text-slate-900">
                                    Overview
                                </Link>
                            </div>

                            <div className="mb-7">
                                <div className="text-xs font-semibold uppercase tracking-[0.22em] text-slate-500">
                                    Sign in
                                </div>
                                <h2 className="mt-2 text-3xl font-semibold tracking-[-0.045em] text-slate-950 sm:text-4xl">
                                    Access your workspace
                                </h2>
                                <p className="mt-3 text-sm leading-6 text-slate-600">
                                    Use your operator credentials to continue to the internal dashboard.
                                </p>
                            </div>

                            <form onSubmit={handleSubmit} className="space-y-5 rounded-[1.75rem] border border-slate-200 bg-white p-5 shadow-[0_18px_48px_rgba(15,23,42,0.08)] sm:p-6">
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
                                            data-testid="password-toggle"
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
                                    className="btn-primary mt-2 w-full rounded-2xl py-4 text-base"
                                >
                                    {loading ? <Spinner size="sm" /> : (
                                        <>
                                            Sign in to workspace
                                            <ArrowRight size={16} />
                                        </>
                                    )}
                                </button>
                            </form>

                            <div className="mt-5 flex flex-col justify-between gap-3 text-sm text-slate-500 sm:flex-row sm:items-center">
                                <span>Protected by backend session auth.</span>
                                <Link href="/" className="font-medium text-slate-900 hover:text-slate-700">
                                    Product overview
                                </Link>
                            </div>
                        </div>
                    </div>
                </section>
            </main>
        </div>
    );
}

function ValuePoint({
    icon: Icon,
    title,
    detail,
}: {
    icon: typeof Send;
    title: string;
    detail: string;
}) {
    return (
        <div className="flex items-start gap-3 rounded-2xl border border-white/10 bg-white/7 p-4">
            <div className="mt-0.5 flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-white/10 text-sky-100">
                <Icon size={16} />
            </div>
            <div>
                <div className="text-sm font-semibold text-white">{title}</div>
                <div className="mt-1 text-sm leading-5 text-slate-400">{detail}</div>
            </div>
        </div>
    );
}
