"use client"
import { useState } from "react"
import { submitZip, submitRepo } from "@/lib/api"

export default function UploadForm() {
  const [zip, setZip] = useState(null)
  const [repo, setRepo] = useState("")
  const [status, setStatus] = useState("")

  async function handleZip(e) {
    e.preventDefault()
    if (!zip) return setStatus("Select a ZIP first!")
    setStatus("Uploading...")
    await submitZip(zip)
    setStatus("ZIP submitted for admin review ✅")
  }

  async function handleRepo(e) {
    e.preventDefault()
    if (!repo) return setStatus("Enter repo URL!")
    setStatus("Submitting...")
    await submitRepo(repo)
    setStatus("Repo submitted for review ✅")
  }

  return (
    <div className="bg-gray-800/80 p-6 rounded-xl border border-gray-700 shadow-md space-y-4">
      <form onSubmit={handleZip} className="space-y-2">
        <label className="block text-sm text-gray-400">Upload ZIP File</label>
        <input
          type="file"
          accept=".zip"
          onChange={(e) => setZip(e.target.files[0])}
          className="bg-gray-700 text-gray-100 w-full rounded px-3 py-2 focus:outline-none"
        />
        <button className="bg-indigo-600 hover:bg-indigo-700 px-4 py-2 rounded text-sm w-full mt-2">Upload ZIP</button>
      </form>

      <div className="border-t border-gray-700 my-4"></div>

      <form onSubmit={handleRepo} className="space-y-2">
        <label className="block text-sm text-gray-400">GitHub Repo URL</label>
        <input
          type="text"
          value={repo}
          onChange={(e) => setRepo(e.target.value)}
          placeholder="https://github.com/user/repo"
          className="bg-gray-700 text-gray-100 w-full rounded px-3 py-2 focus:outline-none"
        />
        <button className="bg-indigo-600 hover:bg-indigo-700 px-4 py-2 rounded text-sm w-full mt-2">Submit Repo</button>
      </form>

      {status && <p className="text-gray-300 text-sm mt-3">{status}</p>}
    </div>
  )
}
