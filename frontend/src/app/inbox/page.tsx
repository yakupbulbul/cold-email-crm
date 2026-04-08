"use client";
import { useState, useEffect } from 'react';
import { Search, Sparkles, Send, Reply, Archive, ServerCrash, Inbox as InboxIcon } from 'lucide-react';
import { useApiService } from '@/services/api';
import { Thread, Message } from '@/types/models';
import Spinner from '@/components/ui/Spinner';

export default function InboxPage() {
  const [selectedThread, setSelectedThread] = useState<string | null>(null);
  const { getThreads, getMessages, loading, error } = useApiService();
  const [threads, setThreads] = useState<Thread[]>([]);
  const [messages, setMessages] = useState<Message[]>([]);

  useEffect(() => {
    const fetchInbox = async () => {
        const data = await getThreads();
        if (data) setThreads(data);
    };
    fetchInbox();
  }, [getThreads]);

  useEffect(() => {
    if (selectedThread) {
        const fetchMsgs = async () => {
            const data = await getMessages(selectedThread);
            if (data) setMessages(data);
        };
        fetchMsgs();
    }
  }, [selectedThread, getMessages]);

  if (error) {
    return (
        <div className="h-[calc(100vh-8rem)] flex items-center justify-center animate-fade-in">
           <div className="bg-white rounded-2xl border border-slate-200 shadow-sm flex flex-col items-center justify-center p-16 text-center max-w-lg">
                <div className="w-16 h-16 bg-red-50 rounded-full flex items-center justify-center mb-4 border border-red-100">
                    <ServerCrash className="text-red-500" size={28} />
                </div>
                <h3 className="text-lg font-bold text-slate-800 mb-2">Inbox Unavailable</h3>
                <p className="text-sm text-slate-500 mb-4">The local backend responded with an error while loading inbox threads or messages.</p>
                <p className="text-xs text-red-600 font-medium bg-red-50 px-3 py-1 rounded w-full break-words">Error: {error}</p>
            </div>
        </div>
    );
  }

  if (loading && threads.length === 0) {
      return (
          <div className="h-[calc(100vh-8rem)] flex items-center justify-center bg-white rounded-2xl border border-slate-200 shadow-sm animate-fade-in">
              <Spinner size="lg" />
          </div>
      );
  }

  if (threads.length === 0) {
      return (
          <div className="h-[calc(100vh-8rem)] flex items-center justify-center animate-fade-in">
           <div className="bg-white rounded-2xl border border-slate-200 shadow-sm flex flex-col items-center justify-center p-16 text-center max-w-lg">
                <div className="w-16 h-16 bg-slate-50 rounded-full flex items-center justify-center mb-4 border border-slate-100">
                    <InboxIcon className="text-slate-400" size={28} />
                </div>
                <h3 className="text-lg font-bold text-slate-800 mb-2">Inbox Empty</h3>
                <p className="text-sm text-slate-500 mb-4">You have no active threads or unread replies right now.</p>
            </div>
        </div>
      );
  }

  return (
    <div className="h-[calc(100vh-8rem)] flex gap-6 animate-fade-in">
      {/* Thread List */}
      <div className="w-1/3 bg-white rounded-2xl border border-slate-200 shadow-sm flex flex-col overflow-hidden">
        <div className="p-5 border-b border-slate-100 flex items-center justify-between">
          <h2 className="text-xl font-bold text-slate-800">Inbox</h2>
          <span className="text-xs bg-blue-100 text-blue-700 font-semibold px-2.5 py-1 rounded-full">{threads.filter(t => t.unread).length} Unread</span>
        </div>
        <div className="flex-1 overflow-y-auto w-full">
          {threads.map((thread) => (
            <div 
              key={thread.id} 
              onClick={() => setSelectedThread(thread.id)}
              className={`p-5 border-b border-slate-50 cursor-pointer transition-colors w-full ${selectedThread === thread.id ? 'bg-indigo-50/50 border-l-4 border-l-indigo-500' : 'hover:bg-slate-50 border-l-4 border-l-transparent'}`}
            >
              <div className="flex justify-between items-start mb-1.5 w-full">
                <span className={`text-sm text-slate-800 ${thread.unread ? 'font-bold' : 'font-semibold'}`}>{thread.contact_name || thread.contact_email}</span>
                <span className={`text-xs ${thread.unread ? 'text-indigo-600 font-bold' : 'text-slate-400 font-medium'}`}>{new Date(thread.last_message_at).toLocaleTimeString()}</span>
              </div>
              <p className={`text-sm mb-1 ${thread.unread ? 'font-bold text-slate-800' : 'font-medium text-slate-700'} truncate`}>{thread.subject}</p>
              <p className="text-sm text-slate-500 line-clamp-2 leading-relaxed">{thread.snippet || "No snippet available."}</p>
            </div>
          ))}
        </div>
      </div>

      {/* Message View */}
      <div className="flex-1 flex flex-col bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden mb-6">
        {selectedThread ? (
            <>
            <div className="p-6 border-b border-slate-100 flex justify-between items-center w-full">
              <div>
                <h2 className="text-2xl font-bold text-slate-800 mb-2">{threads.find(t => t.id === selectedThread)?.subject}</h2>
                <div className="flex items-center gap-2 text-sm text-slate-500 font-medium">
                  <span className="text-slate-800 font-semibold">{threads.find(t => t.id === selectedThread)?.contact_name || "Unknown"}</span>
                  <span>&lt;{threads.find(t => t.id === selectedThread)?.contact_email}&gt;</span>
                </div>
              </div>
              <div className="flex gap-2">
                <button className="p-2.5 text-slate-400 hover:text-blue-600 hover:bg-blue-50 rounded-xl transition-colors"><Reply size={20}/></button>
                <button className="p-2.5 text-slate-400 hover:text-slate-600 hover:bg-slate-50 rounded-xl transition-colors"><Archive size={20}/></button>
              </div>
            </div>
            
            <div className="p-8 flex-1 overflow-y-auto text-slate-700 text-base leading-relaxed break-words w-full">
              {messages.length === 0 ? (
                  <div className="flex items-center justify-center h-full text-slate-400">Loading messages...</div>
              ) : (
                  messages.map(msg => (
                      <div key={msg.id} className={`mb-4 p-4 rounded-xl ${msg.direction === 'inbound' ? 'bg-slate-50' : 'bg-blue-50'} border border-slate-100`}>
                          <p>{msg.body_text}</p>
                      </div>
                  ))
              )}
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
            </>
        ) : (
            <div className="flex items-center justify-center flex-1 text-slate-400 flex-col gap-4">
                <InboxIcon size={48} className="opacity-20" />
                Select a thread to view messages
            </div>
        )}
      </div>

      {/* AI Side Panel */}
      {selectedThread && (
          <div className="w-80 bg-white rounded-2xl border border-slate-200 shadow-sm p-6 flex flex-col gap-8 overflow-y-auto mb-6">
            <div className="flex items-center gap-2 text-indigo-600 font-bold text-lg mb-2 border-b border-indigo-50 pb-4">
              <Sparkles size={22} /> Thread AI Insights
            </div>
            
            <div className="p-6 bg-slate-50 border border-slate-100 rounded-xl text-center text-slate-400 font-medium h-48 flex items-center justify-center">
                AI thread insights will appear here when inbox metadata becomes available.
            </div>
          </div>
      )}
    </div>
  );
}
