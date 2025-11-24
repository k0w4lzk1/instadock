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

export async function getContainersForAdmin() {
  return apiFetch("/admin/containers");
}

export async function getUserInstances() {
  return apiFetch("/instance/me");
}

export async function getApprovedSubmissions() {
  return apiFetch("/user/approved_submissions");
}

export async function spawnNewInstance(submission_id) {
    return apiFetch("/spawn", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        // Hardcode TTL to 1 hour (3600 seconds) for simplicity
        body: JSON.stringify({ submission_id, ttl_seconds: 3600 }), 
    });
}

export async function stopInstance(cid) {
  return apiFetch(`/stop/${cid}`, { method: "POST" });
}

export async function startInstance(cid) {
  return apiFetch(`/start/${cid}`, { method: "POST" });
}

export async function restartInstance(cid) {
  return apiFetch(`/restart/${cid}`, { method: "POST" });
}

// FR-4.0: New API wrapper for permanent deletion
export async function deleteInstance(cid) {
  return apiFetch(`/delete/${cid}`, { method: "DELETE" });
}

export function getLogWebSocketUrl(cid) {
    const token = getToken();
    // Assuming API_BASE is http://127.0.0.1:8000, convert to ws://
    const wsBase = API_BASE.replace('http', 'ws');
    return `${wsBase}/ws/logs/${cid}?authorization=Bearer%20${token}`;
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

// FIX 2: New API wrapper for admin permanent submission deletion
export async function deleteSubmission(id) {
  return apiFetch(`/admin/submission/${id}`, { method: "DELETE" });
}