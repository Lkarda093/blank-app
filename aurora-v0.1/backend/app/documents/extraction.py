import json
import subprocess
import sys
from pathlib import Path

MAX_FILE_BYTES=3*1024*1024
MAX_PAGES=30
MAX_CHARS=24000
MAX_STORAGE_BYTES=10*1024*1024
MAX_DOCUMENTS=20

class ExtractionError(ValueError):
    pass

def extract(content:bytes,kind:str,deadline:float=12)->list[str]:
    if not content or len(content)>MAX_FILE_BYTES:
        raise ExtractionError('O arquivo deve ter conteúdo e no máximo 3 MB.')
    if kind=='txt':
        try:
            text=content.decode('utf-8-sig').strip()
        except UnicodeError:
            raise ExtractionError('Salve o TXT com codificação UTF-8 e envie novamente.') from None
        if not text or any(ord(c)<32 and c not in '\t\r\n' for c in text):
            raise ExtractionError('O TXT está vazio ou contém dados binários.')
        if len(text)>MAX_CHARS:
            raise ExtractionError('O documento excede 24 mil caracteres de texto. Divida-o em arquivos menores.')
        return [text]
    if kind!='pdf' or not content.startswith(b'%PDF-'):
        raise ExtractionError('Envie um PDF válido ou um arquivo TXT UTF-8.')
    try:
        result=subprocess.run([sys.executable,str(Path(__file__).with_name('extract_worker.py'))],input=content,
                              stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,timeout=deadline,check=False)
        if len(result.stdout)>MAX_CHARS*6+8192:
            raise ExtractionError('O PDF excedeu os limites de extração.')
        data=json.loads(result.stdout)
        if result.returncode or 'error' in data:
            raise ExtractionError(data.get('error','O PDF excedeu os limites de processamento.'))
        pages=data['pages']
        if not isinstance(pages,list) or not 1<=len(pages)<=MAX_PAGES or any(not isinstance(p,str) for p in pages) or sum(map(len,pages))>MAX_CHARS:
            raise ExtractionError('O PDF excedeu os limites de extração.')
        return pages
    except (subprocess.TimeoutExpired,ValueError,KeyError,TypeError) as error:
        if isinstance(error,ExtractionError):
            raise
        raise ExtractionError('O PDF não pôde ser extraído dentro dos limites de tempo e memória. Tente um arquivo menor.') from None
