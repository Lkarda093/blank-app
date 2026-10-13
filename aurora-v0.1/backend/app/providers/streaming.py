"""Gemini SSE parsing. No automatic retries after a stream has started."""
import json
from asyncio import sleep, timeout
import httpx
from .base import ProviderError

SYSTEM='Você é Aurora, uma assistente pessoal. Responda em português do Brasil, salvo pedido diferente. Seja clara e honesta. Você não possui ferramentas nem acesso direto a arquivos, computador ou pesquisa web. Você pode analisar o texto de documentos que a aplicação inclua explicitamente no contexto. Não afirme ter executado ações externas.'

def payload(messages,personalization):
    limit=1536 if 'Detalhe solicitado nesta conversa (prevalece sobre preferências gerais): conciso' in personalization else 4096
    return {'contents':[{'role':'model' if m['role']=='assistant' else 'user','parts':[{'text':m['content']}]} for m in messages],
            'systemInstruction':{'parts':[{'text':SYSTEM+personalization}]},'generationConfig':{'maxOutputTokens':limit}}

def upstream_error(status,attempts):
    messages={400:'O Gemini recusou os parâmetros. Confira a chave e a compatibilidade do modelo.',401:'A chave Gemini foi recusada. Confira backend/.env.',403:'Acesso ao Gemini negado. Confira chave, projeto, região e permissões.',404:'Modelo não encontrado. Atualize GEMINI_MODELS com um modelo disponível na sua conta.',429:'Cota ou limite de requisições do Gemini atingido. Consulte o Google AI Studio e aguarde.',500:f'O Gemini retornou uma falha interna (HTTP 500) após {attempts} tentativas. Aguarde um pouco antes de reenviar.',503:f'O Gemini está temporariamente indisponível (HTTP 503) após {attempts} tentativas. Aguarde um pouco antes de reenviar.'}
    return ProviderError(429 if status==429 else 502,messages.get(status,f'O Gemini retornou um erro (HTTP {status}). Tente novamente mais tarde.'),upstream_status=status)

async def gemini_stream(provider,model,messages,personalization):
    if not provider.api_key:raise ProviderError(503,'Configure GEMINI_API_KEY em backend/.env e reinicie o servidor.')
    body=payload(messages,personalization)
    try:
        async with timeout(65):
            for attempt in range(3):
                retry=False
                async with provider.client.stream('POST',f'https://generativelanguage.googleapis.com/v1beta/models/{model}:streamGenerateContent?alt=sse',headers={'x-goog-api-key':provider.api_key},json=body) as response:
                    if response.status_code!=200:
                        if response.status_code in (500,503) and attempt<2:retry=True
                        else:raise upstream_error(response.status_code,attempt+1)
                    else:
                        size=0;finished=False;reason=None;event=[]
                        async def frames():
                            async for line in response.aiter_lines():
                                if len(line)>512000:raise ProviderError(502,'O Gemini retornou um bloco inválido.')
                                if not line:
                                    if event:
                                        value='\n'.join(event);event.clear();yield value
                                elif line.startswith('data:'):
                                    event.append(line[5:].lstrip())
                                    if sum(map(len,event))>512000:raise ProviderError(502,'O Gemini retornou um bloco inválido.')
                            if event:yield '\n'.join(event)
                        async for raw in frames():
                            if raw=='[DONE]':continue
                            try:
                                data=json.loads(raw)
                                if data.get('error'):raise ProviderError(502,'O Gemini interrompeu o envio da resposta.')
                                if data.get('promptFeedback',{}).get('blockReason'):raise ProviderError(422,'O Gemini bloqueou esta solicitação. Reformule a mensagem.')
                                candidates=data.get('candidates') or []
                                if not candidates:continue
                                candidate=candidates[0]
                                reason=candidate.get('finishReason',reason)
                                if reason not in (None,'STOP','MAX_TOKENS'):raise ProviderError(422,'O Gemini interrompeu a resposta. Reformule a mensagem.')
                                text=''.join(p['text'] for p in candidate.get('content',{}).get('parts',[]) if isinstance(p.get('text'),str) and not p.get('thought'))
                            except (ValueError,TypeError,KeyError,AttributeError):
                                raise ProviderError(502,'O Gemini retornou uma resposta inválida.') from None
                            if text:
                                size+=len(text)
                                if size>100000:raise ProviderError(502,'A resposta excedeu o limite de texto.')
                                yield text
                            finished=reason in ('STOP','MAX_TOKENS')
                        if not size:raise ProviderError(502,'O Gemini não retornou texto. Tente uma solicitação mais curta.')
                        if not finished:raise ProviderError(502,'A resposta foi interrompida antes de concluir. O trecho recebido não foi salvo; confira antes de reenviar.')
                        if reason=='MAX_TOKENS':yield '\n\n[Resposta interrompida pelo limite de saída. Peça para continuar.]'
                        return
                if retry:await sleep(0.75*(2**attempt))
    except (httpx.TimeoutException,TimeoutError):
        raise ProviderError(504,'O Gemini demorou demais. Aguarde antes de tentar novamente; a chamada pode ter consumido cota.') from None
    except httpx.RequestError:
        raise ProviderError(502,'A conexão com o Gemini foi interrompida. O trecho recebido não foi salvo; confira antes de reenviar.') from None
