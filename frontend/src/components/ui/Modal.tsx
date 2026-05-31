"use client";

import { X } from "lucide-react";
import { useEffect } from "react";

interface ModalProps {
    isOpen: boolean;
    onClose: () => void;
    title: string;
    children: React.ReactNode;
    maxWidth?: string;
}

export default function Modal({ isOpen, onClose, title, children, maxWidth = "max-w-md" }: ModalProps) {
    useEffect(() => {
        if (isOpen) {
            document.body.style.overflow = "hidden";
        } else {
            document.body.style.overflow = "unset";
        }
        return () => { document.body.style.overflow = "unset"; };
    }, [isOpen]);

    if (!isOpen) return null;

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
            <div className="absolute inset-0 bg-[var(--sidebar)]/60 backdrop-blur-sm transition-opacity" onClick={onClose} />
            <div className={`relative w-full ${maxWidth} bg-[var(--surface)] rounded-2xl shadow-2xl overflow-hidden transform transition-all`}>
                <div className="px-6 py-4 border-b border-[var(--surface-muted)] flex items-center justify-between bg-[var(--surface-muted)]/50">
                    <h3 className="text-lg font-bold text-[var(--foreground)]">{title}</h3>
                    <button 
                        onClick={onClose}
                        className="p-2 text-[var(--muted-foreground)] hover:text-[var(--muted-foreground)] hover:bg-[var(--surface-muted)] rounded-xl transition-colors"
                    >
                        <X size={20} />
                    </button>
                </div>
                <div className="p-6">
                    {children}
                </div>
            </div>
        </div>
    );
}
