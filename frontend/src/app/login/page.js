"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { setToken } from "@/lib/auth";

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

    // const formData = new URLSearchParams();
    // formData.append("username", username);
    // formData.append("password", password);

      const res = await fetch("http://127.0.0.1:8000/user/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username, password }),
      });

    setLoading(false);

    if (res.ok) {
      const data = await res.json();
      setToken(data.access_token);
      router.push("/dashboard");
    } else {
      setError("Invalid username or password");
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-[#0a0a0a] via-[#1e1e1e] to-[#6b21a8] text-gray-100 font-[JetBrains_Mono]">
      <div className="p-8 rounded-xl max-w-md w-full backdrop-blur-md bg-[#1e1e1e]/70 border border-[#a855f7]/30">
        <div className="flex justify-center items-center mb-6">
          <div className="animate-spin-slow border-2 border-[#a855f7] w-10 h-10 rounded-lg mr-3"></div>
          <h1 className="text-3xl font-bold bg-gradient-to-r from-[#a855f7] to-[#9333ea] bg-clip-text text-transparent">
            DockerVerse
          </h1>
        </div>

        <form onSubmit={handleSubmit} className="space-y-5">
          <div>
            <label className="text-sm font-medium mb-1 block">Username</label>
            <input
              type="text"
              required
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              className="w-full px-4 py-2 bg-[#2d2d2d] border border-[#3d3d3d] rounded-md focus:outline-none focus:ring-2 focus:ring-[#a855f7]"
            />
          </div>

          <div>
            <label className="text-sm font-medium mb-1 block">Password</label>
            <input
              type="password"
              required
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full px-4 py-2 bg-[#2d2d2d] border border-[#3d3d3d] rounded-md focus:outline-none focus:ring-2 focus:ring-[#a855f7]"
            />
          </div>

          {error && <p className="text-red-400 text-sm">{error}</p>}

          <button
            type="submit"
            disabled={loading}
            className={`w-full py-2 rounded-md font-medium transition-colors ${
              loading
                ? "bg-[#7e22ce] cursor-not-allowed"
                : "bg-[#a855f7] hover:bg-[#9333ea]"
            }`}
          >
            {loading ? "Signing in..." : "Sign In"}
          </button>
        </form>

        <p className="mt-5 text-sm text-gray-400 text-center">
          Need an account?{" "}
          <a href="/register" className="text-[#a855f7] hover:underline">
            Register
          </a>
        </p>
      </div>
    </div>
  );
}
