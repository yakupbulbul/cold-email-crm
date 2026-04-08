"use client";

import { useEffect, useMemo, useState } from "react";
import { AlertCircle, ListPlus, LoaderCircle, Pencil, Trash2, Users, X } from "lucide-react";

import Spinner from "@/components/ui/Spinner";
import Table, { TableCell, TableRow } from "@/components/ui/Table";
import { useApiService } from "@/services/api";
import { Contact, LeadList, LeadListLeadResponse } from "@/types/models";

type EditState = {
  id: string;
  name: string;
  description: string;
};

export default function ListsPage() {
  const {
    getLists,
    getLeads,
    getListLeads,
    createList,
    updateList,
    deleteList,
    addLeadToList,
    removeLeadFromList,
    loading,
    error,
  } = useApiService();

  const [lists, setLists] = useState<LeadList[]>([]);
  const [leads, setLeads] = useState<Contact[]>([]);
  const [selectedListId, setSelectedListId] = useState<string | null>(null);
  const [selectedListLeads, setSelectedListLeads] = useState<LeadListLeadResponse | null>(null);
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [banner, setBanner] = useState<string | null>(null);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [editState, setEditState] = useState<EditState | null>(null);
  const [selectedLeadId, setSelectedLeadId] = useState("");
  const [busyId, setBusyId] = useState<string | null>(null);

  useEffect(() => {
    const load = async () => {
      const [listData, leadData] = await Promise.all([getLists(), getLeads()]);
      if (listData) setLists(listData);
      if (leadData) {
        setLeads(leadData);
        setSelectedLeadId((current) => current || leadData[0]?.id || "");
      }
    };
    void load();
  }, [getLists, getLeads]);

  useEffect(() => {
    if (!selectedListId) {
      setSelectedListLeads(null);
      return;
    }
    void (async () => {
      const detail = await getListLeads(selectedListId);
      if (detail) setSelectedListLeads(detail);
    })();
  }, [selectedListId, getListLeads]);

  const availableLeads = useMemo(() => {
    const currentIds = new Set(selectedListLeads?.leads.map((lead) => lead.id) || []);
    return leads.filter((lead) => !currentIds.has(lead.id));
  }, [leads, selectedListLeads]);

  const refreshLists = async (focusListId?: string | null) => {
    const listData = await getLists();
    if (listData) {
      setLists(listData);
      if (focusListId) {
        setSelectedListId(focusListId);
        const detail = await getListLeads(focusListId);
        if (detail) setSelectedListLeads(detail);
      } else if (selectedListId) {
        const detail = await getListLeads(selectedListId);
        if (detail) setSelectedListLeads(detail);
      }
    }
  };

  const handleCreate = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setSubmitError(null);
    if (!name.trim()) {
      setSubmitError("List name is required.");
      return;
    }
    try {
      const created = await createList({ name: name.trim(), description: description.trim() || undefined });
      setName("");
      setDescription("");
      setBanner(`List ${created.name} created.`);
      await refreshLists(created.id);
    } catch (err) {
      setSubmitError(err instanceof Error ? err.message : "List create failed.");
    }
  };

  const handleSaveEdit = async () => {
    if (!editState) return;
    setBusyId(editState.id);
    try {
      const updated = await updateList(editState.id, {
        name: editState.name.trim(),
        description: editState.description.trim(),
      });
      setEditState(null);
      setBanner(`List ${updated.name} updated.`);
      await refreshLists(updated.id);
    } catch (err) {
      setBanner(err instanceof Error ? err.message : "List update failed.");
    } finally {
      setBusyId(null);
    }
  };

  const handleBeginEdit = (list: LeadList) => {
    setSelectedListId(list.id);
    setEditState({
      id: list.id,
      name: list.name,
      description: list.description || "",
    });
  };

  const handleDelete = async (listId: string) => {
    setBusyId(listId);
    try {
      await deleteList(listId);
      setBanner("List deleted.");
      if (selectedListId === listId) {
        setSelectedListId(null);
        setSelectedListLeads(null);
      }
      await refreshLists();
    } finally {
      setBusyId(null);
    }
  };

  const handleAddLead = async () => {
    if (!selectedListId || !selectedLeadId) return;
    setBusyId(selectedListId);
    try {
      await addLeadToList(selectedListId, selectedLeadId);
      setBanner("Lead added to list.");
      await refreshLists(selectedListId);
    } finally {
      setBusyId(null);
    }
  };

  const handleRemoveLead = async (leadId: string) => {
    if (!selectedListId) return;
    setBusyId(leadId);
    try {
      await removeLeadFromList(selectedListId, leadId);
      setBanner("Lead removed from list.");
      await refreshLists(selectedListId);
    } finally {
      setBusyId(null);
    }
  };

  return (
    <div className="space-y-6 animate-fade-in">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight text-slate-800">Lead Lists</h1>
          <p className="mt-2 text-sm font-medium text-slate-500">Create reusable static lead groups and attach them to multiple campaigns.</p>
        </div>
      </div>

      {banner && (
        <div className="rounded-2xl border border-blue-100 bg-blue-50 px-5 py-4 text-sm font-medium text-blue-700">
          {banner}
        </div>
      )}

      <form onSubmit={handleCreate} className="grid gap-4 rounded-2xl border border-slate-200 bg-white p-5 shadow-sm md:grid-cols-2">
        <div>
          <label className="mb-2 block text-sm font-semibold text-slate-700">List Name</label>
          <input value={name} onChange={(event) => setName(event.target.value)} className="w-full rounded-xl border border-slate-200 px-4 py-3" placeholder="Verified High Score" />
        </div>
        <div>
          <label className="mb-2 block text-sm font-semibold text-slate-700">Description</label>
          <input value={description} onChange={(event) => setDescription(event.target.value)} className="w-full rounded-xl border border-slate-200 px-4 py-3" placeholder="Reusable list for strong verified leads" />
        </div>
        <div className="md:col-span-2 flex items-center justify-between gap-4">
          {submitError ? <div className="text-sm font-medium text-red-700">{submitError}</div> : <div className="text-sm text-slate-500">Static lists persist and can be reused across campaigns.</div>}
          <button type="submit" className="inline-flex items-center gap-2 rounded-xl bg-slate-900 px-5 py-3 font-bold text-white">
            <ListPlus size={18} /> Create List
          </button>
        </div>
      </form>

      {error && lists.length === 0 ? (
        <div className="rounded-2xl border border-red-200 bg-red-50 py-16 text-center text-red-700">
          <AlertCircle className="mx-auto mb-4" size={32} />
          Failed to load lists
        </div>
      ) : loading && lists.length === 0 ? (
        <div className="flex h-64 items-center justify-center rounded-2xl border border-slate-200 bg-white"><Spinner size="lg" /></div>
      ) : (
        <div className="grid gap-6 xl:grid-cols-[1.1fr,0.9fr]">
          <div className="space-y-4">
            <Table columns={["Name", "Type", "Leads", "Reachable", "Suppressed", "Actions"]}>
              {lists.map((list) => (
                <TableRow key={list.id}>
                  <TableCell>
                    <button className="text-left" onClick={() => setSelectedListId(list.id)}>
                      <div className="font-bold text-slate-800">{list.name}</div>
                      <div className="text-xs text-slate-500">{list.description || "No description"}</div>
                    </button>
                  </TableCell>
                  <TableCell>{list.type}</TableCell>
                  <TableCell>{list.lead_count}</TableCell>
                  <TableCell>{list.reachable_count}</TableCell>
                  <TableCell>{list.suppressed_count}</TableCell>
                  <TableCell>
                    <div className="flex items-center gap-2">
                      <button
                        type="button"
                        onClick={() => handleBeginEdit(list)}
                        className="rounded-lg border border-slate-200 px-3 py-2 text-xs font-bold text-slate-700"
                      >
                        <Pencil size={14} />
                      </button>
                      <button
                        type="button"
                        onClick={() => void handleDelete(list.id)}
                        disabled={busyId === list.id}
                        className="rounded-lg border border-red-200 px-3 py-2 text-xs font-bold text-red-700"
                      >
                        <Trash2 size={14} />
                      </button>
                    </div>
                  </TableCell>
                </TableRow>
              ))}
              {lists.length === 0 && (
                <TableRow>
                  <TableCell colSpan={6} className="py-12 text-center">
                    <div className="text-lg font-bold text-slate-500">No lists yet</div>
                    <div className="text-sm text-slate-400">Create your first static lead list above.</div>
                  </TableCell>
                </TableRow>
              )}
            </Table>
          </div>

          <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
            {!selectedListLeads ? (
              <div className="flex min-h-[320px] flex-col items-center justify-center text-center text-slate-500">
                <Users size={32} className="mb-3" />
                <div className="text-lg font-bold text-slate-700">Select a list</div>
                <div className="text-sm">Open a list to inspect members and manage membership.</div>
              </div>
            ) : (
              <div className="space-y-4">
                <div className="flex items-start justify-between">
                  <div>
                    <h2 className="text-xl font-bold text-slate-800">{selectedListLeads.list.name}</h2>
                    <p className="text-sm text-slate-500">{selectedListLeads.list.description || "No description set."}</p>
                  </div>
                  {editState?.id === selectedListLeads.list.id ? (
                    <div className="flex gap-2">
                      <button onClick={() => void handleSaveEdit()} className="rounded-xl bg-slate-900 px-4 py-2 text-sm font-bold text-white">{busyId === editState.id ? "Saving..." : "Save"}</button>
                      <button onClick={() => setEditState(null)} className="rounded-xl border border-slate-200 px-4 py-2 text-sm font-bold text-slate-700"><X size={16} /></button>
                    </div>
                  ) : null}
                </div>

                {editState?.id === selectedListLeads.list.id ? (
                  <div className="grid gap-3 rounded-xl border border-slate-200 bg-slate-50 p-4">
                    <input value={editState.name} onChange={(event) => setEditState((current) => current ? { ...current, name: event.target.value } : current)} className="rounded-xl border border-slate-200 px-3 py-2" />
                    <input value={editState.description} onChange={(event) => setEditState((current) => current ? { ...current, description: event.target.value } : current)} className="rounded-xl border border-slate-200 px-3 py-2" />
                  </div>
                ) : null}

                <div className="grid grid-cols-2 gap-3 text-sm">
                  <Stat label="Lead count" value={selectedListLeads.list.lead_count} />
                  <Stat label="Reachable" value={selectedListLeads.list.reachable_count} />
                  <Stat label="Invalid" value={selectedListLeads.list.invalid_count} />
                  <Stat label="Suppressed" value={selectedListLeads.list.suppressed_count} />
                </div>

                <div className="rounded-xl border border-slate-200 bg-slate-50 p-4">
                  <div className="mb-3 text-sm font-bold text-slate-700">Add lead to list</div>
                  <div className="flex gap-3">
                    <select value={selectedLeadId} onChange={(event) => setSelectedLeadId(event.target.value)} className="flex-1 rounded-xl border border-slate-200 px-3 py-2">
                      <option value="">Select a lead</option>
                      {availableLeads.map((lead) => (
                        <option key={lead.id} value={lead.id}>{lead.email}</option>
                      ))}
                    </select>
                    <button onClick={() => void handleAddLead()} disabled={!selectedLeadId || busyId === selectedListLeads.list.id} className="rounded-xl bg-blue-600 px-4 py-2 text-sm font-bold text-white disabled:opacity-50">
                      {busyId === selectedListLeads.list.id ? <LoaderCircle size={16} className="animate-spin" /> : "Add"}
                    </button>
                  </div>
                </div>

                <Table columns={["Lead", "Status", "Score", "Actions"]}>
                  {selectedListLeads.leads.map((lead) => (
                    <TableRow key={lead.id}>
                      <TableCell>
                        <div className="font-semibold text-slate-800">{lead.email}</div>
                        <div className="text-xs text-slate-500">{lead.company || "No company"}</div>
                      </TableCell>
                      <TableCell>{lead.email_status}</TableCell>
                      <TableCell>{lead.verification_score ?? "Not scored"}</TableCell>
                      <TableCell>
                        <button onClick={() => void handleRemoveLead(lead.id)} className="rounded-lg border border-red-200 px-3 py-2 text-xs font-bold text-red-700">
                          Remove
                        </button>
                      </TableCell>
                    </TableRow>
                  ))}
                  {selectedListLeads.leads.length === 0 && (
                    <TableRow>
                      <TableCell colSpan={4} className="py-10 text-center text-slate-500">
                        This list has no leads yet.
                      </TableCell>
                    </TableRow>
                  )}
                </Table>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

function Stat({ label, value }: { label: string; value: number }) {
  return (
    <div className="rounded-xl border border-slate-200 bg-slate-50 p-4">
      <div className="text-xs font-bold uppercase tracking-wide text-slate-500">{label}</div>
      <div className="mt-1 text-lg font-bold text-slate-800">{value}</div>
    </div>
  );
}
