import Link from 'next/link';
import { LayoutDashboard, Globe, Send, Inbox, Activity, Server, Users, Settings } from 'lucide-react';

export default function Sidebar() {
  return (
    <div className="w-64 bg-slate-900 text-slate-400 flex flex-col h-screen fixed top-0 left-0 border-r border-slate-800">
      <div className="p-6 text-2xl font-bold tracking-wider flex items-center gap-3 text-white border-b border-slate-800">
        <Send className="text-blue-500" strokeWidth={2.5} /> CRMx
      </div>
      <nav className="flex-1 px-4 py-6 space-y-1.5 overflow-y-auto">
        <Link href="/" className="flex items-center gap-3 px-4 py-3 rounded-xl hover:bg-blue-600 hover:text-white transition-all duration-200 font-medium group">
          <LayoutDashboard size={20} className="group-hover:scale-110 transition-transform"/> Dashboard
        </Link>
        <div className="pt-4 pb-2 px-4 text-xs font-bold text-slate-600 uppercase tracking-wider">Infrastructure</div>
        <Link href="/domains" className="flex items-center gap-3 px-4 py-3 rounded-xl hover:bg-blue-600 hover:text-white transition-all duration-200 font-medium group">
          <Server size={20} className="group-hover:scale-110 transition-transform"/> Domains
        </Link>
        <Link href="/mailboxes" className="flex items-center gap-3 px-4 py-3 rounded-xl hover:bg-blue-600 hover:text-white transition-all duration-200 font-medium group">
          <Globe size={20} className="group-hover:scale-110 transition-transform"/> Mailboxes
        </Link>
        <div className="pt-4 pb-2 px-4 text-xs font-bold text-slate-600 uppercase tracking-wider">Outreach</div>
        <Link href="/warmup" className="flex items-center gap-3 px-4 py-3 rounded-xl hover:bg-blue-600 hover:text-white transition-all duration-200 font-medium group">
          <Activity size={20} className="group-hover:scale-110 transition-transform"/> Warm-up
        </Link>
        <Link href="/campaigns" className="flex items-center gap-3 px-4 py-3 rounded-xl hover:bg-blue-600 hover:text-white transition-all duration-200 font-medium group">
          <Send size={20} className="group-hover:scale-110 transition-transform"/> Campaigns
        </Link>
        <Link href="/contacts" className="flex items-center gap-3 px-4 py-3 rounded-xl hover:bg-blue-600 hover:text-white transition-all duration-200 font-medium group">
          <Users size={20} className="group-hover:scale-110 transition-transform"/> Contacts
        </Link>
        <div className="pt-4 pb-2 px-4 text-xs font-bold text-slate-600 uppercase tracking-wider">Intelligence</div>
        <Link href="/inbox" className="flex items-center gap-3 px-4 py-3 rounded-xl hover:bg-blue-600 hover:text-white transition-all duration-200 font-medium group">
          <Inbox size={20} className="group-hover:scale-110 transition-transform"/> Inbox
        </Link>
      </nav>
      <div className="p-4 border-t border-slate-800">
        <Link href="/settings" className="flex items-center gap-3 px-4 py-3 rounded-xl hover:bg-slate-800 hover:text-white transition-all duration-200 font-medium group">
          <Settings size={20} className="group-hover:rotate-90 transition-transform duration-300"/> Settings
        </Link>
      </div>
    </div>
  );
}
