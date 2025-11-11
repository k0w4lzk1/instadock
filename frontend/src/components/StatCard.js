export default function StatCard({ title, value }) {
  return (
    <div className="bg-gray-800/70 backdrop-blur p-4 rounded-xl border border-gray-700 shadow-md hover:border-indigo-500 transition">
      <h3 className="text-gray-400 text-sm">{title}</h3>
      <p className="text-3xl font-bold text-indigo-400 mt-2">{value}</p>
    </div>
  )
}
