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
    root.geometry('640x390')
    kind = tk.StringVar(value=old.get('provider', 'llamacpp'))
    binary = tk.StringVar(value=old.get('binary', ''))
    model = tk.StringVar(value=old.get('model_file', ''))
    ollama = tk.StringVar(value=old.get('model', 'llama3.2:1b'))
    result = []
    tk.Label(root, text='Escolha como executar a IA local', font=('', 15)).pack(pady=12)
    tk.Radiobutton(root, text='Motor integrado llama.cpp (a Aurora inicia e encerra)', variable=kind, value='llamacpp').pack(anchor='w', padx=18)
    tk.Radiobutton(root, text='Usar Ollama já instalado neste computador', variable=kind, value='ollama').pack(anchor='w', padx=18)
    for label, variable, types in [('Executável llama-server', binary, [('Executável', '*.exe'), ('Todos', '*')]),
                                    ('Modelo local GGUF', model, [('Modelo GGUF', '*.gguf')])]:
        row = tk.Frame(root)
        row.pack(fill='x', padx=18, pady=7)
        tk.Label(row, text=label, width=23, anchor='w').pack(side='left')
        tk.Entry(row, textvariable=variable).pack(side='left', expand=True, fill='x')
        tk.Button(row, text='Escolher', command=lambda v=variable,t=types: v.set(filedialog.askopenfilename(filetypes=t) or v.get())).pack(side='right')
    tk.Label(root, text='Modelo instalado no Ollama (apenas para a segunda opção)').pack(anchor='w', padx=18)
    tk.Entry(root, textvariable=ollama).pack(fill='x', padx=18)
    tk.Label(root, text='Perfil leve: contexto de 4096 tokens, até 768 tokens por resposta.\nModelos e motores são obtidos separadamente. Veja DESKTOP.md.', wraplength=590).pack(pady=12)
    def save():
        cfg = {'provider':kind.get(), 'binary':binary.get(), 'model_file':model.get(), 'model':ollama.get().strip()}
        try:
            validate_config(cfg)
        except ValueError as exc:
            messagebox.showerror('Confira a configuração', str(exc))
            return
        temporary = path.with_suffix('.tmp')
        temporary.write_text(json.dumps(cfg, ensure_ascii=False, indent=2), 'utf-8')
        temporary.replace(path)
        result.append(cfg)
        root.destroy()
    tk.Button(root, text='Salvar configuração', command=save).pack(pady=5)
    root.mainloop()
    return result[0] if result else None


def validate_config(cfg):
    import re
    if cfg.get('provider') not in {'ollama', 'llamacpp'}:
        raise ValueError('Selecione um motor local.')
    if cfg['provider'] == 'llamacpp':
        binary, model = Path(cfg.get('binary', '')), Path(cfg.get('model_file', ''))
        if not binary.is_file() or not model.is_file() or model.suffix.lower() != '.gguf':
            raise ValueError('Selecione o executável llama-server e um modelo .gguf existente.')
    elif not re.fullmatch(r'[a-zA-Z0-9._:/-]{1,100}', cfg.get('model', '')):
        raise ValueError('Informe o identificador do modelo instalado no Ollama.')


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
    from app.config import Settings
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
        settings = Settings(secrets.token_urlsafe(48), models=(model,), database=directory/'aurora.sqlite3',
                            provider=cfg['provider'], local_url=url)
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
        print(f'Aurora não iniciou: {exc}', file=sys.stderr)
        sys.exit(1)
