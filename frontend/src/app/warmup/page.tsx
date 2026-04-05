"use client";

import { useEffect, useState } from 'react';
import { Activity, Play, Pause, Thermometer, Zap, AlertCircle } from 'lucide-react';
import { useApiService } from '@/services/api';
import Spinner from '@/components/ui/Spinner';

export default function WarmupPage() {
  const { getWarmupStatus, loading, error } = useApiService();
  const [stats, setStats] = useState<any>(null);

  useEffect(() => {
    const loadWarmup = async () => {
      const data = await getWarmupStatus();
      if (data) setStats(data);
    };
    loadWarmup();
  }, [getWarmupStatus]);

  return (
    <div className="space-y-6 animate-fade-in relative min-h-[50vh]">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold text-slate-800 tracking-tight">Warm-up Engine</h1>
        <div className="flex gap-3">
          <button className="bg-white border border-slate-200 hover:bg-slate-50 text-slate-700 px-5 py-2.5 rounded-xl font-medium transition-colors shadow-sm flex items-center gap-2">
            <Pause size={18} /> Pause All
          </button>
          <button className="bg-blue-600 hover:bg-blue-700 text-white px-5 py-2.5 rounded-xl font-bold transition-colors shadow-lg shadow-blue-600/30 flex items-center gap-2">
            <Play size={18} fill="currentColor" /> Start Warm-up
          </button>
        </div>
      </div>

      {error ? (
         <div className="p-6 bg-red-50 border border-red-200 text-red-700 rounded-2xl flex flex-col items-center justify-center h-64 shadow-sm text-center">
             <AlertCircle className="mb-4 text-red-500" size={32} />
             <span className="font-bold mb-2">Failed to load Warm-up Data</span>
             <span className="text-sm">{error}</span>
         </div>
      ) : loading ? (
         <div className="h-64 flex items-center justify-center bg-white rounded-2xl border border-slate-200 shadow-sm">
             <Spinner size="lg" />
         </div>
      ) : (
        <>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm relative overflow-hidden group">
              <div className="absolute top-0 right-0 w-32 h-32 bg-green-50 rounded-full blur-3xl -mr-16 -mt-16 opacity-50 group-hover:opacity-100 transition-opacity"></div>
              <div className="relative z-10 flex items-center justify-between">
                <div>
                  <p className="text-sm font-semibold text-slate-500 uppercase tracking-wider mb-1">Global Health</p>
                  <h3 className="text-4xl font-extrabold text-slate-800">{stats?.global_health || '0'}%</h3>
                </div>
                <div className="p-4 bg-green-100 text-green-600 rounded-2xl shadow-sm"><Thermometer size={28} /></div>
              </div>
            </div>

            <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm relative overflow-hidden group">
              <div className="absolute top-0 right-0 w-32 h-32 bg-blue-50 rounded-full blur-3xl -mr-16 -mt-16 opacity-50 group-hover:opacity-100 transition-opacity"></div>
              <div className="relative z-10 flex items-center justify-between">
                <div>
                  <p className="text-sm font-semibold text-slate-500 uppercase tracking-wider mb-1">Total Sent</p>
                  <h3 className="text-4xl font-extrabold text-slate-800">{stats?.total_sent || '0'}</h3>
                </div>
                <div className="p-4 bg-blue-100 text-blue-600 rounded-2xl shadow-sm"><Activity size={28} /></div>
              </div>
            </div>

            <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm relative overflow-hidden group">
              <div className="absolute top-0 right-0 w-32 h-32 bg-purple-50 rounded-full blur-3xl -mr-16 -mt-16 opacity-50 group-hover:opacity-100 transition-opacity"></div>
              <div className="relative z-10 flex items-center justify-between">
                <div>
                  <p className="text-sm font-semibold text-slate-500 uppercase tracking-wider mb-1">Inboxes Warming</p>
                  <h3 className="text-4xl font-extrabold text-slate-800">{stats?.active_pairs ? stats.active_pairs.length : 0}</h3>
                </div>
                <div className="p-4 bg-purple-100 text-purple-600 rounded-2xl shadow-sm"><Zap size={28} /></div>
              </div>
            </div>
          </div>

          <div className="bg-white text-slate-800 rounded-2xl border border-slate-200 shadow-sm overflow-hidden mt-8">
            <div className="p-6 border-b border-slate-100 flex items-center justify-between">
              <h2 className="text-lg font-bold">Active Warm-up Pairs</h2>
            </div>
            
            {!stats?.active_pairs || stats.active_pairs.length === 0 ? (
                <div className="flex flex-col items-center justify-center p-12 text-slate-400">
                    <Zap className="mb-4 opacity-50" size={48} />
                    <p className="font-semibold text-slate-600">No Warm-up Pairs Found</p>
                    <p className="text-sm mt-1">Enable warm-up on your mailboxes to see activity here.</p>
                </div>
            ) : (
                <table className="w-full text-left">
                  <thead className="bg-slate-50 text-xs uppercase tracking-wider font-semibold text-slate-500">
                    <tr>
                      <th className="py-4 px-6 border-b border-slate-100">Mailbox A</th>
                      <th className="py-4 px-6 border-b border-slate-100">Mailbox B</th>
                      <th className="py-4 px-6 border-b border-slate-100">Status</th>
                      <th className="py-4 px-6 border-b border-slate-100 w-64">Daily Volume</th>
                    </tr>
                  </thead>
                  <tbody>
                    {stats.active_pairs.map((pair: any, i: number) => (
                        <tr key={i} className="hover:bg-slate-50 transition-colors">
                          <td className="py-4 px-6 font-bold border-b border-slate-50">{pair.mailbox_a}</td>
                          <td className="py-4 px-6 font-bold border-b border-slate-50">{pair.mailbox_b}</td>
                          <td className="py-4 px-6 border-b border-slate-50">
                            <span className="px-3 py-1 bg-green-100 text-green-700 font-bold text-xs rounded-full border border-green-200">Active</span>
                          </td>
                          <td className="py-4 px-6 font-medium text-slate-600 border-b border-slate-50">
                            <div className="flex flex-col gap-1.5 w-full">
                              <div className="flex justify-between items-center text-xs font-semibold text-slate-600">
                                <span>{pair.sent} / {pair.limit}</span>
                                <span>{Math.round((pair.sent / pair.limit) * 100) || 0}%</span>
                              </div>
                              <div className="w-full h-2 bg-slate-100 rounded-full overflow-hidden shadow-inner">
                                <div className="h-full rounded-full bg-blue-500" style={{ width: `${(pair.sent / pair.limit) * 100}%` }}></div>
                              </div>
                            </div>
                          </td>
                        </tr>
                    ))}
                  </tbody>
                </table>
            )}
          </div>
        </>
      )}
    </div>
  );
}
