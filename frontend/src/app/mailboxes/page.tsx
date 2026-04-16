"use client";
import { useState, useEffect } from 'react';
import { Plus, Mail, Edit2, ShieldCheck, Trash2, ServerCrash, Link2, Unplug } from 'lucide-react';
import { useApiService } from '@/services/api';
import { Domain, MailProviderType, Mailbox, SMTPDiagnosticResult, SettingsSummary } from '@/types/models';
import Spinner from '@/components/ui/Spinner';
import { AlertBanner, EmptyState, MetricCard, PageHeader, SurfaceCard } from '@/components/ui/primitives';

export default function MailboxesPage() {
  const { getMailboxes, getDomains, getSettingsSummary, createMailbox, updateMailbox, deleteMailbox, checkMailboxProvider, startMailboxOAuth, disconnectMailboxOAuth, loading, error } = useApiService();
  const [mailboxes, setMailboxes] = useState<Mailbox[]>([]);
  const [domains, setDomains] = useState<Domain[]>([]);
  const [settingsSummary, setSettingsSummary] = useState<SettingsSummary | null>(null);
  const [selectedDomainId, setSelectedDomainId] = useState('');
  const [localPart, setLocalPart] = useState('');
  const [displayName, setDisplayName] = useState('');
  const [providerType, setProviderType] = useState<MailProviderType>('mailcow');
  const [password, setPassword] = useState('');
  const [smtpSecurityMode, setSmtpSecurityMode] = useState<'starttls' | 'ssl' | 'plain'>('starttls');
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [editingMailboxId, setEditingMailboxId] = useState<string | null>(null);
  const [editingDisplayName, setEditingDisplayName] = useState('');
  const [editingDailyLimit, setEditingDailyLimit] = useState('50');
  const [editingStatus, setEditingStatus] = useState('active');
  const [editingSecurityMode, setEditingSecurityMode] = useState<'starttls' | 'ssl' | 'plain'>('starttls');
  const [actionError, setActionError] = useState<string | null>(null);
  const [busyMailboxId, setBusyMailboxId] = useState<string | null>(null);
  const [smtpDiagnostics, setSmtpDiagnostics] = useState<Record<string, SMTPDiagnosticResult>>({});

  useEffect(() => {
    const fetchPageData = async () => {
        const [mailboxData, domainData, settingsData] = await Promise.all([getMailboxes(), getDomains(), getSettingsSummary()]);
        if (mailboxData) setMailboxes(mailboxData);
        if (domainData) {
          setDomains(domainData);
          setSelectedDomainId((current) => current || domainData[0]?.id || '');
        }
        if (settingsData) {
          setSettingsSummary(settingsData);
          setProviderType(settingsData.default_provider);
        }
    };
    fetchPageData();
  }, [getMailboxes, getDomains, getSettingsSummary]);

  const selectedDomain = domains.find((domain) => domain.id === selectedDomainId);

  const refreshMailboxes = async () => {
    const refreshed = await getMailboxes();
    if (refreshed) setMailboxes(refreshed);
  };

  const enabledProviders = settingsSummary?.enabled_providers || [];
  const mailboxModeMessage = providerType === "mailcow"
    ? (settingsSummary?.mailcow_mutations_enabled
      ? 'Mutation mode creates the mailbox in Mailcow and CRM together. If Mailcow rejects the request, nothing is stored locally.'
      : 'Safe mode stores the Mailcow mailbox locally only. It does not provision anything in Mailcow.')
    : 'Google Workspace mailboxes use backend-only OAuth. SMTP and IMAP routing stay unified after connection.';

  const handleCreateMailbox = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setSubmitError(null);
    if (!selectedDomain) {
      setSubmitError('Create a domain first before adding a mailbox.');
      return;
    }
    if (!localPart.trim() || !displayName.trim()) {
      setSubmitError('Mailbox local-part and display name are required.');
      return;
    }
    if (providerType === "mailcow" && !password.trim()) {
      setSubmitError('Mailcow mailboxes require the mailbox password.');
      return;
    }
    const email = `${localPart.trim().toLowerCase()}@${selectedDomain.name}`;
    setIsSubmitting(true);
    let created: Mailbox | null = null;
    try {
      created = await createMailbox({
        domain_id: selectedDomain.id,
        email,
        display_name: displayName.trim(),
        provider_type: providerType,
        smtp_security_mode: smtpSecurityMode,
        smtp_password: providerType === "mailcow" ? password : undefined,
        imap_password: providerType === "mailcow" ? password : undefined,
        oauth_enabled: providerType === "google_workspace",
      });
    } catch (createError) {
      setSubmitError(createError instanceof Error ? createError.message : 'Mailbox create failed.');
    }
    setIsSubmitting(false);
    if (!created) {
      return;
    }
    setLocalPart('');
    setDisplayName('');
    setPassword('');
    setSmtpSecurityMode('starttls');
    await refreshMailboxes();
  };

  const beginEditMailbox = (mailbox: Mailbox) => {
    setActionError(null);
    setEditingMailboxId(mailbox.id);
    setEditingDisplayName(mailbox.display_name);
    setEditingDailyLimit(String(mailbox.daily_send_limit));
    setEditingStatus(mailbox.status);
    setEditingSecurityMode(mailbox.smtp_security_mode);
  };

  const cancelEditMailbox = () => {
    setEditingMailboxId(null);
    setEditingDisplayName('');
    setEditingDailyLimit('50');
    setEditingStatus('active');
    setEditingSecurityMode('starttls');
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
      smtp_security_mode: editingSecurityMode,
    });
    setBusyMailboxId(null);

    if (!updated) {
      setActionError('Mailbox update failed. Check the backend response and try again.');
      return;
    }

    setMailboxes((current) => current.map((mailbox) => mailbox.id === mailboxId ? updated : mailbox));
    cancelEditMailbox();
  };

  const handleCheckMailboxProvider = async (mailboxId: string) => {
    setActionError(null);
    setBusyMailboxId(mailboxId);
    try {
      const result = await checkMailboxProvider(mailboxId);
      setSmtpDiagnostics((current) => ({ ...current, [mailboxId]: { ...current[mailboxId], status: result.smtp.status, category: result.smtp.category, message: `${result.smtp.message} IMAP: ${result.imap.message}`, host: "", port: 0, security_mode: "starttls", dns_resolved: true, connected: true, tls_negotiated: true, auth_succeeded: result.smtp.status === "healthy" } }));
      await refreshMailboxes();
    } catch (checkError) {
      setActionError(checkError instanceof Error ? checkError.message : 'Provider check failed.');
    } finally {
      setBusyMailboxId(null);
    }
  };

  const handleStartOAuth = async (mailboxId: string) => {
    setActionError(null);
    setBusyMailboxId(mailboxId);
    try {
      const result = await startMailboxOAuth(mailboxId);
      window.open(result.authorization_url, "_blank", "noopener,noreferrer");
    } catch (oauthError) {
      setActionError(oauthError instanceof Error ? oauthError.message : "Google OAuth start failed.");
    } finally {
      setBusyMailboxId(null);
    }
  };

  const handleDisconnectOAuth = async (mailboxId: string) => {
    setActionError(null);
    setBusyMailboxId(mailboxId);
    try {
      const updated = await disconnectMailboxOAuth(mailboxId);
      setMailboxes((current) => current.map((mailbox) => mailbox.id === mailboxId ? updated : mailbox));
    } catch (oauthError) {
      setActionError(oauthError instanceof Error ? oauthError.message : "Google OAuth disconnect failed.");
    } finally {
      setBusyMailboxId(null);
    }
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
      <PageHeader
        eyebrow="Infrastructure"
        title="Mailbox management"
        description="Configure sender identity, SMTP transport posture, and operational mailbox status from one place."
      />

      <div className="grid gap-4 md:grid-cols-3">
        <MetricCard title="Configured mailboxes" value={mailboxes.length} detail="Senders currently available in the app." icon={Mail} />
        <MetricCard title="Domains" value={domains.length} detail="Verified or local domains ready for mailbox creation." icon={ShieldCheck} tone="info" />
        <MetricCard title="Provisioning mode" value={providerType === "mailcow" ? (settingsSummary?.mailcow_mutations_enabled ? "Mailcow synced" : "Local only") : "OAuth mailbox"} detail={mailboxModeMessage} icon={Edit2} tone={providerType === "mailcow" && settingsSummary?.mailcow_mutations_enabled ? "success" : "warning"} />
      </div>

      <SurfaceCard className="p-5">
      <form onSubmit={handleCreateMailbox} className="grid gap-4 md:grid-cols-2">
          <div>
            <label htmlFor="mailbox-provider" className="block text-sm font-semibold text-slate-700 mb-2">Provider</label>
            <select id="mailbox-provider" value={providerType} onChange={(event) => setProviderType(event.target.value as MailProviderType)} className="form-input">
              {(["mailcow", "google_workspace"] as MailProviderType[]).filter((provider) => enabledProviders.includes(provider)).map((provider) => (
                <option key={provider} value={provider}>{provider === "mailcow" ? "Mailcow" : "Google Workspace"}</option>
              ))}
            </select>
          </div>
          <div>
            <label htmlFor="mailbox-domain" className="block text-sm font-semibold text-slate-700 mb-2">Domain</label>
            <select id="mailbox-domain" data-testid="mailbox-domain-select" value={selectedDomainId} onChange={(event) => setSelectedDomainId(event.target.value)} className="form-input">
              <option value="">Select a domain</option>
              {domains.map((domain) => (
                <option key={domain.id} value={domain.id}>{domain.name}</option>
              ))}
            </select>
          </div>
          <div>
            <label htmlFor="mailbox-local-part" className="block text-sm font-semibold text-slate-700 mb-2">Mailbox Local Part</label>
            <input id="mailbox-local-part" data-testid="mailbox-local-part-input" value={localPart} onChange={(event) => setLocalPart(event.target.value)} placeholder="sales" className="form-input" />
          </div>
          <div>
            <label htmlFor="mailbox-display-name" className="block text-sm font-semibold text-slate-700 mb-2">Display Name</label>
            <input id="mailbox-display-name" data-testid="mailbox-display-name-input" value={displayName} onChange={(event) => setDisplayName(event.target.value)} placeholder="Sales Team" className="form-input" />
            <p className="mt-2 text-xs text-slate-500">This becomes the visible sender name in email clients, for example: Sales Team &lt;sales@example.com&gt;.</p>
          </div>
          <div>
            <label htmlFor="mailbox-password" className="block text-sm font-semibold text-slate-700 mb-2">Mailbox Password</label>
            <input id="mailbox-password" data-testid="mailbox-password-input" type="password" value={password} onChange={(event) => setPassword(event.target.value)} placeholder={providerType === "mailcow" ? "Local mailbox password" : "Not required for OAuth mailboxes"} disabled={providerType !== "mailcow"} className="form-input disabled:bg-slate-100 disabled:text-slate-400" />
          </div>
          <div>
            <label htmlFor="mailbox-smtp-mode" className="block text-sm font-semibold text-slate-700 mb-2">SMTP Security Mode</label>
            <select id="mailbox-smtp-mode" value={smtpSecurityMode} onChange={(event) => setSmtpSecurityMode(event.target.value as 'starttls' | 'ssl' | 'plain')} className="form-input">
              <option value="starttls">STARTTLS</option>
              <option value="ssl">SSL/TLS</option>
              <option value="plain">Plain</option>
            </select>
          </div>
          <div className="md:col-span-2 flex items-center justify-between gap-4">
            {submitError ? <div className="text-sm font-medium text-red-700">{submitError}</div> : <div data-testid="mailbox-mode-message" className="text-sm text-slate-500">{mailboxModeMessage}</div>}
            <button data-testid="create-mailbox-button" type="submit" disabled={isSubmitting || domains.length === 0} className="btn-primary">
              <Plus size={18} /> {isSubmitting ? 'Adding...' : 'Add Mailbox'}
            </button>
          </div>
      </form>
      </SurfaceCard>

      {error ? (
         <SurfaceCard className="mt-6 flex flex-col items-center justify-center p-16 text-center">
            <div className="w-16 h-16 bg-red-50 rounded-full flex items-center justify-center mb-4 border border-red-100">
                <ServerCrash className="text-red-500" size={28} />
            </div>
            <h3 className="text-lg font-bold text-slate-800 mb-2">Failed to Load Mailboxes</h3>
            <p className="text-sm text-slate-500 max-w-sm mb-2">Something went wrong while fetching your mailbox infrastructure.</p>
            <p className="text-xs text-red-600 font-medium bg-red-50 px-3 py-1 rounded">{error}</p>
        </SurfaceCard>
      ) : loading ? (
         <SurfaceCard className="mt-6 flex justify-center items-center py-16">
            <Spinner size="lg" />
         </SurfaceCard>
      ) : mailboxes.length > 0 ? (
        <div className="space-y-4">
          {actionError ? <AlertBanner tone="danger" title="Mailbox action failed">{actionError}</AlertBanner> : null}
        <SurfaceCard className="overflow-hidden">
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
                const diagnostic = smtpDiagnostics[mb.id];
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
                        <p className="mt-1 text-[11px] font-semibold uppercase tracking-wide text-slate-500">{mb.provider_type.replaceAll("_", " ")}</p>
                        <p className="mt-1 text-[11px] text-slate-500">Visible sender: {mb.display_name?.trim() ? `${mb.display_name} <${mb.email}>` : mb.email}</p>
                        <p className={`mt-1 inline-flex rounded-full px-2.5 py-1 text-[11px] font-semibold ${
                          mb.provider_type === "mailcow" && mb.remote_mailcow_provisioned ? 'bg-blue-50 text-blue-700 border border-blue-200' : 'bg-slate-100 text-slate-600 border border-slate-200'
                        }`}>
                          {mb.provider_type === "mailcow" ? (mb.remote_mailcow_provisioned ? 'Mailcow synced' : 'Local only') : (mb.oauth_connection_status || 'OAuth pending').replaceAll("_", " ")}
                        </p>
                        <p className="mt-1 text-[11px] font-medium text-slate-500">SMTP {mb.smtp_security_mode.toUpperCase()} on {mb.smtp_host}:{mb.smtp_port}</p>
                        <p className="mt-1 text-[11px] font-medium text-slate-500">IMAP {(mb.imap_security_mode || 'ssl').toUpperCase()} on {mb.imap_host}:{mb.imap_port}</p>
                        <p className={`mt-1 text-[11px] font-medium ${((diagnostic?.status || mb.smtp_last_check_status) === 'healthy') ? 'text-emerald-700' : 'text-slate-500'}`}>
                          {diagnostic?.message || mb.last_provider_check_message || mb.smtp_last_check_message || 'Provider diagnostics have not been checked yet.'}
                        </p>
                        {mb.provider_type === "google_workspace" ? (
                          <p className="mt-1 text-[11px] font-medium text-slate-500">
                            OAuth: {(mb.oauth_connection_status || "not_connected").replaceAll("_", " ")}
                            {mb.external_account_email ? ` as ${mb.external_account_email}` : ""}
                          </p>
                        ) : null}
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
                        <select value={editingSecurityMode} onChange={(event) => setEditingSecurityMode(event.target.value as 'starttls' | 'ssl' | 'plain')} className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm text-slate-700 outline-none focus:border-blue-500">
                          <option value="starttls">STARTTLS</option>
                          <option value="ssl">SSL/TLS</option>
                          <option value="plain">Plain</option>
                        </select>
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
                            data-testid={`check-smtp-mailbox-${mb.id}`}
                            disabled={isBusy}
                            onClick={() => void handleCheckMailboxProvider(mb.id)}
                            className="p-2 text-slate-400 hover:text-emerald-600 hover:bg-emerald-50 rounded-lg transition-colors border border-transparent hover:border-emerald-100 disabled:opacity-50"
                          >
                            <ShieldCheck size={16} />
                          </button>
                          {mb.provider_type === "google_workspace" ? (
                            mb.oauth_connection_status === "connected" ? (
                              <button
                                type="button"
                                disabled={isBusy}
                                onClick={() => void handleDisconnectOAuth(mb.id)}
                                className="p-2 text-slate-400 hover:text-amber-600 hover:bg-amber-50 rounded-lg transition-colors border border-transparent hover:border-amber-100 disabled:opacity-50"
                                title="Disconnect Google OAuth"
                              >
                                <Unplug size={16} />
                              </button>
                            ) : (
                              <button
                                type="button"
                                disabled={isBusy}
                                onClick={() => void handleStartOAuth(mb.id)}
                                className="p-2 text-slate-400 hover:text-violet-600 hover:bg-violet-50 rounded-lg transition-colors border border-transparent hover:border-violet-100 disabled:opacity-50"
                                title="Connect Google OAuth"
                              >
                                <Link2 size={16} />
                              </button>
                            )
                          ) : null}
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
        </SurfaceCard>
        </div>
      ) : (
        <EmptyState
          icon={Mail}
          title="No mailboxes found"
          description="Use the form above to add the first local mailbox for a verified or local-only domain."
        />
      )}
    </div>
  );
}
