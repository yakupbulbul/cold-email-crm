"use client";

import { useEffect, useState } from 'react';
import { Plus, Users, BarChart2, Calendar, AlertCircle } from 'lucide-react';
import { useApiService } from '@/services/api';
import { Campaign, Mailbox } from '@/types/models';
import Spinner from '@/components/ui/Spinner';

export default function CampaignsPage() {
  const { getCampaigns, getMailboxes, createCampaign, loading, error } = useApiService();
  const [campaigns, setCampaigns] = useState<Campaign[]>([]);
  const [mailboxes, setMailboxes] = useState<Mailbox[]>([]);
  const [name, setName] = useState('');
  const [mailboxId, setMailboxId] = useState('');
  const [subject, setSubject] = useState('');
  const [body, setBody] = useState('');
  const [dailyLimit, setDailyLimit] = useState('50');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);

  useEffect(() => {
    const fetchPageData = async () => {
      const [campaignData, mailboxData] = await Promise.all([getCampaigns(), getMailboxes()]);
      if (campaignData) setCampaigns(campaignData);
      if (mailboxData) {
        setMailboxes(mailboxData);
        setMailboxId((current) => current || mailboxData[0]?.id || '');
      }
    };
    fetchPageData();
  }, [getCampaigns, getMailboxes]);

  const handleCreate = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setSubmitError(null);
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
    const refreshed = await getCampaigns();
    if (refreshed) setCampaigns(refreshed);
  };

  return (
    <div className="space-y-6 animate-fade-in relative min-h-[50vh]">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold text-slate-800 tracking-tight">Campaigns</h1>
      </div>

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

      {error ? (
        <div className="p-6 bg-red-50 border border-red-200 text-red-700 rounded-2xl flex flex-col items-center justify-center py-16 text-center">
            <AlertCircle className="mb-4 text-red-500" size={32} />
            <span className="font-bold mb-2">Error Fetching Campaigns</span>
            <span className="text-sm">{error}</span>
        </div>
      ) : loading ? (
        <div className="flex justify-center items-center py-16 bg-white rounded-2xl border border-slate-200">
           <Spinner size="lg" />
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
          {campaigns.map((campaign) => (
            <div key={campaign.id} className="bg-white rounded-2xl border border-slate-200 shadow-sm hover:shadow-md transition-all p-7 group cursor-pointer relative overflow-hidden">
              <div className={`absolute top-0 right-0 w-32 h-32 rounded-full blur-3xl -mr-16 -mt-16 opacity-30 group-hover:opacity-70 transition-opacity ${campaign.status === 'active' ? 'bg-blue-300' : 'bg-slate-300'}`}></div>
              <div className="relative z-10">
                <div className="flex justify-between items-start mb-6">
                  <div>
                    <h3 className="text-xl font-extrabold text-slate-800 mb-1.5 group-hover:text-blue-600 transition-colors">{campaign.name}</h3>
                    <p className="text-sm font-semibold text-slate-400 flex items-center gap-1.5">
                      <Calendar size={14}/> Started on {new Date(campaign.created_at).toLocaleDateString()}
                    </p>
                  </div>
                  <span className={`px-4 py-1 text-xs font-bold tracking-wide rounded-full border shadow-sm ${campaign.status === 'active' ? 'bg-blue-50 text-blue-700 border-blue-200' : 'bg-slate-50 text-slate-600 border-slate-200'}`}>
                    {campaign.status}
                  </span>
                </div>
                
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
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
