"use client";

import Navbar from "@/components/Navbar";

export default function ThemeWrapper() {
  // This component ensures Navbar runs inside the ThemeProvider in layout.js
  return <Navbar />;
}