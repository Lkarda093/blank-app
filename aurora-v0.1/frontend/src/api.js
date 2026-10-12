async function request(path, token, options = {}) {
  let response;
  try {
    response = await fetch(`/api${path}`, {
      ...options,
      credentials: 'same-origin',
      headers: { 'Content-Type': 'application/json', 'X-Aurora-Request': '1',
        ...(token ? { Authorization: `Bearer ${token}` } : {}), ...options.headers },
      signal: options.signal ?? AbortSignal.timeout(75000),
    });
  } catch (error) {
    throw new Error(error.name === 'TimeoutError' ? 'O servidor demorou demais. Confira o resultado antes de repetir a operação.' : 'Sem conexão com o servidor. Verifique o terminal e tente novamente.');
  }
  if (!response.ok) {
    let data;
    try { data = await response.json(); } catch { throw new Error('Resposta inválida do servidor. Confira se o FastAPI está iniciado.'); }
    const error = new Error(typeof data.detail === 'string' ? data.detail : 'Não foi possível concluir a operação.');
    error.status = response.status;
    throw error;
  }
  return response;
}
export async function api(path, token = null, options = {}) {
  const response = await request(path, token, options);
  if (response.status === 204) return null;
  try { return await response.json(); } catch { throw new Error('Resposta inválida do servidor. Confira se o FastAPI está iniciado.'); }
}
export function saveFile(blob, filename) {
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url; link.download = filename;
  document.body.appendChild(link); link.click(); link.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
export async function download(path, filename) {
  const response = await request(path, null);
  saveFile(await response.blob(), filename);
}
