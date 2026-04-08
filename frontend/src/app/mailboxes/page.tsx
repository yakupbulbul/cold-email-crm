"use client";
import { useState, useEffect } from 'react';
import { Plus, Globe, Mail, Edit2, Trash2, ServerCrash } from 'lucide-react';
import { useApiService } from '@/services/api';
import { Domain, Mailbox } from '@/types/models';
import Spinner from '@/components/ui/Spinner';

export default function MailboxesPage() {
  const [activeTab, setActiveTab] = useState('mailboxes');
  const { getMailboxes, getDomains, createMailbox, updateMailbox, deleteMailbox, loading, error } = useApiService();
  const [mailboxes, setMailboxes] = useState<Mailbox[]>([]);
  const [domains, setDomains] = useState<Domain[]>([]);
  const [selectedDomainId, setSelectedDomainId] = useState('');
  const [localPart, setLocalPart] = useState('');
  const [displayName, setDisplayName] = useState('');
  const [password, setPassword] = useState('');
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [editingMailboxId, setEditingMailboxId] = useState<string | null>(null);
  const [editingDisplayName, setEditingDisplayName] = useState('');
  const [editingDailyLimit, setEditingDailyLimit] = useState('50');
  const [editingStatus, setEditingStatus] = useState('active');
  const [actionError, setActionError] = useState<string | null>(null);
  const [busyMailboxId, setBusyMailboxId] = useState<string | null>(null);

  useEffect(() => {
    const fetchPageData = async () => {
        const [mailboxData, domainData] = await Promise.all([getMailboxes(), getDomains()]);
        if (mailboxData) setMailboxes(mailboxData);
        if (domainData) {
          setDomains(domainData);
          setSelectedDomainId((current) => current || domainData[0]?.id || '');
        }
    };
    fetchPageData();
  }, [getMailboxes, getDomains]);

  const selectedDomain = domains.find((domain) => domain.id === selectedDomainId);

  const refreshMailboxes = async () => {
    const refreshed = await getMailboxes();
    if (refreshed) setMailboxes(refreshed);
  };

  const handleCreateMailbox = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setSubmitError(null);
    if (!selectedDomain) {
      setSubmitError('Create a domain first before adding a mailbox.');
      return;
    }
    if (!localPart.trim() || !displayName.trim() || !password.trim()) {
      setSubmitError('Mailbox local-part, display name, and password are required.');
      return;
    }
    const email = `${localPart.trim().toLowerCase()}@${selectedDomain.name}`;
    setIsSubmitting(true);
    const created = await createMailbox({
      domain_id: selectedDomain.id,
      email,
      display_name: displayName.trim(),
      smtp_password: password,
      imap_password: password,
    });
    setIsSubmitting(false);
    if (!created) {
      setSubmitError('Mailbox create failed. Check the backend response and try again.');
      return;
    }
    setLocalPart('');
    setDisplayName('');
    setPassword('');
    await refreshMailboxes();
  };

  const beginEditMailbox = (mailbox: Mailbox) => {
    setActionError(null);
    setEditingMailboxId(mailbox.id);
    setEditingDisplayName(mailbox.display_name);
    setEditingDailyLimit(String(mailbox.daily_send_limit));
    setEditingStatus(mailbox.status);
  };

  const cancelEditMailbox = () => {
    setEditingMailboxId(null);
    setEditingDisplayName('');
    setEditingDailyLimit('50');
    setEditingStatus('active');
    setActionError(null);
  };

  const handleUpdateMailbox = async (mailboxId: string) => {
    setActionError(null);
    if (!editingDisplayName.trim()) {
      setActionError('Display name is required.');
      return;
    }
    const dailySendLimit = Number(editingDailyLimit);
    if (!Number.isFinite(dailySendLimit) || dailySendLimit <= 0) {
      setActionError('Daily limit must be a positive number.');
      return;
    }

    setBusyMailboxId(mailboxId);
    const updated = await updateMailbox(mailboxId, {
      display_name: editingDisplayName.trim(),
      daily_send_limit: dailySendLimit,
      status: editingStatus,
    });
    setBusyMailboxId(null);

    if (!updated) {
      setActionError('Mailbox update failed. Check the backend response and try again.');
      return;
    }

    setMailboxes((current) => current.map((mailbox) => mailbox.id === mailboxId ? updated : mailbox));
    cancelEditMailbox();
  };

  const handleDeleteMailbox = async (mailboxId: string) => {
    setActionError(null);
    setBusyMailboxId(mailboxId);
    const removed = await deleteMailbox(mailboxId);
    setBusyMailboxId(null);

    if (!removed) {
      setActionError('Mailbox delete failed. Check the backend response and try again.');
      return;
    }

    setMailboxes((current) => current.filter((mailbox) => mailbox.id !== mailboxId));
    if (editingMailboxId === mailboxId) {
      cancelEditMailbox();
    }
  };

  return (
    <div className="space-y-6 animate-fade-in relative min-h-[50vh]">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold text-slate-800 tracking-tight">Infrastructure</h1>
      </div>

      <div className="flex bg-white rounded-xl p-1.5 border border-slate-200 w-fit shadow-sm">
        <button 
          className={`px-6 py-2 rounded-lg font-semibold text-sm transition-all ${activeTab === 'mailboxes' ? 'bg-blue-50 text-blue-700 shadow-sm' : 'text-slate-500 hover:text-slate-700 hover:bg-slate-50'}`}
          onClick={() => setActiveTab('mailboxes')}
        >
          Mailboxes
        </button>
        <button 
          className={`px-6 py-2 rounded-lg font-semibold text-sm transition-all ${activeTab === 'domains' ? 'bg-blue-50 text-blue-700 shadow-sm' : 'text-slate-500 hover:text-slate-700 hover:bg-slate-50'}`}
          onClick={() => setActiveTab('domains')}
        >
          Domains
        </button>
      </div>

      {activeTab === 'mailboxes' ? (
        <form onSubmit={handleCreateMailbox} className="bg-white rounded-2xl border border-slate-200 shadow-sm p-5 grid gap-4 md:grid-cols-2">
          <div>
            <label htmlFor="mailbox-domain" className="block text-sm font-semibold text-slate-700 mb-2">Domain</label>
            <select id="mailbox-domain" data-testid="mailbox-domain-select" value={selectedDomainId} onChange={(event) => setSelectedDomainId(event.target.value)} className="w-full rounded-xl border border-slate-200 px-4 py-3 text-slate-900 outline-none focus:border-blue-500 focus:ring-4 focus:ring-blue-100 transition-all">
              <option value="">Select a domain</option>
              {domains.map((domain) => (
                <option key={domain.id} value={domain.id}>{domain.name}</option>
              ))}
            </select>
          </div>
          <div>
            <label htmlFor="mailbox-local-part" className="block text-sm font-semibold text-slate-700 mb-2">Mailbox Local Part</label>
            <input id="mailbox-local-part" data-testid="mailbox-local-part-input" value={localPart} onChange={(event) => setLocalPart(event.target.value)} placeholder="sales" className="w-full rounded-xl border border-slate-200 px-4 py-3 text-slate-900 outline-none focus:border-blue-500 focus:ring-4 focus:ring-blue-100 transition-all" />
          </div>
          <div>
            <label htmlFor="mailbox-display-name" className="block text-sm font-semibold text-slate-700 mb-2">Display Name</label>
            <input id="mailbox-display-name" data-testid="mailbox-display-name-input" value={displayName} onChange={(event) => setDisplayName(event.target.value)} placeholder="Sales Team" className="w-full rounded-xl border border-slate-200 px-4 py-3 text-slate-900 outline-none focus:border-blue-500 focus:ring-4 focus:ring-blue-100 transition-all" />
          </div>
          <div>
            <label htmlFor="mailbox-password" className="block text-sm font-semibold text-slate-700 mb-2">Mailbox Password</label>
            <input id="mailbox-password" data-testid="mailbox-password-input" type="password" value={password} onChange={(event) => setPassword(event.target.value)} placeholder="Local mailbox password" className="w-full rounded-xl border border-slate-200 px-4 py-3 text-slate-900 outline-none focus:border-blue-500 focus:ring-4 focus:ring-blue-100 transition-all" />
          </div>
          <div className="md:col-span-2 flex items-center justify-between gap-4">
            {submitError ? <div className="text-sm font-medium text-red-700">{submitError}</div> : <div className="text-sm text-slate-500">Safe mode stores the mailbox locally only. It does not provision anything in Mailcow.</div>}
            <button data-testid="create-mailbox-button" type="submit" disabled={isSubmitting || domains.length === 0} className="inline-flex items-center gap-2 rounded-xl bg-slate-900 px-5 py-3 font-medium text-white transition-colors shadow-lg shadow-slate-900/20 active:scale-95 disabled:cursor-not-allowed disabled:opacity-50">
              <Plus size={18} /> {isSubmitting ? 'Adding...' : 'Add Mailbox'}
            </button>
          </div>
        </form>
      ) : (
        <div className="bg-white rounded-2xl border border-slate-200 shadow-sm p-5 text-sm text-slate-600">
          Domain onboarding now lives on the dedicated <a href="/domains" className="font-semibold text-blue-600 hover:underline">Domains</a> page so Mailcow and DNS readiness stay visible.
        </div>
      )}

      {error ? (
         <div className="bg-white rounded-2xl border border-slate-200 shadow-sm flex flex-col items-center justify-center p-16 text-center mt-6">
            <div className="w-16 h-16 bg-red-50 rounded-full flex items-center justify-center mb-4 border border-red-100">
                <ServerCrash className="text-red-500" size={28} />
            </div>
            <h3 className="text-lg font-bold text-slate-800 mb-2">Failed to Load Mailboxes</h3>
            <p className="text-sm text-slate-500 max-w-sm mb-2">Something went wrong while fetching your mailbox infrastructure.</p>
            <p className="text-xs text-red-600 font-medium bg-red-50 px-3 py-1 rounded">{error}</p>
        </div>
      ) : loading ? (
         <div className="flex justify-center items-center py-16 bg-white rounded-2xl border border-slate-200 shadow-sm mt-6">
            <Spinner size="lg" />
         </div>
      ) : activeTab === 'mailboxes' && mailboxes.length > 0 ? (
        <div className="space-y-4">
          {actionError && (
            <div className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm font-medium text-red-700">
              {actionError}
            </div>
          )}
        <div className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="bg-slate-50 border-b border-slate-200">
                <th className="py-4 px-6 font-semibold text-xs text-slate-500 uppercase tracking-wider">Email Server</th>
                <th className="py-4 px-6 font-semibold text-xs text-slate-500 uppercase tracking-wider">Status</th>
                <th className="py-4 px-6 font-semibold text-xs text-slate-500 uppercase tracking-wider w-48">Daily Limit</th>
                <th className="py-4 px-6 font-semibold text-xs text-slate-500 uppercase tracking-wider text-right">Actions</th>
              </tr>
            </thead>
            <tbody>
              {mailboxes.map((mb) => {
                const isEditing = editingMailboxId === mb.id;
                const isBusy = busyMailboxId === mb.id;
                return (
                <tr key={mb.id} className="border-b border-slate-100 hover:bg-slate-50 transition-colors group">
                  <td className="py-4 px-6">
                    <div className="flex items-center gap-4">
                      <div className="p-3 bg-gradient-to-br from-blue-50 to-indigo-50 text-blue-600 rounded-xl shadow-sm border border-blue-100">
                        <Mail size={20} />
                      </div>
                      <div>
                        <p className="font-bold text-slate-800 text-sm mb-0.5">{mb.email}</p>
                        <p className="text-xs text-slate-500 font-medium">{mb.display_name || "SMTP/IMAP Account"}</p>
                      </div>
                    </div>
                  </td>
                  <td className="py-4 px-6">
                    {isEditing ? (
                      <select value={editingStatus} onChange={(event) => setEditingStatus(event.target.value)} className="rounded-lg border border-slate-200 px-3 py-2 text-sm text-slate-700 outline-none focus:border-blue-500">
                        <option value="active">active</option>
                        <option value="paused">paused</option>
                        <option value="disabled">disabled</option>
                      </select>
                    ) : (
                      <span className={`px-3 py-1.5 rounded-full text-xs font-bold tracking-wide border ${mb.status === 'active' ? 'bg-green-50 text-green-700 border-green-200' : 'bg-yellow-50 text-yellow-700 border-yellow-200 shadow-sm'}`}>
                        {mb.status}
                      </span>
                    )}
                  </td>
                  <td className="py-4 px-6">
                    {isEditing ? (
                      <div className="space-y-2">
                        <input
                          value={editingDisplayName}
                          onChange={(event) => setEditingDisplayName(event.target.value)}
                          placeholder="Display name"
                          className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm text-slate-700 outline-none focus:border-blue-500"
                        />
                        <input
                          value={editingDailyLimit}
                          onChange={(event) => setEditingDailyLimit(event.target.value)}
                          type="number"
                          min="1"
                          className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm text-slate-700 outline-none focus:border-blue-500"
                        />
                      </div>
                    ) : (
                      <div className="flex flex-col gap-1.5">
                        <div className="flex justify-between items-center text-xs font-semibold text-slate-600">
                          <span>{mb.display_name || 'Mailbox'}</span>
                          <span>Max {mb.daily_send_limit}</span>
                        </div>
                        <div className="w-full h-2 bg-slate-100 rounded-full overflow-hidden shadow-inner">
                          <div className={`h-full rounded-full ${mb.status === 'active' ? 'bg-gradient-to-r from-green-400 to-green-500' : 'bg-gradient-to-r from-yellow-400 to-amber-500'}`} style={{ width: '0%' }}></div>
                        </div>
                      </div>
                    )}
                  </td>
                  <td className="py-4 px-6 text-right">
                    <div className="flex items-center justify-end gap-2 opacity-100 md:opacity-0 md:group-hover:opacity-100 transition-opacity">
                      {isEditing ? (
                        <>
                          <button
                            data-testid={`save-mailbox-${mb.id}`}
                            disabled={isBusy}
                            onClick={() => void handleUpdateMailbox(mb.id)}
                            className="rounded-lg bg-blue-600 px-3 py-2 text-xs font-bold text-white transition-colors disabled:opacity-50"
                          >
                            {isBusy ? 'Saving...' : 'Save'}
                          </button>
                          <button
                            data-testid={`cancel-mailbox-${mb.id}`}
                            onClick={cancelEditMailbox}
                            className="rounded-lg border border-slate-200 px-3 py-2 text-xs font-bold text-slate-600 transition-colors hover:bg-slate-50"
                          >
                            Cancel
                          </button>
                        </>
                      ) : (
                        <>
                          <button
                            data-testid={`edit-mailbox-${mb.id}`}
                            onClick={() => beginEditMailbox(mb)}
                            className="p-2 text-slate-400 hover:text-blue-600 hover:bg-blue-50 rounded-lg transition-colors border border-transparent hover:border-blue-100"
                          >
                            <Edit2 size={16} />
                          </button>
                          <button
                            data-testid={`delete-mailbox-${mb.id}`}
                            disabled={isBusy}
                            onClick={() => void handleDeleteMailbox(mb.id)}
                            className="p-2 text-slate-400 hover:text-red-600 hover:bg-red-50 rounded-lg transition-colors border border-transparent hover:border-red-100 disabled:opacity-50"
                          >
                            <Trash2 size={16} />
                          </button>
                        </>
                      )}
                    </div>
                  </td>
                </tr>
              )})}
            </tbody>
          </table>
        </div>
        </div>
      ) : activeTab === 'mailboxes' ? (
        <div className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden flex flex-col items-center justify-center p-16">
           <div className="w-20 h-20 bg-slate-50 rounded-full flex items-center justify-center mb-6 shadow-inner border border-slate-100">
             <Globe className="text-slate-300" size={32} />
           </div>
           <h3 className="text-xl font-bold text-slate-800 mb-2">No Mailboxes Found</h3>
           <p className="text-sm text-slate-500 mb-6 max-w-sm text-center">Use the form above to add the first local mailbox for a verified or local-only domain.</p>
        </div>
      ) : null}
    </div>
  );
}
