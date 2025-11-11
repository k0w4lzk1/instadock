"use client";
import { useEffect, useState } from "react";
import { getToken, removeToken } from "@/lib/auth";
import { useRouter } from "next/navigation";

export default function Navbar() {
  const router = useRouter();
  const [loggedIn, setLoggedIn] = useState(false);
  const [hydrated, setHydrated] = useState(false);

  useEffect(() => {
    setHydrated(true);
    const token = getToken();
    setLoggedIn(!!token);
  }, []);

  if (!hydrated) {
    // Avoid SSR/client mismatch: render placeholder while hydrating
    return (
      <nav className="bg-[#0f0f15] border-b border-[#6332ff]/30 px-6 py-3">
        <h1 className="text-2xl font-bold text-gray-300">DockerVerse</h1>
      </nav>
    );
  }

  return (
    <nav className="fade-in bg-[#0f0f15] border-b border-[#6332ff]/30 px-6 py-3 flex justify-between items-center">
      <h1 className="text-2xl font-bold bg-gradient-to-r from-[#b480ff] to-[#6332ff] bg-clip-text text-transparent">
        DockerVerse
      </h1>
      <div className="space-x-4">
        {loggedIn && (
          <>
            <a href="/dashboard" className="hover:text-[#b480ff]">Dashboard</a>
            <a href="/upload" className="hover:text-[#b480ff]">Upload</a>
            <a href="/admin" className="hover:text-[#b480ff]">Admin</a>
          </>
        )}
        <button
          onClick={() => {
            if (loggedIn) {
              removeToken();
              setLoggedIn(false);
              router.push("/login");
            } else {
              router.push("/login");
            }
          }}
          className="bg-[#a855f7] hover:bg-[#9333ea] px-3 py-1.5 rounded text-sm"
        >
          {loggedIn ? "Logout" : "Login"}
        </button>
      </div>
    </nav>
  );
}
