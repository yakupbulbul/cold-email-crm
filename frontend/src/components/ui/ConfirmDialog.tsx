"use client";

import Modal from "./Modal";
import Spinner from "./Spinner";

interface ConfirmDialogProps {
  isOpen: boolean;
  onClose: () => void;
  onConfirm: () => void | Promise<void>;
  title: string;
  message: string;
  confirmLabel?: string;
  confirmTone?: "danger" | "primary";
  loading?: boolean;
}

export default function ConfirmDialog({
  isOpen,
  onClose,
  onConfirm,
  title,
  message,
  confirmLabel = "Confirm",
  confirmTone = "primary",
  loading = false,
}: ConfirmDialogProps) {
  const confirmClass =
    confirmTone === "danger"
      ? "inline-flex items-center justify-center gap-2 rounded-2xl bg-red-600 px-5 py-2.5 text-sm font-semibold text-white transition-colors hover:bg-red-700 disabled:opacity-50"
      : "btn-primary px-5 py-2.5 text-sm disabled:opacity-50";

  return (
    <Modal isOpen={isOpen} onClose={onClose} title={title} maxWidth="max-w-sm">
      <p className="text-sm leading-6 text-[var(--muted-foreground)]">{message}</p>
      <div className="mt-6 flex items-center justify-end gap-3">
        <button
          type="button"
          onClick={onClose}
          disabled={loading}
          className="btn-secondary px-4 py-2.5 text-sm disabled:opacity-50"
        >
          Cancel
        </button>
        <button
          type="button"
          onClick={onConfirm}
          disabled={loading}
          className={confirmClass}
        >
          {loading ? <Spinner size="sm" /> : confirmLabel}
        </button>
      </div>
    </Modal>
  );
}
