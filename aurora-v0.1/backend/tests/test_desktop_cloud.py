"""Cloud desktop safety contracts. No real vault, key, model or Google call."""
import ctypes
import importlib.util
import json
from pathlib import Path
import sys
import types

import httpx
import pytest

from app import config, credentials
from app.cloud_policy import CLOUD_NOTICE_VERSION
from app.credentials import CredentialError

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('cloud_desktop_launcher', ROOT/'desktop'/'launcher.py')
desktop = importlib.util.module_from_spec(spec)
spec.loader.exec_module(desktop)
KEY = 'synthetic-key-not-valid-at-google'


def cloud_config():
    return {'provider':'gemini', 'gemini_model':'synthetic-model', 'cloud_notice_version':CLOUD_NOTICE_VERSION}


class Vault:
    def __init__(self, key=KEY):
        self.key = key
    def read(self):
        return self.key
    def write(self, value):
        self.key = value


class NativeVault:
    """Exercise the ctypes pointer/blob protocol without calling Windows APIs."""
    def __init__(self):
        self.value = None
        self.error = credentials.ERROR_NOT_FOUND
        self.freed = 0
        self.fail_write = False
    def CredWriteW(self, pointer, flags):
        entry = ctypes.cast(pointer, ctypes.POINTER(credentials.CREDENTIALW)).contents
        assert entry.Type == 1 and entry.Persist == 2
        assert entry.TargetName == credentials.TARGET and flags == 0
        if self.fail_write:
            return False
        self.value = ctypes.string_at(entry.CredentialBlob, entry.CredentialBlobSize)
        return True
    def CredReadW(self, target, kind, flags, output):
        assert target == credentials.TARGET and kind == 1 and flags == 0
        if self.value is None:
            return False
        self.blob = (ctypes.c_ubyte * len(self.value)).from_buffer_copy(self.value)
        self.entry = credentials.CREDENTIALW()
        self.entry.CredentialBlobSize = len(self.value)
        self.entry.CredentialBlob = ctypes.cast(self.blob, ctypes.POINTER(ctypes.c_ubyte))
        ctypes.cast(output, ctypes.POINTER(ctypes.POINTER(credentials.CREDENTIALW)))[0] = ctypes.pointer(self.entry)
        return True
    def CredDeleteW(self, target, kind, flags):
        assert target == credentials.TARGET and kind == 1 and flags == 0
        self.value = None
        return True
    def CredFree(self, pointer):
        self.freed += 1


def test_native_vault_roundtrip_and_missing_key():
    api = NativeVault()
    store = credentials.WindowsCredentialStore(api=api, last_error=lambda: api.error)
    assert store.read() is None
    store.write(KEY)
    assert api.value == KEY.encode('utf-16-le')
    assert store.read() == KEY and api.freed == 1
    store.delete()
    assert store.read() is None


def test_native_vault_failure_redacts_and_corrupt_blob_is_freed():
    api = NativeVault()
    store = credentials.WindowsCredentialStore(api=api, last_error=lambda: api.error)
    api.fail_write = True
    with pytest.raises(CredentialError) as error:
        store.write(KEY)
    assert KEY not in str(error.value)
    api.value = b'\xff'
    with pytest.raises(CredentialError):
        store.read()
    assert api.freed == 1
    api.value = None
    api.error = 5
    with pytest.raises(CredentialError):
        store.read()


def test_non_windows_has_no_plaintext_vault_fallback(monkeypatch):
    if sys.platform == 'win32':
        pytest.skip('Linux-only unavailable-vault assertion')
    with pytest.raises(CredentialError, match='requer Windows'):
        credentials.WindowsCredentialStore()


def test_settings_repr_never_exposes_credentials():
    settings = config.Settings('synthetic-owner-token', api_key=KEY)
    assert KEY not in repr(settings) and 'synthetic-owner-token' not in repr(settings)


def test_cloud_config_persists_no_credential_or_legacy_fields(tmp_path):
    path = tmp_path/'desktop.json'
    vault = Vault(None)
    cfg = {**cloud_config(), 'binary':'old.exe', 'model_file':'old.gguf', 'unused':KEY}
    saved = desktop.save_config(path, cfg, KEY, vault)
    assert vault.key == KEY
    assert json.loads(path.read_text()) == cloud_config() == saved
    assert KEY not in path.read_text() and not path.with_suffix('.tmp').exists()


@pytest.mark.parametrize('change', [{'cloud_notice_version':0}, {'gemini_model':'../secret'}, {'api_key':KEY}])
def test_invalid_cloud_config_never_writes_vault_or_disk(tmp_path, change):
    class Forbidden:
        def write(self, _):
            pytest.fail('Invalid configuration touched the credential vault')
    with pytest.raises(ValueError):
        desktop.save_config(tmp_path/'desktop.json', {**cloud_config(), **change}, KEY, Forbidden())
    assert list(tmp_path.iterdir()) == []


def test_missing_or_unavailable_vault_preserves_existing_configuration(tmp_path):
    path = tmp_path/'desktop.json'
    previous = '{"provider":"ollama","model":"tiny"}'
    path.write_text(previous)
    with pytest.raises(CredentialError):
        desktop.save_config(path, cloud_config(), store=Vault(None))
    assert path.read_text() == previous
    class Unavailable:
        def write(self, _):
            raise CredentialError('Cofre indisponível')
    with pytest.raises(CredentialError):
        desktop.save_config(path, cloud_config(), KEY, Unavailable())
    assert path.read_text() == previous
    assert not path.with_suffix('.tmp').exists()


@pytest.mark.parametrize('provider', ['ollama', 'llamacpp'])
def test_local_configuration_does_not_access_vault_or_cloud_env(tmp_path, monkeypatch, provider):
    def forbidden():
        pytest.fail('Local mode accessed the Windows credential vault')
    monkeypatch.setattr(desktop, 'WindowsCredentialStore', forbidden)
    monkeypatch.setenv('GEMINI_API_KEY', KEY)
    monkeypatch.setenv('GEMINI_FREE_FALLBACK_MODELS', 'cloud-model')
    cfg = {'provider':'ollama', 'model':'tiny'}
    if provider == 'llamacpp':
        binary = tmp_path/'engine.exe'; binary.touch()
        model = tmp_path/'tiny.gguf'; model.touch()
        cfg = {'provider':provider, 'binary':str(binary), 'model_file':str(model)}
    desktop.save_config(tmp_path/'desktop.json', cfg, api_key=KEY)
    settings = desktop.settings_for_config(cfg, tmp_path)
    assert settings.provider == provider and settings.api_key == ''
    assert settings.free_fallback_models == ()


def test_windows_server_uses_only_native_vault(tmp_path, monkeypatch):
    monkeypatch.setattr(config, 'ROOT', tmp_path)
    monkeypatch.setattr(config, 'is_windows', lambda: True)
    monkeypatch.setattr(credentials, 'WindowsCredentialStore', lambda: Vault(KEY))
    monkeypatch.setenv('GEMINI_API_KEY', 'ignored-environment-key')
    assert config.load_gemini_key() == KEY


def test_plaintext_key_is_rejected_before_env_loading(tmp_path, monkeypatch):
    monkeypatch.setattr(config, 'ROOT', tmp_path)
    monkeypatch.delenv('GEMINI_API_KEY', raising=False)
    (tmp_path/'.env').write_text('GEMINI_API_KEY='+KEY+'\n')
    with pytest.raises(ValueError) as error:
        config.Settings.load()
    assert KEY not in str(error.value)
    import os
    assert 'GEMINI_API_KEY' not in os.environ


def test_cloud_launcher_uses_vault_without_spawning_any_engine(tmp_path, monkeypatch):
    dist = tmp_path/'frontend'/'dist'; dist.mkdir(parents=True)
    (dist/'index.html').write_text('unchanged Cosmic UI')
    (tmp_path/'desktop.json').write_text(json.dumps(cloud_config()))
    monkeypatch.setattr(desktop, 'ROOT', tmp_path)
    monkeypatch.setattr(desktop, 'data_directory', lambda: tmp_path)
    monkeypatch.setattr(desktop, 'WindowsCredentialStore', lambda: Vault(KEY))
    def forbidden(*args, **kwargs):
        pytest.fail('Cloud mode tried to start or poll a local engine')
    monkeypatch.setattr(desktop.subprocess, 'Popen', forbidden)
    monkeypatch.setattr(desktop, 'wait_for_engine', forbidden)
    windows = []
    def start(**kwargs):
        with httpx.Client(follow_redirects=True, trust_env=False) as client:
            assert client.get(windows[0]).text == 'unchanged Cosmic UI'
            origin = str(client.get(windows[0].split('/desktop/')[0]).url).rstrip('/')
            response = client.get(origin+'/api/config')
            cfg = response.json()
            assert cfg['provider'] == 'Gemini' and cfg['configured'] and not cfg['local_mode']
            assert cfg['free_fallback_models'] == []
            assert KEY not in response.text
    monkeypatch.setitem(sys.modules, 'webview', types.SimpleNamespace(settings={}, create_window=lambda title,url,**kw: windows.append(url), start=start))
    desktop.run()
    assert len(windows) == 1


def test_missing_vault_key_never_creates_cloud_settings(tmp_path):
    with pytest.raises(CredentialError, match='Chave Gemini ausente'):
        desktop.settings_for_config(cloud_config(), tmp_path, store=Vault(None))
    assert list(tmp_path.iterdir()) == []


def test_legacy_setup_writes_no_api_key_or_secret_to_output(tmp_path, monkeypatch, capsys):
    spec = importlib.util.spec_from_file_location('web_setup', ROOT/'scripts'/'configure.py')
    setup = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(setup)
    (tmp_path/'backend').mkdir()
    monkeypatch.setattr(setup, 'root', tmp_path)
    monkeypatch.setattr(setup, 'is_windows', lambda: True)
    answers = iter(['ACEITO', 'synthetic-model'])
    monkeypatch.setattr('builtins.input', lambda _: next(answers))
    monkeypatch.setattr(setup, 'getpass', lambda _: KEY)
    vault = Vault(None)
    monkeypatch.setattr(credentials, 'WindowsCredentialStore', lambda: vault)
    setup.main()
    data = (tmp_path/'backend'/'.env').read_text()
    assert 'GEMINI_API_KEY' not in data and KEY not in data
    assert vault.key == KEY and KEY not in capsys.readouterr().out


def test_legacy_setup_cancellation_changes_nothing(tmp_path, monkeypatch):
    spec = importlib.util.spec_from_file_location('web_setup_cancel', ROOT/'scripts'/'configure.py')
    setup = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(setup)
    monkeypatch.setattr(setup, 'root', tmp_path)
    monkeypatch.setattr('builtins.input', lambda _: 'CANCELAR')
    with pytest.raises(SystemExit, match='cancelada'):
        setup.main()
    assert list(tmp_path.iterdir()) == []
