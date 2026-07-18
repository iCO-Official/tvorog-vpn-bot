import subprocess
import ipaddress
import os
from config import WG_INTERFACE, WG_SERVER_IP, WG_PORT, WG_DNS

# Пул IP-адресов для пользователей
USER_IP_POOL = "10.0.0.0/24"
USED_IPs = set()

def generate_wg_keys():
    """Генерация ключей WireGuard"""
    # Генерация приватного ключа
    private_key = subprocess.run(
        ["wg", "genkey"],
        capture_output=True,
        text=True
    ).stdout.strip()
    
    # Генерация публичного ключа из приватного
    public_key = subprocess.run(
        ["wg", "pubkey"],
        input=private_key,
        capture_output=True,
        text=True
    ).stdout.strip()
    
    return private_key, public_key

def get_next_ip():
    """Получить следующий доступный IP из пула"""
    network = ipaddress.ip_network(USER_IP_POOL)
    used_hosts = set()
    
    # Читаем существующие конфиги
    try:
        result = subprocess.run(
            ["wg", "show", WG_INTERFACE, "allowed-ips"],
            capture_output=True,
            text=True
        )
        for line in result.stdout.split('\n'):
            if '/' in line:
                ip = line.split('/')[0].strip()
                if ip:
                    used_hosts.add(ip)
    except:
        pass
    
    # Находим первый свободный IP (пропускаем .1 - это сервер)
    for host in network.hosts():
        if str(host) not in used_hosts and host != network.network_address + 1:
            return str(host)
    
    raise Exception("Нет свободных IP-адресов")

def add_peer(public_key: str, allowed_ip: str):
    """Добавить пир (пользователя) в WireGuard"""
    subprocess.run(
        ["wg", "set", WG_INTERFACE, "peer", public_key, 
         "allowed-ips", f"{allowed_ip}/32"],
        check=True
    )

def remove_peer(public_key: str):
    """Удалить пир из WireGuard"""
    subprocess.run(
        ["wg", "set", WG_INTERFACE, "peer", public_key, "remove"],
        check=True
    )

def create_client_config(user_id: int, private_key: str, public_key: str) -> str:
    """Создать конфигурацию для клиента"""
    client_ip = get_next_ip()
    
    config = f"""[Interface]
PrivateKey = {private_key}
Address = {client_ip}/32
DNS = {WG_DNS}

[Peer]
PublicKey = {public_key}
Endpoint = {WG_SERVER_IP}:{WG_PORT}
AllowedIPs = 0.0.0.0/0
PersistentKeepalive = 25
"""
    return config, client_ip

def save_client_config(user_id: int, config: str):
    """Сохранить конфигурацию клиента"""
    os.makedirs("configs", exist_ok=True)
    with open(f"configs/{user_id}.conf", "w") as f:
        f.write(config)

def get_wg_status():
    """Получить статус WireGuard"""
    try:
        result = subprocess.run(
            ["wg", "show", WG_INTERFACE],
            capture_output=True,
            text=True
        )
        return result.stdout
    except:
        return "WireGuard не запущен"

def setup_wg_server(server_public_key: str):
    """Настройка сервера WireGuard (вызывается при установке)"""
    config = f"""[Interface]
PrivateKey = SERVER_PRIVATE_KEY
Address = 10.0.0.1/24
ListenPort = {WG_PORT}
SaveConfig = false

# Поставьте сюда ваш серверный PublicKey
# PublicKey = {server_public_key}
"""
    
    os.makedirs("/etc/wireguard", exist_ok=True)
    with open(f"/etc/wireguard/{WG_INTERFACE}.conf", "w") as f:
        f.write(config)
    
    print(f"Конфигурация сервера сохранена в /etc/wireguard/{WG_INTERFACE}.conf")
    print("Не забудьте заменить SERVER_PRIVATE_KEY на реальный ключ!")