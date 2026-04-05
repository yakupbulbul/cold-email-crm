"use client";

import { useEffect, useState } from 'react';
import { Plus, Users, BarChart2, Calendar, AlertCircle } from 'lucide-react';
import { useApiService } from '@/services/api';
import { Campaign } from '@/types/models';
import Spinner from '@/components/ui/Spinner';

export default function CampaignsPage() {
  const { getCampaigns, loading, error } = useApiService();
  const [campaigns, setCampaigns] = useState<Campaign[]>([]);

  useEffect(() => {
    const fetchCampaigns = async () => {
      const data = await getCampaigns();
      if (data) setCampaigns(data);
    };
    fetchCampaigns();
  }, [getCampaigns]);

  return (
    <div className="space-y-6 animate-fade-in relative min-h-[50vh]">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold text-slate-800 tracking-tight">Campaigns</h1>
        <button className="bg-slate-900 hover:bg-slate-800 text-white px-5 py-2.5 rounded-xl font-bold transition-colors shadow-lg shadow-slate-900/20 active:scale-95 flex items-center gap-2">
          <Plus size={18} strokeWidth={3} /> Create Campaign
        </button>
      </div>

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
          <p className="text-sm text-slate-500 max-w-sm mb-6">You haven't created any campaigns yet. Start your first outreach sequence.</p>
          <button className="bg-slate-900 hover:bg-slate-800 text-white px-5 py-2.5 rounded-xl font-bold transition-colors shadow-lg shadow-slate-900/20 active:scale-95">
            Create Campaign
          </button>
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
