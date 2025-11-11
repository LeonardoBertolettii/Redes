### 1. Arquivo de Configuração

Crie um arquivo `roteadores.txt` na mesma pasta do script com os IPs dos vizinhos diretos:

**Formato simples:**
```
192.168.1.2
192.168.1.3
```

**Com porta específica:**
```
PORTA=6000
192.168.1.2:6000
192.168.1.3:7000
```

- `PORTA=<número>` - Define porta deste roteador (padrão: 6000)
- `IP` ou `IP:PORTA` - Define vizinhos diretos
- Linhas começadas com `#` são comentários

### 2. Executar o Roteador

```bash
python roteador.py <IP_ROTEADOR>
```

Exemplo:
```bash
python roteador.py 192.168.1.1
```

## Uso

### Comandos Disponíveis

- `enviar <IP_DESTINO> <mensagem>` - Envia mensagem de texto para um roteador destino
- `tabela` - Exibe a tabela de roteamento atual
- `sair` - Encerra o roteador