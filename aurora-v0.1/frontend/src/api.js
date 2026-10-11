export async function api(path, token, options = {}) {
  let response;
  try {
    response = await fetch(`/api${path}`, {
      ...options,
      headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}`, ...options.headers },
      signal: options.signal ?? AbortSignal.timeout(75000),
    });
  } catch (error) {
    throw new Error(error.name === 'TimeoutError' ? 'O servidor demorou demais. Tente novamente: envios concluídos não serão duplicados.' : 'Sem conexão com o servidor. Verifique o terminal e tente novamente.');
  }
  if (response.status === 204) return null;
  let data;
  try { data = await response.json(); } catch { throw new Error('Resposta inválida do servidor. Confira se o FastAPI está iniciado.'); }
  if (!response.ok) {
    const error = new Error(typeof data.detail === 'string' ? data.detail : 'Não foi possível concluir a operação.');
    error.status = response.status;
    throw error;
  }
  return data;
}
