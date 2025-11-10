# Sistema de Roteamento Dinâmico por Vetor de Distância

Implementação em Python de um protocolo de roteamento dinâmico por vetor de distância conforme especificação do trabalho final de Fundamentos de Redes de Computadores.

## Características

- ✅ Inicialização e tabela de roteamento
- ✅ Split Horizon (evita loops de roteamento)
- ✅ Atualização periódica de rotas (a cada 10 segundos)
- ✅ Detecção de falhas (timeout de 15 segundos)
- ✅ Protocolo de comunicação completo
- ✅ Roteamento de mensagens de texto entre roteadores
- ✅ Comunicação UDP na porta 6000 (configurável)

## Requisitos

- Python 3.6 ou superior
- Todas as máquinas na mesma rede local
- Firewall permitindo UDP na porta 6000

## Instalação e Configuração

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

### Exemplo de Topologia

Para testar com 4 roteadores em topologia linear:

**Roteador 1 (192.168.1.1):**
```
192.168.1.2
```

**Roteador 2 (192.168.1.2):**
```
192.168.1.1
192.168.1.3
```

**Roteador 3 (192.168.1.3):**
```
192.168.1.2
192.168.1.4
```

**Roteador 4 (192.168.1.4):**
```
192.168.1.3
```

Em cada máquina, execute:
```bash
python roteador.py <IP_DA_MAQUINA>
```

## Funcionamento

1. **Inicialização**: Carrega vizinhos diretos do arquivo `roteadores.txt` e cria rotas iniciais com métrica 1
2. **Anúncio de entrada**: Quando entra na rede, o roteador se anuncia aos vizinhos
3. **Atualização periódica**: A cada 10 segundos, envia tabela de roteamento para todos os vizinhos (aplicando Split Horizon)
4. **Processamento de rotas**: Ao receber atualização:
   - Adiciona novas rotas (métrica incrementada em 1)
   - Atualiza rotas existentes se encontrar métrica menor
   - Remove rotas que não são mais anunciadas
5. **Detecção de falhas**: Se um vizinho não enviar mensagens por 15 segundos, todas as rotas relacionadas são removidas
6. **Mensagens de texto**: Permite enviar mensagens entre roteadores, roteadas automaticamente conforme a tabela

## Protocolo de Comunicação

### Mensagem 1 - Anúncio de rotas
Formato: `*IP;métrica*IP;métrica...`
Exemplo: `*192.168.1.2;1*192.168.1.3;2`

### Mensagem 2 - Anúncio de roteador
Formato: `@IP`
Exemplo: `@192.168.1.1`

### Mensagem 3 - Mensagem de texto
Formato: `!origem;destino;texto`
Exemplo: `!192.168.1.1;192.168.1.4;Olá, como vai?`

## Testes

### Teste 1: Verificação de Inicialização
1. Inicie todos os roteadores
2. Verifique se cada roteador exibe sua tabela inicial
3. Aguarde alguns ciclos (a cada 10 segundos)
4. Verifique se as tabelas convergem

**Resultado esperado:** Após alguns ciclos, todos os roteadores devem conhecer todos os outros na rede.

### Teste 2: Convergência da Tabela
1. Inicie todos os roteadores simultaneamente
2. Aguarde 30-40 segundos
3. Execute `tabela` em cada roteador
4. Verifique se todas as rotas estão corretas

**Resultado esperado:** 
- Rotas diretas devem ter métrica 1
- Rotas indiretas devem ter métrica maior que 1

### Teste 3: Envio de Mensagens
1. No roteador 1, envie: `enviar 192.168.1.4 Olá, esta mensagem está sendo roteada?`
2. Verifique que a mensagem aparece no roteador 4
3. Verifique que os roteadores intermediários mostram o roteamento

**Resultado esperado:** Mensagem deve ser roteada corretamente através dos roteadores intermediários.

### Teste 4: Detecção de Falhas
1. Inicie todos os roteadores
2. Aguarde a convergência
3. Encerre um roteador intermediário
4. Aguarde 15-20 segundos
5. Verifique as tabelas dos outros roteadores

**Resultado esperado:** Rotas que dependiam do roteador inativo devem ser removidas.

### Teste 5: Entrada de Novo Roteador
1. Inicie 3 roteadores (1, 2, 3)
2. Aguarde a convergência
3. Inicie o roteador 4
4. Verifique se o roteador 4 é anunciado e adicionado às tabelas

**Resultado esperado:** Roteador 4 deve se anunciar e ser adicionado às tabelas rapidamente.

## Troubleshooting

**Roteadores não se comunicam:**
- Verifique se todos estão na mesma rede
- Verifique se o firewall permite UDP na porta 6000
- Verifique se os IPs estão corretos no arquivo `roteadores.txt`
- Verifique se o IP informado ao iniciar corresponde ao IP real da máquina

**Mensagens não são roteadas:**
- Verifique se a tabela de roteamento tem rota para o destino
- Aguarde alguns ciclos para convergência da tabela

**Rotas não convergem:**
- Verifique se todos os roteadores estão rodando
- Verifique se a topologia está corretamente configurada
- Aguarde mais tempo (pode levar alguns ciclos)

## Exemplo de Saída

```
[INIT] Roteador 192.168.1.1 inicializado na porta 6000
[INIT] Vizinhos diretos: 192.168.1.2
[INIT] Tabela inicial:
IP Destino            Métrica    IP Saída             
--------------------------------------------------
192.168.1.2           1          192.168.1.2          

[ANÚNCIO] Roteador 192.168.1.1 anunciado para 192.168.1.2:6000

[NOVA ROTA] 192.168.1.3 via 192.168.1.2 (métrica: 2)
[NOVA ROTA] 192.168.1.4 via 192.168.1.2 (métrica: 3)

[14:30:45] Tabela de roteamento atualizada:
IP Destino            Métrica    IP Saída             
--------------------------------------------------
192.168.1.2           1          192.168.1.2          
192.168.1.3           2          192.168.1.2          
192.168.1.4           3          192.168.1.2          
```

## Interoperabilidade

O sistema está **100% pronto** para interoperar com implementações de outros grupos que sigam o mesmo protocolo:

✅ **Formato de mensagens exato** - Segue rigorosamente a especificação  
✅ **Sem extensões** - Não adiciona campos ou informações extras  
✅ **Encoding UTF-8** - Padrão universal para strings  
✅ **Protocolo UDP** - Porta 6000 (configurável)  
✅ **Sem dependências externas** - Usa apenas bibliotecas padrão do Python

**Checklist antes de testar com outro grupo:**
- Formato das mensagens conforme especificação
- Porta 6000 UDP configurada
- Split Horizon funcionando
- Atualização periódica a cada 10 segundos
- Detecção de falhas após 15 segundos

## Observações

- A tabela de roteamento é exibida automaticamente a cada 30 segundos e sempre que houver alterações
- O sistema detecta automaticamente a porta dos vizinhos quando recebe mensagens
- Split Horizon é aplicado automaticamente para evitar loops de roteamento
