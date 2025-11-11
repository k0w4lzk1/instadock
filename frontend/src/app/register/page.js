"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { setToken } from "@/lib/auth";

export default function RegisterPage() {
  const router = useRouter();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [message, setMessage] = useState("");

  async function handleRegister(e) {
    e.preventDefault();
    setMessage("");

    if (password !== confirm) {
      setMessage("Passwords do not match.");
      return;
    }

    try {
      const res = await fetch("http://127.0.0.1:8000/user/register", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username, password }),
      });

      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || "Registration failed");
      }

      const data = await res.json();
      if (data.access_token) {
        setToken(data.access_token); // save JWT
        router.push("/dashboard");
      } else {
        setMessage("Registered successfully. Please log in.");
        setTimeout(() => router.push("/login"), 1500);
      }
    } catch (err) {
      setMessage(err.message);
    }
  }

  return (
    <div className="flex items-center justify-center min-h-screen bg-[#0a0a0f] text-gray-100">
      <div className="w-full max-w-md bg-[#161622]/80 border border-[#6332ff]/30 p-6 rounded-lg shadow-lg">
        <h1 className="text-3xl font-bold mb-6 bg-gradient-to-r from-[#b480ff] to-[#6332ff] bg-clip-text text-transparent text-center">
          Create Account
        </h1>
        <form onSubmit={handleRegister} className="space-y-4">
          <input
            type="text"
            placeholder="Username"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            required
            className="w-full p-2 bg-[#2d2d3a] border border-[#444] rounded focus:outline-none focus:ring-2 focus:ring-[#6332ff]"
          />
          <input
            type="password"
            placeholder="Password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
            className="w-full p-2 bg-[#2d2d3a] border border-[#444] rounded focus:outline-none focus:ring-2 focus:ring-[#6332ff]"
          />
          <input
            type="password"
            placeholder="Confirm Password"
            value={confirm}
            onChange={(e) => setConfirm(e.target.value)}
            required
            className="w-full p-2 bg-[#2d2d3a] border border-[#444] rounded focus:outline-none focus:ring-2 focus:ring-[#6332ff]"
          />
          <button
            type="submit"
            className="w-full bg-[#6332ff] hover:bg-[#5b2be3] py-2 rounded font-semibold"
          >
            Register
          </button>
        </form>
        {message && <p className="text-sm text-center mt-3 text-[#b480ff]">{message}</p>}

        <p className="mt-4 text-sm text-gray-400 text-center">
          Already have an account?{" "}
          <a href="/login" className="text-[#b480ff] hover:underline">
            Login
          </a>
        </p>
      </div>
    </div>
  );
}
