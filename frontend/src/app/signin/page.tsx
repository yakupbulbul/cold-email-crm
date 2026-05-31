"use client";

import React, { useEffect, useRef, useState } from "react";
import { useAuth } from "@/context/AuthContext";
import Image from "next/image";
import Link from "next/link";
import { Mail, Lock, ShieldCheck, Activity, Eye, EyeOff, ArrowRight, CheckCircle2 } from "lucide-react";
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
        <div className="min-h-screen bg-[radial-gradient(circle_at_top,_rgba(45,106,79,0.06),_transparent_38%),linear-gradient(180deg,#faf8f5_0%,#f5f0eb_100%)] px-4 py-5 sm:px-6 lg:px-8">
            <main className="mx-auto flex min-h-[calc(100vh-2.5rem)] w-full max-w-5xl items-center justify-center">
                <section className="grid w-full items-center gap-8 lg:grid-cols-[0.78fr,1fr] lg:gap-10">
                    <div className="order-2 rounded-[1.75rem] border border-[var(--border)] bg-[var(--surface)]/70 p-5 text-[var(--foreground)] shadow-[0_16px_45px_rgba(45,31,20,0.06)] backdrop-blur lg:order-1 lg:p-6">
                        <Link href="/" className="inline-flex items-center gap-3">
                            <div className="rounded-2xl bg-[var(--sidebar)] px-4 py-3">
                                <Image src="/crm-logo.png" alt="Campaign Manager" width={76} height={38} className="h-auto w-[76px]" priority />
                            </div>
                            <div>
                                <div className="text-sm font-semibold text-[var(--foreground)]">Campaign Manager</div>
                                <div className="text-xs text-[var(--muted-foreground)]">Workspace access</div>
                            </div>
                        </Link>

                        <div className="mt-8">
                            <div className="text-xs font-semibold uppercase tracking-[0.2em] text-[var(--muted-foreground)]">
                                Secure operator sign-in
                            </div>
                            <h1 className="mt-3 text-2xl font-semibold leading-tight tracking-[-0.04em] text-[var(--foreground)] sm:text-3xl">
                                Access the workspace for campaigns, senders, and replies.
                            </h1>
                            <p className="mt-4 text-sm leading-6 text-[var(--muted-foreground)]">
                                Sign in with your operator credentials to manage outbound infrastructure and campaign operations.
                            </p>
                        </div>

                        <div className="mt-6 space-y-3">
                            <ValuePoint icon={ShieldCheck} text="Backend-authenticated workspace access" />
                            <ValuePoint icon={Activity} text="Operational status, warm-up, inbox, and campaign controls" />
                            <ValuePoint icon={CheckCircle2} text="Focused entry point for authorized users" />
                        </div>
                    </div>

                    <div className="order-1 flex justify-center lg:order-2">
                        <div className="w-full max-w-[29rem] rounded-[2rem] border border-[var(--border)] bg-[var(--surface)] p-6 shadow-[0_28px_70px_rgba(45,31,20,0.12)] sm:p-8">
                            <div className="mb-6">
                                <div className="mb-5 flex items-center justify-between gap-4 lg:hidden">
                                    <Link href="/" className="flex items-center gap-3">
                                        <div className="rounded-2xl bg-[var(--sidebar)] px-4 py-3">
                                            <Image src="/crm-logo.png" alt="Campaign Manager" width={74} height={38} className="h-auto w-[74px]" priority />
                                        </div>
                                        <div>
                                            <div className="text-sm font-semibold text-[var(--foreground)]">Campaign Manager</div>
                                            <div className="text-xs text-[var(--muted-foreground)]">Workspace access</div>
                                        </div>
                                    </Link>
                                    <Link href="/" className="text-sm font-medium text-[var(--muted-foreground)] hover:text-[var(--foreground)]">
                                        Overview
                                    </Link>
                                </div>

                                <div className="inline-flex rounded-full border border-[var(--border)] bg-[var(--surface-muted)] px-3 py-1 text-xs font-semibold uppercase tracking-[0.18em] text-[var(--muted-foreground)]">
                                    Workspace access
                                </div>
                                <h2 className="mt-4 text-3xl font-semibold tracking-[-0.045em] text-[var(--foreground)] sm:text-4xl">
                                    Sign in
                                </h2>
                                <p className="mt-3 text-sm leading-6 text-[var(--muted-foreground)]">
                                    Continue to your internal dashboard.
                                </p>
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
                                        <Mail size={18} className="pointer-events-none absolute left-4 top-1/2 -translate-y-1/2 text-[var(--muted-foreground)]" />
                                        <input
                                            data-testid="email-input"
                                            type="email"
                                            required
                                            value={email}
                                            onChange={(e) => {
                                                setEmail(e.target.value);
                                                if (emailError) setEmailError(null);
                                            }}
                                            className="form-input form-input-with-leading-icon"
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
                                        <Lock size={18} className="pointer-events-none absolute left-4 top-1/2 -translate-y-1/2 text-[var(--muted-foreground)]" />
                                        <input
                                            data-testid="password-input"
                                            type={showPassword ? "text" : "password"}
                                            required
                                            value={password}
                                            onChange={(e) => {
                                                setPassword(e.target.value);
                                                if (passwordError) setPasswordError(null);
                                            }}
                                            className="form-input form-input-with-leading-icon form-input-with-trailing-action"
                                            placeholder="••••••••"
                                            autoComplete="current-password"
                                        />
                                        <button
                                            data-testid="password-toggle"
                                            type="button"
                                            onClick={() => setShowPassword((current) => !current)}
                                            className="absolute right-3 top-1/2 inline-flex h-9 w-9 -translate-y-1/2 items-center justify-center rounded-xl text-[var(--muted-foreground)] hover:bg-[var(--surface-muted)] hover:text-[var(--foreground)]"
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

                            <div className="mt-6 flex flex-col justify-between gap-3 border-t border-[var(--surface-muted)] pt-5 text-sm text-[var(--muted-foreground)] sm:flex-row sm:items-center">
                                <span>Protected by backend session auth.</span>
                                <Link href="/" className="font-medium text-[var(--foreground)] hover:text-[var(--foreground)]">
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
    text,
}: {
    icon: typeof ShieldCheck;
    text: string;
}) {
    return (
        <div className="flex items-start gap-3 text-sm leading-6 text-[var(--muted-foreground)]">
            <div className="mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-[var(--sidebar)] text-white">
                <Icon size={13} />
            </div>
            <span>{text}</span>
        </div>
    );
}
