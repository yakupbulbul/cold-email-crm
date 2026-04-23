"use client";

import React, { createContext, useContext, useState, useEffect, useCallback, useRef } from "react";
import { useRouter, usePathname } from "next/navigation";

interface User {
    email: string;
    full_name?: string;
    is_admin: boolean;
}

interface AuthContextType {
    user: User | null;
    token: string | null;
    isLoading: boolean;
    login: (token: string) => Promise<void>;
    logout: () => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);
const PUBLIC_ROUTES = new Set(["/", "/signin", "/login"]);

export function AuthProvider({ children }: { children: React.ReactNode }) {
    const [user, setUser] = useState<User | null>(null);
    const [token, setToken] = useState<string | null>(null);
    const [isLoading, setIsLoading] = useState(true);
    const isMountedRef = useRef(true);
    const router = useRouter();
    const pathname = usePathname();
    const isPublicRoute = PUBLIC_ROUTES.has(pathname || "");

    useEffect(() => {
        return () => {
            isMountedRef.current = false;
        };
    }, []);

    const fetchMe = useCallback(async (authToken: string) => {
        try {
            const API_URL = process.env.NEXT_PUBLIC_API_URL || "/api/v1";
            const res = await fetch(`${API_URL}/auth/me`, {
                headers: {
                    "Authorization": `Bearer ${authToken}`
                }
            });
            if (res.ok) {
                const userData = await res.json();
                if (isMountedRef.current) {
                    setUser(userData);
                }
            } else {
                // If token is invalid, clear it
                localStorage.removeItem("token");
                if (isMountedRef.current) {
                    setToken(null);
                    setUser(null);
                }
            }
        } catch {
            // network error during auth check — token will be cleared if invalid
        } finally {
            if (isMountedRef.current) {
                setIsLoading(false);
            }
        }
    }, []);

    useEffect(() => {
        const storedToken = localStorage.getItem("token");
        if (storedToken) {
            setToken(storedToken);
            fetchMe(storedToken);
        } else {
            setIsLoading(false);
        }
    }, [fetchMe]);

    useEffect(() => {
        if (!isLoading && !token && !isPublicRoute) {
            router.push("/signin");
        }
    }, [isLoading, isPublicRoute, token, router]);

    const login = async (newToken: string) => {
        localStorage.setItem("token", newToken);
        if (isMountedRef.current) {
            setToken(newToken);
        }
        await fetchMe(newToken);
        router.replace("/dashboard");
    };

    const logout = () => {
        localStorage.removeItem("token");
        if (isMountedRef.current) {
            setToken(null);
            setUser(null);
        }
        router.replace("/signin");
    };

    return (
        <AuthContext.Provider value={{ user, token, isLoading, login, logout }}>
            {children}
        </AuthContext.Provider>
    );
}

export function useAuth() {
    const context = useContext(AuthContext);
    if (context === undefined) {
        throw new Error("useAuth must be used within an AuthProvider");
    }
    return context;
}
