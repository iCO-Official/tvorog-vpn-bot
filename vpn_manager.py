import subprocess
import ipaddress
import logging
import os
import shutil
from config import WG_INTERFACE, WG_SERVER_IP, WG_PORT, WG_DNS, WG_SERVER_PUBLIC_KEY

logger = logging.getLogger(__name__)

# Пул IP-адресов для пользователей (10.0.0.1 — сервер)
USER_IP_POOL = "10.0.0.0/24"
SERVER_PUBLIC_KEY_FILE = "/etc/wireguard/server_public.key"


class WireGuardError(Exception):
    """Ошибка работы с WireGuard"""


def _wg(*args, input_text=None) -> str:
    """Вызвать утилиту wg и вернуть stdout"""
    if not shutil.which("wg"):
        raise WireGuardError("Утилита wg не найдена. Установите: apt install wireguard-tools")
    result = subprocess.run(["wg", *args], input=input_text, capture_output=True, text=True)
    if result.returncode != 0:
        raise WireGuardError(f"wg {' '.join(args)}: {result.stderr.strip()}")
    return result.stdout.strip()


def generate_wg_keys():
    """Генерация ключей WireGuard для клиента"""
    private_key = _wg("genkey")
    public_key = _wg("pubkey", input_text=private_key)
    return private_key, public_key


def get_server_public_key() -> str:
    """Публичный ключ сервера: из .env, из работающего интерфейса или из файла"""
    if WG_SERVER_PUBLIC_KEY:
        return WG_SERVER_PUBLIC_KEY
    try:
        return _wg("show", WG_INTERFACE, "public-key")
    except WireGuardError:
        pass
    if os.path.exists(SERVER_PUBLIC_KEY_FILE):
        with open(SERVER_PUBLIC_KEY_FILE) as f:
            return f.read().strip()
    raise WireGuardError(
        "Не найден публичный ключ сервера WireGuard. "
        "Укажите WG_SERVER_PUBLIC_KEY в .env или запустите интерфейс " + WG_INTERFACE
    )


def get_next_ip(used_ips: set) -> str:
    """Получить следующий свободный IP из пула"""
    network = ipaddress.ip_network(USER_IP_POOL)
    server_ip = network.network_address + 1
    for host in network.hosts():
        if host != server_ip and str(host) not in used_ips:
            return str(host)
    raise WireGuardError("Нет свободных IP-адресов")


def add_peer(public_key: str, allowed_ip: str):
    """Добавить пир (пользователя) в WireGuard"""
    _wg("set", WG_INTERFACE, "peer", public_key, "allowed-ips", f"{allowed_ip}/32")


def remove_peer(public_key: str):
    """Удалить пир из WireGuard"""
    _wg("set", WG_INTERFACE, "peer", public_key, "remove")


def create_client_config(private_key: str, client_ip: str) -> str:
    """Создать конфигурацию для клиента"""
    return f"""[Interface]
PrivateKey = {private_key}
Address = {client_ip}/32
DNS = {WG_DNS}

[Peer]
PublicKey = {get_server_public_key()}
Endpoint = {WG_SERVER_IP}:{WG_PORT}
AllowedIPs = 0.0.0.0/0
PersistentKeepalive = 25
"""


def save_client_config(user_id: int, config: str) -> str:
    """Сохранить конфигурацию клиента, вернуть путь к файлу"""
    os.makedirs("configs", exist_ok=True)
    path = f"configs/{user_id}.conf"
    with open(path, "w") as f:
        f.write(config)
    os.chmod(path, 0o600)
    return path


def get_wg_status():
    """Получить статус WireGuard"""
    try:
        return _wg("show", WG_INTERFACE)
    except WireGuardError as e:
        return f"WireGuard не запущен: {e}"
