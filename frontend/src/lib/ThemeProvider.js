"use client"; // CRITICAL: This directive is mandatory for using React Hooks

import React, { createContext, useContext, useState, useEffect } from 'react';

const ThemeContext = createContext(undefined); // Default to undefined

export const useTheme = () => useContext(ThemeContext); // FIX: Simple useContext call

export const ThemeProvider = ({ children }) => {
  const [theme, setTheme] = useState('dark');
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    // 1. Check for stored theme preference on initial load
    const savedTheme = localStorage.getItem('theme');
    const initialTheme = savedTheme || 'dark'; // Default to dark if none found
    
    setTheme(initialTheme);
    setMounted(true);
  }, []);

  useEffect(() => {
    if (!mounted) return;

    const root = window.document.documentElement;

    // 2. Apply/Remove 'dark' class to the root HTML element
    if (theme === 'dark') {
      root.classList.add('dark');
    } else {
      root.classList.remove('dark');
    }
    
    // 3. Save preference
    localStorage.setItem('theme', theme);
  }, [theme, mounted]);

  const toggleTheme = () => {
    setTheme(currentTheme => (currentTheme === 'dark' ? 'light' : 'dark'));
  };

  if (!mounted) {
    // Prevent flicker by not rendering until theme is determined
    return <div className="min-h-screen bg-[#0a0a0f]">{children}</div>;
  }

  const contextValue = { theme, toggleTheme };
  
  return (
    <ThemeContext.Provider value={contextValue}>
      {children}
    </ThemeContext.Provider>
  );
};