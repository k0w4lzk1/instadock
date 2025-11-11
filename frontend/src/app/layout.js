import './globals.css'
import Navbar from '@/components/Navbar'

export const metadata = {
  title: 'InstaDock Dashboard',
  description: 'Manage sandbox containers with style, you will.',
}

export default function RootLayout({ children }) {
  return (
    <html lang="en">
      <body className="bg-gradient-to-b from-gray-950 via-gray-900 to-gray-800 text-gray-100 min-h-screen flex flex-col">
        <Navbar />
        <main className="flex-1 container mx-auto px-6 py-8 animate-fade-in">{children}</main>
      </body>
    </html>
  )
}
