"use client";

import { useEffect, useState } from "react";
import { getToken } from "@/lib/auth";
import { deleteSubmission, approveSubmission, rejectSubmission } from "@/lib/api"; // Updated imports

export default function AdminPanel() {
  const [submissions, setSubmissions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  // 🧠 Fetch pending submissions from backend
  async function fetchSubmissions() {
    try {
      const token = getToken();
      const res = await fetch("http://127.0.0.1:8000/admin/submissions", {
        headers: { Authorization: `Bearer ${token}` },
      });

      if (!res.ok) throw new Error("Failed to fetch submissions");
      const data = await res.json();
      setSubmissions(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  // 🧱 Approve, Reject, or Delete Submission
  async function handleAction(subId, action) {
    let actionFn;
    let message;
    
    if (action === "delete") {
        if (!window.confirm("WARNING: Are you sure you want to PERMANENTLY DELETE this submission? This cannot be undone and deletes the git branch.")) {
            return;
        }
        actionFn = deleteSubmission;
        message = "Failed to permanently delete submission.";
    } else if (action === "approve") {
        actionFn = approveSubmission;
        message = "Failed to approve submission.";
    } else if (action === "reject") {
        actionFn = rejectSubmission;
        message = "Failed to reject submission.";
    } else {
        return;
    }

    try {
        await actionFn(subId);
        setSubmissions((prev) => prev.filter((s) => s.id !== subId));
    } catch (err) {
      const errMsg = err.message.includes('404') ? 'Submission not found.' : err.message;
      alert(`${message} Error: ${errMsg}`);
    }
  }

  useEffect(() => {
    fetchSubmissions();
  }, []);

  if (loading) return <p className="text-center text-gray-400 mt-10">Loading...</p>;
  if (error) return <p className="text-center text-red-400 mt-10">Error: {error}</p>;

  return (
    <div className="p-8 text-gray-100">
      <h1 className="text-3xl font-bold text-center bg-gradient-to-r from-[#b480ff] to-[#6332ff] bg-clip-text text-transparent mb-8">
        Admin Control Panel
      </h1>

      {submissions.length === 0 ? (
        <p className="text-center text-gray-400">No pending submissions found.</p>
      ) : (
        <div className="space-y-4">
          {submissions.map((sub) => (
            <div
              key={sub.id}
              className="bg-[#161622]/80 border border-[#6332ff]/30 p-4 rounded-lg flex justify-between items-center shadow-lg"
            >
              <div>
                <p className="font-semibold text-[#b480ff]">{sub.branch}</p>
                <p className="text-sm text-gray-400">
                  Submitted by: <span className="text-gray-300">{sub.user_id}</span>
                </p>
              </div>
              <div className="space-x-3">
                <button
                  onClick={() => handleAction(sub.id, "approve")}
                  className="px-3 py-1 bg-green-600 hover:bg-green-700 rounded-md"
                >
                  Approve
                </button>
                <button
                  onClick={() => handleAction(sub.id, "reject")}
                  className="px-3 py-1 bg-red-600 hover:bg-red-700 rounded-md"
                >
                  Reject
                </button>
                <button
                  onClick={() => handleAction(sub.id, "delete")}
                  className="px-3 py-1 bg-gray-700 hover:bg-gray-800 rounded-md text-red-400 border border-red-500"
                >
                  Delete (Perm)
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}