import type { Metadata } from 'next'
import { Inter } from 'next/font/google'
import './globals.css'
import Sidebar from '@/components/Sidebar'
import TopBar from '@/components/TopBar'

const inter = Inter({ subsets: ['latin'] })

export const metadata: Metadata = {
  title: 'AI Cold Email CRM',
  description: 'AI-Powered Cold Email Platform',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en">
      <body className={inter.className + " bg-slate-50 text-slate-900 flex min-h-screen overflow-hidden"}>
        <Sidebar />
        <div className="flex-1 flex flex-col ml-64 min-h-screen bg-slate-50/50">
          <TopBar />
          <main className="flex-1 overflow-y-auto p-10">
            {children}
          </main>
        </div>
      </body>
    </html>
  )
}
