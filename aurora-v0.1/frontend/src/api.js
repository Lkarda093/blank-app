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

export async function uploadDocument(file) {
  if (!file || !file.size) throw new Error('Este arquivo está vazio. Escolha um arquivo com conteúdo.');
  if (file.size > 3 * 1024 * 1024) throw new Error('Este arquivo supera 3 MB. Envie uma versão menor.');
  if (!/\.(pdf|txt)$/i.test(file.name)) throw new Error('Envie somente PDF ou TXT UTF-8.');
  return api(`/documents?name=${encodeURIComponent(file.name)}`, null, {method:'POST',body:file,headers:{'Content-Type':'application/octet-stream'}});
}

export async function streamMessage(path,payload,onEvent){
 const response=await request(path,null,{method:'POST',body:JSON.stringify(payload)});
 const reader=response.body?.getReader();
 if(!reader)throw new Error('O navegador não recebeu o fluxo de resposta. Confira o histórico antes de reenviar.');
 const decoder=new TextDecoder();let buffer='';
 try{
  while(true){
   const {value,done}=await reader.read();buffer+=decoder.decode(value,{stream:!done});
   if(buffer.length>2000000)throw new Error('Resposta do servidor fora dos limites.');
   const lines=buffer.split('\n');buffer=lines.pop();
   if(done&&buffer){lines.push(buffer);buffer='';}
   for(const line of lines){
    if(!line.trim())continue;
    let event;try{event=JSON.parse(line);}catch{throw new Error('O fluxo da resposta ficou inválido. Confira o histórico antes de reenviar.');}
    if(event.type==='error'){const error=new Error(event.detail);error.status=event.status;throw error;}
    if(event.type==='done')return event.result;
    onEvent?.(event);
   }
   if(done)break;
  }
  throw new Error('A conexão terminou antes da confirmação. Confira o histórico antes de reenviar; o texto recebido pode estar incompleto.');
 }catch(error){
  if(['TimeoutError','AbortError'].includes(error.name))throw new Error('A resposta demorou demais. Confira o histórico antes de reenviar.');
  if(error instanceof TypeError)throw new Error('A conexão foi interrompida. Confira o histórico antes de reenviar.');
  throw error;
 }finally{await reader.cancel().catch(()=>{});}
}
