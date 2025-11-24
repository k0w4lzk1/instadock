"use client"
import { stopInstance, startInstance, restartInstance, deleteInstance } from "@/lib/api";
import Link from 'next/link'; 

export default function ContainerCard({ cid, name, status, expiresAt, subdomain, onActionSuccess }) {
  const color =
    status === "running" ? "text-green-400" :
    status === "stopped" ? "text-yellow-400" : 
    "text-red-400" 
  
  // Dynamic border color based on status
  const borderColor = 
    status === "running" ? "border-green-600/50" :
    status === "stopped" ? "border-yellow-600/50" :
    "border-red-600/50";


  const displayStatus = status.charAt(0).toUpperCase() + status.slice(1);
  
  let expiryDate = "N/A";
  try {
    expiryDate = new Date(expiresAt).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  } catch (e) {
    // Gracefully handle invalid date format
  }

  const instanceUrl = subdomain && subdomain !== "N/A" ? `http://${subdomain}` : "N/A";
  
  const isRunning = status === 'running';
  const isStopped = status === 'stopped';
  const canViewLogs = status !== 'removed' && status !== 'deleted'; 

  async function handleAction(actionType) {
    let confirmationMessage;
    
    if (actionType === 'delete') {
        confirmationMessage = `WARNING: Are you sure you want to PERMANENTLY DELETE container ${name} (${cid})? This cannot be undone.`;
    } else {
        confirmationMessage = `Are you sure you want to ${actionType} container ${name} (${cid})?`;
    }
    
    if (!window.confirm(confirmationMessage)) {
      return;
    }
    
    let actionFn;
    switch (actionType) {
      case 'stop': actionFn = stopInstance; break;
      case 'start': actionFn = startInstance; break;
      case 'restart': actionFn = restartInstance; break;
      case 'delete': actionFn = deleteInstance; break; 
      default: return;
    }

    try {
      await actionFn(cid);
      onActionSuccess();
    } catch (e) {
      alert(`Failed to ${actionType} container: ${e.message}`);
    }
  }


  return (
    <div className={`bg-gray-800/70 backdrop-blur p-5 rounded-xl border-t-4 ${borderColor} shadow-2xl hover:shadow-indigo-900/50 transition group space-y-3`}>
      <div className="border-b border-gray-700 pb-3">
        <h4 className="text-xl font-bold text-indigo-300 group-hover:text-indigo-400 transition truncate">{name}</h4>
        <p className={`text-sm mt-1 font-semibold ${color}`}>Status: {displayStatus}</p>
      </div>
      
      <div className="text-xs space-y-1">
        <p className="text-gray-400">ID: <span className="text-gray-300">{cid}</span></p>
        <p className="text-gray-400">Expires at: <span className="text-gray-300">{expiryDate}</span></p>
        
        {/* URL Link */}
        <p className="text-gray-400 truncate">
            URL: {instanceUrl !== "N/A" ? (
                <a href={instanceUrl} target="_blank" rel="noopener noreferrer" className="text-blue-400 hover:underline font-medium">{instanceUrl}</a>
            ) : (
                <span className="text-gray-500">(N/A)</span>
            )}
        </p>
      </div>
      
      {/* Action Buttons */}
      <div className="flex gap-2 pt-2">
          <Link 
              href={`/log/${cid}`}
              className={`flex-1 text-center px-3 py-2 rounded text-sm font-semibold transition-colors ${
                  canViewLogs 
                  ? "bg-[#a855f7] hover:bg-[#9333ea]"
                  : "bg-gray-500 cursor-not-allowed text-gray-300"
              }`}
              style={{ pointerEvents: canViewLogs ? 'auto' : 'none' }}
          >
              View Logs
          </Link>
      </div>

      <div className="flex gap-2">
        
        {/* Restart Button */}
        <button 
          className={`flex-1 px-3 py-2 rounded text-sm font-medium transition-colors ${
            isRunning 
            ? "bg-indigo-600 hover:bg-indigo-700" 
            : "bg-gray-500 cursor-not-allowed" 
          }`}
          onClick={() => handleAction('restart')}
          disabled={!isRunning} 
        >
          Restart
        </button>
        
        {/* Start Button */}
        <button 
          className={`flex-1 px-3 py-2 rounded text-sm font-medium transition-colors ${
            isStopped 
            ? "bg-green-600 hover:bg-green-700" 
            : "bg-gray-500 cursor-not-allowed"
          }`}
          onClick={() => handleAction('start')}
          disabled={!isStopped}
        >
          Start
        </button>
        
        {/* Stop Button */}
        <button 
          className={`flex-1 px-3 py-2 rounded text-sm font-medium transition-colors ${
            isRunning 
            ? "bg-red-600 hover:bg-red-700" 
            : "bg-gray-500 cursor-not-allowed"
          }`}
          onClick={() => handleAction('stop')}
          disabled={!isRunning}
        >
          Stop
        </button>
      </div>
      
      {/* Delete Button */}
      <div>
        <button
          className="w-full px-3 py-2 rounded text-sm font-semibold transition-colors bg-gray-700 hover:bg-gray-800 border border-red-500 text-red-400"
          onClick={() => handleAction('delete')}
        >
          PERMANENTLY DELETE
        </button>
      </div>
    </div>
  )
}