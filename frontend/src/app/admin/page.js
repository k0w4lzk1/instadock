"use client";
import { useEffect, useState } from "react";
import { getToken } from "@/lib/auth";

export default function AdminPanel() {
  const [submissions, setSubmissions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    async function fetchSubs() {
      try {
        const res = await fetch("http://127.0.0.1:8000/system/stats", {
          headers: {
            Authorization: `Bearer ${getToken()}`,
          },
        });
        if (!res.ok) throw new Error("Failed to fetch submissions");
        const data = await res.json();
        setSubmissions(data.submissions || []);
      } catch (err) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    }
    fetchSubs();
  }, []);

  async function handleAction(sub_id, action) {
    try {
      const res = await fetch(`http://127.0.0.1:8000/admin/${action}/${sub_id}`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${getToken()}`,
        },
      });
      if (!res.ok) throw new Error(`Failed to ${action}`);
      alert(`${action} successful`);
      setSubmissions(submissions.filter((s) => s.id !== sub_id));
    } catch (err) {
      alert(err.message);
    }
  }

  if (loading)
    return (
      <div className="flex justify-center items-center min-h-screen text-gray-300">
        Loading submissions...
      </div>
    );

  if (error)
    return (
      <div className="text-red-400 text-center mt-10">
        Error fetching submissions: {error}
      </div>
    );

  return (
    <div className="p-10 text-gray-200 min-h-screen bg-[#0a0a0f]">
      <h1 className="text-4xl font-bold mb-8 bg-gradient-to-r from-[#b480ff] to-[#6332ff] bg-clip-text text-transparent">
        Admin Control Panel
      </h1>

      {submissions.length === 0 ? (
        <p className="text-gray-400">No pending submissions found.</p>
      ) : (
        <div className="grid gap-6">
          {submissions.map((sub) => (
            <div
              key={sub.id}
              className="bg-[#161622]/80 border border-[#6332ff]/30 p-5 rounded-lg shadow-md flex justify-between items-center"
            >
              <div>
                <p>
                  <span className="font-semibold text-[#b480ff]">User:</span>{" "}
                  {sub.user_id}
                </p>
                <p>
                  <span className="font-semibold text-[#b480ff]">Branch:</span>{" "}
                  {sub.branch}
                </p>
                <p>
                  <span className="font-semibold text-[#b480ff]">Repo:</span>{" "}
                  {sub.repo_url}
                </p>
                <p>
                  <span className="font-semibold text-[#b480ff]">Status:</span>{" "}
                  {sub.status}
                </p>
              </div>
              <div className="flex gap-3">
                <button
                  onClick={() => handleAction(sub.id, "approve")}
                  className="bg-green-600 hover:bg-green-700 px-3 py-1 rounded"
                >
                  ✅ Approve
                </button>
                <button
                  onClick={() => handleAction(sub.id, "reject")}
                  className="bg-red-600 hover:bg-red-700 px-3 py-1 rounded"
                >
                  ❌ Reject
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
