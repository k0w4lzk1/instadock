"use client"
import { stopInstance, startInstance, restartInstance, deleteInstance } from "@/lib/api";
import Link from 'next/link'; 

export default function ContainerCard({ cid, name, status, expiresAt, subdomain, onActionSuccess }) {
  const color =
    status === "running" ? "text-green-400" :
    status === "stopped" ? "text-yellow-400" : 
    "text-red-400" 

  const displayStatus = status.charAt(0).toUpperCase() + status.slice(1);
  
  let expiryDate = "N/A";
  try {
    expiryDate = new Date(expiresAt).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  } catch (e) {
    // Gracefully handle invalid date format
  }

  // FIX 4: Construct the full URL
  const instanceUrl = subdomain && subdomain !== "N/A" ? `http://${subdomain}` : "N/A";
  
  const isRunning = status === 'running';
  const isStopped = status === 'stopped';
  const canViewLogs = status !== 'removed' && status !== 'deleted'; // Ensure logs can't be viewed if removed

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
      case 'delete': actionFn = deleteInstance; break; // New action
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
    <div className="bg-gray-800/70 backdrop-blur p-5 rounded-xl border border-gray-700 hover:border-indigo-500 transition group">
      <div>
        <h4 className="text-lg font-semibold text-indigo-300 group-hover:text-indigo-400 transition truncate">{name}</h4>
        <p className={`text-sm mt-1 ${color}`}>Status: {displayStatus}</p>
        <p className="text-xs text-gray-400 mt-1">ID: {cid}</p>
        <p className="text-xs text-gray-400 mt-1">Expires at: {expiryDate}</p>
        {/* FIX 4: Display URL */}
        <p className="text-xs text-gray-400 mt-1 truncate">
            URL: {instanceUrl !== "N/A" ? (
                <a href={instanceUrl} target="_blank" rel="noopener noreferrer" className="text-blue-400 hover:underline">{instanceUrl}</a>
            ) : (
                "N/A (Stopped or Invalid)"
            )}
        </p>
      </div>
      
      {/* FR-5.0: View Logs Button */}
      <div className="flex gap-2 mt-4">
          <Link 
              href={`/log/${cid}`}
              className={`flex-1 text-center px-3 py-1 rounded text-sm transition-colors ${
                  canViewLogs 
                  ? "bg-[#a855f7] hover:bg-[#9333ea]"
                  : "bg-gray-500 cursor-not-allowed text-gray-300"
              }`}
              style={{ pointerEvents: canViewLogs ? 'auto' : 'none' }}
          >
              View Logs
          </Link>
      </div>

      <div className="flex gap-2 mt-2">
        
        {/* FR-4.0: Restart Button */}
        <button 
          className={`flex-1 px-3 py-1 rounded text-sm transition-colors ${
            isRunning 
            ? "bg-indigo-600 hover:bg-indigo-700" 
            : "bg-gray-500 cursor-not-allowed" 
          }`}
          onClick={() => handleAction('restart')}
          disabled={!isRunning} 
        >
          Restart
        </button>
        
        {/* FR-4.0: Start Button */}
        <button 
          className={`flex-1 px-3 py-1 rounded text-sm transition-colors ${
            isStopped 
            ? "bg-green-600 hover:bg-green-700" 
            : "bg-gray-500 cursor-not-allowed"
          }`}
          onClick={() => handleAction('start')}
          disabled={!isStopped}
        >
          Start
        </button>
        
        {/* FR-4.0: Stop Button */}
        <button 
          className={`flex-1 px-3 py-1 rounded text-sm transition-colors ${
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
      
      {/* FR-4.0: Delete Button (New) */}
      <div className="mt-2">
        <button
          className="w-full px-3 py-1 rounded text-sm transition-colors bg-gray-700 hover:bg-gray-800 border border-red-500 text-red-400"
          onClick={() => handleAction('delete')}
        >
          PERMANENTLY DELETE
        </button>
      </div>
    </div>
  )
}