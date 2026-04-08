"use client";

import { useEffect, useState } from 'react';
import { AlertCircle, BarChart2, Calendar, LoaderCircle, Pencil, Play, Plus, ShieldAlert, Users, X } from 'lucide-react';

import Spinner from '@/components/ui/Spinner';
import { useApiService } from '@/services/api';
import { Campaign, CampaignPreflightResult, Mailbox } from '@/types/models';

type ActionState = {
  type: 'start' | 'pause' | 'preflight' | 'save';
  campaignId: string;
};

type EditState = {
  campaignId: string;
  name: string;
  mailboxId: string;
  subject: string;
  body: string;
  dailyLimit: string;
};

export default function CampaignsPage() {
  const {
    getCampaigns,
    getMailboxes,
    createCampaign,
    updateCampaign,
    startCampaign,
    pauseCampaign,
    runPreflight,
  } = useApiService();
  const [campaigns, setCampaigns] = useState<Campaign[]>([]);
  const [mailboxes, setMailboxes] = useState<Mailbox[]>([]);
  const [name, setName] = useState('');
  const [mailboxId, setMailboxId] = useState('');
  const [subject, setSubject] = useState('');
  const [body, setBody] = useState('');
  const [dailyLimit, setDailyLimit] = useState('50');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [banner, setBanner] = useState<{ tone: 'success' | 'error'; message: string } | null>(null);
  const [actionState, setActionState] = useState<ActionState | null>(null);
  const [actionErrors, setActionErrors] = useState<Record<string, string>>({});
  const [preflightResults, setPreflightResults] = useState<Record<string, CampaignPreflightResult>>({});
  const [isPageLoading, setIsPageLoading] = useState(true);
  const [pageError, setPageError] = useState<string | null>(null);
  const [editState, setEditState] = useState<EditState | null>(null);

  useEffect(() => {
    const fetchPageData = async () => {
      setIsPageLoading(true);
      setPageError(null);
      const [campaignData, mailboxData] = await Promise.all([getCampaigns(), getMailboxes()]);
      if (!campaignData || !mailboxData) {
        setPageError('Failed to load campaigns or mailboxes. Check the backend response and try again.');
        setIsPageLoading(false);
        return;
      }
      setCampaigns(campaignData);
      if (mailboxData) {
        setMailboxes(mailboxData);
        setMailboxId((current) => current || mailboxData[0]?.id || '');
      }
      setIsPageLoading(false);
    };
    void fetchPageData();
  }, [getCampaigns, getMailboxes]);

  const refreshCampaigns = async () => {
    const refreshed = await getCampaigns();
    if (refreshed) setCampaigns(refreshed);
  };

  const clearCampaignMessages = (campaignId: string) => {
    setActionErrors((current) => {
      if (!current[campaignId]) return current;
      const next = { ...current };
      delete next[campaignId];
      return next;
    });
    setPreflightResults((current) => {
      if (!current[campaignId]) return current;
      const next = { ...current };
      delete next[campaignId];
      return next;
    });
  };

  const handleCreate = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setSubmitError(null);
    setBanner(null);
    if (!name.trim() || !mailboxId || !subject.trim() || !body.trim()) {
      setSubmitError('Name, mailbox, subject, and body are required.');
      return;
    }
    setIsSubmitting(true);
    const created = await createCampaign({
      name: name.trim(),
      mailbox_id: mailboxId,
      template_subject: subject.trim(),
      template_body: body.trim(),
      daily_limit: Number(dailyLimit) || 50,
    });
    setIsSubmitting(false);
    if (!created) {
      setSubmitError('Campaign create failed. Check the backend response and try again.');
      return;
    }
    setName('');
    setSubject('');
    setBody('');
    setDailyLimit('50');
    await refreshCampaigns();
    setBanner({ tone: 'success', message: `Campaign ${created.name} created.` });
  };

  const handleStart = async (campaignId: string) => {
    setBanner(null);
    clearCampaignMessages(campaignId);
    setActionState({ type: 'start', campaignId });
    try {
      const result = await startCampaign(campaignId);
      await refreshCampaigns();
      const message = result.job_queued
        ? `Campaign activation queued${result.eligible_leads ? ` for ${result.eligible_leads} eligible leads` : ''}.`
        : 'Campaign activated.';
      setBanner({ tone: 'success', message });
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Campaign activation failed. Check the backend response and try again.';
      setActionErrors((current) => ({
        ...current,
        [campaignId]: message,
      }));
    } finally {
      setActionState(null);
    }
  };

  const handlePause = async (campaignId: string) => {
    setBanner(null);
    clearCampaignMessages(campaignId);
    setActionState({ type: 'pause', campaignId });
    try {
      await pauseCampaign(campaignId);
      await refreshCampaigns();
      setBanner({ tone: 'success', message: 'Campaign paused.' });
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Campaign pause failed. Check the backend response and try again.';
      setActionErrors((current) => ({
        ...current,
        [campaignId]: message,
      }));
    } finally {
      setActionState(null);
    }
  };

  const handlePreflight = async (campaignId: string) => {
    setBanner(null);
    setActionErrors((current) => {
      if (!current[campaignId]) return current;
      const next = { ...current };
      delete next[campaignId];
      return next;
    });
    setActionState({ type: 'preflight', campaignId });
    try {
      const result = await runPreflight(campaignId);
      setPreflightResults((current) => ({ ...current, [campaignId]: result }));
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Campaign preflight failed. Check the backend response and try again.';
      setActionErrors((current) => ({
        ...current,
        [campaignId]: message,
      }));
    } finally {
      setActionState(null);
    }
  };

  const isActionPending = (campaignId: string, type: ActionState['type']) =>
    actionState?.campaignId === campaignId && actionState?.type === type;

  const beginEdit = (campaign: Campaign) => {
    setBanner(null);
    clearCampaignMessages(campaign.id);
    setEditState({
      campaignId: campaign.id,
      name: campaign.name,
      mailboxId: campaign.mailbox_id || '',
      subject: campaign.template_subject,
      body: campaign.template_body,
      dailyLimit: String(campaign.daily_limit),
    });
  };

  const cancelEdit = () => {
    setEditState(null);
  };

  const handleSave = async (campaignId: string) => {
    if (!editState || editState.campaignId !== campaignId) return;
    const normalizedName = editState.name.trim();
    const normalizedSubject = editState.subject.trim();
    const normalizedBody = editState.body.trim();
    const dailyLimitValue = Number(editState.dailyLimit);

    if (!normalizedName || !editState.mailboxId || !normalizedSubject || !normalizedBody) {
      setActionErrors((current) => ({
        ...current,
        [campaignId]: 'Name, mailbox, subject, and body are required.',
      }));
      return;
    }

    if (!Number.isFinite(dailyLimitValue) || dailyLimitValue <= 0) {
      setActionErrors((current) => ({
        ...current,
        [campaignId]: 'Daily limit must be a positive number.',
      }));
      return;
    }

    setBanner(null);
    clearCampaignMessages(campaignId);
    setActionState({ type: 'save', campaignId });
    try {
      const updated = await updateCampaign(campaignId, {
        name: normalizedName,
        mailbox_id: editState.mailboxId,
        template_subject: normalizedSubject,
        template_body: normalizedBody,
        daily_limit: dailyLimitValue,
      });
      setCampaigns((current) => current.map((campaign) => campaign.id === campaignId ? updated : campaign));
      setEditState(null);
      setBanner({ tone: 'success', message: `Campaign ${updated.name} updated.` });
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Campaign update failed. Check the backend response and try again.';
      setActionErrors((current) => ({
        ...current,
        [campaignId]: message,
      }));
    } finally {
      setActionState(null);
    }
  };

  return (
    <div className="space-y-6 animate-fade-in relative min-h-[50vh]">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold text-slate-800 tracking-tight">Campaigns</h1>
      </div>

      {banner && (
        <div className={`rounded-2xl border px-5 py-4 text-sm font-medium ${
          banner.tone === 'success'
            ? 'border-emerald-200 bg-emerald-50 text-emerald-700'
            : 'border-red-200 bg-red-50 text-red-700'
        }`}>
          {banner.message}
        </div>
      )}

      <form onSubmit={handleCreate} className="bg-white rounded-2xl border border-slate-200 shadow-sm p-5 grid gap-4 md:grid-cols-2">
        <div>
          <label htmlFor="campaign-name" className="block text-sm font-semibold text-slate-700 mb-2">Campaign Name</label>
          <input id="campaign-name" data-testid="campaign-name-input" value={name} onChange={(event) => setName(event.target.value)} placeholder="April outreach" className="w-full rounded-xl border border-slate-200 px-4 py-3 text-slate-900 outline-none focus:border-blue-500 focus:ring-4 focus:ring-blue-100 transition-all" />
        </div>
        <div>
          <label htmlFor="campaign-mailbox" className="block text-sm font-semibold text-slate-700 mb-2">Mailbox</label>
          <select id="campaign-mailbox" data-testid="campaign-mailbox-select" value={mailboxId} onChange={(event) => setMailboxId(event.target.value)} className="w-full rounded-xl border border-slate-200 px-4 py-3 text-slate-900 outline-none focus:border-blue-500 focus:ring-4 focus:ring-blue-100 transition-all">
            <option value="">Select a mailbox</option>
            {mailboxes.map((mailbox) => (
              <option key={mailbox.id} value={mailbox.id}>{mailbox.email}</option>
            ))}
          </select>
        </div>
        <div>
          <label htmlFor="campaign-subject" className="block text-sm font-semibold text-slate-700 mb-2">Template Subject</label>
          <input id="campaign-subject" data-testid="campaign-subject-input" value={subject} onChange={(event) => setSubject(event.target.value)} placeholder="Quick introduction" className="w-full rounded-xl border border-slate-200 px-4 py-3 text-slate-900 outline-none focus:border-blue-500 focus:ring-4 focus:ring-blue-100 transition-all" />
        </div>
        <div>
          <label htmlFor="campaign-daily-limit" className="block text-sm font-semibold text-slate-700 mb-2">Daily Limit</label>
          <input id="campaign-daily-limit" data-testid="campaign-daily-limit-input" type="number" min="1" value={dailyLimit} onChange={(event) => setDailyLimit(event.target.value)} className="w-full rounded-xl border border-slate-200 px-4 py-3 text-slate-900 outline-none focus:border-blue-500 focus:ring-4 focus:ring-blue-100 transition-all" />
        </div>
        <div className="md:col-span-2">
          <label htmlFor="campaign-body" className="block text-sm font-semibold text-slate-700 mb-2">Template Body</label>
          <textarea id="campaign-body" data-testid="campaign-body-input" value={body} onChange={(event) => setBody(event.target.value)} rows={5} placeholder="Hi {{first_name}}, ..." className="w-full rounded-xl border border-slate-200 px-4 py-3 text-slate-900 outline-none focus:border-blue-500 focus:ring-4 focus:ring-blue-100 transition-all resize-y" />
        </div>
        <div className="md:col-span-2 flex items-center justify-between gap-4">
          {submitError ? <div className="text-sm font-medium text-red-700">{submitError}</div> : <div className="text-sm text-slate-500">Campaigns stay local until you explicitly start them with background workers enabled.</div>}
          <button data-testid="create-campaign-button" type="submit" disabled={isSubmitting || mailboxes.length === 0} className="inline-flex items-center gap-2 rounded-xl bg-slate-900 px-5 py-3 font-bold text-white shadow-lg shadow-slate-900/20 transition-colors hover:bg-slate-800 disabled:cursor-not-allowed disabled:opacity-50">
            <Plus size={18} strokeWidth={3} /> {isSubmitting ? 'Creating...' : 'Create Campaign'}
          </button>
        </div>
      </form>

      {isPageLoading ? (
        <div className="flex justify-center items-center py-16 bg-white rounded-2xl border border-slate-200">
           <Spinner size="lg" />
        </div>
      ) : pageError ? (
        <div className="p-6 bg-red-50 border border-red-200 text-red-700 rounded-2xl flex flex-col items-center justify-center py-16 text-center">
            <AlertCircle className="mb-4 text-red-500" size={32} />
            <span className="font-bold mb-2">Error Fetching Campaigns</span>
            <span className="text-sm">{pageError}</span>
        </div>
      ) : campaigns.length === 0 ? (
        <div className="bg-white rounded-2xl border border-slate-200 shadow-sm flex flex-col items-center justify-center p-16 text-center">
          <div className="w-16 h-16 bg-slate-50 rounded-full flex items-center justify-center mb-4 border border-slate-100">
             <Calendar className="text-slate-400" size={28} />
          </div>
          <h3 className="text-lg font-bold text-slate-800 mb-2">No Campaigns Found</h3>
          <p className="text-sm text-slate-500 max-w-sm mb-6">You haven&apos;t created any campaigns yet. Use the form above to create the first draft.</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {campaigns.map((campaign) => {
            const blockedMessage = actionErrors[campaign.id];
            const preflight = preflightResults[campaign.id];
            const canStart = campaign.status === 'draft' || campaign.status === 'paused';
            const canPause = campaign.status === 'active';
            const isEditing = editState?.campaignId === campaign.id;

            return (
              <div key={campaign.id} data-testid={`campaign-card-${campaign.id}`} className="bg-white rounded-2xl border border-slate-200 shadow-sm hover:shadow-md transition-all p-7 group relative overflow-hidden">
                <div className={`absolute top-0 right-0 w-32 h-32 rounded-full blur-3xl -mr-16 -mt-16 opacity-30 group-hover:opacity-70 transition-opacity ${campaign.status === 'active' ? 'bg-blue-300' : 'bg-slate-300'}`}></div>
                <div className="relative z-10">
                  <div className="flex justify-between items-start mb-6">
                    <div>
                      {isEditing ? (
                        <div className="space-y-3">
                          <input
                            data-testid={`edit-campaign-name-${campaign.id}`}
                            value={editState.name}
                            onChange={(event) => setEditState((current) => current ? { ...current, name: event.target.value } : current)}
                            className="w-full rounded-xl border border-slate-200 px-3 py-2 text-sm font-semibold text-slate-900 outline-none focus:border-blue-500 focus:ring-4 focus:ring-blue-100"
                          />
                          <select
                            data-testid={`edit-campaign-mailbox-${campaign.id}`}
                            value={editState.mailboxId}
                            onChange={(event) => setEditState((current) => current ? { ...current, mailboxId: event.target.value } : current)}
                            className="w-full rounded-xl border border-slate-200 px-3 py-2 text-sm text-slate-900 outline-none focus:border-blue-500 focus:ring-4 focus:ring-blue-100"
                          >
                            <option value="">Select a mailbox</option>
                            {mailboxes.map((mailbox) => (
                              <option key={mailbox.id} value={mailbox.id}>{mailbox.email}</option>
                            ))}
                          </select>
                        </div>
                      ) : (
                        <>
                          <h3 className="text-xl font-extrabold text-slate-800 mb-1.5 group-hover:text-blue-600 transition-colors">{campaign.name}</h3>
                          <p className="text-sm font-semibold text-slate-400 flex items-center gap-1.5">
                            <Calendar size={14}/> Created on {new Date(campaign.created_at).toLocaleDateString()}
                          </p>
                        </>
                      )}
                    </div>
                    <span data-testid={`campaign-status-${campaign.id}`} className={`px-4 py-1 text-xs font-bold tracking-wide rounded-full border shadow-sm ${campaign.status === 'active' ? 'bg-blue-50 text-blue-700 border-blue-200' : campaign.status === 'paused' ? 'bg-amber-50 text-amber-700 border-amber-200' : 'bg-slate-50 text-slate-600 border-slate-200'}`}>
                      {campaign.status}
                    </span>
                  </div>

                  {isEditing ? (
                    <div className="mb-6 space-y-3 rounded-xl border border-slate-200 bg-slate-50 p-4">
                      <div>
                        <label className="mb-2 block text-xs font-bold uppercase tracking-wide text-slate-500">Subject</label>
                        <input
                          data-testid={`edit-campaign-subject-${campaign.id}`}
                          value={editState.subject}
                          onChange={(event) => setEditState((current) => current ? { ...current, subject: event.target.value } : current)}
                          className="w-full rounded-xl border border-slate-200 px-3 py-2 text-sm text-slate-900 outline-none focus:border-blue-500 focus:ring-4 focus:ring-blue-100"
                        />
                      </div>
                      <div>
                        <label className="mb-2 block text-xs font-bold uppercase tracking-wide text-slate-500">Body</label>
                        <textarea
                          data-testid={`edit-campaign-body-${campaign.id}`}
                          value={editState.body}
                          onChange={(event) => setEditState((current) => current ? { ...current, body: event.target.value } : current)}
                          rows={4}
                          className="w-full rounded-xl border border-slate-200 px-3 py-2 text-sm text-slate-900 outline-none focus:border-blue-500 focus:ring-4 focus:ring-blue-100"
                        />
                      </div>
                      <div>
                        <label className="mb-2 block text-xs font-bold uppercase tracking-wide text-slate-500">Daily Limit</label>
                        <input
                          data-testid={`edit-campaign-limit-${campaign.id}`}
                          type="number"
                          min="1"
                          value={editState.dailyLimit}
                          onChange={(event) => setEditState((current) => current ? { ...current, dailyLimit: event.target.value } : current)}
                          className="w-full rounded-xl border border-slate-200 px-3 py-2 text-sm text-slate-900 outline-none focus:border-blue-500 focus:ring-4 focus:ring-blue-100"
                        />
                      </div>
                    </div>
                  ) : null}

                  <div className="grid grid-cols-3 gap-4 border-t border-slate-100 pt-6">
                    <div>
                      <p className="text-xs font-bold text-slate-400 uppercase tracking-widest mb-1 shadow-sm flex items-center gap-1.5"><Users size={14}/> Leads</p>
                      <p className="text-3xl font-extrabold text-slate-800">{campaign.lead_count || 0}</p>
                    </div>
                    <div>
                      <p className="text-xs font-bold text-slate-400 uppercase tracking-widest mb-1 shadow-sm flex items-center gap-1.5"><BarChart2 size={14}/> Sent</p>
                      <p className="text-3xl font-extrabold text-slate-800">{campaign.sent_count || 0}</p>
                    </div>
                     <div>
                      <p className="text-xs font-bold text-slate-400 uppercase tracking-widest mb-1 shadow-sm">Reply Rate</p>
                      <p className="text-3xl font-extrabold text-green-600">{campaign.reply_rate || '0%'}</p>
                    </div>
                  </div>

                  <div className="mt-4 text-sm font-medium text-slate-500">
                    Daily limit: <span className="font-semibold text-slate-800">{campaign.daily_limit}</span>
                  </div>

                  <div className="mt-6 flex flex-wrap items-center gap-3">
                    {isEditing ? (
                      <>
                        <button
                          data-testid={`save-campaign-${campaign.id}`}
                          type="button"
                          onClick={() => void handleSave(campaign.id)}
                          disabled={!!actionState}
                          className="inline-flex items-center gap-2 rounded-xl bg-slate-900 px-4 py-2.5 text-sm font-bold text-white shadow-lg shadow-slate-900/20 transition-colors hover:bg-slate-800 disabled:cursor-not-allowed disabled:opacity-50"
                        >
                          {isActionPending(campaign.id, 'save') ? <LoaderCircle size={16} className="animate-spin" /> : <Pencil size={16} />}
                          Save
                        </button>
                        <button
                          data-testid={`cancel-edit-campaign-${campaign.id}`}
                          type="button"
                          onClick={cancelEdit}
                          disabled={!!actionState}
                          className="inline-flex items-center gap-2 rounded-xl border border-slate-200 px-4 py-2.5 text-sm font-bold text-slate-700 transition-colors hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-50"
                        >
                          <X size={16} />
                          Cancel
                        </button>
                      </>
                    ) : (
                      <button
                        data-testid={`edit-campaign-${campaign.id}`}
                        type="button"
                        onClick={() => beginEdit(campaign)}
                        disabled={!!actionState || !!editState}
                        className="inline-flex items-center gap-2 rounded-xl border border-slate-200 px-4 py-2.5 text-sm font-bold text-slate-700 transition-colors hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-50"
                      >
                        <Pencil size={16} />
                        Edit
                      </button>
                    )}
                    {canStart && (
                      <>
                        <button
                          data-testid={`start-campaign-${campaign.id}`}
                          type="button"
                          onClick={() => void handleStart(campaign.id)}
                          disabled={!!actionState || isEditing}
                          className="inline-flex items-center gap-2 rounded-xl bg-blue-600 px-4 py-2.5 text-sm font-bold text-white shadow-lg shadow-blue-600/20 transition-colors hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-50"
                        >
                          {isActionPending(campaign.id, 'start') ? <LoaderCircle size={16} className="animate-spin" /> : <Play size={16} />}
                          Start
                        </button>
                        <button
                          data-testid={`preflight-campaign-${campaign.id}`}
                          type="button"
                          onClick={() => void handlePreflight(campaign.id)}
                          disabled={!!actionState || isEditing}
                          className="inline-flex items-center gap-2 rounded-xl border border-slate-200 px-4 py-2.5 text-sm font-bold text-slate-700 transition-colors hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-50"
                        >
                          {isActionPending(campaign.id, 'preflight') ? <LoaderCircle size={16} className="animate-spin" /> : <ShieldAlert size={16} />}
                          Preflight
                        </button>
                      </>
                    )}
                    {canPause && (
                      <button
                        data-testid={`pause-campaign-${campaign.id}`}
                        type="button"
                        onClick={() => void handlePause(campaign.id)}
                        disabled={!!actionState || isEditing}
                        className="inline-flex items-center gap-2 rounded-xl bg-amber-500 px-4 py-2.5 text-sm font-bold text-white shadow-lg shadow-amber-500/20 transition-colors hover:bg-amber-600 disabled:cursor-not-allowed disabled:opacity-50"
                      >
                        {isActionPending(campaign.id, 'pause') ? <LoaderCircle size={16} className="animate-spin" /> : <PauseGlyph />}
                        Pause
                      </button>
                    )}
                  </div>

                  {blockedMessage && (
                    <div data-testid={`campaign-message-${campaign.id}`} className="mt-4 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm font-medium text-red-700">
                      {blockedMessage}
                    </div>
                  )}

                  {preflight && (
                    <div data-testid={`campaign-preflight-${campaign.id}`} className="mt-4 rounded-xl border border-slate-200 bg-slate-50 px-4 py-3">
                      <div className="flex items-center justify-between gap-3">
                        <span className="text-sm font-bold text-slate-700">Preflight: {preflight.status}</span>
                        <span className={`rounded-full px-3 py-1 text-xs font-bold ${preflight.blocked ? 'bg-red-100 text-red-700' : 'bg-emerald-100 text-emerald-700'}`}>
                          {preflight.blocked ? 'Blocked' : 'Ready'}
                        </span>
                      </div>
                      <div className="mt-3 space-y-2">
                        {preflight.checks.map((check) => (
                          <div key={check.name} className="rounded-lg bg-white px-3 py-2 text-sm text-slate-600 border border-slate-200">
                            <span className="font-semibold text-slate-800">{check.name}</span>: {check.message}
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

function PauseGlyph() {
  return (
    <span className="inline-flex gap-1">
      <span className="h-3.5 w-1 rounded bg-current" />
      <span className="h-3.5 w-1 rounded bg-current" />
    </span>
  );
}
