"use client";

import { Loader2 } from "lucide-react";

export default function Spinner({ size = "md" }: { size?: "sm" | "md" | "lg" }) {
    const sizeClasses = {
        sm: "w-4 h-4",
        md: "w-8 h-8",
        lg: "w-12 h-12"
    };

    return (
        <div className="flex items-center justify-center w-full h-full p-4">
            <Loader2 className={`animate-spin text-blue-600 ${sizeClasses[size]}`} />
        </div>
    );
}
