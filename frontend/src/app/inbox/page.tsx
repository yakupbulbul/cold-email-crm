"use client";
import { useState } from 'react';
import { Search, Sparkles, Send, Reply, Archive } from 'lucide-react';

export default function InboxPage() {
  const [selectedThread, setSelectedThread] = useState<number | null>(1);

  return (
    <div className="h-[calc(100vh-8rem)] flex gap-6 animate-fade-in">
      {/* Thread List */}
      <div className="w-1/3 bg-white rounded-2xl border border-slate-200 shadow-sm flex flex-col overflow-hidden">
        <div className="p-5 border-b border-slate-100 flex items-center justify-between">
          <h2 className="text-xl font-bold text-slate-800">Inbox</h2>
          <span className="text-xs bg-blue-100 text-blue-700 font-semibold px-2.5 py-1 rounded-full">3 Unread</span>
        </div>
        <div className="flex-1 overflow-y-auto w-full">
          {[1, 2, 3].map((thread) => (
            <div 
              key={thread} 
              onClick={() => setSelectedThread(thread)}
              className={`p-5 border-b border-slate-50 cursor-pointer transition-colors w-full ${selectedThread === thread ? 'bg-indigo-50/50 border-l-4 border-l-indigo-500' : 'hover:bg-slate-50 border-l-4 border-l-transparent'}`}
            >
              <div className="flex justify-between items-start mb-1.5 w-full">
                <span className={`text-sm text-slate-800 ${thread === 1 ? 'font-bold' : 'font-semibold'}`}>Sarah Jenkins</span>
                <span className={`text-xs ${thread === 1 ? 'text-indigo-600 font-bold' : 'text-slate-400 font-medium'}`}>10:42 AM</span>
              </div>
              <p className={`text-sm mb-1 ${thread === 1 ? 'font-bold text-slate-800' : 'font-medium text-slate-700'} truncate`}>Re: Partnership Opportunity</p>
              <p className="text-sm text-slate-500 line-clamp-2 leading-relaxed">Thanks for reaching out. Yes, we are currently looking for new partners in the CRM space...</p>
            </div>
          ))}
        </div>
      </div>

      {/* Message View */}
      <div className="flex-1 flex flex-col bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden mb-6">
        <div className="p-6 border-b border-slate-100 flex justify-between items-center w-full">
          <div>
            <h2 className="text-2xl font-bold text-slate-800 mb-2">Re: Partnership Opportunity</h2>
            <div className="flex items-center gap-2 text-sm text-slate-500 font-medium">
              <span className="text-slate-800 font-semibold">Sarah Jenkins</span>
              <span>&lt;sarah@techflow.io&gt;</span>
            </div>
          </div>
          <div className="flex gap-2">
            <button className="p-2.5 text-slate-400 hover:text-blue-600 hover:bg-blue-50 rounded-xl transition-colors"><Reply size={20}/></button>
            <button className="p-2.5 text-slate-400 hover:text-slate-600 hover:bg-slate-50 rounded-xl transition-colors"><Archive size={20}/></button>
          </div>
        </div>
        
        <div className="p-8 flex-1 overflow-y-auto text-slate-700 text-base leading-relaxed break-words w-full">
          <p>Hi John,</p><br/>
          <p>Thanks for reaching out. Yes, we are currently looking for new partners in the CRM space. Your product looks interesting.</p><br/>
          <p>Can we schedule a quick 15-minute call sometime next Tuesday?</p><br/>
          <p>Best,<br/>Sarah</p>
        </div>
        
        <div className="p-5 border-t border-slate-100 bg-slate-50/50 w-full">
          <div className="bg-white rounded-xl border border-slate-200 focus-within:ring-2 focus-within:ring-blue-100 focus-within:border-blue-300 transition-all shadow-inner relative">
            <textarea 
              className="w-full h-32 p-4 outline-none text-sm resize-none rounded-xl"
              placeholder="Draft your reply..."
            ></textarea>
            <div className="flex justify-between items-center p-3 border-t border-slate-100 bg-slate-50 rounded-b-xl w-full">
              <button className="flex items-center gap-2 text-indigo-600 font-semibold text-sm hover:bg-indigo-100 px-4 py-2 rounded-lg transition-colors border border-indigo-200 shadow-sm">
                <Sparkles size={16} /> Generate AI Reply
              </button>
              <button className="bg-blue-600 hover:bg-blue-700 text-white px-6 py-2.5 rounded-lg font-bold transition-colors shadow-md shadow-blue-600/20 flex items-center gap-2">
                Send <Send size={16} className="ml-1" />
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* AI Side Panel */}
      <div className="w-80 bg-white rounded-2xl border border-slate-200 shadow-sm p-6 flex flex-col gap-8 overflow-y-auto mb-6">
        <div className="flex items-center gap-2 text-indigo-600 font-bold text-lg mb-2 border-b border-indigo-50 pb-4">
          <Sparkles size={22} /> Thread AI Insights
        </div>
        
        <div>
          <p className="text-xs font-bold text-slate-400 uppercase tracking-widest mb-3">Intent Classification</p>
          <span className="px-4 py-2bg-green-100 text-green-700 font-bold text-sm rounded-xl border border-green-200 shadow-sm bg-green-50 inline-block">
            Positive Reply
          </span>
        </div>

        <div>
          <p className="text-xs font-bold text-slate-400 uppercase tracking-widest mb-3">AI Summary</p>
          <div className="p-5 rounded-xl bg-gradient-to-br from-indigo-50 to-blue-50 border border-indigo-100 text-sm font-medium text-slate-700 leading-relaxed shadow-sm">
            Sarah is interested in the CRM tool and wants to schedule a 15-minute partnership call next Tuesday.
          </div>
        </div>

        <div className="mt-auto border-t border-slate-100 pt-6">
          <p className="text-xs font-bold text-slate-400 uppercase tracking-widest mb-3">Suggested Action</p>
          <button className="w-full bg-slate-900 hover:bg-slate-800 text-white shadow-lg shadow-slate-900/20 font-semibold py-3 rounded-xl text-sm transition-colors">
            Draft Calendar Invite
          </button>
        </div>
      </div>
    </div>
  );
}
