import { useState, useCallback } from "react";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8050/api/v1";

interface ApiOptions {
    method?: "GET" | "POST" | "PUT" | "DELETE";
    body?: any;
    headers?: Record<string, string>;
}

export function useApi() {
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);

    const request = useCallback(async <T = any,>(endpoint: string, options: ApiOptions = {}): Promise<T | null> => {
        setLoading(true);
        setError(null);
        
        try {
            const url = endpoint.startsWith("http") ? endpoint : `${API_BASE}${endpoint}`;
            const headers = {
                "Content-Type": "application/json",
                ...options.headers,
                // Add Authorization JWT headers here in Phase 11
            };

            const res = await fetch(url, {
                method: options.method || "GET",
                headers,
                body: options.body ? JSON.stringify(options.body) : undefined,
            });

            if (!res.ok) {
                const errData = await res.json().catch(() => ({}));
                throw new Error(errData.detail || `Request failed with status ${res.status}`);
            }

            const data = await res.json();
            return data as T;
        } catch (err: any) {
            setError(err.message || "An unexpected network error occurred");
            return null;
        } finally {
            setLoading(false);
        }
    }, []);

    return { request, loading, error };
}
