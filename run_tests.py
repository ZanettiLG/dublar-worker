#!/usr/bin/env python3
"""
Script para executar os testes do dublar-worker
"""
import subprocess
import sys
import os


def run_command(command, description):
    """Executa um comando e exibe o resultado"""
    print(f"\n{'='*60}")
    print(f"🚀 {description}")
    print(f"{'='*60}")
    print(f"Executando: {command}")
    print()
    
    try:
        result = subprocess.run(command, shell=True, check=True, capture_output=False)
        print(f"\n✅ {description} - Concluído com sucesso!")
        return True
    except subprocess.CalledProcessError as e:
        print(f"\n❌ {description} - Falhou com código {e.returncode}")
        return False


def main():
    """Função principal"""
    print("🧪 Executando Testes do Dublar Worker")
    print("=" * 60)
    
    # Verifica se estamos no diretório correto
    if not os.path.exists("pyproject.toml"):
        print("❌ Erro: Execute este script no diretório raiz do projeto")
        sys.exit(1)
    
    # Lista de comandos para executar
    commands = [
        ("pytest --version", "Verificando versão do pytest"),
        ("pytest tests/deps/test_dep_base.py -v", "Testes da classe DepBase"),
        ("pytest tests/deps/test_spleeter.py -v", "Testes da classe Spleeter"),
        ("pytest tests/deps/test_media.py -v", "Testes da classe Media"),
        ("pytest tests/deps/test_transformers.py -v", "Testes da classe Transformers"),
        ("pytest tests/deps/test_transcriber.py -v", "Testes da classe Transcriber"),
        ("pytest tests/deps/ -v --cov=deps --cov-report=term-missing", "Todos os testes com cobertura"),
    ]
    
    success_count = 0
    total_commands = len(commands)
    
    for command, description in commands:
        if run_command(command, description):
            success_count += 1
    
    # Resumo final
    print(f"\n{'='*60}")
    print(f"📊 RESUMO DOS TESTES")
    print(f"{'='*60}")
    print(f"✅ Comandos executados com sucesso: {success_count}/{total_commands}")
    
    if success_count == total_commands:
        print("🎉 Todos os testes foram executados com sucesso!")
        sys.exit(0)
    else:
        print("⚠️  Alguns testes falharam. Verifique os logs acima.")
        sys.exit(1)


if __name__ == "__main__":
    main()
