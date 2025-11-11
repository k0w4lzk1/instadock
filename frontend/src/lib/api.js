import { getToken } from "./auth";

const API_BASE = "http://127.0.0.1:8000";

export async function apiFetch(endpoint, options = {}) {
  const token = getToken();
  const headers = {
    ...(options.headers || {}),
    Authorization: token ? `Bearer ${token}` : undefined,
  };

  const res = await fetch(`${API_BASE}${endpoint}`, {
    ...options,
    headers,
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Request failed: ${res.status}`);
  }

  return res.json();
}

export async function getSystemStats() {
  return apiFetch("/system/stats");
}

export async function getContainers() {
  return apiFetch("/admin/containers");
}

export async function submitRepo(repo_url, ref) {
  return apiFetch("/submit/repo", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ repo_url, ref }),
  });
}

export async function submitZip(file) {
  const formData = new FormData();
  formData.append("file", file);

  return apiFetch("/submit/zip", {
    method: "POST",
    body: formData,
  });
}

export async function approveSubmission(id) {
  return apiFetch(`/admin/approve/${id}`, { method: "POST" });
}

export async function rejectSubmission(id) {
  return apiFetch(`/admin/reject/${id}`, { method: "POST" });
}
