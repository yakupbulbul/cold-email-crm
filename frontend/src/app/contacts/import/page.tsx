"use client";

import { useState } from "react";
import CSVUploadDropzone from "@/components/ui/CSVUploadDropzone";
import { useApi } from "@/hooks/useApi";
import { CheckCircle, AlertTriangle } from "lucide-react";

type ImportValidationResult = {
    valid_rows: number;
    invalid_rows: number;
    duplicate_rows: number;
};

type ImportConfirmResult = {
    status?: string;
};

export default function LeadImportPage() {
    const { request, loading } = useApi();
    const [step, setStep] = useState<1 | 2 | 3>(1);
    
    // Upload state
    const [headers, setHeaders] = useState<string[]>([]);
    const [jobId, setJobId] = useState<string | null>(null);
    
    // Mapping state
    const [mappings, setMappings] = useState<Record<string, string>>({
        email: "",
        first_name: "",
        last_name: "",
        company: ""
    });

    // Validation State
    const [validationResult, setValidationResult] = useState<ImportValidationResult | null>(null);

    const handleUploadSuccess = async (csvHeaders: string[], _rawRows: unknown[], uploadedFile: File) => {
        setHeaders(csvHeaders);
        
        // Auto-map common names
        const newMap = { ...mappings };
        csvHeaders.forEach(h => {
            const hLow = h.toLowerCase();
            if (hLow.includes("email")) newMap.email = h;
            if (hLow.includes("first")) newMap.first_name = h;
            if (hLow.includes("last")) newMap.last_name = h;
            if (hLow.includes("company")) newMap.company = h;
        });
        setMappings(newMap);

        // Upload to backend to generate LeadImportJob
        const formData = new FormData();
        formData.append("file", uploadedFile);
        
        try {
            const token = localStorage.getItem("token");
            const apiBase = (process.env.NEXT_PUBLIC_API_URL || "/api/v1");
            const res = await fetch(`${apiBase}/leads/import/csv`, {
                method: "POST",
                headers: token ? { Authorization: `Bearer ${token}` } : {},
                body: formData  // Do NOT set Content-Type - browser sets multipart boundary automatically
            });
            const data = await res.json();
            setJobId(data.job_id);
            setStep(2);
        } catch {
            // upload error is surfaced via missing job state
        }
    };

    const confirmMapping = async () => {
        if (!jobId || !mappings.email) return;
        
        const data = await request<ImportValidationResult>(`/leads/import/${jobId}/map`, {
            method: "POST",
            body: { field_mappings: mappings }
        });

        if (data) {
            setValidationResult(data);
            setStep(3);
        }
    };

    const executeImport = async () => {
        if (!jobId) return;
        const data = await request<ImportConfirmResult>(`/leads/import/${jobId}/confirm`, {
            method: "POST"
        });
        if (data && data.status === "completed") {
            window.location.href = `/contacts?source_job=${jobId}`;
        }
    };

    return (
        <div className="space-y-6 animate-fade-in relative min-h-screen">
            <h1 className="text-3xl font-bold text-slate-800 tracking-tight">Bulk Bulk Import</h1>
            
            {/* Stepper */}
            <div className="flex items-center space-x-4 mb-8">
                <div className={`px-4 py-2 rounded-lg font-bold text-sm ${step >= 1 ? 'bg-blue-600 text-white' : 'bg-slate-200 text-slate-500'}`}>1. Upload</div>
                <div className={`w-8 h-1 ${step >= 2 ? 'bg-blue-600' : 'bg-slate-200'} rounded-full`}></div>
                <div className={`px-4 py-2 rounded-lg font-bold text-sm ${step >= 2 ? 'bg-blue-600 text-white' : 'bg-slate-200 text-slate-500'}`}>2. Map Columns</div>
                <div className={`w-8 h-1 ${step >= 3 ? 'bg-blue-600' : 'bg-slate-200'} rounded-full`}></div>
                <div className={`px-4 py-2 rounded-lg font-bold text-sm ${step >= 3 ? 'bg-blue-600 text-white' : 'bg-slate-200 text-slate-500'}`}>3. Review & Import</div>
            </div>

            {step === 1 && (
                <CSVUploadDropzone onUploadSuccess={handleUploadSuccess} />
            )}

            {step === 2 && (
                <div className="bg-white p-8 rounded-2xl border border-slate-200 shadow-sm max-w-3xl">
                    <h3 className="text-xl font-bold text-slate-800 mb-6">Map System Variables</h3>
                    <div className="space-y-5">
                        {Object.keys(mappings).map(sysField => (
                            <div key={sysField} className="flex items-center justify-between p-4 bg-slate-50 rounded-xl border border-slate-100">
                                <span className="font-semibold text-slate-700 capitalize">{sysField.replace("_", " ")}</span>
                                <select 
                                    className="px-4 py-2 rounded-lg border border-slate-300 bg-white font-medium focus:ring-2 focus:ring-blue-500 outline-none w-64"
                                    value={mappings[sysField]}
                                    onChange={e => setMappings({...mappings, [sysField]: e.target.value})}
                                >
                                    <option value="">-- Ignore --</option>
                                    {headers.map(h => <option key={h} value={h}>{h}</option>)}
                                </select>
                            </div>
                        ))}
                    </div>
                    <div className="mt-8 flex justify-end">
                        <button 
                            disabled={!mappings.email || loading}
                            onClick={confirmMapping}
                            className="bg-blue-600 disabled:bg-slate-400 hover:bg-blue-700 text-white px-8 py-3 rounded-xl font-bold transition-all shadow-lg active:scale-95"
                        >
                            {loading ? "Validating Records..." : "Validate Data Sequence"}
                        </button>
                    </div>
                </div>
            )}

            {step === 3 && validationResult && (
                <div className="bg-white p-8 rounded-2xl border border-slate-200 shadow-sm max-w-3xl">
                    <div className="flex items-center gap-3 mb-6">
                        <CheckCircle className="text-green-500" size={32} />
                        <h3 className="text-2xl font-bold text-slate-800">Validation Complete</h3>
                    </div>
                    
                    <div className="grid grid-cols-3 gap-4 mb-8">
                        <div className="bg-green-50 p-4 rounded-xl border border-green-100">
                            <div className="text-sm font-bold text-green-600 uppercase mb-1">Valid Rows</div>
                            <div className="text-3xl font-extrabold text-green-700">{validationResult.valid_rows}</div>
                        </div>
                        <div className="bg-red-50 p-4 rounded-xl border border-red-100">
                            <div className="text-sm font-bold text-red-600 uppercase mb-1">Invalid</div>
                            <div className="text-3xl font-extrabold text-red-700">{validationResult.invalid_rows}</div>
                        </div>
                        <div className="bg-yellow-50 p-4 rounded-xl border border-yellow-100">
                            <div className="text-sm font-bold text-yellow-600 uppercase mb-1">Duplicates</div>
                            <div className="text-3xl font-extrabold text-yellow-700">{validationResult.duplicate_rows}</div>
                        </div>
                    </div>

                    <div className="p-4 bg-slate-50 text-slate-600 text-sm font-medium rounded-xl border border-slate-200 mb-8 flex items-start gap-3">
                        <AlertTriangle className="text-yellow-500 shrink-0" size={20} />
                        Only the Valid records will be imported into the Contact ecosystem. Invalid and Duplicate rows will be safely excluded from the database to prevent infrastructure contamination.
                    </div>

                    <div className="flex justify-end gap-4">
                        <button onClick={() => setStep(2)} className="px-6 py-3 font-bold text-slate-500 hover:text-slate-800 transition-colors">
                            Remap Data
                        </button>
                        <button onClick={executeImport} disabled={loading || validationResult.valid_rows === 0} className="bg-slate-900 hover:bg-black text-white px-8 py-3 rounded-xl font-bold transition-all shadow-lg active:scale-95">
                            {loading ? "Importing..." : "Execute Final Import"}
                        </button>
                    </div>
                </div>
            )}
        </div>
    );
}
