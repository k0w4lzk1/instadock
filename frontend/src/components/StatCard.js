export default function StatCard({ title, value, icon }) {
  return (
    <div className="bg-[#1a1a24]/80 backdrop-blur-sm p-5 rounded-xl border border-[#6332ff]/50 shadow-xl transition duration-300 hover:border-indigo-500/70">
      <div className="flex items-center space-x-3">
          <div className="text-indigo-400 p-2 bg-[#2d2d3a] rounded-lg">
              {icon}
          </div>
          <h3 className="text-gray-300 text-sm font-medium">{title}</h3>
      </div>
      
      <p className="text-4xl font-extrabold text-white mt-4 tracking-tight">
        {value}
      </p>
    </div>
  )
}