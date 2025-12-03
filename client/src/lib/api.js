// client/src/lib/api.js

export async function get(endpoint, params = {}) {
  const url = new URL(`/api${endpoint}`, window.location.origin);
  Object.keys(params).forEach(key => url.searchParams.append(key, params[key]));

  const res = await fetch(url);
  return handleResponse(res);
}

export async function post(endpoint, body) {
  const res = await fetch(`/api${endpoint}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body)
  });
  return handleResponse(res);
}

async function handleResponse(res) {
  if (!res.ok) {
    const text = await res.text();
    let message = text;
    try {
      const json = JSON.parse(text);
      message = json.message || json.error || text;
    } catch (e) {
      // ignore JSON parse error
    }
    throw new Error(message);
  }
  return res.json();
}