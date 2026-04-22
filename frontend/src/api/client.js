const BASE_URL = '/api'

async function handleResponse(res) {
  if (!res.ok) {
    let message = `Request failed: ${res.status} ${res.statusText}`
    try {
      const body = await res.json()
      if (body.detail) {
        message = typeof body.detail === 'string' ? body.detail : JSON.stringify(body.detail)
      }
    } catch {
      // ignore parse error, use default message
    }
    throw new Error(message)
  }
  // 204 No Content
  if (res.status === 204) return null
  return res.json()
}

export async function analyzeJob(url) {
  const res = await fetch(`${BASE_URL}/jobs/analyze`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ url }),
  })
  return handleResponse(res)
}

export async function getProfile() {
  const res = await fetch(`${BASE_URL}/profile`)
  return handleResponse(res)
}

export async function updateProfile(data) {
  const res = await fetch(`${BASE_URL}/profile`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  })
  return handleResponse(res)
}

export async function getResumes() {
  const res = await fetch(`${BASE_URL}/profile/resumes`)
  return handleResponse(res)
}

export async function uploadResume(file, label) {
  const formData = new FormData()
  formData.append('file', file)
  formData.append('label', label)
  const res = await fetch(`${BASE_URL}/profile/resumes/upload`, {
    method: 'POST',
    body: formData,
  })
  return handleResponse(res)
}

export async function deleteResume(label) {
  const res = await fetch(`${BASE_URL}/profile/resumes/${encodeURIComponent(label)}`, {
    method: 'DELETE',
  })
  return handleResponse(res)
}

export async function getApplications(params = {}) {
  const query = new URLSearchParams()
  Object.entries(params).forEach(([k, v]) => {
    if (v !== undefined && v !== null && v !== '') query.append(k, v)
  })
  const qs = query.toString()
  const res = await fetch(`${BASE_URL}/applications${qs ? `?${qs}` : ''}`)
  return handleResponse(res)
}

export async function createApplication(data) {
  const res = await fetch(`${BASE_URL}/applications`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  })
  return handleResponse(res)
}

export async function updateApplication(id, data) {
  const res = await fetch(`${BASE_URL}/applications/${id}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  })
  return handleResponse(res)
}

export async function deleteApplication(id) {
  const res = await fetch(`${BASE_URL}/applications/${id}`, {
    method: 'DELETE',
  })
  return handleResponse(res)
}

export async function getApplicationStats() {
  const res = await fetch(`${BASE_URL}/applications/stats/summary`)
  return handleResponse(res)
}

export async function getSettings() {
  const res = await fetch(`${BASE_URL}/settings`)
  return handleResponse(res)
}

export async function updateSettings(settings) {
  const res = await fetch(`${BASE_URL}/settings`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(settings),
  })
  return handleResponse(res)
}

export async function testConnections() {
  const res = await fetch(`${BASE_URL}/settings/test-connections`, {
    method: 'POST',
  })
  return handleResponse(res)
}
