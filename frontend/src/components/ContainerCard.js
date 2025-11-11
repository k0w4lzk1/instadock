"use client"
export default function ContainerCard({ name, status }) {
  const color =
    status === "Running" ? "text-green-400" :
    status === "Pending" ? "text-yellow-400" :
    "text-red-400"

  return (
    <div className="bg-gray-800/70 backdrop-blur p-5 rounded-xl border border-gray-700 hover:border-indigo-500 transition group">
      <div>
        <h4 className="text-lg font-semibold text-indigo-300 group-hover:text-indigo-400 transition">{name}</h4>
        <p className={`text-sm mt-1 ${color}`}>{status}</p>
      </div>
      <div className="flex gap-2 mt-4">
        <button className="flex-1 bg-indigo-600 hover:bg-indigo-700 px-3 py-1 rounded text-sm">Start</button>
        <button className="flex-1 bg-red-600 hover:bg-red-700 px-3 py-1 rounded text-sm">Stop</button>
      </div>
    </div>
  )
}
