@echo off
REM Script para testar o roteador no Windows
REM Uso: testar_roteador.bat <IP_ROTEADOR>
REM Exemplo: testar_roteador.bat 192.168.1.1

if "%1"=="" (
    echo Uso: testar_roteador.bat ^<IP_ROTEADOR^>
    echo Exemplo: testar_roteador.bat 192.168.1.1
    exit /b 1
)

python roteador.py %1

