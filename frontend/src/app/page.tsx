"use client";

import { Send, Globe, Inbox, Activity, AlertCircle } from 'lucide-react';
import { useApiService } from '@/services/api';
import { useEffect, useState } from 'react';
import Spinner from '@/components/ui/Spinner';
import { DeliverabilitySummary } from '@/types/models';

export default function Dashboard() {
  const { getDeliverabilitySummary, getMailboxes, loading, error } = useApiService();
  const [stats, setStats] = useState<DeliverabilitySummary | null>(null);
  const [mailboxCount, setMailboxCount] = useState<number>(0);

  useEffect(() => {
    const fetchDashboardStats = async () => {
      // In a real load we would do Promise.all, but we handle missing endpoints gracefully
      const res = await getDeliverabilitySummary();
      if (res) setStats(res);
      
      const boxes = await getMailboxes();
      if (boxes) setMailboxCount(boxes.length);
    };
    fetchDashboardStats();
  }, [getDeliverabilitySummary, getMailboxes]);

  return (
    <div className="space-y-6 animate-fade-in relative min-h-screen">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold text-slate-800 tracking-tight">Dashboard Overview</h1>
        <button className="bg-blue-600 hover:bg-blue-700 text-white px-5 py-2.5 rounded-xl font-medium transition-colors shadow-lg shadow-blue-600/30 active:scale-95">
          + New Campaign
        </button>
      </div>
      
      {error && !stats ? (
        <div className="p-6 bg-red-50 border border-red-200 text-red-700 rounded-2xl flex flex-col items-center justify-center h-64 shadow-sm text-center">
            <AlertCircle className="mb-4 text-red-500" size={32} />
            <span className="font-bold mb-2">Backend Connection Error</span>
            <span className="text-sm">{error}</span>
        </div>
      ) : loading && !stats ? (
        <div className="h-64 flex items-center justify-center bg-white rounded-2xl border border-slate-200">
          <Spinner size="lg" />
        </div>
      ) : (
        <>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
            <StatCard title="Emails Sent Today" value={stats?.sent || 0} icon={<Send size={24} />} trend="Live analytics" />
            <StatCard title="Active Mailboxes" value={mailboxCount} icon={<Globe size={24} />} trend="Global infrastructure" />
            <StatCard title="Total Replies" value={stats?.replied || 0} icon={<Inbox size={24} />} trend="User-level responses" />
            <StatCard title="Bounces Blocked" value={stats?.suppressed || 0} icon={<Activity size={24} />} trend="Autosuppression active" success={true} />
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mt-8">
            <div className="col-span-2 bg-white rounded-2xl p-6 border border-slate-200 shadow-sm flex flex-col items-center justify-center min-h-[300px]">
              <h2 className="text-lg font-semibold text-slate-800 mb-6 flex items-center gap-2 self-start">
                <Activity className="text-blue-500" size={20} /> Sending Volume
              </h2>
              <div className="flex flex-col items-center text-slate-400">
                <BarChartPlaceholder />
                <p className="font-medium text-sm mt-4">Not enough data to render volume charts yet.</p>
              </div>
            </div>
            
            <div className="bg-white rounded-2xl p-6 border border-slate-200 shadow-sm flex flex-col">
              <h2 className="text-lg font-semibold text-slate-800 mb-6 flex items-center gap-2">
                <Inbox className="text-indigo-500" size={20} /> Recent AI Summaries
              </h2>
              <div className="flex-1 flex flex-col items-center justify-center text-slate-400 pb-10">
                 <Inbox className="opacity-20 mb-3" size={48} />
                 <p className="text-sm font-semibold">No recent unread thread summaries.</p>
              </div>
            </div>
          </div>
        </>
      )}
    </div>
  );
}

function BarChartPlaceholder() {
    return (
        <div className="flex items-end gap-2 opacity-50 h-32">
            {[40, 70, 30, 80, 50, 100, 60].map((h, i) => (
                <div key={i} className="w-8 bg-slate-200 rounded-t-md" style={{ height: `${h}%` }}></div>
            ))}
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
