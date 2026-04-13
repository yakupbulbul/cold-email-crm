import type { Metadata } from 'next'
import { IBM_Plex_Mono, Manrope } from 'next/font/google'
import './globals.css'
import { AuthProvider } from '@/context/AuthContext'
import AppLayout from '@/components/AppLayout'

const manrope = Manrope({ subsets: ['latin'], variable: '--font-manrope' })
const ibmPlexMono = IBM_Plex_Mono({ subsets: ['latin'], variable: '--font-ibm-plex-mono', weight: ['400', '500', '600'] })

export const metadata: Metadata = {
  title: 'Campaign Manager',
  description: 'B2B and B2C outreach operations platform',
  icons: {
    icon: [
      { url: '/icon.png', type: 'image/png' },
      { url: '/favicon.ico', sizes: 'any' },
    ],
    apple: [{ url: '/apple-icon.png', type: 'image/png' }],
    shortcut: ['/icon.png'],
  },
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en">
      <body className={`${manrope.variable} ${ibmPlexMono.variable}`}>
        <AuthProvider>
          <AppLayout>
            {children}
          </AppLayout>
        </AuthProvider>
      </body>
    </html>
  )
}
