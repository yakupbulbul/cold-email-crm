import { useState, useCallback, useRef, useEffect } from "react";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "/api/v1";

interface ApiOptions {
    method?: "GET" | "POST" | "PUT" | "PATCH" | "DELETE";
    body?: unknown;
    headers?: Record<string, string>;
}

export function useApi() {
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const controllersRef = useRef<Map<string, AbortController>>(new Map());

    // Abort all in-flight requests on unmount
    useEffect(() => {
        return () => {
            controllersRef.current.forEach((controller) => controller.abort());
            controllersRef.current.clear();
        };
    }, []);

    const performRequest = useCallback(async <T = unknown,>(endpoint: string, options: ApiOptions = {}): Promise<T> => {
        // Abort previous request to the same endpoint (deduplication)
        const key = `${options.method || "GET"}:${endpoint}`;
        const prev = controllersRef.current.get(key);
        if (prev) prev.abort();

        const controller = new AbortController();
        controllersRef.current.set(key, controller);

        setLoading(true);
        setError(null);

        try {
            const token = localStorage.getItem("token");
            const url = endpoint.startsWith("http") ? endpoint : `${API_BASE}${endpoint}`;
            const headers: Record<string, string> = {
                "Content-Type": "application/json",
                ...options.headers,
            };

            if (token) {
                headers["Authorization"] = `Bearer ${token}`;
            }

            const res = await fetch(url, {
                method: options.method || "GET",
                headers,
                body: options.body ? JSON.stringify(options.body) : undefined,
                signal: controller.signal,
            });

            if (res.status === 401) {
                localStorage.removeItem("token");
                window.location.href = "/signin";
                throw new Error("Authentication required");
            }

            if (!res.ok) {
                const errData = await res.json().catch(() => ({}));
                const detail = errData.detail;
                const normalizedMessage =
                    typeof detail === "string"
                        ? detail
                        : typeof detail?.message === "string"
                            ? detail.message
                            : typeof errData.message === "string"
                                ? errData.message
                                : `Request failed with status ${res.status}`;
                throw new Error(normalizedMessage);
            }

            const data = await res.json();
            return data as T;
        } catch (err: unknown) {
            // Ignore abort errors — they're expected when deduplicating
            if (err instanceof DOMException && err.name === "AbortError") {
                throw err;
            }
            const normalizedError = err instanceof Error ? err : new Error("An unexpected network error occurred");
            setError(normalizedError.message);
            throw normalizedError;
        } finally {
            controllersRef.current.delete(key);
            setLoading(false);
        }
    }, []);

    const request = useCallback(async <T = unknown,>(endpoint: string, options: ApiOptions = {}): Promise<T | null> => {
        try {
            return await performRequest<T>(endpoint, options);
        } catch (err: unknown) {
            // Silently ignore aborted requests
            if (err instanceof DOMException && err.name === "AbortError") return null;
            return null;
        }
    }, [performRequest]);

    const requestOrThrow = useCallback(async <T = unknown,>(endpoint: string, options: ApiOptions = {}): Promise<T> => performRequest<T>(endpoint, options), [performRequest]);

    return { request, requestOrThrow, loading, error };
}
