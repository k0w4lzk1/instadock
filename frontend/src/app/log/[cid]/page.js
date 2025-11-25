"use client";
import { useEffect, useRef, useState, useCallback } from 'react';
import { useParams } from 'next/navigation';
import { fetchInstanceLogs } from '@/lib/api'; // FIX: Import new REST function
import { Terminal, X, Zap, Loader } from 'lucide-react';
import Link from 'next/link';

export default function LogStreamPage() {
  const { cid } = useParams();
  const [logs, setLogs] = useState([]);
  const [status, setStatus] = useState('Loading...');
  const [isPolling, setIsPolling] = useState(true);
  const [error, setError] = useState(null);
  const logContainerRef = useRef(null);
  const POLLING_INTERVAL = 2000; // Poll every 2 seconds

  const fetchLogs = useCallback(async () => {
    try {
        const data = await fetchInstanceLogs(cid);
        // We only want to set logs if they have changed or on first load
        setLogs(data.logs);
        setStatus('Streaming via HTTP Polling');
        setError(null);
    } catch (e) {
        // If the container is gone (404), stop polling
        if (e.message.includes("404")) {
            setStatus('Instance Not Found (Stopped or Removed)');
            setIsPolling(false);
            setError(e.message);
        } else {
            setStatus('Polling Failed');
            setError(e.message);
        }
    }
  }, [cid]);

  useEffect(() => {
    if (!isPolling) return;
    
    // 1. Initial fetch
    fetchLogs();
    
    // 2. Set up polling interval
    const interval = setInterval(fetchLogs, POLLING_INTERVAL); 

    // 3. Cleanup function: clear interval when component unmounts
    return () => clearInterval(interval);

  }, [isPolling, fetchLogs]);


  useEffect(() => {
    // Auto-scroll to the bottom when new logs arrive
    if (logContainerRef.current) {
      logContainerRef.current.scrollTop = logContainerRef.current.scrollHeight;
    }
  }, [logs]);


  const statusColor = isPolling ? 'text-green-400' : 'text-red-400';

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-[#0a0a0f] text-gray-800 dark:text-gray-100 p-8 transition-colors duration-300">
      <div className="max-w-7xl mx-auto">
        
        <div className="flex justify-between items-center border-b border-gray-300 dark:border-gray-700 pb-4 mb-6">
            <div className="flex items-center space-x-3">
                <Terminal size={32} className="text-[#6332ff] dark:text-[#b480ff]" />
                <h1 className="text-3xl font-bold">Logs for CID: {cid}</h1>
            </div>
            <Link href="/dashboard" className="flex items-center space-x-2 px-3 py-2 bg-gray-700 dark:bg-gray-700 hover:bg-gray-600 dark:hover:bg-gray-600 rounded text-sm text-white">
                <X size={16} />
                <span>Close</span>
            </Link>
        </div>

        <div className="mb-4 p-3 bg-white dark:bg-[#1a1a24] rounded-lg border border-gray-300 dark:border-gray-700">
            <p className="text-sm font-medium flex items-center space-x-2">
                {isPolling ? <Loader size={16} className="animate-spin" /> : <Zap size={16} />}
                <span className={statusColor}>{status}</span>
                {error && <span className="text-red-400 ml-4">Error: {error}</span>}
            </p>
        </div>

        {/* Log Display Terminal */}
        <div 
          ref={logContainerRef}
          className="bg-black text-xs text-green-300 font-mono p-4 rounded-lg h-[70vh] overflow-y-scroll border border-gray-800 shadow-inner"
        >
          {logs.length === 0 ? (
            <p className="text-gray-500">Awaiting log output...</p>
          ) : (
            logs.map((line, index) => (
              <p key={index} className="whitespace-pre-wrap leading-tight">{line}</p>
            ))
          )}
        </div>
      </div>
    </div>
  );
}