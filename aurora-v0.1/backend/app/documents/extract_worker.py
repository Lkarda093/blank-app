"""Isolated PDF parser: no filesystem output or network use."""
import io
import json
import sys

MAX_BYTES=3*1024*1024
MAX_PAGES=30
MAX_CHARS=24000

class DocumentError(ValueError):
    pass

def main():
    try:
        import resource
        resource.setrlimit(resource.RLIMIT_AS,(256*1024*1024,256*1024*1024))
        resource.setrlimit(resource.RLIMIT_CPU,(8,8))
    except ImportError:
        pass
    try:
        from pypdf import PdfReader
        raw=sys.stdin.buffer.read(MAX_BYTES+1)
        if len(raw)>MAX_BYTES or not raw.startswith(b'%PDF-'):
            raise DocumentError('Arquivo PDF inválido ou acima de 3 MB.')
        reader=PdfReader(io.BytesIO(raw),strict=True)
        if reader.is_encrypted:
            raise DocumentError('PDF protegido por senha não é aceito nesta versão.')
        if not 1<=len(reader.pages)<=MAX_PAGES:
            raise DocumentError('O PDF deve ter entre 1 e 30 páginas.')
        pages=[];total=0
        for page in reader.pages:
            text=(page.extract_text() or '').strip()
            total+=len(text)
            if total>MAX_CHARS:
                raise DocumentError('O documento excede 24 mil caracteres de texto. Divida-o em arquivos menores.')
            pages.append(text)
        if not any(pages):
            raise DocumentError('Não foi encontrado texto legível. PDFs escaneados precisam de OCR, ainda indisponível.')
        print(json.dumps({'pages':pages},ensure_ascii=False))
    except DocumentError as error:
        print(json.dumps({'error':str(error)},ensure_ascii=False));sys.exit(2)
    except Exception:
        print(json.dumps({'error':'Não foi possível ler este PDF. Verifique o arquivo e tente um PDF com texto selecionável.'},ensure_ascii=False));sys.exit(2)

if __name__=='__main__':
    main()
