"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import {
  Activity,
  BookOpenCheck,
  CalendarClock,
  CheckCircle2,
  ClipboardList,
  Flag,
  NotebookPen,
  Plus,
  RefreshCw,
  ShieldAlert,
} from "lucide-react";

import Spinner from "@/components/ui/Spinner";
import { AlertBanner, EmptyState, FieldGroup, MetricCard, PageHeader, SectionTitle, StatusBadge, SurfaceCard } from "@/components/ui/primitives";
import { useApiService } from "@/services/api";
import type { CommandCenterSummary, OperatorActionLog, OperatorTask, OperatorTaskCategory, OperatorTaskPriority, OperatorTaskStatus, Runbook } from "@/types/models";

const categoryOptions: OperatorTaskCategory[] = ["campaign", "inbox", "deliverability", "warmup", "provider", "domain", "mailbox", "system", "manual"];
const priorityOptions: OperatorTaskPriority[] = ["critical", "high", "normal", "low"];
const statusOptions: OperatorTaskStatus[] = ["todo", "in_progress", "blocked", "done", "dismissed"];

const todayKey = () => new Date().toISOString().slice(0, 10);

function formatDate(value?: string | null) {
  if (!value) return "Not scheduled";
  return new Date(value).toLocaleString();
}

function entityHref(taskOrAction: { related_entity_type?: string | null; related_entity_id?: string | null }) {
  const id = taskOrAction.related_entity_id;
  switch (taskOrAction.related_entity_type) {
    case "campaign":
      return id ? `/campaigns?campaign=${id}` : "/campaigns";
    case "mailbox":
      return "/mailboxes";
    case "domain":
      return "/domains";
    case "contact":
      return "/contacts";
    case "list":
      return "/lists";
    default:
      return null;
  }
}

function priorityTone(priority: OperatorTaskPriority): "neutral" | "success" | "warning" | "danger" | "info" {
  if (priority === "critical") return "danger";
  if (priority === "high") return "warning";
  if (priority === "low") return "neutral";
  return "info";
}

function statusTone(status: OperatorTaskStatus): "neutral" | "success" | "warning" | "danger" | "info" {
  if (status === "done") return "success";
  if (status === "blocked") return "danger";
  if (status === "in_progress") return "info";
  if (status === "dismissed") return "neutral";
  return "warning";
}

function resultTone(result: string): "neutral" | "success" | "warning" | "danger" | "info" {
  if (result === "success") return "success";
  if (result === "failed") return "danger";
  if (result === "blocked") return "warning";
  if (result === "skipped") return "neutral";
  return "info";
}

export default function CommandCenterPage() {
  const {
    getCommandCenterSummary,
    getOperatorTasks,
    getOperatorActions,
    createOperatorTask,
    updateOperatorTask,
    getDailyNotes,
    upsertDailyNote,
    getRunbooks,
    createRunbook,
    startRunbook,
  } = useApiService();

  const [summary, setSummary] = useState<CommandCenterSummary | null>(null);
  const [tasks, setTasks] = useState<OperatorTask[]>([]);
  const [actions, setActions] = useState<OperatorActionLog[]>([]);
  const [runbooks, setRunbooks] = useState<Runbook[]>([]);
  const [dailyNote, setDailyNote] = useState("");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [banner, setBanner] = useState<string | null>(null);
  const [taskForm, setTaskForm] = useState({
    title: "",
    description: "",
    category: "manual" as OperatorTaskCategory,
    priority: "normal" as OperatorTaskPriority,
    due_at: "",
  });
  const [runbookForm, setRunbookForm] = useState({
    name: "",
    description: "",
    category: "manual" as OperatorTaskCategory,
    steps: "",
  });

  const loadData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [summaryData, taskData, actionData, noteData, runbookData] = await Promise.all([
        getCommandCenterSummary(),
        getOperatorTasks("active_only=true"),
        getOperatorActions("limit=80"),
        getDailyNotes(7),
        getRunbooks(),
      ]);
      setSummary(summaryData);
      setTasks(taskData || []);
      setActions(actionData || []);
      setRunbooks(runbookData || []);
      const todayNote = (noteData || []).find((note) => note.note_date === todayKey());
      setDailyNote(todayNote?.content || "");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Command Center could not be loaded.");
    } finally {
      setLoading(false);
    }
  }, [getCommandCenterSummary, getDailyNotes, getOperatorActions, getOperatorTasks, getRunbooks]);

  useEffect(() => {
    void loadData();
  }, [loadData]);

  async function handleCreateTask(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!taskForm.title.trim()) return;
    setSaving("task");
    setBanner(null);
    try {
      await createOperatorTask({
        title: taskForm.title.trim(),
        description: taskForm.description.trim() || null,
        category: taskForm.category,
        priority: taskForm.priority,
        due_at: taskForm.due_at ? new Date(taskForm.due_at).toISOString() : null,
      });
      setTaskForm({ title: "", description: "", category: "manual", priority: "normal", due_at: "" });
      setBanner("Task created.");
      await loadData();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Task could not be created.");
    } finally {
      setSaving(null);
    }
  }

  async function handleTaskStatus(task: OperatorTask, status: OperatorTaskStatus) {
    setSaving(task.id);
    try {
      await updateOperatorTask(task.id, { status });
      await loadData();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Task could not be updated.");
    } finally {
      setSaving(null);
    }
  }

  async function handleSaveNote() {
    setSaving("note");
    setBanner(null);
    try {
      await upsertDailyNote(todayKey(), dailyNote);
      setBanner("Daily note saved.");
      await loadData();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Daily note could not be saved.");
    } finally {
      setSaving(null);
    }
  }

  async function handleCreateRunbook(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!runbookForm.name.trim()) return;
    setSaving("runbook");
    setBanner(null);
    try {
      const steps = runbookForm.steps
        .split("\n")
        .map((line) => line.trim())
        .filter(Boolean)
        .map((title, index) => ({ step_order: index + 1, title, default_status: "todo" as OperatorTaskStatus }));
      await createRunbook({
        name: runbookForm.name.trim(),
        description: runbookForm.description.trim() || null,
        category: runbookForm.category,
        steps,
      });
      setRunbookForm({ name: "", description: "", category: "manual", steps: "" });
      setBanner("Runbook created.");
      await loadData();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Runbook could not be created.");
    } finally {
      setSaving(null);
    }
  }

  async function handleStartRunbook(runbook: Runbook) {
    setSaving(`runbook-${runbook.id}`);
    setBanner(null);
    try {
      const created = await startRunbook(runbook.id);
      setBanner(`${created.length} task${created.length === 1 ? "" : "s"} created from ${runbook.name}.`);
      await loadData();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Runbook could not be started.");
    } finally {
      setSaving(null);
    }
  }

  const nextActions = tasks.filter((task) => !["done", "dismissed"].includes(task.status));
  const stats = summary?.stats || {};

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Internal operations"
        title="Command Center"
        description="Plan the day, track operator actions, keep runbooks close, and connect manual work to real campaign, inbox, warm-up, and provider activity."
        actions={
          <button
            type="button"
            onClick={() => void loadData()}
            className="inline-flex items-center gap-2 rounded-xl border border-slate-200 bg-white px-4 py-2 text-sm font-semibold text-slate-700 shadow-sm hover:bg-slate-50"
          >
            <RefreshCw size={16} /> Refresh
          </button>
        }
      />

      {error ? <AlertBanner tone="danger" title="Command Center error">{error}</AlertBanner> : null}
      {banner ? <AlertBanner tone="success">{banner}</AlertBanner> : null}

      {loading ? (
        <div className="flex justify-center py-20"><Spinner size="lg" /></div>
      ) : (
        <>
          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-5">
            <MetricCard title="Todo" value={stats.todo || 0} detail="Open planned tasks" icon={ClipboardList} tone="warning" />
            <MetricCard title="In Progress" value={stats.in_progress || 0} detail="Work currently active" icon={Activity} tone="info" />
            <MetricCard title="Blocked" value={stats.blocked || 0} detail="Needs attention" icon={ShieldAlert} tone="danger" />
            <MetricCard title="Done Today" value={stats.done_today || 0} detail="Completed tasks" icon={CheckCircle2} tone="success" />
            <MetricCard title="Actions Today" value={stats.actions_today || 0} detail="Logged operations" icon={Flag} tone="neutral" />
          </div>

          <div className="grid gap-6 xl:grid-cols-[1.1fr_0.9fr]">
            <SurfaceCard className="p-6">
              <SectionTitle title="Today and Next Actions" description="Create manual tasks and update the operational queue as you test campaigns, inbox, providers, and warm-up." />
              <form onSubmit={handleCreateTask} className="grid gap-3 rounded-2xl border border-slate-200 bg-slate-50 p-4 md:grid-cols-[1.4fr_0.8fr_0.7fr_0.7fr_auto]">
                <input
                  value={taskForm.title}
                  onChange={(event) => setTaskForm({ ...taskForm, title: event.target.value })}
                  placeholder="Add a task, e.g. Test 9 April campaign"
                  className="rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm outline-none focus:border-slate-400"
                />
                <select value={taskForm.category} onChange={(event) => setTaskForm({ ...taskForm, category: event.target.value as OperatorTaskCategory })} className="rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm">
                  {categoryOptions.map((category) => <option key={category} value={category}>{category}</option>)}
                </select>
                <select value={taskForm.priority} onChange={(event) => setTaskForm({ ...taskForm, priority: event.target.value as OperatorTaskPriority })} className="rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm">
                  {priorityOptions.map((priority) => <option key={priority} value={priority}>{priority}</option>)}
                </select>
                <input
                  type="datetime-local"
                  value={taskForm.due_at}
                  onChange={(event) => setTaskForm({ ...taskForm, due_at: event.target.value })}
                  className="rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm"
                />
                <button disabled={saving === "task" || !taskForm.title.trim()} className="inline-flex items-center justify-center gap-2 rounded-xl bg-slate-900 px-4 py-2 text-sm font-semibold text-white disabled:bg-slate-400">
                  {saving === "task" ? <Spinner size="sm" /> : <Plus size={16} />} Add
                </button>
              </form>

              <div className="mt-5 space-y-3">
                {nextActions.length === 0 ? (
                  <EmptyState title="No active tasks yet" description="Add a task or start a runbook to create a concrete operating plan for today." icon={ClipboardList} />
                ) : (
                  nextActions.map((task) => {
                    const href = entityHref(task);
                    return (
                      <div key={task.id} className="rounded-2xl border border-slate-200 bg-white p-4">
                        <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
                          <div className="min-w-0">
                            <div className="flex flex-wrap items-center gap-2">
                              <StatusBadge tone={priorityTone(task.priority)}>{task.priority}</StatusBadge>
                              <StatusBadge tone={statusTone(task.status)}>{task.status.replace("_", " ")}</StatusBadge>
                              <StatusBadge>{task.category}</StatusBadge>
                            </div>
                            <h3 className="mt-3 font-semibold text-slate-900">{task.title}</h3>
                            {task.description ? <p className="mt-1 text-sm text-slate-500">{task.description}</p> : null}
                            <div className="mt-2 text-xs text-slate-400">Due: {formatDate(task.due_at)}</div>
                            {href ? <Link href={href} className="mt-2 inline-block text-xs font-semibold text-sky-700 hover:text-sky-900">Open related context</Link> : null}
                          </div>
                          <div className="flex flex-wrap gap-2">
                            {statusOptions.map((status) => (
                              <button
                                key={status}
                                type="button"
                                disabled={saving === task.id || task.status === status}
                                onClick={() => void handleTaskStatus(task, status)}
                                className="rounded-xl border border-slate-200 px-3 py-1.5 text-xs font-semibold text-slate-600 hover:bg-slate-50 disabled:opacity-40"
                              >
                                {status.replace("_", " ")}
                              </button>
                            ))}
                          </div>
                        </div>
                      </div>
                    );
                  })
                )}
              </div>
            </SurfaceCard>

            <div className="space-y-6">
              <SurfaceCard className="p-6">
                <SectionTitle title="Daily Notes" description="Write what you tested, what failed, and what needs checking next." />
                <textarea
                  value={dailyNote}
                  onChange={(event) => setDailyNote(event.target.value)}
                  rows={8}
                  placeholder="Today: tested direct send, checked inbox sync, campaign retry still needs validation..."
                  className="w-full rounded-2xl border border-slate-200 bg-white px-4 py-3 text-sm outline-none focus:border-slate-400"
                />
                <button
                  type="button"
                  onClick={() => void handleSaveNote()}
                  disabled={saving === "note"}
                  className="mt-4 inline-flex items-center gap-2 rounded-xl bg-slate-900 px-4 py-2 text-sm font-semibold text-white disabled:bg-slate-400"
                >
                  {saving === "note" ? <Spinner size="sm" /> : <NotebookPen size={16} />} Save today’s note
                </button>
              </SurfaceCard>

              <SurfaceCard className="p-6">
                <SectionTitle title="Runbooks" description="Create reusable operating checklists, then start them as real tasks." />
                <form onSubmit={handleCreateRunbook} className="space-y-3 rounded-2xl border border-slate-200 bg-slate-50 p-4">
                  <FieldGroup label="Runbook name">
                    <input value={runbookForm.name} onChange={(event) => setRunbookForm({ ...runbookForm, name: event.target.value })} className="w-full rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm" placeholder="Campaign launch checklist" />
                  </FieldGroup>
                  <FieldGroup label="Steps" hint="One step per line. They become tasks when the runbook starts.">
                    <textarea value={runbookForm.steps} onChange={(event) => setRunbookForm({ ...runbookForm, steps: event.target.value })} rows={4} className="w-full rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm" placeholder="Run dry-run&#10;Check deliverability blockers&#10;Start campaign pass" />
                  </FieldGroup>
                  <div className="grid gap-3 sm:grid-cols-[1fr_auto]">
                    <select value={runbookForm.category} onChange={(event) => setRunbookForm({ ...runbookForm, category: event.target.value as OperatorTaskCategory })} className="rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm">
                      {categoryOptions.map((category) => <option key={category} value={category}>{category}</option>)}
                    </select>
                    <button disabled={saving === "runbook" || !runbookForm.name.trim()} className="inline-flex items-center justify-center gap-2 rounded-xl bg-white px-4 py-2 text-sm font-semibold text-slate-800 shadow-sm disabled:opacity-50">
                      {saving === "runbook" ? <Spinner size="sm" /> : <BookOpenCheck size={16} />} Create
                    </button>
                  </div>
                </form>

                <div className="mt-4 space-y-3">
                  {runbooks.length === 0 ? (
                    <EmptyState title="No runbooks yet" description="Create your first checklist for campaign launch, Google Workspace setup, inbox sync, or warm-up testing." icon={BookOpenCheck} />
                  ) : (
                    runbooks.map((runbook) => (
                      <div key={runbook.id} className="rounded-2xl border border-slate-200 bg-white p-4">
                        <div className="flex items-start justify-between gap-3">
                          <div>
                            <div className="flex flex-wrap items-center gap-2">
                              <StatusBadge>{runbook.category}</StatusBadge>
                              <span className="text-xs text-slate-400">{runbook.steps.length} steps</span>
                            </div>
                            <h3 className="mt-2 font-semibold text-slate-900">{runbook.name}</h3>
                            {runbook.description ? <p className="mt-1 text-sm text-slate-500">{runbook.description}</p> : null}
                          </div>
                          <button
                            type="button"
                            onClick={() => void handleStartRunbook(runbook)}
                            disabled={saving === `runbook-${runbook.id}` || !runbook.is_active}
                            className="rounded-xl bg-slate-900 px-3 py-2 text-xs font-semibold text-white disabled:bg-slate-400"
                          >
                            {saving === `runbook-${runbook.id}` ? "Starting..." : "Start"}
                          </button>
                        </div>
                      </div>
                    ))
                  )}
                </div>
              </SurfaceCard>
            </div>
          </div>

          <SurfaceCard className="p-6">
            <SectionTitle title="Operational Timeline" description="Real system and operator actions from campaigns, sending, inbox, warm-up, provider checks, domains, and mailboxes." />
            {actions.length === 0 ? (
              <EmptyState title="No operational actions logged yet" description="Actions appear here after you start campaigns, run dry-runs, send email, sync inboxes, check providers, or create manual tasks." icon={CalendarClock} />
            ) : (
              <div className="divide-y divide-slate-100">
                {actions.map((action) => {
                  const href = entityHref(action);
                  return (
                    <div key={action.id} className="grid gap-3 py-4 md:grid-cols-[10rem_1fr_auto] md:items-start">
                      <div className="text-xs text-slate-400">{formatDate(action.created_at)}</div>
                      <div>
                        <div className="flex flex-wrap items-center gap-2">
                          <StatusBadge tone={resultTone(action.result)}>{action.result}</StatusBadge>
                          <StatusBadge>{action.source}</StatusBadge>
                          <span className="text-xs font-semibold uppercase tracking-wide text-slate-400">{action.action_type.replaceAll("_", " ")}</span>
                        </div>
                        <p className="mt-2 text-sm font-medium text-slate-800">{action.message}</p>
                      </div>
                      {href ? <Link href={href} className="text-sm font-semibold text-sky-700 hover:text-sky-900">Open context</Link> : null}
                    </div>
                  );
                })}
              </div>
            )}
          </SurfaceCard>
        </>
      )}
    </div>
  );
}
