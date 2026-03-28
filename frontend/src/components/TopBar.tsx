import { Bell, Search, User } from 'lucide-react';

export default function TopBar() {
  return (
    <header className="h-20 bg-white/70 backdrop-blur-md border-b border-slate-200 flex items-center justify-between px-10 sticky top-0 z-10 w-full transition-all">
      <div className="flex items-center bg-slate-100 rounded-full px-4 py-2.5 w-[400px] border border-slate-200 focus-within:ring-2 focus-within:ring-blue-100 focus-within:border-blue-300 transition-all">
        <Search className="text-slate-400" size={20} />
        <input 
          type="text" 
          placeholder="Search campaigns, leads..." 
          className="bg-transparent border-none outline-none ml-3 w-full text-sm font-medium text-slate-700 placeholder:text-slate-400"
        />
      </div>
      <div className="flex items-center gap-6">
        <button className="p-2 hover:bg-slate-100 rounded-full relative transition-colors">
          <Bell size={22} className="text-slate-600" />
          <span className="absolute top-2 right-2.5 w-2 h-2 bg-red-500 rounded-full ring-2 ring-white"></span>
        </button>
        <div className="flex items-center gap-3 cursor-pointer hover:bg-slate-50 p-1.5 pr-4 rounded-full border border-transparent hover:border-slate-200 transition-all">
          <div className="w-10 h-10 bg-gradient-to-tr from-blue-600 to-indigo-500 rounded-full flex items-center justify-center text-white font-medium shadow-md">
            <User size={18} />
          </div>
          <span className="text-sm font-semibold text-slate-700">Admin</span>
        </div>
      </div>
    </header>
  );
}
