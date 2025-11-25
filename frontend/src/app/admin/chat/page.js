"use client";
import React, { useState, useEffect, useRef, useCallback } from 'react';
import { getToken } from '@/lib/auth';
import { X, MessageSquare, Send } from 'lucide-react';
import Link from 'next/link';

// NOTE: This setup uses a simple broadcast mechanism. In a real chat, the backend 
// would handle user lookup to allow direct admin-to-user messaging.

const getChatWebSocketUrl = () => {
    const token = getToken();
    const wsBase = "ws://127.0.0.1:8000"; // Assuming API_BASE is http://127.0.0.1:8000
    return `${wsBase}/ws/admin/chat?authorization=Bearer%20${token}`;
};


export default function AdminChatPage() {
    const [messages, setMessages] = useState([]);
    const [inputValue, setInputValue] = useState('');
    const [status, setStatus] = useState('Connecting...');
    const wsRef = useRef(null);
    const chatEndRef = useRef(null);

    const setupWebSocket = useCallback(() => {
        const wsUrl = getChatWebSocketUrl();
        
        const ws = new WebSocket(wsUrl);
        wsRef.current = ws;

        ws.onopen = () => {
            setStatus('Connected. Ready for chat/support.');
        };

        ws.onmessage = (event) => {
            setMessages(prev => [...prev, { text: event.data, sender: 'server' }]);
        };

        ws.onclose = (event) => {
            let reason = event.reason || 'Closed by server or network error';
            if (event.code === 1008) {
                reason = "Authentication failed. Please log in again.";
            }
            setStatus(`Disconnected. Code: ${event.code}. Reason: ${reason}`);
        };

        ws.onerror = (error) => {
            setStatus('Connection Error.');
            ws.close();
        };

        return ws;
    }, []);

    useEffect(() => {
        // 1. Establish connection
        setupWebSocket();

        // 2. Cleanup function: close WebSocket when component unmounts
        return () => {
            if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
                wsRef.current.close();
            }
        };
    }, [setupWebSocket]);
    
    useEffect(() => {
        // Auto-scroll to bottom
        chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, [messages]);


    const sendMessage = (e) => {
        e.preventDefault();
        if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN || !inputValue.trim()) return;

        const message = inputValue.trim();
        
        // Display user message immediately
        setMessages(prev => [...prev, { text: `[You]: ${message}`, sender: 'user' }]);

        // Send message to server
        wsRef.current.send(message);

        setInputValue('');
    };

    return (
        <div className="min-h-screen bg-gray-50 dark:bg-[#0a0a0f] text-gray-800 dark:text-gray-100 p-8 transition-colors duration-300">
            <div className="max-w-3xl mx-auto h-[85vh] flex flex-col bg-white dark:bg-[#1a1a24] rounded-xl shadow-2xl border border-indigo-400/40 dark:border-[#6332ff]/40">
                
                {/* Header */}
                <div className="p-4 border-b border-gray-300 dark:border-gray-700 flex justify-between items-center">
                    <div className="flex items-center space-x-3">
                        <MessageSquare size={24} className="text-[#6332ff] dark:text-[#b480ff]" />
                        <h1 className="text-xl font-bold">Admin Support Chat</h1>
                    </div>
                    <Link href="/dashboard" className="text-gray-600 dark:text-gray-400 hover:text-red-500">
                        <X size={20} />
                    </Link>
                </div>

                {/* Status */}
                <div className="p-3 text-xs bg-gray-100 dark:bg-[#2d2d3a] border-b border-gray-300 dark:border-gray-700">
                    Status: <span className={status.includes('Connected') ? 'text-green-500' : 'text-red-500'}>{status}</span>
                </div>

                {/* Message Display Area */}
                <div className="flex-1 overflow-y-auto p-4 space-y-3">
                    {messages.map((msg, index) => (
                        <div 
                            key={index} 
                            className={`text-wrap ${msg.sender === 'user' ? 'text-right' : 'text-left'}`}
                        >
                            <span 
                                className={`inline-block px-3 py-1 rounded-lg max-w-[80%] ${
                                    msg.sender === 'user' 
                                    ? 'bg-[#6332ff] text-white' 
                                    : 'bg-gray-200 dark:bg-gray-700 text-gray-800 dark:text-gray-100'
                                }`}
                            >
                                {msg.text}
                            </span>
                        </div>
                    ))}
                    <div ref={chatEndRef} />
                </div>

                {/* Input Area */}
                <form onSubmit={sendMessage} className="p-4 border-t border-gray-300 dark:border-gray-700 flex space-x-3">
                    <input
                        type="text"
                        value={inputValue}
                        onChange={(e) => setInputValue(e.target.value)}
                        placeholder="Type your message or 'ping'..."
                        className="flex-1 p-3 bg-gray-100 dark:bg-[#2d2d3a] border border-gray-300 dark:border-gray-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#b480ff] text-gray-800 dark:text-gray-100"
                        disabled={wsRef.current && wsRef.current.readyState !== WebSocket.OPEN}
                    />
                    <button
                        type="submit"
                        className="bg-[#a855f7] hover:bg-[#9333ea] text-white p-3 rounded-lg disabled:bg-gray-500"
                        disabled={wsRef.current && wsRef.current.readyState !== WebSocket.OPEN}
                    >
                        <Send size={20} />
                    </button>
                </form>
            </div>
        </div>
    );
}