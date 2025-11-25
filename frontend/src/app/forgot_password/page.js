"use client";
import { useState } from "react";
import { requestPasswordReset } from "@/lib/api";
import Link from "next/link";

export default function ForgotPasswordPage() {
    const [username, setUsername] = useState("");
    const [msg, setMsg] = useState("");
    const [error, setError] = useState("");

    async function handleSubmit(e) {
        e.preventDefault();
        setMsg("Sending request...");
        setError("");
        
        try {
            const res = await requestPasswordReset(username);
            setMsg(res.message + " (Reset token is available in your browser's console for local testing only).");
            // Optional: Log the reset link/token for the user to copy in development
            console.log("Password Reset Token:", res.reset_token);
        } catch (e) {
            setError(e.message);
        } finally {
            setUsername("");
        }
    }

    return (
        <div className="min-h-screen flex items-center justify-center bg-gray-50 dark:bg-[#0a0a0f] text-gray-800 dark:text-gray-100 transition-colors duration-300">
            <div className="bg-white dark:bg-[#1a1a24] p-8 rounded-xl shadow-2xl w-full max-w-md border border-indigo-400/40 dark:border-[#6332ff]/40">
                <div className="flex flex-col items-center mb-6">
                    <div className="text-4xl text-[#3b82f6] mb-2">🔑</div> 
                    <h1 className="text-3xl font-bold text-indigo-600 dark:text-[#b480ff] text-center">
                        Forgot Password
                    </h1>
                </div>
                
                <p className="text-sm text-gray-600 dark:text-gray-400 text-center mb-6">
                    Enter your username to receive a password reset link.
                </p>
                <form onSubmit={handleSubmit} className="space-y-4">
                    <div>
                        <label className="block text-sm font-medium text-gray-600 dark:text-gray-300 mb-1">Username</label>
                        <input
                            type="text"
                            value={username}
                            onChange={(e) => setUsername(e.target.value)}
                            className="w-full p-3 bg-gray-100 dark:bg-[#2d2d3a] border border-gray-300 dark:border-[#444] rounded-lg text-gray-800 dark:text-gray-100 focus:ring-2 focus:ring-[#b480ff]"
                            required
                        />
                    </div>
                    <button
                        type="submit"
                        className="w-full bg-[#6332ff] text-white py-3 rounded-lg font-semibold hover:bg-[#5b2be3] transition-colors"
                    >
                        Send Reset Link
                    </button>
                </form>
                {msg && <p className="mt-4 text-center text-yellow-600 dark:text-yellow-400 text-sm">{msg}</p>}
                {error && <p className="mt-4 text-center text-red-600 dark:text-red-400 text-sm">{error}</p>}
                <p className="mt-4 text-center text-sm text-gray-500 dark:text-gray-400">
                    <Link href="/login" className="text-indigo-600 dark:text-[#b480ff] hover:underline">Back to Login</Link>
                </p>
            </div>
        </div>
    );
}