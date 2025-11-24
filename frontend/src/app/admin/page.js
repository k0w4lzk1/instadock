"use client";
import { useEffect, useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import { getToken } from "@/lib/auth";
import AdminPanel from "@/components/AdminPanel"; 
import { getAllApprovedSubmissionsAdmin, getAllInstancesAdmin, getAdminStats, deleteInstance, stopInstance, startInstance, restartInstance } from "@/lib/api";
import { formatDistanceToNow, isFuture, parseISO } from 'date-fns';
import { RefreshCw, Activity, StopCircle, PlayCircle, Trash2 } from 'lucide-react';
import StatCard from "@/components/StatCard";


function AdminTable({ title, data, headers, actions, onActionSuccess }) {
    if (!data) return <p>Loading {title}...</p>;
    
    // Check if data is an empty list, handle both instances and submissions
    const hasData = Array.isArray(data) && data.length > 0;

    return (
        <div className="bg-[#1a1a24]/60 p-6 rounded-lg border border-[#6332ff]/30 shadow-xl overflow-x-auto">
            <div className="flex justify-between items-center mb-4">
                <h2 className="text-xl font-bold text-gray-100">{title} ({hasData ? data.length : 0})</h2>
                {actions && <button onClick={onActionSuccess} className="text-gray-400 hover:text-[#b480ff]"><RefreshCw size={16} /></button>}
            </div>
            
            {!hasData ? (
                <p className="text-gray-400">No {title.toLowerCase()} found.</p>
            ) : (
                <table className="min-w-full text-sm text-left text-gray-400">
                    <thead className="text-xs uppercase bg-[#2d2d3a]">
                        <tr>
                            {headers.map(header => <th key={header} scope="col" className="px-6 py-3">{header}</th>)}
                            {actions && <th scope="col" className="px-6 py-3 text-right">Actions</th>}
                        </tr>
                    </thead>
                    <tbody>
                        {data.map((item) => {
                            const isInstance = !!item.cid;
                            const isRunning = isInstance && (item.status === 'running' || item.live_status === 'running');
                            const isStopped = isInstance && (item.status === 'stopped' || item.live_status === 'exited');
                            const isExpired = isInstance && !isFuture(parseISO(item.expires_at));
                            
                            // Handler for instance controls
                            const handleInstanceAction = async (cid, actionType) => {
                                let actionFn;
                                const actionMap = { 'delete': deleteInstance, 'stop': stopInstance, 'start': startInstance, 'restart': restartInstance };
                                actionFn = actionMap[actionType];

                                if (actionType === 'delete' && !window.confirm(`WARNING: Are you sure you want to PERMANENTLY DELETE container ${cid}?`)) {
                                    return;
                                }

                                try {
                                    await actionFn(cid);
                                    onActionSuccess();
                                } catch (e) {
                                    alert(`Failed to ${actionType} container: ${e.message}`);
                                }
                            };

                            return (
                                <tr key={item.id || item.cid} className="bg-[#161622] border-b border-gray-700 hover:bg-[#2d2d3a] transition-colors">
                                    
                                    {/* General Data Columns (Applies to both) */}
                                    <td className="px-6 py-4 font-medium text-gray-200 truncate">{item.id ? item.id.substring(0, 8) : item.cid.substring(0, 10)}</td>
                                    <td className="px-6 py-4">{item.user_id.substring(0, 8)}</td>
                                    <td className="px-6 py-4 truncate text-xs">{isInstance ? item.image : item.image_tag}</td>
                                    
                                    {/* Instance-Specific Columns */}
                                    {isInstance && (
                                        <>
                                            <td className={`px-6 py-4 font-semibold ${isRunning ? 'text-green-400' : isExpired ? 'text-red-400' : 'text-yellow-400'}`}>
                                                {isRunning ? 'RUNNING' : item.status.toUpperCase()}
                                            </td>
                                            <td className="px-6 py-4 text-xs">{item.subdomain}</td>
                                            <td className="px-6 py-4 text-xs">
                                                {isFuture(parseISO(item.expires_at)) 
                                                    ? formatDistanceToNow(parseISO(item.expires_at), { addSuffix: true })
                                                    : <span className="text-red-400">EXPIRED</span>
                                                }
                                            </td>
                                            <td className="px-6 py-4 text-xs text-center">{item.cpu}% / {item.mem}MB</td>
                                        </>
                                    )}

                                    {/* Submission-Specific Columns */}
                                    {!isInstance && (
                                        <>
                                            <td className="px-6 py-4 text-xs">{item.source.includes('github') ? 'Repo' : 'ZIP'}</td>
                                            <td className="px-6 py-4 text-xs text-green-400">{item.status.toUpperCase()}</td>
                                        </>
                                    )}

                                    {/* Actions Column */}
                                    {actions && isInstance && (
                                        <td className="px-6 py-4 text-right flex justify-end space-x-2">
                                            <button 
                                                onClick={() => handleInstanceAction(item.cid, 'restart')}
                                                disabled={!isRunning} 
                                                title="Restart"
                                                className={`p-1 rounded ${isRunning ? 'bg-indigo-600 hover:bg-indigo-700' : 'bg-gray-500 cursor-not-allowed'}`}
                                            >
                                                <RefreshCw size={16} />
                                            </button>
                                            <button 
                                                onClick={() => handleInstanceAction(item.cid, 'stop')}
                                                disabled={!isRunning} 
                                                title="Stop"
                                                className={`p-1 rounded ${isRunning ? 'bg-red-600 hover:bg-red-700' : 'bg-gray-500 cursor-not-allowed'}`}
                                            >
                                                <StopCircle size={16} />
                                            </button>
                                            <button 
                                                onClick={() => handleInstanceAction(item.cid, 'delete')}
                                                title="Delete Permanently"
                                                className="p-1 rounded bg-gray-700 hover:bg-red-900 text-red-400 border border-red-500"
                                            >
                                                <Trash2 size={16} />
                                            </button>
                                        </td>
                                    )}
                                </tr>
                            );
                        })}
                    </tbody>
                </table>
            )}
        </div>
    );
}


export default function AdminPage() {
    const router = useRouter();
    const [stats, setStats] = useState(null);
    const [allInstances, setAllInstances] = useState(null);
    const [allApprovedSubmissions, setAllApprovedSubmissions] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState("");

    const fetchAllAdminData = useCallback(async () => {
        const token = getToken();
        if (!token) {
            router.push("/login");
            return;
        }

        try {
            const [instancesRes, approvedRes, statsRes] = await Promise.all([
                getAllInstancesAdmin(),
                getAllApprovedSubmissionsAdmin(),
                getAdminStats()
            ]);
            setAllInstances(instancesRes);
            setAllApprovedSubmissions(approvedRes);
            setStats(statsRes);
        } catch (e) {
            setError(`Error fetching global data: ${e.message}`);
            if (e.message.includes("expired") || e.message.includes("403")) {
                router.push("/login");
            }
        } finally {
            setLoading(false);
        }
    }, [router]);


    useEffect(() => {
        fetchAllAdminData();
    }, [fetchAllAdminData]);

    if (loading) return <p className="text-center text-gray-400 mt-10">Loading Admin Data...</p>;
    if (error && !error.includes("403")) return <p className="text-center text-red-400 mt-10">Error: {error}</p>;

    const runningInstances = allInstances ? allInstances.filter(i => i.status === 'running').length : 0;
    const totalSubmissions = allApprovedSubmissions ? allApprovedSubmissions.length : 0;


    return (
        <div className="min-h-screen bg-[#0a0a0f] text-gray-100 p-8">
            <h1 className="text-4xl font-extrabold text-center text-[#b480ff] mb-8">
                🐋 Admin Control Panel
            </h1>

            <div className="space-y-12">
                
                {/* FIX 3: Admin System Overview */}
                <section className="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-4 gap-6">
                    <StatCard title="Running Containers" value={runningInstances} icon={<Activity size={20} />} />
                    <StatCard title="Total Images (Approved)" value={totalSubmissions} icon={<Activity size={20} />} />
                    <StatCard title="Host CPU Usage" value={`${stats ? stats.cpu_percent : '0'}%`} icon={<Activity size={20} />} />
                    <StatCard title="Host Memory Used" value={`${stats ? stats.memory_percent : '0'}%`} icon={<Activity size={20} />} />
                </section>
                
                {/* Pending Submissions Approval */}
                <section>
                    <h2 className="text-2xl font-bold mb-4 text-gray-100">Awaiting Approval</h2>
                    <AdminPanel fetchPending={fetchAllAdminData} /> 
                </section>

                {/* FIX 2: All Active Instances Table */}
                <AdminTable 
                    title="All Spawning Instances" 
                    data={allInstances}
                    headers={['Container ID', 'User ID', 'Status', 'Image Tag', 'URL', 'Expiry', 'Metrics']}
                    actions={true}
                    onActionSuccess={fetchAllAdminData}
                />
                
                {/* FIX 2: All Approved Submissions Table */}
                <AdminTable 
                    title="All Approved Images (Full List)" 
                    data={allApprovedSubmissions}
                    headers={['Submission ID', 'User ID', 'Image Tag', 'Source', 'Status']}
                />
            </div>
        </div>
    );
}