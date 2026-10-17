"""Gemini credential in the current Windows user's native credential vault.

No file, environment-variable or third-party keyring fallback. The native API
boundary is injectable so its protocol can be tested without touching a vault.
"""
import ctypes
from ctypes import wintypes
import os
import re

TARGET = "Aurora/Gemini/APIKey"
CRED_TYPE_GENERIC = 1
CRED_PERSIST_LOCAL_MACHINE = 2
ERROR_NOT_FOUND = 1168


class CredentialError(RuntimeError):
    pass


class CREDENTIALW(ctypes.Structure):
    _fields_ = [
        ("Flags", wintypes.DWORD),
        ("Type", wintypes.DWORD),
        ("TargetName", wintypes.LPWSTR),
        ("Comment", wintypes.LPWSTR),
        ("LastWritten", wintypes.FILETIME),
        ("CredentialBlobSize", wintypes.DWORD),
        ("CredentialBlob", ctypes.POINTER(ctypes.c_ubyte)),
        ("Persist", wintypes.DWORD),
        ("AttributeCount", wintypes.DWORD),
        ("Attributes", ctypes.c_void_p),
        ("TargetAlias", wintypes.LPWSTR),
        ("UserName", wintypes.LPWSTR),
    ]


def validate_key(value):
    if not isinstance(value, str) or not re.fullmatch(r"[A-Za-z0-9_-]{1,512}", value):
        raise CredentialError("Formato de chave inválido. Confira a chave no Google AI Studio.")
    return value


def _native_api():
    if os.name != "nt":
        raise CredentialError("O cofre de credenciais da Aurora requer Windows.")
    try:
        api = ctypes.WinDLL("Advapi32.dll", use_last_error=True)
        api.CredWriteW.argtypes = [ctypes.POINTER(CREDENTIALW), wintypes.DWORD]
        api.CredWriteW.restype = wintypes.BOOL
        api.CredReadW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD,
                                  ctypes.POINTER(ctypes.POINTER(CREDENTIALW))]
        api.CredReadW.restype = wintypes.BOOL
        api.CredDeleteW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD]
        api.CredDeleteW.restype = wintypes.BOOL
        api.CredFree.argtypes = [ctypes.c_void_p]
        api.CredFree.restype = None
        return api
    except (OSError, AttributeError):
        raise CredentialError("Não foi possível acessar o Gerenciador de Credenciais do Windows.") from None


class WindowsCredentialStore:
    def __init__(self, api=None, last_error=None):
        self.api = api if api is not None else _native_api()
        self.last_error = last_error or ctypes.get_last_error

    def read(self):
        pointer = ctypes.POINTER(CREDENTIALW)()
        if not self.api.CredReadW(TARGET, CRED_TYPE_GENERIC, 0, ctypes.byref(pointer)):
            if self.last_error() == ERROR_NOT_FOUND:
                return None
            raise CredentialError("Não foi possível ler a chave no Gerenciador de Credenciais.")
        try:
            entry = pointer.contents
            if not 0 < entry.CredentialBlobSize <= 1024:
                raise CredentialError("Credencial Gemini inválida. Cadastre a chave novamente.")
            try:
                value = ctypes.string_at(entry.CredentialBlob, entry.CredentialBlobSize).decode("utf-16-le")
            except UnicodeError:
                raise CredentialError("Credencial Gemini inválida. Cadastre a chave novamente.") from None
            return validate_key(value)
        finally:
            self.api.CredFree(pointer)

    def write(self, value):
        encoded = validate_key(value).encode("utf-16-le")
        blob = (ctypes.c_ubyte * len(encoded)).from_buffer_copy(encoded)
        entry = CREDENTIALW()
        entry.Type = CRED_TYPE_GENERIC
        entry.TargetName = TARGET
        entry.UserName = "Aurora"
        entry.CredentialBlobSize = len(encoded)
        entry.CredentialBlob = ctypes.cast(blob, ctypes.POINTER(ctypes.c_ubyte))
        entry.Persist = CRED_PERSIST_LOCAL_MACHINE
        try:
            if not self.api.CredWriteW(ctypes.byref(entry), 0):
                raise CredentialError("Não foi possível salvar a chave no Gerenciador de Credenciais.")
        finally:
            ctypes.memset(blob, 0, len(encoded))

    def delete(self):
        if not self.api.CredDeleteW(TARGET, CRED_TYPE_GENERIC, 0) and self.last_error() != ERROR_NOT_FOUND:
            raise CredentialError("Não foi possível remover a chave do Gerenciador de Credenciais.")
