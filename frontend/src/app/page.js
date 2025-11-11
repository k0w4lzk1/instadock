"use client";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { getToken } from "@/lib/auth";

export default function Home() {
  const router = useRouter();
  const [checked, setChecked] = useState(false);
  const [token, setToken] = useState(null);

  useEffect(() => {
    // Run only in the browser
    if (typeof window !== "undefined") {
      const stored = getToken();
      setToken(stored);
      setChecked(true);
    }
  }, []);

  useEffect(() => {
    if (!checked) return;
    if (token) router.push("/dashboard");
    else router.push("/login");
  }, [checked, token, router]);

  return (
    <div className="flex items-center justify-center min-h-screen bg-[#0a0a0f] text-gray-200">
      <h1 className="text-xl font-semibold text-[#b480ff] animate-pulse">
        Preparing DockerVerse...
      </h1>
    </div>
  );
}
