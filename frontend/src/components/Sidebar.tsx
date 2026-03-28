import Link from 'next/link';
import { LayoutDashboard, Globe, Mail, Send, Inbox, Activity } from 'lucide-react';

export default function Sidebar() {
  return (
    <div className="w-64 bg-slate-900 text-slate-400 flex flex-col h-screen fixed top-0 left-0 border-r border-slate-800">
      <div className="p-6 text-2xl font-bold tracking-wider flex items-center gap-3 text-white border-b border-slate-800">
        <Send className="text-blue-500" strokeWidth={2.5} /> CRMx
      </div>
      <nav className="flex-1 px-4 py-8 space-y-2">
        <Link href="/" className="flex items-center gap-3 px-4 py-3 rounded-xl hover:bg-blue-600 hover:text-white transition-all duration-300 font-medium group">
          <LayoutDashboard size={20} className="group-hover:scale-110 transition-transform"/> Dashboard
        </Link>
        <Link href="/mailboxes" className="flex items-center gap-3 px-4 py-3 rounded-xl hover:bg-blue-600 hover:text-white transition-all duration-300 font-medium group">
          <Globe size={20} className="group-hover:scale-110 transition-transform"/> Mailboxes
        </Link>
        <Link href="/warmup" className="flex items-center gap-3 px-4 py-3 rounded-xl hover:bg-blue-600 hover:text-white transition-all duration-300 font-medium group">
          <Activity size={20} className="group-hover:scale-110 transition-transform"/> Warm-up
        </Link>
        <Link href="/campaigns" className="flex items-center gap-3 px-4 py-3 rounded-xl hover:bg-blue-600 hover:text-white transition-all duration-300 font-medium group">
          <Send size={20} className="group-hover:scale-110 transition-transform"/> Campaigns
        </Link>
        <Link href="/inbox" className="flex items-center gap-3 px-4 py-3 rounded-xl hover:bg-blue-600 hover:text-white transition-all duration-300 font-medium group">
          <Inbox size={20} className="group-hover:scale-110 transition-transform"/> Inbox
        </Link>
      </nav>
      <div className="p-6 border-t border-slate-800 text-sm text-slate-500">
        &copy; 2026 The Project
      </div>
    </div>
  );
}
