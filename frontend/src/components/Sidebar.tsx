import Image from 'next/image';
import Link from 'next/link';
import { LayoutDashboard, Globe, Send, Inbox, Activity, Server, Users, Settings, ShieldX, TrendingUp, Network, Bell, Cpu, LogOut, ListChecks } from 'lucide-react';
import { useAuth } from '@/context/AuthContext';

export default function Sidebar() {
  const { logout, user } = useAuth();

  return (
    <div className="w-64 bg-slate-900 text-slate-400 flex flex-col h-screen fixed top-0 left-0 border-r border-slate-800">
      <div className="border-b border-slate-700 bg-slate-100 px-4 py-2">
        <Link href="/" className="flex justify-center transition-transform hover:scale-[1.01]">
          <Image
            src="/crm-logo.png"
            alt="Campaign Manager"
            width={85}
            height={43}
            priority
            className="h-auto w-full max-w-[85px]"
          />
        </Link>
      </div>
      <nav className="flex-1 px-4 py-6 space-y-1.5 overflow-y-auto">
        <Link href="/" className="flex items-center gap-3 px-4 py-3 rounded-xl hover:bg-blue-600 hover:text-white transition-all duration-200 font-medium group text-[15px]">
          <LayoutDashboard size={20} className="group-hover:scale-110 transition-transform"/> Dashboard
        </Link>
        <div className="pt-4 pb-2 px-4 text-xs font-bold text-slate-600 uppercase tracking-wider">Infrastructure</div>
        <Link href="/domains" className="flex items-center gap-3 px-4 py-3 rounded-xl hover:bg-blue-600 hover:text-white transition-all duration-200 font-medium group text-[15px]">
          <Server size={20} className="group-hover:scale-110 transition-transform"/> Domains
        </Link>
        <Link href="/mailboxes" className="flex items-center gap-3 px-4 py-3 rounded-xl hover:bg-blue-600 hover:text-white transition-all duration-200 font-medium group text-[15px]">
          <Globe size={20} className="group-hover:scale-110 transition-transform"/> Mailboxes
        </Link>
        <div className="pt-4 pb-2 px-4 text-xs font-bold text-slate-600 uppercase tracking-wider">Outreach</div>
        <Link href="/warmup" className="flex items-center gap-3 px-4 py-3 rounded-xl hover:bg-blue-600 hover:text-white transition-all duration-200 font-medium group text-[15px]">
          <Activity size={20} className="group-hover:scale-110 transition-transform"/> Warm-up
        </Link>
        <Link href="/campaigns" className="flex items-center gap-3 px-4 py-3 rounded-xl hover:bg-blue-600 hover:text-white transition-all duration-200 font-medium group text-[15px]">
          <Send size={20} className="group-hover:scale-110 transition-transform"/> Campaigns
        </Link>
        <Link href="/contacts" className="flex items-center gap-3 px-4 py-3 rounded-xl hover:bg-blue-600 hover:text-white transition-all duration-200 font-medium group text-[15px]">
          <Users size={20} className="group-hover:scale-110 transition-transform"/> Contacts
        </Link>
        <Link href="/lists" className="flex items-center gap-3 px-4 py-3 rounded-xl hover:bg-blue-600 hover:text-white transition-all duration-200 font-medium group text-[15px]">
          <ListChecks size={20} className="group-hover:scale-110 transition-transform"/> Lists
        </Link>
        <div className="pt-4 pb-2 px-4 text-xs font-bold text-slate-600 uppercase tracking-wider">Intelligence</div>
        <Link href="/inbox" className="flex items-center gap-3 px-4 py-3 rounded-xl hover:bg-blue-600 hover:text-white transition-all duration-200 font-medium group text-[15px]">
          <Inbox size={20} className="group-hover:scale-110 transition-transform"/> Inbox
        </Link>
        <Link href="/suppression" className="flex items-center gap-3 px-4 py-3 rounded-xl hover:bg-blue-600 hover:text-white transition-all duration-200 font-medium group text-[15px]">
          <ShieldX size={20} className="group-hover:scale-110 transition-transform"/> Suppression
        </Link>
        <div className="pt-4 pb-2 px-4 text-xs font-bold text-slate-600 uppercase tracking-wider">Operations & Telemetry</div>
        <Link href="/ops" className="flex items-center gap-3 px-4 py-3 rounded-xl hover:bg-blue-600 hover:text-white transition-all duration-200 font-medium group text-[15px]">
          <Activity size={20} className="group-hover:scale-110 transition-transform"/> System Health
        </Link>
        <Link href="/ops/deliverability" className="flex items-center gap-3 px-4 py-3 rounded-xl hover:bg-blue-600 hover:text-white transition-all duration-200 font-medium group text-[15px]">
          <TrendingUp size={20} className="group-hover:scale-110 transition-transform"/> Deliverability
        </Link>
        <Link href="/ops/jobs" className="flex items-center gap-3 px-4 py-3 rounded-xl hover:bg-blue-600 hover:text-white transition-all duration-200 font-medium group text-[15px]">
          <Network size={20} className="group-hover:scale-110 transition-transform"/> Worker Queues
        </Link>
        <Link href="/ops/alerts" className="flex items-center gap-3 px-4 py-3 rounded-xl hover:bg-blue-600 hover:text-white transition-all duration-200 font-medium group text-[15px]">
          <Bell size={20} className="group-hover:scale-110 transition-transform"/> System Alerts
        </Link>
        <Link href="/ops/readiness" className="flex items-center gap-3 px-4 py-3 rounded-xl hover:bg-blue-600 hover:text-white transition-all duration-200 font-medium group text-[15px]">
          <Cpu size={20} className="group-hover:scale-110 transition-transform"/> Prod Readiness
        </Link>
      </nav>
      
      <div className="mt-auto border-t border-slate-800 p-4 space-y-4">
        {user && (
          <div className="flex items-center gap-3 px-4 py-2">
            <div className="w-8 h-8 bg-blue-600 rounded-lg flex items-center justify-center text-white font-bold text-xs">
              {user.email[0].toUpperCase()}
            </div>
            <div className="flex-1 overflow-hidden">
               <p className="text-sm font-bold text-white truncate">{user.full_name || 'Admin'}</p>
               <p className="text-[10px] text-slate-500 font-medium uppercase tracking-wider">{user.is_admin ? 'Super Admin' : 'User'}</p>
            </div>
          </div>
        )}
        <div className="space-y-1">
          <Link href="/settings" className="flex items-center gap-3 px-4 py-3 rounded-xl hover:bg-slate-800 hover:text-white transition-all duration-200 font-medium group text-[15px]">
            <Settings size={20} className="group-hover:rotate-90 transition-transform duration-300"/> Settings
          </Link>
          <button 
            onClick={logout}
            className="w-full flex items-center gap-3 px-4 py-3 rounded-xl hover:bg-red-900/20 hover:text-red-400 transition-all duration-200 font-bold group text-[15px] text-red-500/80"
          >
            <LogOut size={20} className="group-hover:-translate-x-1 transition-transform"/> Sign Out
          </button>
        </div>
      </div>
    </div>
  );
}
