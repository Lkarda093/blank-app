"""Aurora desktop: native webview + private local API + optional managed llama.cpp.

The desktop shell exposes no Python/JavaScript bridge or arbitrary command executor.
"""
import argparse
import json
import os
from pathlib import Path
import secrets
import socket
import subprocess
import sys
import threading
import time

ROOT = Path(getattr(sys, '_MEIPASS', Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(ROOT / 'backend'))
from app.cloud_policy import CLOUD_NOTICE, CLOUD_NOTICE_VERSION
from app.credentials import CredentialError, WindowsCredentialStore


def data_directory():
    base = Path(os.environ.get('LOCALAPPDATA', Path.home() / '.local' / 'share'))
    directory = base / 'Aurora'
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def configure(path):
    import tkinter as tk
    from tkinter import filedialog, messagebox
    old = json.loads(path.read_text('utf-8')) if path.exists() else {}
    root = tk.Tk()
    root.title('Preparar Aurora Desktop')
    root.geometry('710x630')
    kind = tk.StringVar(value=old.get('provider', 'gemini'))
    binary = tk.StringVar(value=old.get('binary', ''))
    model = tk.StringVar(value=old.get('model_file', ''))
    ollama = tk.StringVar(value=old.get('model', 'llama3.2:1b'))
    gemini_model = tk.StringVar(value=old.get('gemini_model', ''))
    api_key = tk.StringVar()
    accepted = tk.BooleanVar(value=False)
    result = []
    tk.Label(root, text='Escolha onde a Aurora processa suas mensagens', font=('', 15)).pack(pady=12)
    tk.Radiobutton(root, text='Nuvem / Gemini — padrão, sem carregar motor local', variable=kind, value='gemini').pack(anchor='w', padx=18)
    tk.Radiobutton(root, text='Motor integrado llama.cpp (a Aurora inicia e encerra)', variable=kind, value='llamacpp').pack(anchor='w', padx=18)
    tk.Radiobutton(root, text='Usar Ollama já instalado neste computador', variable=kind, value='ollama').pack(anchor='w', padx=18)
    details = tk.Frame(root)
    details.pack(fill='both', expand=True, padx=18, pady=8)
    cloud = tk.LabelFrame(details, text='Nuvem / Gemini', padx=10, pady=8)
    tk.Label(cloud, text='Identificador de um modelo disponível na sua conta do AI Studio').pack(anchor='w')
    model_entry = tk.Entry(cloud, textvariable=gemini_model)
    model_entry.pack(fill='x')
    tk.Label(cloud, text='Chave Gemini (deixe vazia para manter a chave já cadastrada)').pack(anchor='w')
    key_entry = tk.Entry(cloud, textvariable=api_key, show='•')
    key_entry.pack(fill='x')
    tk.Label(cloud, text='A chave fica no Gerenciador de Credenciais deste usuário do Windows. Nunca é mostrada aqui.', wraplength=640, justify='left').pack(anchor='w', pady=4)
    tk.Label(cloud, text=CLOUD_NOTICE, wraplength=640, justify='left').pack(anchor='w')
    consent = tk.Checkbutton(cloud, text='Li o aviso e autorizo ativar a nuvem com este modelo.', variable=accepted)
    consent.pack(anchor='w', pady=4)
    def remove_key():
        if not messagebox.askyesno('Remover chave Gemini', 'Remover somente a chave Aurora/Gemini/APIKey do cofre do Windows? O histórico será preservado.'):
            return
        try:
            WindowsCredentialStore().delete()
            api_key.set('')
            messagebox.showinfo('Chave removida', 'Cadastre uma chave antes de usar Gemini novamente.')
        except CredentialError as exc:
            messagebox.showerror('Credenciais', str(exc))
    remove_button = tk.Button(cloud, text='Remover chave cadastrada', command=remove_key)
    remove_button.pack(anchor='w')
    llama = tk.LabelFrame(details, text='llama.cpp — execução local', padx=10, pady=8)
    for label, variable, types in [('Executável llama-server', binary, [('Executável', '*.exe'), ('Todos', '*')]),
                                    ('Modelo local GGUF', model, [('Modelo GGUF', '*.gguf')])]:
        row = tk.Frame(llama)
        row.pack(fill='x', pady=7)
        tk.Label(row, text=label, width=23, anchor='w').pack(side='left')
        entry = tk.Entry(row, textvariable=variable)
        entry.pack(side='left', expand=True, fill='x')
        button = tk.Button(row, text='Escolher', command=lambda v=variable,t=types: v.set(filedialog.askopenfilename(filetypes=t) or v.get()))
        button.pack(side='right')
    ollama_frame = tk.LabelFrame(details, text='Ollama — execução local', padx=10, pady=8)
    tk.Label(ollama_frame, text='Modelo já instalado no Ollama').pack(anchor='w')
    tk.Entry(ollama_frame, textvariable=ollama).pack(fill='x')
    tk.Label(root, text='O modo local nunca troca para nuvem sozinho.\nModelos e motores locais são obtidos separadamente. Veja DESKTOP.md.', wraplength=640).pack(pady=8)
    def save():
        cfg = {'provider':kind.get(), 'binary':binary.get(), 'model_file':model.get(), 'model':ollama.get().strip(),
               'gemini_model':gemini_model.get().strip(),
               'cloud_notice_version':CLOUD_NOTICE_VERSION if accepted.get() else 0}
        try:
            cfg = save_config(path, cfg, api_key.get().strip())
        except (ValueError, CredentialError) as exc:
            messagebox.showerror('Confira a configuração', str(exc))
            return
        except OSError:
            messagebox.showerror('Configuração', 'Não foi possível salvar. A configuração anterior foi preservada; confira a chave no cofre antes de tentar novamente.')
            return
        api_key.set('')
        result.append(cfg)
        root.destroy()
    tk.Button(root, text='Salvar configuração', command=save).pack(pady=5)
    def update_fields(*_):
        for frame in (cloud, llama, ollama_frame):
            frame.pack_forget()
        {'gemini':cloud, 'llamacpp':llama, 'ollama':ollama_frame}[kind.get()].pack(fill='x')
    kind.trace_add('write', update_fields)
    update_fields()
    root.mainloop()
    api_key.set('')
    return result[0] if result else None


def validate_config(cfg):
    import re
    if not isinstance(cfg, dict) or cfg.get('provider') not in {'gemini', 'ollama', 'llamacpp'}:
        raise ValueError('Selecione Nuvem/Gemini, llama.cpp ou Ollama.')
    if any(name in cfg for name in ('api_key', 'GEMINI_API_KEY', 'key', 'token')):
        raise ValueError('Credenciais não podem ficar em desktop.json. Remova esse campo e cadastre a chave no cofre do Windows.')
    if cfg['provider'] == 'gemini':
        if not isinstance(cfg.get('gemini_model'), str) or not re.fullmatch(r'[A-Za-z0-9._-]{1,100}', cfg['gemini_model']):
            raise ValueError('Informe o identificador do modelo Gemini disponível na sua conta.')
        if cfg.get('cloud_notice_version') != CLOUD_NOTICE_VERSION:
            raise ValueError('Leia e aceite o aviso de privacidade em Configurar-Aurora.cmd antes de ativar a nuvem.')
    if cfg['provider'] == 'llamacpp':
        binary, model = Path(cfg.get('binary', '')), Path(cfg.get('model_file', ''))
        if not binary.is_file() or not model.is_file() or model.suffix.lower() != '.gguf':
            raise ValueError('Selecione o executável llama-server e um modelo .gguf existente.')
    elif cfg['provider'] == 'ollama' and not re.fullmatch(r'[a-zA-Z0-9._:/-]{1,100}', cfg.get('model', '')):
        raise ValueError('Informe o identificador do modelo instalado no Ollama.')


def save_config(path, cfg, api_key='', store=None):
    """Persist only allowlisted non-secret fields, never a credential fallback."""
    validate_config(cfg)
    clean = {'provider': cfg['provider']}
    if cfg['provider'] == 'gemini':
        clean.update(gemini_model=cfg['gemini_model'], cloud_notice_version=CLOUD_NOTICE_VERSION)
        store = store if store is not None else WindowsCredentialStore()
        if api_key:
            store.write(api_key)
        elif not store.read():
            raise CredentialError('Cadastre sua chave Gemini no Gerenciador de Credenciais para ativar a nuvem.')
    elif cfg['provider'] == 'llamacpp':
        clean.update(binary=cfg['binary'], model_file=cfg['model_file'])
    else:
        clean['model'] = cfg['model']
    temporary = path.with_suffix('.tmp')
    try:
        temporary.write_text(json.dumps(clean, ensure_ascii=False, indent=2), 'utf-8')
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)
    return clean


def settings_for_config(cfg, directory, local_url='http://127.0.0.1:11434', store=None):
    from app.config import Settings
    validate_config(cfg)
    key = ''
    if cfg['provider'] == 'gemini':
        store = store if store is not None else WindowsCredentialStore()
        key = store.read()
        if not key:
            raise CredentialError('Chave Gemini ausente. Abra Configurar-Aurora.cmd para cadastrá-la no cofre do Windows.')
        model = cfg['gemini_model']
    else:
        model = 'aurora-local' if cfg['provider'] == 'llamacpp' else cfg['model']
    return Settings(secrets.token_urlsafe(48), api_key=key, models=(model,),
                    database=directory/'aurora.sqlite3', provider=cfg['provider'], local_url=local_url)


def engine_command(cfg, port):
    return [str(Path(cfg['binary']).resolve()), '-m', str(Path(cfg['model_file']).resolve()),
            '--host', '127.0.0.1', '--port', str(port), '--alias', 'aurora-local',
            '-c', '4096', '-t', '2', '-ngl', '0', '--parallel', '1']


def free_port():
    with socket.socket() as sock:
        sock.bind(('127.0.0.1', 0))
        return sock.getsockname()[1]


def wait_for_engine(process, url, seconds=120):
    import httpx
    deadline = time.monotonic()+seconds
    with httpx.Client(timeout=1, trust_env=False) as client:
        while time.monotonic() < deadline:
            if process.poll() is not None:
                raise RuntimeError('O motor local encerrou durante a carga. Confira a compatibilidade do executável e do modelo.')
            try:
                if client.get(url+'/health').status_code == 200:
                    return
            except httpx.RequestError:
                pass
            time.sleep(0.2)
    raise RuntimeError('O modelo não carregou em dois minutos. Tente um GGUF menor.')


def desktop_app(settings, dist, ticket, port):
    from fastapi import HTTPException, Request
    from fastapi.responses import RedirectResponse
    from fastapi.staticfiles import StaticFiles
    from starlette.middleware.trustedhost import TrustedHostMiddleware
    from app.main import create_app
    from app.auth.dependencies import COOKIE, session_digest
    from app.database import connect
    app = create_app(settings)
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=['127.0.0.1'])
    pending = {'ticket':ticket}
    @app.get('/desktop/{value}')
    def bootstrap(value: str, request: Request):
        if not pending['ticket'] or not secrets.compare_digest(value, pending['ticket']):
            raise HTTPException(404)
        # Reject cross-origin navigation before consuming the one-use capability.
        if request.headers.get('sec-fetch-site') not in (None, 'none', 'same-origin'):
            raise HTTPException(403)
        pending['ticket'] = None
        session = secrets.token_urlsafe(32)
        with connect(settings.database) as db:
            db.execute('INSERT INTO sessions VALUES (?,?)', (session_digest(session, settings.owner_token), int(time.time())+43200))
        response = RedirectResponse('/', status_code=303)
        response.set_cookie(COOKIE, session, httponly=True, samesite='strict', path='/api')
        return response
    app.mount('/', StaticFiles(directory=str(dist), html=True), name='desktop-ui')
    return app


def run(configure_only=False):
    import uvicorn
    directory = data_directory()
    # OS lock prevents simultaneous desktop processes sharing the database/engine.
    lock = open(directory/'desktop.lock', 'a+b')
    lock.seek(0)
    if os.name == 'nt':
        import msvcrt
        if lock.read(1) == b'':
            lock.write(b'0'); lock.flush()
        lock.seek(0)
        try:
            msvcrt.locking(lock.fileno(), msvcrt.LK_NBLCK, 1)
        except OSError:
            raise RuntimeError('A Aurora já está aberta. Feche-a antes de iniciar ou configurar.') from None
    else:
        import fcntl
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            raise RuntimeError('A Aurora já está aberta.') from None
    process = server = thread = None
    try:
        config_path = directory/'desktop.json'
        cfg = configure(config_path) if configure_only or not config_path.exists() else json.loads(config_path.read_text('utf-8'))
        if not cfg or configure_only:
            return
        validate_config(cfg)
        dist = ROOT/'frontend'/'dist'
        if not (dist/'index.html').is_file():
            raise RuntimeError('Interface não compilada. Execute Instalar-Aurora.cmd primeiro.')
        import webview
        webview.settings['ALLOW_DOWNLOADS'] = True
        url, model = 'http://127.0.0.1:11434', cfg.get('model', 'llama3.2:1b')
        if cfg['provider'] == 'llamacpp':
            engine_port = free_port()
            url, model = f'http://127.0.0.1:{engine_port}', 'aurora-local'
            process = subprocess.Popen(engine_command(cfg, engine_port), stdin=subprocess.DEVNULL,
                                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                                       creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
            print('Carregando o modelo local. Aguarde a janela da Aurora...', flush=True)
            wait_for_engine(process, url)
        settings = settings_for_config(cfg, directory, url)
        ticket = secrets.token_urlsafe(48)
        # Bind first to avoid another process taking the API port before Uvicorn.
        sock = socket.socket()
        sock.bind(('127.0.0.1', 0))
        port = sock.getsockname()[1]
        app = desktop_app(settings, dist, ticket, port)
        server = uvicorn.Server(uvicorn.Config(app, access_log=False, log_level='error',
                                               proxy_headers=False, timeout_graceful_shutdown=2))
        thread = threading.Thread(target=server.run, kwargs={'sockets':[sock]}, daemon=True)
        thread.start()
        deadline = time.monotonic()+15
        while not server.started:
            if not thread.is_alive() or time.monotonic() > deadline:
                raise RuntimeError('Não foi possível iniciar a Aurora local.')
            time.sleep(0.05)
        webview.create_window('Aurora Desktop', f'http://127.0.0.1:{port}/desktop/{ticket}',
                              width=1100, height=760, min_size=(760, 580))
        webview.start(gui='edgechromium' if os.name == 'nt' else None, private_mode=False,
                      storage_path=str(directory/'webview'))
    finally:
        if server:
            server.should_exit = True
        if thread:
            thread.join(timeout=5)
        if process and process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill(); process.wait()
        lock.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--configure', action='store_true')
    args = parser.parse_args()
    try:
        run(args.configure)
    except Exception as exc:
        # Config errors are local paths/status, never model prompts or API secrets.
        message = str(exc) if isinstance(exc, (CredentialError, ValueError, RuntimeError)) else 'Falha ao iniciar. Confira a instalação e a configuração.'
        print(f'Aurora não iniciou: {message}', file=sys.stderr)
        sys.exit(1)
