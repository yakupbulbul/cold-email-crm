"use client";

import { useEffect, useMemo, useState } from "react";
import { ListPlus, LoaderCircle, Pencil, Trash2, Users, X } from "lucide-react";

import Spinner from "@/components/ui/Spinner";
import Table, { TableCell, TableRow } from "@/components/ui/Table";
import { AlertBanner, EmptyState, PageHeader, SurfaceCard } from "@/components/ui/primitives";
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
    updateLead,
    updateLeadContactTypeBulk,
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
  const [leadTypeDrafts, setLeadTypeDrafts] = useState<Record<string, "b2b" | "b2c" | "mixed">>({});
  const [selectedMemberLeadIds, setSelectedMemberLeadIds] = useState<string[]>([]);
  const [bulkContactType, setBulkContactType] = useState<"b2b" | "b2c" | "mixed">("mixed");

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

  useEffect(() => {
    if (!selectedListLeads) {
      setLeadTypeDrafts({});
      setSelectedMemberLeadIds([]);
      return;
    }
    setLeadTypeDrafts(
      Object.fromEntries(
        selectedListLeads.leads.map((lead) => [lead.id, (lead.contact_type || "mixed") as "b2b" | "b2c" | "mixed"]),
      ),
    );
  }, [selectedListLeads]);

  const availableLeads = useMemo(() => {
    const currentIds = new Set(selectedListLeads?.leads.map((lead) => lead.id) || []);
    return leads.filter((lead) => !currentIds.has(lead.id));
  }, [leads, selectedListLeads]);

  const allMembersSelected = !!selectedListLeads?.leads.length
    && selectedListLeads.leads.every((lead) => selectedMemberLeadIds.includes(lead.id));

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

  const handleUpdateLeadType = async (leadId: string) => {
    const contactType = leadTypeDrafts[leadId];
    if (!contactType) return;
    setBusyId(leadId);
    try {
      const updated = await updateLead(leadId, { contact_type: contactType });
      setBanner(`Updated ${updated.email} contact type to ${updated.contact_type || "mixed"}.`);
      await refreshLists(selectedListId);
      const refreshedLeads = await getLeads();
      if (refreshedLeads) setLeads(refreshedLeads);
    } catch (err) {
      setBanner(err instanceof Error ? err.message : "Lead update failed.");
    } finally {
      setBusyId(null);
    }
  };

  const toggleMemberLead = (leadId: string) => {
    setSelectedMemberLeadIds((current) =>
      current.includes(leadId) ? current.filter((id) => id !== leadId) : [...current, leadId],
    );
  };

  const toggleAllMemberLeads = () => {
    if (!selectedListLeads?.leads.length) return;
    if (allMembersSelected) {
      setSelectedMemberLeadIds([]);
      return;
    }
    setSelectedMemberLeadIds(selectedListLeads.leads.map((lead) => lead.id));
  };

  const handleBulkUpdateLeadType = async () => {
    if (!selectedMemberLeadIds.length) {
      setBanner("Select one or more list members to update contact type.");
      return;
    }
    setBusyId("__bulk_contact_type__");
    try {
      const result = await updateLeadContactTypeBulk({
        lead_ids: selectedMemberLeadIds,
        contact_type: bulkContactType,
      });
      setSelectedMemberLeadIds([]);
      setBanner(`Updated ${result.lead_count} lead${result.lead_count === 1 ? "" : "s"} to ${result.contact_type || "mixed"}.`);
      await refreshLists(selectedListId);
      const refreshedLeads = await getLeads();
      if (refreshedLeads) setLeads(refreshedLeads);
    } catch (err) {
      setBanner(err instanceof Error ? err.message : "Bulk contact type update failed.");
    } finally {
      setBusyId(null);
    }
  };

  return (
    <div className="space-y-6 animate-fade-in">
      <PageHeader
        eyebrow="Audience"
        title="Reusable lead lists"
        description="Create, inspect, and reuse persistent static lead groups across campaigns without reselecting leads manually."
      />

      {banner ? <AlertBanner tone="info">{banner}</AlertBanner> : null}

      <SurfaceCard className="p-5">
      <form onSubmit={handleCreate} className="grid gap-4 md:grid-cols-2">
        <div>
          <label className="mb-2 block text-sm font-semibold text-[var(--foreground)]">List Name</label>
          <input value={name} onChange={(event) => setName(event.target.value)} className="form-input" placeholder="Verified High Score" />
        </div>
        <div>
          <label className="mb-2 block text-sm font-semibold text-[var(--foreground)]">Description</label>
          <input value={description} onChange={(event) => setDescription(event.target.value)} className="form-input" placeholder="Reusable list for strong verified leads" />
        </div>
        <div className="md:col-span-2 flex items-center justify-between gap-4">
          {submitError ? <div className="text-sm font-medium text-red-700">{submitError}</div> : <div className="text-sm text-[var(--muted-foreground)]">Static lists persist and can be reused across campaigns.</div>}
          <button type="submit" className="btn-primary">
            <ListPlus size={18} /> Create List
          </button>
        </div>
      </form>
      </SurfaceCard>

      {error && lists.length === 0 ? (
        <AlertBanner tone="danger" title="Failed to load lists">Check the backend response and try again.</AlertBanner>
      ) : loading && lists.length === 0 ? (
        <SurfaceCard className="flex h-64 items-center justify-center"><Spinner size="lg" /></SurfaceCard>
      ) : (
        <div className="grid gap-6 xl:grid-cols-[1.1fr,0.9fr]">
          <div className="space-y-4">
            <Table columns={["Name", "Type", "Leads", "Reachable", "Audience Mix", "Actions"]}>
              {lists.map((list) => (
                <TableRow key={list.id}>
                  <TableCell>
                    <button className="text-left" onClick={() => setSelectedListId(list.id)}>
                      <div className="font-bold text-[var(--foreground)]">{list.name}</div>
                      <div className="text-xs text-[var(--muted-foreground)]">{list.description || "No description"}</div>
                    </button>
                  </TableCell>
                  <TableCell>{list.type}</TableCell>
                  <TableCell>{list.lead_count}</TableCell>
                  <TableCell>{list.reachable_count}</TableCell>
                  <TableCell>
                    <div className="space-y-1 text-xs text-[var(--muted-foreground)]">
                      <div>B2B: {list.contact_type_counts?.b2b ?? 0}</div>
                      <div>B2C: {list.contact_type_counts?.b2c ?? 0}</div>
                      <div>Unknown: {list.contact_type_counts?.mixed ?? 0}</div>
                    </div>
                  </TableCell>
                  <TableCell>
                    <div className="flex items-center gap-2">
                      <button
                        type="button"
                        onClick={() => handleBeginEdit(list)}
                        className="rounded-lg border border-[var(--border)] px-3 py-2 text-xs font-bold text-[var(--foreground)]"
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
                    <div className="text-lg font-bold text-[var(--muted-foreground)]">No lists yet</div>
                    <div className="text-sm text-[var(--muted-foreground)]">Create your first static lead list above.</div>
                  </TableCell>
                </TableRow>
              )}
            </Table>
          </div>

          <div className="rounded-2xl border border-[var(--border)] bg-[var(--surface)] p-5 shadow-sm">
            {!selectedListLeads ? (
              <EmptyState icon={Users} title="Select a list" description="Open a list to inspect members, manage membership, and review quality counts." />
            ) : (
              <div className="space-y-4">
                <div className="flex items-start justify-between">
                  <div>
                    <h2 className="text-xl font-bold text-[var(--foreground)]">{selectedListLeads.list.name}</h2>
                    <p className="text-sm text-[var(--muted-foreground)]">{selectedListLeads.list.description || "No description set."}</p>
                  </div>
                  {editState?.id === selectedListLeads.list.id ? (
                    <div className="flex gap-2">
                      <button onClick={() => void handleSaveEdit()} className="rounded-xl bg-[var(--sidebar)] px-4 py-2 text-sm font-bold text-white">{busyId === editState.id ? "Saving..." : "Save"}</button>
                      <button onClick={() => setEditState(null)} className="rounded-xl border border-[var(--border)] px-4 py-2 text-sm font-bold text-[var(--foreground)]"><X size={16} /></button>
                    </div>
                  ) : null}
                </div>

                {editState?.id === selectedListLeads.list.id ? (
                  <div className="grid gap-3 rounded-xl border border-[var(--border)] bg-[var(--surface-muted)] p-4">
                    <input value={editState.name} onChange={(event) => setEditState((current) => current ? { ...current, name: event.target.value } : current)} className="rounded-xl border border-[var(--border)] px-3 py-2" />
                    <input value={editState.description} onChange={(event) => setEditState((current) => current ? { ...current, description: event.target.value } : current)} className="rounded-xl border border-[var(--border)] px-3 py-2" />
                  </div>
                ) : null}

                <div className="grid grid-cols-2 gap-3 text-sm md:grid-cols-3">
                  <Stat label="Lead count" value={selectedListLeads.list.lead_count} />
                  <Stat label="Reachable" value={selectedListLeads.list.reachable_count} />
                  <Stat label="Invalid" value={selectedListLeads.list.invalid_count} />
                  <Stat label="Suppressed" value={selectedListLeads.list.suppressed_count} />
                  <Stat label="Unsubscribed" value={selectedListLeads.list.unsubscribed_count || 0} />
                  <Stat label="Consent unknown" value={selectedListLeads.list.consent_unknown_count || 0} />
                </div>

                <div className="grid grid-cols-3 gap-3 text-sm">
                  <Stat label="High quality" value={selectedListLeads.list.high_quality_count || 0} />
                  <Stat label="Medium quality" value={selectedListLeads.list.medium_quality_count || 0} />
                  <Stat label="Low quality" value={selectedListLeads.list.low_quality_count || 0} />
                </div>

                <div className="rounded-xl border border-[var(--border)] bg-[var(--surface-muted)] p-4">
                  <div className="mb-3 text-sm font-bold text-[var(--foreground)]">Add lead to list</div>
                  <div className="flex gap-3">
                    <select value={selectedLeadId} onChange={(event) => setSelectedLeadId(event.target.value)} className="flex-1 rounded-xl border border-[var(--border)] px-3 py-2">
                      <option value="">Select a lead</option>
                      {availableLeads.map((lead) => (
                        <option key={lead.id} value={lead.id}>{lead.email}</option>
                      ))}
                    </select>
                    <button onClick={() => void handleAddLead()} disabled={!selectedLeadId || busyId === selectedListLeads.list.id} className="rounded-xl bg-[var(--primary)] px-4 py-2 text-sm font-bold text-white disabled:opacity-50">
                      {busyId === selectedListLeads.list.id ? <LoaderCircle size={16} className="animate-spin" /> : "Add"}
                    </button>
                  </div>
                </div>

                <div className="rounded-xl border border-[var(--border)] bg-[var(--surface-muted)] p-4">
                  <div className="mb-3 text-sm font-bold text-[var(--foreground)]">Set contact type for selected members</div>
                  <div className="flex gap-3">
                    <select
                      value={bulkContactType}
                      onChange={(event) => setBulkContactType(event.target.value as "b2b" | "b2c" | "mixed")}
                      aria-label="Bulk member contact type"
                      className="flex-1 rounded-xl border border-[var(--border)] px-3 py-2"
                    >
                      <option value="b2b">B2B</option>
                      <option value="b2c">B2C</option>
                      <option value="mixed">Mixed</option>
                    </select>
                    <button
                      onClick={() => void handleBulkUpdateLeadType()}
                      disabled={!selectedMemberLeadIds.length || busyId === "__bulk_contact_type__"}
                      className="rounded-xl border border-[var(--border)] bg-[var(--surface)] px-4 py-2 text-sm font-bold text-[var(--foreground)] disabled:opacity-50"
                    >
                      {busyId === "__bulk_contact_type__" ? <LoaderCircle size={16} className="animate-spin" /> : "Apply"}
                    </button>
                  </div>
                </div>

                <Table columns={["", "Lead", "Audience", "Contact Type", "Status", "Score", "Actions"]}>
                  {selectedListLeads.leads.map((lead) => (
                    <TableRow key={lead.id}>
                      <TableCell className="w-12">
                        <input
                          type="checkbox"
                          aria-label={`Select ${lead.email}`}
                          checked={selectedMemberLeadIds.includes(lead.id)}
                          onChange={() => toggleMemberLead(lead.id)}
                          className="h-4 w-4 rounded border-[var(--border-strong)] text-[var(--primary)] focus:ring-[#2d6a4f]"
                        />
                      </TableCell>
                      <TableCell>
                        <div className="font-semibold text-[var(--foreground)]">{lead.email}</div>
                        <div className="text-xs text-[var(--muted-foreground)]">{lead.company || "No company"}</div>
                      </TableCell>
                      <TableCell>
                        <div className="text-xs text-[var(--muted-foreground)]">{lead.consent_status || "unknown"}</div>
                        <div className="text-xs text-[var(--muted-foreground)]">{lead.unsubscribe_status || "subscribed"} • {lead.contact_quality_tier || "low"} quality</div>
                      </TableCell>
                      <TableCell>
                        <div className="flex items-center gap-2">
                          <select
                            value={leadTypeDrafts[lead.id] || (lead.contact_type || "mixed")}
                            onChange={(event) => setLeadTypeDrafts((current) => ({ ...current, [lead.id]: event.target.value as "b2b" | "b2c" | "mixed" }))}
                            className="rounded-lg border border-[var(--border)] px-2 py-2 text-xs font-medium text-[var(--foreground)]"
                            disabled={busyId === lead.id}
                          >
                            <option value="b2b">B2B</option>
                            <option value="b2c">B2C</option>
                            <option value="mixed">Mixed</option>
                          </select>
                          <button
                            onClick={() => void handleUpdateLeadType(lead.id)}
                            disabled={busyId === lead.id || (leadTypeDrafts[lead.id] || (lead.contact_type || "mixed")) === (lead.contact_type || "mixed")}
                            className="rounded-lg border border-[var(--border)] px-3 py-2 text-xs font-bold text-[var(--foreground)] disabled:cursor-not-allowed disabled:opacity-50"
                          >
                            {busyId === lead.id ? <LoaderCircle size={14} className="animate-spin" /> : "Save"}
                          </button>
                        </div>
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
                      <TableCell colSpan={7} className="py-10 text-center text-[var(--muted-foreground)]">
                        This list has no leads yet.
                      </TableCell>
                    </TableRow>
                  )}
                </Table>
                {selectedListLeads.leads.length > 0 && (
                  <div className="flex items-center gap-3">
                    <input
                      type="checkbox"
                      aria-label="Select all list members"
                      checked={allMembersSelected}
                      onChange={toggleAllMemberLeads}
                      className="h-4 w-4 rounded border-[var(--border-strong)] text-[var(--primary)] focus:ring-[#2d6a4f]"
                    />
                    <span className="text-sm font-medium text-[var(--muted-foreground)]">
                      Select all visible members ({selectedListLeads.leads.length})
                    </span>
                  </div>
                )}
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
    <div className="rounded-xl border border-[var(--border)] bg-[var(--surface-muted)] p-4">
      <div className="text-xs font-bold uppercase tracking-wide text-[var(--muted-foreground)]">{label}</div>
      <div className="mt-1 text-lg font-bold text-[var(--foreground)]">{value}</div>
    </div>
  );
}
