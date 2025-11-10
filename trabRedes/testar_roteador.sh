#!/bin/bash
# Script para testar o roteador no Linux/Mac
# Uso: ./testar_roteador.sh <IP_ROTEADOR>
# Exemplo: ./testar_roteador.sh 192.168.1.1

if [ -z "$1" ]; then
    echo "Uso: ./testar_roteador.sh <IP_ROTEADOR>"
    echo "Exemplo: ./testar_roteador.sh 192.168.1.1"
    exit 1
fi

python3 roteador.py "$1"

