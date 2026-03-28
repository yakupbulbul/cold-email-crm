"use client";

import { Send, Globe, Inbox, Activity } from 'lucide-react';
import { useApi } from '@/hooks/useApi';
import { useEffect, useState } from 'react';
import Spinner from '@/components/ui/Spinner';

export default function Dashboard() {
  const { request, loading } = useApi();
  const [stats, setStats] = useState({
    sent: "1,284",
    mailboxes: "8",
    unread: "23",
    health: "98%"
  });

  useEffect(() => {
    // In Phase 10 we hook this up via useApi, simulating the load for now seamlessly.
    const fetchDashboardStats = async () => {
      // Stubbing the V1 aggregated analytics endpoint request
      // const data = await request('/analytics/dashboard');
      // if (data) setStats(data);
    };
    fetchDashboardStats();
  }, [request]);

  return (
    <div className="space-y-6 animate-fade-in relative min-h-screen">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold text-slate-800 tracking-tight">Dashboard Overview</h1>
        <button className="bg-blue-600 hover:bg-blue-700 text-white px-5 py-2.5 rounded-xl font-medium transition-colors shadow-lg shadow-blue-600/30 active:scale-95">
          + New Campaign
        </button>
      </div>
      
      {loading ? (
        <div className="h-64 flex items-center justify-center bg-white rounded-2xl border border-slate-200">
          <Spinner size="lg" />
        </div>
      ) : (
        <>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
            <StatCard title="Emails Sent Today" value={stats.sent} icon={<Send size={24} />} trend="+12% from yesterday" />
            <StatCard title="Active Mailboxes" value={stats.mailboxes} icon={<Globe size={24} />} trend="All systems normal" />
            <StatCard title="Unread Replies" value={stats.unread} icon={<Inbox size={24} />} trend="5 high intent" alert />
            <StatCard title="Warm-up Health" value={stats.health} icon={<Activity size={24} />} trend="Excellent condition" success />
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mt-8">
            <div className="col-span-2 bg-white rounded-2xl p-6 border border-slate-200 shadow-sm">
              <h2 className="text-lg font-semibold text-slate-800 mb-6 flex items-center gap-2">
                <Activity className="text-blue-500" size={20} /> Sending Volume
              </h2>
              <div className="h-72 flex items-center justify-center text-slate-400 bg-gradient-to-br from-slate-50 to-slate-100 rounded-xl border border-dashed border-slate-200">
                <p className="font-medium text-sm">Real-time Volume Analytics coming in Phase 15</p>
              </div>
            </div>
            
            <div className="bg-white rounded-2xl p-6 border border-slate-200 shadow-sm flex flex-col">
              <h2 className="text-lg font-semibold text-slate-800 mb-6 flex items-center gap-2">
                <Inbox className="text-indigo-500" size={20} /> Recent AI Summaries
              </h2>
              <div className="space-y-4 flex-1 overflow-y-auto pr-2">
                <div className="p-4 rounded-xl bg-blue-50/50 border border-blue-100 flex flex-col justify-between">
                  <div className="flex justify-between items-start mb-2">
                    <span className="font-semibold text-sm text-slate-800">Acme Corp</span>
                    <span className="text-xs bg-green-100 text-green-700 px-2.5 py-0.5 rounded-full font-semibold tracking-wide">Positive</span>
                  </div>
                  <p className="text-sm text-slate-600 line-clamp-2">They are interested in a demo next Tuesday. Asking for available times.</p>
                </div>
                <div className="p-4 rounded-xl bg-slate-50 border border-slate-100 flex flex-col justify-between">
                  <div className="flex justify-between items-start mb-2">
                    <span className="font-semibold text-sm text-slate-800">TechFlow Inc</span>
                    <span className="text-xs bg-yellow-100 text-yellow-700 px-2.5 py-0.5 rounded-full font-semibold tracking-wide">Question</span>
                  </div>
                  <p className="text-sm text-slate-600 line-clamp-2">Asking about pricing structure for teams over 50 users. Needs clarification.</p>
                </div>
              </div>
              <button className="w-full mt-4 text-center text-sm font-semibold text-blue-600 hover:text-blue-700 py-2">
                View all in Inbox &rarr;
              </button>
            </div>
          </div>
        </>
      )}
    </div>
  );
}

function StatCard({ title, value, icon, trend, alert = false, success = false }: any) {
  return (
    <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm hover:shadow-md transition-all group overflow-hidden relative">
      <div className={`absolute top-0 right-0 w-32 h-32 bg-gradient-to-br ${success ? 'from-green-50 to-green-100' : alert ? 'from-red-50 to-red-100' : 'from-blue-50 to-indigo-50'} rounded-full blur-3xl -mr-16 -mt-16 opacity-50 group-hover:opacity-100 transition-opacity`}></div>
      <div className="relative z-10">
        <div className="flex items-start justify-between">
          <div>
            <p className="text-sm font-semibold text-slate-500 mb-2 uppercase tracking-wider">{title}</p>
            <h3 className="text-4xl font-extrabold text-slate-800 tracking-tight">{value}</h3>
          </div>
          <div className={`p-3.5 rounded-2xl ${alert ? 'bg-red-100 text-red-600' : success ? 'bg-green-100 text-green-600' : 'bg-blue-100 text-blue-600'} shadow-sm`}>
            {icon}
          </div>
        </div>
        <div className="flex items-center gap-1.5 mt-5">
          <div className={`w-2 h-2 rounded-full ${alert ? 'bg-red-500' : success ? 'bg-green-500' : 'bg-blue-500'}`}></div>
          <p className={`text-sm font-medium ${alert ? 'text-red-600' : success ? 'text-green-600' : 'text-slate-600'}`}>
            {trend}
          </p>
        </div>
      </div>
    </div>
  );
}
