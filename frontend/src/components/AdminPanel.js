"use client"
import { useEffect, useState } from "react"
import { fetchPending, approveSubmission, rejectSubmission } from "@/lib/api"

export default function AdminPanel() {
  const [pending, setPending] = useState([])

  useEffect(() => {
    fetchPending().then(setPending)
  }, [])

  async function handleDecision(id, approved) {
    approved ? await approveSubmission(id) : await rejectSubmission(id)
    setPending((p) => p.filter((x) => x.id !== id))
  }

  return (
    <div className="bg-gray-800/80 border border-gray-700 rounded-xl p-6 shadow-md space-y-4">
      {pending.length === 0 && (
        <p className="text-gray-500 text-sm text-center">No pending submissions 🎉</p>
      )}
      {pending.map((item) => (
        <div key={item.id} className="flex justify-between items-center bg-gray-900/70 p-4 rounded-lg">
          <div>
            <p className="font-medium text-indigo-300">{item.name}</p>
            <p className="text-sm text-gray-400">{item.type === "repo" ? item.repo : item.filename}</p>
          </div>
          <div className="space-x-2">
            <button onClick={() => handleDecision(item.id, true)} className="bg-green-600 hover:bg-green-700 px-3 py-1 rounded text-sm">
              Approve
            </button>
            <button onClick={() => handleDecision(item.id, false)} className="bg-red-600 hover:bg-red-700 px-3 py-1 rounded text-sm">
              Reject
            </button>
          </div>
        </div>
      ))}
    </div>
  )
}
