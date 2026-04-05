"use client";
import { useState, useEffect } from 'react';
import { Plus, Globe, Mail, Edit2, Trash2, ServerCrash } from 'lucide-react';
import { useApiService } from '@/services/api';
import { Mailbox } from '@/types/models';
import Spinner from '@/components/ui/Spinner';

export default function MailboxesPage() {
  const [activeTab, setActiveTab] = useState('mailboxes');
  const { getMailboxes, loading, error } = useApiService();
  const [mailboxes, setMailboxes] = useState<Mailbox[]>([]);

  useEffect(() => {
    const fetchBoxes = async () => {
        const data = await getMailboxes();
        if (data) setMailboxes(data);
    };
    if (activeTab === 'mailboxes') fetchBoxes();
  }, [getMailboxes, activeTab]);

  return (
    <div className="space-y-6 animate-fade-in relative min-h-[50vh]">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold text-slate-800 tracking-tight">Infrastructure</h1>
        <button className="bg-slate-900 hover:bg-slate-800 text-white px-5 py-2.5 rounded-xl font-medium transition-colors shadow-lg shadow-slate-900/20 active:scale-95 flex items-center gap-2">
          <Plus size={18} /> Add {activeTab === 'mailboxes' ? 'Mailbox' : 'Domain'}
        </button>
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
              {mailboxes.map((mb) => (
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
                    <span className={`px-3 py-1.5 rounded-full text-xs font-bold tracking-wide border ${mb.status === 'active' ? 'bg-green-50 text-green-700 border-green-200' : 'bg-yellow-50 text-yellow-700 border-yellow-200 shadow-sm'}`}>
                      {mb.status}
                    </span>
                  </td>
                  <td className="py-4 px-6">
                    <div className="flex flex-col gap-1.5">
                      <div className="flex justify-between items-center text-xs font-semibold text-slate-600">
                        <span>Max {mb.daily_send_limit}</span>
                        <span>0%</span>
                      </div>
                      <div className="w-full h-2 bg-slate-100 rounded-full overflow-hidden shadow-inner">
                        <div className={`h-full rounded-full ${mb.status === 'active' ? 'bg-gradient-to-r from-green-400 to-green-500' : 'bg-gradient-to-r from-yellow-400 to-amber-500'}`} style={{ width: '0%' }}></div>
                      </div>
                    </div>
                  </td>
                  <td className="py-4 px-6 text-right">
                    <div className="flex items-center justify-end gap-2 opacity-0 group-hover:opacity-100 transition-opacity">
                      <button className="p-2 text-slate-400 hover:text-blue-600 hover:bg-blue-50 rounded-lg transition-colors border border-transparent hover:border-blue-100">
                        <Edit2 size={16} />
                      </button>
                      <button className="p-2 text-slate-400 hover:text-red-600 hover:bg-red-50 rounded-lg transition-colors border border-transparent hover:border-red-100">
                        <Trash2 size={16} />
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <div className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden flex flex-col items-center justify-center p-16">
           <div className="w-20 h-20 bg-slate-50 rounded-full flex items-center justify-center mb-6 shadow-inner border border-slate-100">
             <Globe className="text-slate-300" size={32} />
           </div>
           <h3 className="text-xl font-bold text-slate-800 mb-2">No {activeTab} Found</h3>
           <p className="text-sm text-slate-500 mb-6 max-w-sm text-center">Add your first {activeTab === 'mailboxes' ? 'mailbox' : 'domain'} to start configuring and sending emails.</p>
           <button className="bg-blue-600 hover:bg-blue-700 text-white px-6 py-2.5 rounded-xl font-medium transition-colors shadow-lg shadow-blue-600/30">
             Add {activeTab === 'mailboxes' ? 'Mailbox' : 'Domain'}
           </button>
        </div>
      )}
    </div>
  );
}
