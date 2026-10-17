"""Local inference adapters. No tool execution, cloud routing or automatic downloads."""
import json
import httpx
from .base import ProviderError
from .streaming import SYSTEM


class LocalProvider:
    def __init__(self, client, kind, url):
        self.client, self.kind, self.url = client, kind, url.rstrip('/')

    async def generate(self, model, messages, personalization=""):
        return ''.join([part async for part in self.stream(model, messages, personalization)]).strip()

    async def stream(self, model, messages, personalization=""):
        # A modest context/output budget avoids using an entire GPU for long responses.
        if sum(len(m['content']) for m in messages)+len(personalization) > 6000:
            raise ProviderError(400, 'O modo local admite até 6.000 caracteres de contexto. Reduza anexos, memórias ou resumo.')
        chat = [{'role':'system','content':SYSTEM+personalization}] + messages
        body = {'model':model, 'messages':chat, 'stream':True}
        if self.kind == 'ollama':
            body.update(options={'num_ctx':4096, 'num_predict':768, 'num_thread':2}, keep_alive='2m')
            endpoint = '/api/chat'
        else:
            body.update(max_tokens=768, temperature=0.5)
            endpoint = '/v1/chat/completions'
        size = 0
        finished = False
        reason = None
        try:
            if self.kind == 'ollama':
                # Ollama also supports cloud models; reject those explicitly in local mode.
                response = await self.client.get(self.url+'/api/tags')
                if response.status_code != 200:
                    raise ProviderError(503, 'Não foi possível verificar os modelos locais do Ollama.')
                try:
                    installed = next((m for m in response.json()['models'] if m.get('name') in {model, model+':latest'}), None)
                except (ValueError, TypeError, KeyError, AttributeError):
                    raise ProviderError(502, 'Lista de modelos locais inválida.') from None
                if not installed:
                    raise ProviderError(404, 'Modelo não instalado no Ollama. Instale-o antes de conversar.')
                if installed.get('remote_host') or installed.get('remote_model') or 'cloud' in model.lower():
                    raise ProviderError(400, 'Modelos de nuvem do Ollama não são permitidos no modo local.')
            async with self.client.stream('POST', self.url+endpoint, json=body) as response:
                if response.status_code != 200:
                    detail = ('Modelo local não encontrado. Confira o modelo instalado e a configuração.'
                              if response.status_code == 404 else
                              'O motor local recusou a solicitação. Reduza o contexto e confira se o modelo está carregado.')
                    raise ProviderError(502, detail)
                async for line in response.aiter_lines():
                    if len(line) > 512000:
                        raise ProviderError(502, 'Bloco do motor local excedeu o limite.')
                    if not line.strip():
                        continue
                    if self.kind != 'ollama':
                        if not line.startswith('data:'):
                            continue
                        line = line[5:].strip()
                        if line == '[DONE]':
                            break
                    try:
                        data = json.loads(line)
                        if data.get('error'):
                            raise ProviderError(502, 'O motor local interrompeu a resposta.')
                        if self.kind == 'ollama':
                            content = data.get('message', {}).get('content', '')
                            finished = data.get('done') is True
                            reason = data.get('done_reason')
                        else:
                            choices = data.get('choices') or []
                            if not choices:
                                continue
                            content = choices[0].get('delta', {}).get('content') or ''
                            reason = choices[0].get('finish_reason')
                            finished = reason in ('stop', 'length')
                            if reason not in (None, 'stop', 'length'):
                                raise ProviderError(502, 'O modelo local pediu uma operação não suportada neste chat.')
                        if not isinstance(content, str):
                            raise ValueError()
                    except (ValueError, TypeError, AttributeError, KeyError):
                        raise ProviderError(502, 'Resposta inválida do motor local.') from None
                    size += len(content)
                    if size > 100000:
                        raise ProviderError(502, 'Resposta local excedeu o limite.')
                    if content:
                        yield content
                    if finished:
                        break
                if not finished or not size:
                    raise ProviderError(502, 'Resposta local incompleta; nenhum trecho foi salvo no histórico.')
                if reason == 'length':
                    yield '\n\n[Limite de resposta local atingido. Peça para continuar.]'
        except httpx.TimeoutException:
            raise ProviderError(504, 'O modelo local demorou demais. Experimente um modelo menor ou uma pergunta mais curta.') from None
        except httpx.RequestError:
            raise ProviderError(503, 'Motor local indisponível. Inicie o motor ou reabra a Aurora. Nenhuma mensagem foi enviada à nuvem.') from None
