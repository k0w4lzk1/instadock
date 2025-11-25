"use client";
import { useEffect, useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import { getToken } from "@/lib/auth";
import { getUserInstances, getApprovedSubmissions, spawnNewInstance } from "@/lib/api"; 
import ContainerCard from "@/components/ContainerCard";
import StatCard from "@/components/StatCard";
import { Zap, LayoutGrid, AlertTriangle, StopCircle } from 'lucide-react';
import Link from 'next/link';

// SubmissionSection component remains here (moved in previous fix)
function SubmissionSection({ submissions, refreshDashboard }) {
  const [msg, setMsg] = useState("");
  const [loadingId, setLoadingId] = useState(null);

  async function handleSpawn(submission_id) {
    setLoadingId(submission_id);
    setMsg(`Spawning instance for submission ${submission_id.substring(0, 8)}...`);
    try {
      const res = await spawnNewInstance(submission_id);
      setMsg(`Instance spawned! URL: ${res.url}. Check Your Active Instances below.`);
      setTimeout(refreshDashboard, 1500); 
    } catch (e) {
      setMsg(`Error spawning: ${e.message}`);
    } finally {
      setLoadingId(null);
    }
  }

  return (
    <section className="bg-white dark:bg-[#1a1a24]/60 p-6 rounded-xl border border-indigo-400/50 dark:border-[#6332ff]/40 shadow-2xl space-y-4 transition-colors duration-300">
      <h2 className="text-2xl font-bold text-[#6332ff] dark:text-[#b480ff] flex items-center space-x-2">
        <Zap size={24} /> <span>Quick Launchpad</span>
      </h2>
      {msg && <p className="text-sm text-yellow-400">{msg}</p>}

      {submissions.length === 0 ? (
        <div className="p-4 bg-gray-200 dark:bg-gray-700/50 rounded-lg text-gray-600 dark:text-gray-400 flex items-center space-x-2">
             <AlertTriangle size={20} className="text-yellow-600 dark:text-yellow-400" />
            <p>No approved images found. Submit a project on the <Link href="/upload" className="text-indigo-600 dark:text-[#a855f7] hover:underline">Upload</Link> page.</p>
        </div>
      ) : (
        <div className="space-y-3 max-h-64 overflow-y-auto pr-2">
          {submissions.map((sub) => (
            <div key={sub.id} className="flex justify-between items-center bg-gray-100 dark:bg-[#2d2d3a] p-3 rounded border border-gray-300 dark:border-gray-600/50 hover:bg-gray-200 dark:hover:bg-[#3d3d4a] transition-colors">
              <div>
                <p className="font-semibold text-gray-800 dark:text-gray-200">
                  {sub.source.includes('github') ? sub.source.split('/').pop() : `ZIP Upload (${sub.id.substring(0, 8)})`}
                </p>
                <p className="text-xs text-gray-600 dark:text-gray-400 mt-1">Image Tag: {sub.image_tag.split('/').pop()}</p>
              </div>
              <button
                onClick={() => handleSpawn(sub.id)}
                disabled={loadingId === sub.id}
                className={`px-4 py-2 rounded text-sm font-medium transition-colors ${
                  loadingId === sub.id
                    ? "bg-gray-500 cursor-not-allowed text-white"
                    : "bg-green-600 hover:bg-green-700 text-white"
                }`}
              >
                {loadingId === sub.id ? 'Launching...' : 'Launch Instance'}
              </button>
            </div>
          ))}
        </div>
      )}
    </section>
  );
}


export default function Dashboard() {
  const router = useRouter();
  const [instances, setInstances] = useState([]);
  const [approvedSubmissions, setApprovedSubmissions] = useState([]); 
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const fetchData = useCallback(async () => {
    const token = getToken();
    if (!token) {
      router.push("/login");
      return;
    }
    
    try {
      const [instancesRes, submissionsRes] = await Promise.all([ 
        getUserInstances(),
        getApprovedSubmissions(), 
      ]);

      const enrichedInstances = instancesRes.map(inst => ({
        ...inst,
        name: inst.image.split('/').pop() || inst.cid,
      }));
      setInstances(enrichedInstances);
      setApprovedSubmissions(submissionsRes);

    } catch (e) {
      setError(`Error fetching data: ${e.message}`);
      console.error(e);
      if (e.message.includes("401") || e.message.includes("Missing") || e.message.includes("expired")) {
        router.push("/login");
      }
    } finally {
      setLoading(false);
    }
  }, [router]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);


  if (loading) return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 dark:bg-[#0a0a0f] text-gray-800 dark:text-gray-400">
      <div className="animate-spin text-4xl text-[#3b82f6]">🐳</div>
      <p className="ml-3">Loading InstaDock Dashboard...</p>
    </div>
  );
  
  if (error) return <p className="text-center text-red-600 dark:text-red-400 mt-10">Error: {error}</p>;

  const runningCount = instances.filter(inst => inst.status === 'running').length;
  const stoppedCount = instances.filter(inst => inst.status === 'stopped').length;
  const removedCount = instances.filter(inst => inst.status === 'removed' || inst.status === 'deleted').length;


  return (
    <div className="min-h-screen bg-gray-50 dark:bg-[#0a0a0f] text-gray-800 dark:text-gray-100 transition-colors duration-300">
      <main className="p-8 space-y-10">
        
        {/* User Instance Summary Section */}
        <section className="space-y-6">
            <h2 className="text-3xl font-bold text-gray-800 dark:text-gray-100">Your Containers at a Glance</h2>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                <StatCard title="Total Instances" value={instances.length} icon={<LayoutGrid size={20} />} />
                <StatCard title="Running" value={runningCount} icon={<Zap size={20} />} />
                <StatCard title="Stopped/Exited" value={stoppedCount + removedCount} icon={<StopCircle size={20} />} />
            </div>
        </section>
        
        {/* New Section: Approved Submissions for Spawning */}
        <SubmissionSection 
            submissions={approvedSubmissions} 
            refreshDashboard={fetchData} 
        />
        
        {/* FR-4.0: User Instances List */}
        <section>
          <h2 className="text-2xl mb-4 font-semibold text-indigo-600 dark:text-[#b480ff] flex items-center space-x-2">
            <LayoutGrid size={20} /> <span>Your Active Instances ({instances.length})</span>
          </h2>
          {instances.length === 0 ? (
            <p className="text-gray-600 dark:text-gray-400">You have no active instances. Launch one from the Quick Launchpad above.</p>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
              {instances.map((inst) => (
                <ContainerCard 
                  key={inst.cid}
                  cid={inst.cid}
                  name={inst.name}
                  status={inst.status}
                  expiresAt={inst.expires_at}
                  subdomain={inst.subdomain}
                  onActionSuccess={fetchData} 
                />
              ))}
            </div>
          )}
        </section>
      </main>
    </div>
  );
}