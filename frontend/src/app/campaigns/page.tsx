import { Plus, Users, BarChart2, Calendar } from 'lucide-react';

export default function CampaignsPage() {
  return (
    <div className="space-y-6 animate-fade-in">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold text-slate-800 tracking-tight">Campaigns</h1>
        <button className="bg-slate-900 hover:bg-slate-800 text-white px-5 py-2.5 rounded-xl font-bold transition-colors shadow-lg shadow-slate-900/20 active:scale-95 flex items-center gap-2">
          <Plus size={18} strokeWidth={3} /> Create Campaign
        </button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {[
          { name: 'Q4 SaaS Outreach', leads: 450, sent: 320, replies: '4.5%', status: 'Running' },
          { name: 'Partnership V2', leads: 120, sent: 120, replies: '12%', status: 'Finished' },
        ].map((campaign, i) => (
          <div key={i} className="bg-white rounded-2xl border border-slate-200 shadow-sm hover:shadow-md transition-all p-7 group cursor-pointer relative overflow-hidden">
            <div className={`absolute top-0 right-0 w-32 h-32 rounded-full blur-3xl -mr-16 -mt-16 opacity-30 group-hover:opacity-70 transition-opacity ${campaign.status === 'Running' ? 'bg-blue-300' : 'bg-slate-300'}`}></div>
            <div className="relative z-10">
              <div className="flex justify-between items-start mb-6">
                <div>
                  <h3 className="text-xl font-extrabold text-slate-800 mb-1.5 group-hover:text-blue-600 transition-colors">{campaign.name}</h3>
                  <p className="text-sm font-semibold text-slate-400 flex items-center gap-1.5">
                    <Calendar size={14}/> Started 2 weeks ago
                  </p>
                </div>
                <span className={`px-4 py-1 text-xs font-bold tracking-wide rounded-full border shadow-sm ${campaign.status === 'Running' ? 'bg-blue-50 text-blue-700 border-blue-200' : 'bg-slate-50 text-slate-600 border-slate-200'}`}>
                  {campaign.status}
                </span>
              </div>
              
              <div className="grid grid-cols-3 gap-4 border-t border-slate-100 pt-6">
                <div>
                  <p className="text-xs font-bold text-slate-400 uppercase tracking-widest mb-1 shadow-sm flex items-center gap-1.5"><Users size={14}/> Leads</p>
                  <p className="text-3xl font-extrabold text-slate-800">{campaign.leads}</p>
                </div>
                <div>
                  <p className="text-xs font-bold text-slate-400 uppercase tracking-widest mb-1 shadow-sm flex items-center gap-1.5"><BarChart2 size={14}/> Sent</p>
                  <p className="text-3xl font-extrabold text-slate-800">{campaign.sent}</p>
                </div>
                 <div>
                  <p className="text-xs font-bold text-slate-400 uppercase tracking-widest mb-1 shadow-sm">Reply Rate</p>
                  <p className="text-3xl font-extrabold text-green-600">{campaign.replies}</p>
                </div>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
