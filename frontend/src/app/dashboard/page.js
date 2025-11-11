"use client";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { getToken } from "@/lib/auth";
import Navbar from "@/components/Navbar";
import { getSystemStats } from "@/lib/api";

export default function Dashboard() {
  const router = useRouter();
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const token = getToken();
    if (!token) {
      router.push("/login");
      return;
    }
    getSystemStats()
      .then(setStats)
      .catch((e) => console.error(e))
      .finally(() => setLoading(false));
  }, [router]);

  return (
    <div className="min-h-screen bg-[#0a0a0f] text-gray-100">
      <Navbar />
      <main className="p-8">
        <h2 className="text-2xl mb-4 font-semibold">System Overview</h2>
        {loading ? (
          <div className="text-gray-400">Loading...</div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="bg-[#1a1a24]/60 p-4 rounded-lg border border-[#6332ff]/30">
              <h3 className="text-[#b480ff] font-semibold">CPU Usage</h3>
              <p>{stats.cpu_percent}%</p>
            </div>
            <div className="bg-[#1a1a24]/60 p-4 rounded-lg border border-[#6332ff]/30">
              <h3 className="text-[#b480ff] font-semibold">Memory</h3>
              <p>{stats.memory_percent}%</p>
            </div>
            <div className="bg-[#1a1a24]/60 p-4 rounded-lg border border-[#6332ff]/30">
              <h3 className="text-[#b480ff] font-semibold">Running Containers</h3>
              <p>{stats.containers_running}</p>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}
