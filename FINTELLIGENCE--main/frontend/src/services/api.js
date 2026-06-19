export function apiFactory(token) {
  return async (path, options = {}) => {
    const headers = new Headers(options.headers || {});
    if (!(options.body instanceof FormData)) headers.set('Content-Type', 'application/json');
    if (token) headers.set('Authorization', `Bearer ${token}`);

    const response = await fetch(`/api${path}`, { ...options, headers });
    const contentType = response.headers.get('content-type') || '';
    const data = contentType.includes('application/json') ? await response.json() : await response.blob();

    if (!response.ok) {
      const message = data?.error || data?.msg || data?.message || `Request failed: ${response.status}`;
      throw new Error(message);
    }
    return data;
  };
}
