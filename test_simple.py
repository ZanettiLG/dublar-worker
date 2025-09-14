#!/usr/bin/env python3
"""
Teste simples para verificar o Demucs
"""

import os
import sys
from pathlib import Path

# Adiciona o diretório atual ao path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from deps.demucs import Demucs

def main():
    print("🧪 Teste simples do Demucs...")
    
    # Inicializa o Demucs
    demucs = Demucs()
    demucs.load()
    
    # Arquivo de teste
    audio_path = "./assets/gto_ep1.mp4"
    
    if not os.path.exists(audio_path):
        print(f"❌ Arquivo não encontrado: {audio_path}")
        return
    
    print(f"✅ Processando: {audio_path}")
    
    try:
        result = demucs.execute(audio_path)
        print(f"✅ Resultado: {result}")
    except Exception as e:
        print(f"❌ Erro: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
