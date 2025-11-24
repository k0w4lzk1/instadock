"use client";
import { useEffect, useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import { getToken } from "@/lib/auth";
import { getSystemStats, getUserInstances, getApprovedSubmissions, spawnNewInstance } from "@/lib/api";
import StatCard from "@/components/StatCard"; // Assuming StatCard is used for System Overview
import ContainerCard from "@/components/ContainerCard";

// FIX 3: MOVED SubmissionSection component to dashboard/page.js
function SubmissionSection({ submissions, refreshDashboard }) {
  const [msg, setMsg] = useState("");
  const [loadingId, setLoadingId] = useState(null);

  async function handleSpawn(submission_id) {
    setLoadingId(submission_id);
    setMsg(`Spawning instance for submission ${submission_id.substring(0, 8)}...`);
    try {
      // Call the API to spawn the instance from the approved submission ID
      const res = await spawnNewInstance(submission_id);
      // FIX 4: Update message to show generated URL
      setMsg(`Instance spawned! URL: ${res.url}. Check Your Active Instances below.`);
      // After spawning, refresh the dashboard list to show the new container
      setTimeout(refreshDashboard, 1500); 
    } catch (e) {
      setMsg(`Error spawning: ${e.message}`);
    } finally {
      setLoadingId(null);
    }
  }

  return (
    <section className="bg-[#1a1a24]/60 p-6 rounded-lg border border-[#6332ff]/30 space-y-4">
      <h2 className="text-xl font-semibold mb-4 text-[#b480ff]">Create New Instance from Approved Images</h2>
      {msg && <p className="text-sm text-yellow-400">{msg}</p>}

      {submissions.length === 0 ? (
        <p className="text-gray-400">No approved images found. Submit a project on the <a href="/upload" className="text-[#a855f7] hover:underline">Upload</a> page.</p>
      ) : (
        <div className="space-y-3 max-h-64 overflow-y-auto">
          {submissions.map((sub) => (
            <div key={sub.id} className="flex justify-between items-center bg-[#2d2d3a] p-3 rounded">
              <div>
                <p className="font-semibold text-gray-200">
                  {/* Display a user-friendly name for the submission */}
                  {sub.source.includes('github') ? sub.source.split('/').pop() : `ZIP Upload (${sub.id.substring(0, 8)})`}
                </p>
                <p className="text-xs text-gray-400 mt-1">Image Tag: {sub.image_tag.split('/').pop()}</p>
              </div>
              <button
                onClick={() => handleSpawn(sub.id)}
                disabled={loadingId === sub.id}
                className={`px-4 py-2 rounded text-sm transition-colors ${
                  loadingId === sub.id
                    ? "bg-gray-500 cursor-not-allowed"
                    : "bg-green-600 hover:bg-green-700"
                }`}
              >
                {loadingId === sub.id ? 'Spawning...' : 'Spawn Instance'}
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
  const [stats, setStats] = useState(null);
  const [instances, setInstances] = useState([]);
  const [approvedSubmissions, setApprovedSubmissions] = useState([]); // FIX 3: NEW STATE
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const fetchData = useCallback(async () => {
    const token = getToken();
    if (!token) {
      router.push("/login");
      return;
    }
    
    try {
      // Fetch system stats, user instances, AND approved submissions
      const [statsRes, instancesRes, submissionsRes] = await Promise.all([ 
        getSystemStats(),
        getUserInstances(),
        getApprovedSubmissions(), // FIX 3: NEW FETCH
      ]);

      setStats(statsRes);
      
      const enrichedInstances = instancesRes.map(inst => ({
        ...inst,
        // The DB now returns 'status', we map other needed properties
        name: inst.image.split('/').pop() || inst.cid,
      }));
      setInstances(enrichedInstances);
      setApprovedSubmissions(submissionsRes); // FIX 3: SET NEW STATE

    } catch (e) {
      setError(`Error fetching data: ${e.message}`);
      console.error(e);
      // Redirect to login on authentication error
      if (e.message.includes("401") || e.message.includes("Missing")) {
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
    <div className="min-h-screen flex items-center justify-center bg-[#0a0a0f] text-gray-400">
      Loading DockerVerse Dashboard...
    </div>
  );
  
  if (error) return <p className="text-center text-red-400 mt-10">Error: {error}</p>;

  return (
    <div className="min-h-screen bg-[#0a0a0f] text-gray-100">
      <main className="p-8 space-y-10">
        
        {/* FIX 3: NEW SECTION: Approved Submissions for Spawning */}
        <SubmissionSection 
            submissions={approvedSubmissions} 
            refreshDashboard={fetchData} // Pass the refresh function
        />
        
        {/* FR-5.1: System Overview */}
        <section>
          <h2 className="text-2xl mb-4 font-semibold text-[#b480ff]">System Overview</h2>
          {stats ? (
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              {/* Using raw div for layout simplicity instead of StatCard */}
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
                {/* Count only currently running containers for quota visualization */}
                <p>{instances.filter(inst => inst.status === 'running').length}</p>
              </div>
            </div>
          ) : (
            <div className="text-gray-400">System stats unavailable.</div>
          )}
        </section>
        
        {/* FR-4.0: User Instances List */}
        <section>
          <h2 className="text-2xl mb-4 font-semibold text-[#b480ff]">Your Active Instances ({instances.length})</h2>
          {instances.length === 0 ? (
            <p className="text-gray-400">You have no active instances. Spawn one from an approved image above or visit the <a href="/upload" className="text-[#a855f7] hover:underline">Upload</a> page to submit a new project.</p>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {instances.map((inst) => (
                <ContainerCard 
                  key={inst.cid}
                  cid={inst.cid}
                  name={inst.name}
                  status={inst.status}
                  expiresAt={inst.expires_at}
                  subdomain={inst.subdomain} // FIX 4: Pass subdomain/URL
                  onActionSuccess={fetchData} // Pass the refresh function
                />
              ))}
            </div>
          )}
        </section>
      </main>
    </div>
  );
}