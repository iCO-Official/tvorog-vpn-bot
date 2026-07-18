#!/usr/bin/env python3
"""
Генератор QR-кодов для WireGuard конфигов
"""

import qrcode
import sys
import os

def generate_qr(config_path: str, output_path: str = None):
    """Генерация QR-кода из конфигурационного файла"""
    if not os.path.exists(config_path):
        print(f"❌ Файл не найден: {config_path}")
        return False
    
    with open(config_path, 'r') as f:
        config_content = f.read()
    
    # Создаём QR-код
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(config_content)
    qr.make(fit=True)
    
    # Создаём изображение
    img = qr.make_image(fill_color="black", back_color="white")
    
    # Сохраняем
    if output_path is None:
        output_path = config_path.replace('.conf', '.png')
    
    img.save(output_path)
    print(f"✅ QR-код сохранён: {output_path}")
    return True

def main():
    if len(sys.argv) < 2:
        print("Использование: python qr_generator.py <config_file> [output_file]")
        print("Пример: python qr_generator.py configs/123456.conf")
        sys.exit(1)
    
    config_path = sys.argv[1]
    output_path = sys.argv[2] if len(sys.argv) > 2 else None
    
    generate_qr(config_path, output_path)

if __name__ == "__main__":
    main()