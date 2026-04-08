"use client";

import { Send, Globe, Inbox, Activity, AlertCircle } from 'lucide-react';
import { useApiService } from '@/services/api';
import { useEffect, useState } from 'react';
import Spinner from '@/components/ui/Spinner';
import { DeliverabilitySummary } from '@/types/models';
import { ReactNode } from 'react';

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
            <StatCard title="Total Contacts" value={stats?.total_contacts || 0} icon={<Send size={24} />} trend="Unified B2B + B2C audience" />
            <StatCard title="Active Mailboxes" value={stats?.mailbox_count || mailboxCount} icon={<Globe size={24} />} trend="Global infrastructure" />
            <StatCard title="B2B Campaigns" value={stats?.b2b_campaigns || 0} icon={<Inbox size={24} />} trend="Typed outreach engine" />
            <StatCard title="B2C Campaigns" value={stats?.b2c_campaigns || 0} icon={<Activity size={24} />} trend="Compliance-aware audience sends" success={true} />
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mt-8">
            <div className="col-span-2 bg-white rounded-2xl p-6 border border-slate-200 shadow-sm flex flex-col items-center justify-center min-h-[300px]">
              <h2 className="text-lg font-semibold text-slate-800 mb-6 flex items-center gap-2 self-start">
                <Activity className="text-blue-500" size={20} /> Audience Quality
              </h2>
              <div className="grid w-full gap-4 md:grid-cols-3">
                <StatMini label="Valid" value={stats?.valid_contacts || 0} tone="emerald" />
                <StatMini label="Risky" value={stats?.risky_contacts || 0} tone="amber" />
                <StatMini label="Invalid / Blocked" value={(stats?.invalid_contacts || 0) + (stats?.suppressed_contacts || 0)} tone="rose" />
              </div>
            </div>
            
            <div className="bg-white rounded-2xl p-6 border border-slate-200 shadow-sm flex flex-col">
              <h2 className="text-lg font-semibold text-slate-800 mb-6 flex items-center gap-2">
                <Inbox className="text-indigo-500" size={20} /> Compliance Snapshot
              </h2>
              <div className="space-y-4">
                 <StatMini label="Unsubscribed" value={stats?.unsubscribed_contacts || 0} tone="rose" />
                 <StatMini label="Suppressed" value={stats?.suppressed_contacts || 0} tone="amber" />
                 <StatMini label="Active campaigns" value={stats?.active_campaigns || 0} tone="blue" />
              </div>
            </div>
          </div>
        </>
      )}
    </div>
  );
}

function StatCard({ title, value, icon, trend, alert = false, success = false }: { title: string; value: number | string; icon: ReactNode; trend: string; alert?: boolean; success?: boolean }) {
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

function StatMini({ label, value, tone }: { label: string; value: number; tone: "emerald" | "amber" | "rose" | "blue" }) {
  const styles = {
    emerald: "border-emerald-200 bg-emerald-50 text-emerald-700",
    amber: "border-amber-200 bg-amber-50 text-amber-700",
    rose: "border-rose-200 bg-rose-50 text-rose-700",
    blue: "border-blue-200 bg-blue-50 text-blue-700",
  } as const;
  return (
    <div className={`rounded-2xl border p-4 ${styles[tone]}`}>
      <div className="text-xs font-bold uppercase tracking-wide">{label}</div>
      <div className="mt-2 text-3xl font-extrabold">{value}</div>
    </div>
  );
}
