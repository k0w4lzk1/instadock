"use client";
import { useState } from "react";
import Navbar from "@/components/Navbar";
import { submitRepo, submitZip } from "@/lib/api";
import { useRouter } from "next/navigation";

// FIX 3: REMOVED SubmissionSection component entirely - its logic moves to dashboard/page.js

export default function UploadPage() {
  const router = useRouter();
  const [repo, setRepo] = useState("");
  const [ref, setRef] = useState("");
  const [file, setFile] = useState(null);
  const [msg, setMsg] = useState("");
  // FIX 3: Removed approvedSubmissions, loadingApproved state

  // FIX 3: Removed fetchApproved function and useEffect call

  async function handleRepoSubmit(e) {
    e.preventDefault();
    setMsg("Submitting repo for review...");
    try {
      const res = await submitRepo(repo, ref);
      setMsg(`Submission successful (${res.submission_id.substring(0, 8)}). Awaiting admin approval.`);
    } catch (e) {
      setMsg(e.message);
    }
  }

  async function handleZipSubmit(e) {
    e.preventDefault();
    if (!file) return setMsg("Choose a ZIP file first.");
    setMsg("Uploading zip for review...");
    try {
      const res = await submitZip(file);
      setMsg(`Uploaded (${res.submission_id.substring(0, 8)}). Awaiting admin approval.`);
    } catch (e) {
      setMsg(e.message);
    }
  }
  
  // FIX 3: Removed onSpawnSuccess callback

  return (
    <div className="min-h-screen bg-[#0a0a0f] text-gray-100">
      <main className="p-8 space-y-10">
        
        {/* FIX 3: Removed New Section for Approved Submissions */}
        
        {/* Existing Submission Forms */}
        <section className="bg-[#1a1a24]/60 p-6 rounded-lg border border-[#6332ff]/30">
          <h2 className="text-xl font-semibold mb-4 text-[#b480ff]">Submit New Project from Repository</h2>
          <form onSubmit={handleRepoSubmit} className="space-y-3">
            <input
              type="text"
              placeholder="Repository URL (e.g., https://github.com/user/repo)"
              value={repo}
              onChange={(e) => setRepo(e.target.value)}
              className="w-full p-2 bg-[#2d2d3a] border border-[#444] rounded"
              required
            />
            <input
              type="text"
              placeholder="Branch / Ref (optional)"
              value={ref}
              onChange={(e) => setRef(e.target.value)}
              className="w-full p-2 bg-[#2d2d3a] border border-[#444] rounded"
            />
            <button
              className="bg-[#6332ff] px-4 py-2 rounded hover:bg-[#5b2be3]"
              type="submit"
            >
              Submit Repo for Review
            </button>
          </form>
        </section>

        <section className="bg-[#1a1a24]/60 p-6 rounded-lg border border-[#6332ff]/30">
          <h2 className="text-xl font-semibold mb-4 text-[#b480ff]">Upload New ZIP File</h2>
          <form onSubmit={handleZipSubmit} className="space-y-3">
            <input
              type="file"
              accept=".zip"
              onChange={(e) => setFile(e.target.files[0])}
              className="w-full bg-[#2d2d3a] p-2 border border-[#444] rounded"
            />
            <button
              className="bg-[#6332ff] px-4 py-2 rounded hover:bg-[#5b2be3]"
              type="submit"
            >
              Upload ZIP for Review
            </button>
          </form>
        </section>

        {msg && <p className="text-sm text-[#b480ff] mt-5">{msg}</p>}
      </main>
    </div>
  );
}