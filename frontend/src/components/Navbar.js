"use client"; 
import { useEffect, useState } from "react";
import { getToken, removeToken } from "@/lib/auth";
import { useRouter } from "next/navigation";
import Link from 'next/link';
import { useTheme } from "@/lib/ThemeProvider"; 
import { Sun, Moon, LogOut, MessageSquare } from 'lucide-react'; // Added MessageSquare

export default function Navbar() {
  const router = useRouter();
  
  const themeContext = useTheme(); 
  const { theme, toggleTheme } = themeContext || { theme: 'dark', toggleTheme: () => {} }; 

  const [loggedIn, setLoggedIn] = useState(false);
  const [hydrated, setHydrated] = useState(false);

  useEffect(() => {
    setHydrated(true);
    const token = getToken();
    setLoggedIn(!!token);
  }, []);

  if (!hydrated) {
    return (
      <nav className="bg-[#0f0f15] border-b border-[#6332ff]/30 px-6 py-3">
        <h1 className="text-2xl font-bold text-gray-300">InstaDock</h1>
      </nav>
    );
  }

  const handleLogout = () => {
    removeToken();
    setLoggedIn(false);
    router.push("/login");
  };

  return (
    <nav className="fade-in bg-gray-50 dark:bg-[#0f0f15] border-b border-[#6332ff]/30 px-6 py-3 flex justify-between items-center transition-colors duration-300">
      <div className="flex items-center space-x-2">
        {/* Logo */}
        <div className="text-2xl text-[#3b82f6]">🐳</div> 
        <h1 className="text-2xl font-bold text-gray-800 dark:text-transparent bg-clip-text dark:bg-gradient-to-r from-[#b480ff] to-[#6332ff]">
          InstaDock
        </h1>
      </div>
      
      <div className="flex items-center space-x-4">
        {/* Theme Toggle Button */}
        <button
            onClick={toggleTheme}
            className="p-2 rounded-full text-gray-600 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-700 transition-colors"
            title={`Switch to ${theme === 'dark' ? 'light' : 'dark'} mode`}
        >
            {theme === 'dark' ? <Sun size={20} /> : <Moon size={20} />}
        </button>

        {loggedIn && (
          <>
            <Link href="/dashboard" className="text-gray-700 dark:text-gray-300 hover:text-[#b480ff]">Dashboard</Link>
            <Link href="/upload" className="text-gray-700 dark:text-gray-300 hover:text-[#b480ff]">Upload</Link>
            <Link href="/admin" className="text-gray-700 dark:text-gray-300 hover:text-[#b480ff]">Admin</Link>
            
            {/* FIX: New Support Chat Link */}
            <Link href="/chat" className="text-white bg-green-500 hover:bg-green-600 px-3 py-1.5 rounded text-sm flex items-center space-x-1">
                <MessageSquare size={16} />
                <span>Support</span>
            </Link>

            <button
              onClick={handleLogout}
              className="bg-[#a855f7] hover:bg-[#9333ea] px-3 py-1.5 rounded text-sm text-white flex items-center space-x-1"
            >
              <LogOut size={16} />
              <span>Logout</span>
            </button>
          </>
        )}
        {!loggedIn && (
            <Link href="/login" className="bg-[#a855f7] hover:bg-[#9333ea] px-3 py-1.5 rounded text-sm text-white">
                Login
            </Link>
        )}
      </div>
    </nav>
  );
}