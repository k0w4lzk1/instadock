"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { setToken } from "@/lib/auth";
import Link from 'next/link'; // Import Link

export default function Login() {
  const router = useRouter();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function handleSubmit(e) {
    e.preventDefault();
    setLoading(true);
    setError("");

      const res = await fetch("http://127.0.0.1:8000/user/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username, password }),
      });

    setLoading(false);

    if (res.ok) {
      const data = await res.json();
      // FIX 1: Change data.access_token to data.token to match backend response
      setToken(data.token); 
      router.push("/dashboard");
    } else {
      setError("Invalid username or password");
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 dark:bg-gradient-to-br dark:from-[#0a0a0a] dark:via-[#1e1e1e] dark:to-[#6b21a8] text-gray-800 dark:text-gray-100 transition-colors duration-300 font-[JetBrains_Mono]">
      <div className="p-8 rounded-xl max-w-md w-full backdrop-blur-md bg-white/90 dark:bg-[#1e1e1e]/90 border border-indigo-400/30 dark:border-[#a855f7]/30 shadow-lg">
        <div className="flex flex-col items-center mb-6">
          {/* Integrated Logo */}
          <div className="text-4xl text-[#3b82f6] mb-2">🐳</div> 
          <h1 className="text-3xl font-bold text-indigo-600 dark:text-transparent dark:bg-clip-text dark:bg-gradient-to-r dark:from-[#a855f7] dark:to-[#9333ea]">
            InstaDock
          </h1>
          <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">Container Orchestration Service</p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-5">
          <div>
            <label className="text-sm font-medium mb-1 block">Username</label>
            <input
              type="text"
              required
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              className="w-full px-4 py-2 bg-gray-100 dark:bg-[#2d2d2d] border border-gray-300 dark:border-[#3d3d3d] rounded-md focus:outline-none focus:ring-2 focus:ring-[#a855f7] text-gray-800 dark:text-gray-100"
            />
          </div>

          <div>
            <label className="text-sm font-medium mb-1 block">Password</label>
            <input
              type="password"
              required
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full px-4 py-2 bg-gray-100 dark:bg-[#2d2d2d] border border-gray-300 dark:border-[#3d3d3d] rounded-md focus:outline-none focus:ring-2 focus:ring-[#a855f7] text-gray-800 dark:text-gray-100"
            />
          </div>

          {error && <p className="text-red-600 dark:text-red-400 text-sm">{error}</p>}

          <button
            type="submit"
            disabled={loading}
            className={`w-full py-2 rounded-md font-medium transition-colors ${
              loading
                ? "bg-[#7e22ce] cursor-not-allowed text-white"
                : "bg-[#a855f7] hover:bg-[#9333ea] text-white"
            }`}
          >
            {loading ? "Signing in..." : "Sign In"}
          </button>
          
          {/* FIX 5: Forgot Password Link */}
          <p className="text-center text-xs pt-1">
            <Link href="/forgot_password" className="text-gray-500 hover:text-[#b480ff] hover:underline">Forgot Password?</Link>
          </p>

        </form>

        <p className="mt-5 text-sm text-gray-500 dark:text-gray-400 text-center">
          Need an account?{" "}
          <Link href="/register" className="text-indigo-600 dark:text-[#a855f7] hover:underline">
            Register
          </Link>
        </p>
      </div>
    </div>
  );
}