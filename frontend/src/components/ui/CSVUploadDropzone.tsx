"use client";

import { useState, useCallback } from "react";
import Papa from "papaparse";
import { UploadCloud, FileType, CheckCircle } from "lucide-react";

interface DropzoneProps {
    onUploadSuccess: (headers: string[], rawRows: any[], file: File) => void;
}

export default function CSVUploadDropzone({ onUploadSuccess }: DropzoneProps) {
    const [dragging, setDragging] = useState(false);
    const [parsing, setParsing] = useState(false);
    const [error, setError] = useState<string | null>(null);

    const processFile = (file: File) => {
        if (!file.name.endsWith(".csv")) {
            setError("Please upload a valid CSV file.");
            return;
        }

        setError(null);
        setParsing(true);

        Papa.parse(file, {
            header: true,
            skipEmptyLines: true,
            complete: (results) => {
                if (results.errors.length > 0) {
                    setError("Failed to parse CSV securely. Check formatting.");
                    setParsing(false);
                    return;
                }
                const headers = results.meta.fields || [];
                onUploadSuccess(headers, results.data, file);
                setParsing(false);
            },
            error: (err) => {
                setError(err.message);
                setParsing(false);
            }
        });
    };

    const handleDrop = useCallback((e: React.DragEvent<HTMLDivElement>) => {
        e.preventDefault();
        setDragging(false);
        if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
            processFile(e.dataTransfer.files[0]);
        }
    }, []);

    return (
        <div 
            onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
            onDragLeave={() => setDragging(false)}
            onDrop={handleDrop}
            className={`w-full max-w-2xl mx-auto p-12 mt-8 border-2 border-dashed rounded-3xl flex flex-col items-center justify-center transition-all ${
                dragging ? "border-blue-500 bg-blue-50" : "border-slate-300 bg-slate-50 hover:border-slate-400"
            }`}
        >
            <div className="p-4 bg-white rounded-2xl shadow-sm mb-6">
                {parsing ? <FileType className="animate-pulse text-blue-500" size={40} /> : <UploadCloud className="text-blue-500" size={40} />}
            </div>
            
            <h3 className="text-xl font-bold text-slate-800 mb-2">
                {parsing ? "Parsing Records..." : "Drag & Drop CSV File"}
            </h3>
            <p className="text-sm text-slate-500 text-center max-w-sm mb-6">
                Upload your raw lead contacts in CSV format. The system will automatically map the headers and validate entries securely.
            </p>

            <label className="cursor-pointer bg-slate-900 hover:bg-slate-800 text-white px-6 py-2.5 rounded-xl font-medium transition-colors shadow-lg shadow-slate-900/20 active:scale-95">
                Browse Files
                <input 
                    type="file" 
                    accept=".csv" 
                    className="hidden" 
                    onChange={(e) => e.target.files && processFile(e.target.files[0])}
                />
            </label>

            {error && (
                <div className="mt-4 p-3 bg-red-50 text-red-600 rounded-lg text-sm font-medium w-full text-center">
                    {error}
                </div>
            )}
        </div>
    );
}
