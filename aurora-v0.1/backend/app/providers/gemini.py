"""Real REST adapter. Test doubles exist only in backend/tests."""
from asyncio import sleep, timeout
import httpx
from .base import ProviderError

class GeminiProvider:
    def __init__(self, client: httpx.AsyncClient, api_key: str):
        self.client = client
        self.api_key = api_key

    async def generate(self, model: str, messages: list[dict], personalization: str = "") -> str:
        if not self.api_key:
            raise ProviderError(503, "Configure GEMINI_API_KEY em backend/.env e reinicie o servidor.")
        contents = [{"role": "model" if m["role"] == "assistant" else "user", "parts": [{"text": m["content"]}]} for m in messages]
        payload = {"contents": contents,
                   "systemInstruction": {"parts": [{"text": "Você é Aurora, uma assistente pessoal. Responda em português do Brasil, salvo pedido diferente. Seja clara e honesta. Você não possui ferramentas nem acesso direto a arquivos, computador ou pesquisa web. Você pode analisar o texto de documentos que a aplicação inclua explicitamente no contexto. Não afirme ter executado ações externas." + personalization}]},
                   "generationConfig": {"maxOutputTokens": 4096}}
        attempts = 0
        try:
            # Bound all attempts below the browser's 75-second timeout.
            # Only explicit upstream 500/503 responses are retried, never
            # timeouts, network failures, quota errors or successful responses.
            async with timeout(65):
                for attempt in range(3):
                    attempts += 1
                    response = await self.client.post(
                        f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
                        headers={"x-goog-api-key": self.api_key},
                        json=payload,
                    )
                    if response.status_code not in (500, 503) or attempt == 2:
                        break
                    await sleep(0.75 * (2 ** attempt))
        except (httpx.TimeoutException, TimeoutError):
            raise ProviderError(504, "O Gemini demorou demais. Aguarde antes de tentar novamente; a chamada pode ter consumido cota.") from None
        except httpx.RequestError:
            raise ProviderError(502, "Não foi possível conectar ao Gemini. Verifique a conexão do servidor.") from None
        if response.status_code != 200:
            status = response.status_code
            message = ({400: "O Gemini recusou os parâmetros. Confira a chave e a compatibilidade do modelo.",
                        401: "A chave Gemini foi recusada. Confira backend/.env.",
                        403: "Acesso ao Gemini negado. Confira chave, projeto, região e permissões.",
                        404: "Modelo não encontrado. Atualize GEMINI_MODELS com um modelo disponível na sua conta.",
                        429: "Cota ou limite de requisições do Gemini atingido. Consulte o Google AI Studio e aguarde.",
                        500: f"O Gemini retornou uma falha interna (HTTP 500) após {attempts} tentativas. Aguarde um pouco antes de reenviar.",
                        503: f"O Gemini está temporariamente indisponível (HTTP 503) após {attempts} tentativas. Aguarde um pouco antes de reenviar."}
                       .get(status, f"O Gemini retornou um erro (HTTP {status}). Tente novamente mais tarde."))
            raise ProviderError(429 if status == 429 else 502, message, upstream_status=status)
        try:
            data = response.json()
            candidates = data.get("candidates") or []
            if data.get("promptFeedback", {}).get("blockReason"):
                raise ProviderError(422, "O Gemini bloqueou esta solicitação. Reformule a mensagem.")
            candidate = candidates[0] if candidates else {}
            if candidate.get("finishReason") not in (None, "STOP", "MAX_TOKENS"):
                raise ProviderError(422, "O Gemini interrompeu a resposta. Reformule a mensagem.")
            parts = candidate.get("content", {}).get("parts", [])
            answer = "\n".join(p["text"] for p in parts if isinstance(p.get("text"), str) and not p.get("thought")).strip()
        except (ValueError, TypeError, KeyError, AttributeError):
            raise ProviderError(502, "O Gemini retornou uma resposta inválida.") from None
        if not answer:
            raise ProviderError(502, "O Gemini não retornou texto. Tente uma solicitação mais curta.")
        if candidate.get("finishReason") == "MAX_TOKENS":
            answer += "\n\n[Resposta interrompida pelo limite de saída. Peça para continuar.]"
        return answer
