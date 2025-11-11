import socket
import threading
import time
import sys
from typing import Dict, List, Tuple, Optional
from datetime import datetime, timedelta

class TabelaRoteamento:
    """Classe para gerenciar a tabela de roteamento"""
    
    def __init__(self, ip_roteador: str):
        self.ip_roteador = ip_roteador
        # Tabela: {ip_destino: (metrica, ip_saida, ultima_atualizacao)}
        self.rotas: Dict[str, Tuple[int, str, datetime]] = {}
        
    def adicionar_rota(self, ip_destino: str, metrica: int, ip_saida: str):
        """Adiciona ou atualiza uma rota na tabela"""
        self.rotas[ip_destino] = (metrica, ip_saida, datetime.now())
        
    def remover_rota(self, ip_destino: str):
        """Remove uma rota da tabela"""
        if ip_destino in self.rotas:
            del self.rotas[ip_destino]
            
    def obter_rota(self, ip_destino: str) -> Optional[Tuple[int, str]]:
        """Obtém a rota para um destino (métrica, ip_saida)"""
        if ip_destino in self.rotas:
            metrica, ip_saida, _ = self.rotas[ip_destino]
            return (metrica, ip_saida)
        return None
        
    def obter_rotas_para_envio(self, ip_vizinho: str) -> List[Tuple[str, int]]:
        """Obtém rotas para envio aplicando Split Horizon"""
        rotas_envio = []
        for ip_destino, (metrica, ip_saida, _) in self.rotas.items():
            # Split Horizon: não enviar rota de volta para quem a ensinou
            if ip_saida != ip_vizinho and ip_destino != self.ip_roteador:
                rotas_envio.append((ip_destino, metrica))
        return rotas_envio
        
    def formatar_para_exibicao(self) -> str:
        """Formata a tabela para exibição"""
        if not self.rotas:
            return "Tabela vazia"
        resultado = f"\n{'IP Destino':<20} {'Métrica':<10} {'IP Saída':<20}\n"
        resultado += "-" * 50 + "\n"
        for ip_destino, (metrica, ip_saida, _) in sorted(self.rotas.items()):
            resultado += f"{ip_destino:<20} {metrica:<10} {ip_saida:<20}\n"
        return resultado
        
    def remover_rotas_por_vizinho(self, ip_vizinho: str):
        """Remove todas as rotas que passam por um vizinho específico"""
        rotas_remover = []
        for ip_destino, (_, ip_saida, _) in self.rotas.items():
            if ip_saida == ip_vizinho or ip_destino == ip_vizinho:
                rotas_remover.append(ip_destino)
        for ip_destino in rotas_remover:
            self.remover_rota(ip_destino)


class Roteador:
    """Classe principal do roteador"""
    
    def __init__(self, ip_roteador: str, porta: int = 6000):
        self.ip_roteador = ip_roteador
        self.porta = porta
        self.tabela = TabelaRoteamento(ip_roteador)
        self.vizinhos: List[str] = []
        # Portas dos vizinhos (padrão: mesma porta do roteador)
        self.portas_vizinhos: Dict[str, int] = {}
        
        # Controle de tempo de última mensagem de cada vizinho
        self.ultima_mensagem_vizinho: Dict[str, datetime] = {}
        
        # Socket UDP
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.bind((self.ip_roteador, self.porta))
        self.socket.settimeout(1.0)  # Timeout para permitir verificação periódica
        
        # Flags de controle
        self.rodando = False
        self.rede_existente = False
        
        # Lock para operações thread-safe
        self.lock = threading.Lock()
        
    def carregar_configuracao(self, arquivo: str = "roteadores.txt"):
        """Carrega os vizinhos diretos do arquivo de configuração"""
        try:
            with open(arquivo, 'r') as f:
                for linha in f:
                    # Remove espaços e comentários (linhas que começam com #)
                    linha = linha.strip()
                    if linha.startswith('#'):
                        continue
                    
                    # Verifica se é configuração de porta (PORTA=6000)
                    if linha.upper().startswith('PORTA='):
                        try:
                            porta_config = int(linha.split('=')[1].split('#')[0].strip())
                            self.porta = porta_config
                            # Recria socket com nova porta
                            self.socket.close()
                            self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                            self.socket.bind((self.ip_roteador, self.porta))
                            self.socket.settimeout(1.0)
                            print(f"[CONFIG] Porta configurada: {self.porta}")
                        except (ValueError, IndexError):
                            print(f"[AVISO] Linha de porta inválida: {linha}")
                        continue
                    
                    # Processa linha de vizinho (pode ser IP ou IP:PORTA)
                    linha = linha.split('#')[0].strip()  # Remove comentários no final da linha
                    if not linha:
                        continue
                    
                    # Verifica se tem porta especificada (formato IP:PORTA)
                    if ':' in linha:
                        partes = linha.split(':')
                        if len(partes) == 2:
                            ip, porta_str = partes
                            ip = ip.strip()
                            try:
                                porta_vizinho = int(porta_str.strip())
                                if ip and ip != self.ip_roteador:
                                    self.vizinhos.append(ip)
                                    self.portas_vizinhos[ip] = porta_vizinho
                                    # Adiciona rota inicial com métrica 1
                                    self.tabela.adicionar_rota(ip, 1, ip)
                                    self.ultima_mensagem_vizinho[ip] = datetime.now()
                            except ValueError:
                                print(f"[AVISO] Porta inválida para {ip}: {porta_str}")
                        else:
                            # IP com dois pontos (IPv6?), tratar como IP normal
                            if linha and linha != self.ip_roteador:
                                self.vizinhos.append(linha)
                                self.portas_vizinhos[linha] = self.porta  # Usa porta padrão
                                self.tabela.adicionar_rota(linha, 1, linha)
                                self.ultima_mensagem_vizinho[linha] = datetime.now()
                    else:
                        # Formato simples: apenas IP (usa porta padrão)
                        if linha and linha != self.ip_roteador:
                            self.vizinhos.append(linha)
                            self.portas_vizinhos[linha] = self.porta  # Usa porta padrão
                            # Adiciona rota inicial com métrica 1
                            self.tabela.adicionar_rota(linha, 1, linha)
                            self.ultima_mensagem_vizinho[linha] = datetime.now()
                            
            print(f"[INIT] Roteador {self.ip_roteador} inicializado na porta {self.porta}")
            print(f"[INIT] Vizinhos diretos: {', '.join(self.vizinhos)}")
            if self.portas_vizinhos and any(p != self.porta for p in self.portas_vizinhos.values()):
                print(f"[INIT] Portas dos vizinhos: {dict(self.portas_vizinhos)}")
            print(f"[INIT] Tabela inicial:")
            print(self.tabela.formatar_para_exibicao())
        except FileNotFoundError:
            print(f"[ERRO] Arquivo {arquivo} não encontrado!")
            sys.exit(1)
        except Exception as e:
            print(f"[ERRO] Erro ao carregar configuração: {e}")
            sys.exit(1)
            
    def anunciar_entrada_rede(self):
        """Anuncia entrada do roteador em uma rede existente"""
        mensagem = f"@{self.ip_roteador}"
        for vizinho in self.vizinhos:
            porta_vizinho = self.portas_vizinhos.get(vizinho, self.porta)
            try:
                self.socket.sendto(mensagem.encode('utf-8'), (vizinho, porta_vizinho))
                print(f"[ANÚNCIO] Roteador {self.ip_roteador} anunciado para {vizinho}:{porta_vizinho}")
            except Exception as e:
                print(f"[ERRO] Erro ao anunciar para {vizinho}:{porta_vizinho}: {e}")
        self.rede_existente = True
        
    def enviar_tabela_roteamento(self):
        """Envia tabela de roteamento para todos os vizinhos"""
        with self.lock:
            for vizinho in self.vizinhos:
                rotas_envio = self.tabela.obter_rotas_para_envio(vizinho)
                # Sempre envia mensagem, mesmo que não haja rotas (keepalive)
                mensagem = self._formatar_mensagem_rotas(rotas_envio) if rotas_envio else ""
                porta_vizinho = self.portas_vizinhos.get(vizinho, self.porta)
                try:
                    if mensagem:
                        self.socket.sendto(mensagem.encode('utf-8'), (vizinho, porta_vizinho))
                except Exception as e:
                    print(f"[ERRO] Erro ao enviar tabela para {vizinho}:{porta_vizinho}: {e}")
                    
    def enviar_keepalive(self):
        """Envia keepalive para todos os vizinhos (anuncia presença e envia tabela)"""
        with self.lock:
            # Primeiro anuncia a presença do roteador
            mensagem_anuncio = f"@{self.ip_roteador}"
            for vizinho in self.vizinhos:
                porta_vizinho = self.portas_vizinhos.get(vizinho, self.porta)
                try:
                    # Anuncia presença
                    self.socket.sendto(mensagem_anuncio.encode('utf-8'), (vizinho, porta_vizinho))
                    # Envia tabela de roteamento
                    rotas_envio = self.tabela.obter_rotas_para_envio(vizinho)
                    if rotas_envio:
                        mensagem_rotas = self._formatar_mensagem_rotas(rotas_envio)
                        self.socket.sendto(mensagem_rotas.encode('utf-8'), (vizinho, porta_vizinho))
                except Exception as e:
                    print(f"[ERRO] Erro ao enviar keepalive para {vizinho}:{porta_vizinho}: {e}")
                        
    def _formatar_mensagem_rotas(self, rotas: List[Tuple[str, int]]) -> str:
        """Formata mensagem de anúncio de rotas"""
        partes = []
        for ip_destino, metrica in rotas:
            partes.append(f"*{ip_destino};{metrica}")
        return "".join(partes)
        
    def _parsear_mensagem_rotas(self, mensagem: str) -> List[Tuple[str, int]]:
        """Parseia mensagem de anúncio de rotas"""
        rotas = []
        partes = mensagem.split('*')
        for parte in partes:
            if parte:
                try:
                    ip, metrica = parte.split(';')
                    rotas.append((ip, int(metrica)))
                except ValueError:
                    continue
        return rotas
        
    def processar_mensagem_rotas(self, mensagem: str, ip_remetente: str):
        """Processa mensagem de anúncio de rotas recebida"""
        rotas_recebidas = self._parsear_mensagem_rotas(mensagem)
        tabela_alterada = False
        
        with self.lock:
            self.ultima_mensagem_vizinho[ip_remetente] = datetime.now()
            
            for ip_destino, metrica_recebida in rotas_recebidas:
                nova_metrica = metrica_recebida + 1
                
                rota_atual = self.tabela.obter_rota(ip_destino)
                
                if ip_destino == self.ip_roteador:
                    continue  
                    
                if rota_atual is None:
                    self.tabela.adicionar_rota(ip_destino, nova_metrica, ip_remetente)
                    print(f"[NOVA ROTA] {ip_destino} via {ip_remetente} (métrica: {nova_metrica})")
                    tabela_alterada = True
                else:
                    metrica_atual, ip_saida_atual = rota_atual
                    if nova_metrica < metrica_atual:
                        #  melhor encontrada
                        self.tabela.adicionar_rota(ip_destino, nova_metrica, ip_remetente)
                        print(f"[ROTA MELHORADA] {ip_destino}: {metrica_atual} -> {nova_metrica} via {ip_remetente}")
                        tabela_alterada = True
                        
            # Verifica rotas que não foram mais anunciadas 
            ips_anunciados = {ip for ip, _ in rotas_recebidas}
            rotas_remover = []
            for ip_destino, (_, ip_saida, _) in self.tabela.rotas.items():
                if ip_saida == ip_remetente and ip_destino not in ips_anunciados and ip_destino != ip_remetente:
                    rotas_remover.append(ip_destino)
                    
            for ip_destino in rotas_remover:
                self.tabela.remover_rota(ip_destino)
                print(f"[ROTA REMOVIDA] {ip_destino} (não mais anunciada por {ip_remetente})")
                tabela_alterada = True
                
        if tabela_alterada:
            print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Tabela de roteamento atualizada:")
            print(self.tabela.formatar_para_exibicao())
            self.enviar_tabela_roteamento()
            
    def processar_anuncio_roteador(self, ip_novo_roteador: str):
        """Processa anúncio de novo roteador na rede (também funciona como keepalive)"""
        tabela_alterada = False
        deve_enviar_resposta = False
        
        with self.lock:
            rota_atual = self.tabela.obter_rota(ip_novo_roteador)
            
            # Sempre atualiza o timestamp (keepalive)
            self.ultima_mensagem_vizinho[ip_novo_roteador] = datetime.now()
            
            # Se não existe rota ou se a rota atual tem métrica maior que 1, atualiza
            if rota_atual is None:
                self.tabela.adicionar_rota(ip_novo_roteador, 1, ip_novo_roteador)
                tabela_alterada = True
                print(f"[NOVO ROTEADOR] {ip_novo_roteador} adicionado à tabela (métrica: 1)")
                deve_enviar_resposta = True
            elif rota_atual[0] > 1:
                self.tabela.adicionar_rota(ip_novo_roteador, 1, ip_novo_roteador)
                tabela_alterada = True
                print(f"[ROTA ATUALIZADA] {ip_novo_roteador} atualizado para métrica 1")
                deve_enviar_resposta = True
            else:
                # Roteador já conhecido - sempre responde com tabela (keepalive com resposta)
                deve_enviar_resposta = True
                
            if ip_novo_roteador not in self.vizinhos:
                self.vizinhos.append(ip_novo_roteador)
                # Se não tinha porta configurada, usa porta padrão
                if ip_novo_roteador not in self.portas_vizinhos:
                    self.portas_vizinhos[ip_novo_roteador] = self.porta
            
            if tabela_alterada:
                print(self.tabela.formatar_para_exibicao())
        
        # Fora do lock: envia resposta
        if deve_enviar_resposta:
            # Responde imediatamente com a tabela para o roteador que anunciou
            self._enviar_tabela_para_vizinho(ip_novo_roteador)
            
            # Se houve alteração na tabela, envia para todos os vizinhos
            if tabela_alterada:
                self.enviar_tabela_roteamento()
                
    def _enviar_tabela_para_vizinho(self, vizinho: str):
        """Envia tabela de roteamento para um vizinho específico (sem lock - deve ser chamado cuidadosamente)"""
        with self.lock:
            rotas_envio = self.tabela.obter_rotas_para_envio(vizinho)
            porta_vizinho = self.portas_vizinhos.get(vizinho, self.porta)
        
        # Envia fora do lock
        if rotas_envio:
            mensagem = self._formatar_mensagem_rotas(rotas_envio)
            try:
                self.socket.sendto(mensagem.encode('utf-8'), (vizinho, porta_vizinho))
            except Exception as e:
                print(f"[ERRO] Erro ao enviar tabela para {vizinho}:{porta_vizinho}: {e}")
                
    def verificar_falhas_vizinhos(self):
        """Verifica se algum vizinho parou de responder"""
        timeout = timedelta(seconds=15)
        agora = datetime.now()
        vizinhos_inativos = []
        
        with self.lock:
            for vizinho in list(self.ultima_mensagem_vizinho.keys()):
                ultima_mensagem = self.ultima_mensagem_vizinho[vizinho]
                if agora - ultima_mensagem > timeout:
                    vizinhos_inativos.append(vizinho)
                    
            for vizinho in vizinhos_inativos:
                print(f"[FALHA DETECTADA] Vizinho {vizinho} inativo (sem mensagens por 15s)")
                self.tabela.remover_rotas_por_vizinho(vizinho)
                if vizinho in self.ultima_mensagem_vizinho:
                    del self.ultima_mensagem_vizinho[vizinho]
                print(f"[FALHA] Tabela atualizada após remoção de rotas:")
                print(self.tabela.formatar_para_exibicao())
                
    def processar_mensagem_texto(self, mensagem: str, ip_remetente: str):
        """Processa mensagem de texto recebida"""
        try:
            partes = mensagem[1:].split(';', 2)
            if len(partes) != 3:
                return
                
            ip_origem, ip_destino, texto = partes
            
            if ip_destino == self.ip_roteador:
                # Mensagem chegou ao destino
                print(f"\n[MENSAGEM RECEBIDA]")
                print(f"Origem: {ip_origem}")
                print(f"Destino: {ip_destino} (você)")
                print(f"Mensagem: {texto}")
                print(f"Status: Chegou ao destino\n")
            else:
                rota = self.tabela.obter_rota(ip_destino)
                if rota:
                    _, ip_proximo = rota
                    print(f"[MENSAGEM ROTEADA]")
                    print(f"Origem: {ip_origem}")
                    print(f"Destino: {ip_destino}")
                    print(f"Próximo salto: {ip_proximo}")
                    print(f"Mensagem: {texto}")
                    
                    # Reenvia mensagem para próximo salto
                    porta_proximo = self.portas_vizinhos.get(ip_proximo, self.porta)
                    self.socket.sendto(mensagem.encode('utf-8'), (ip_proximo, porta_proximo))
                else:
                    print(f"[ERRO] Rota não encontrada para {ip_destino}")
        except Exception as e:
            print(f"[ERRO] Erro ao processar mensagem de texto: {e}")
            
    def enviar_mensagem_texto(self, ip_destino: str, texto: str):
        """Envia mensagem de texto para um destino"""
        rota = self.tabela.obter_rota(ip_destino)
        if rota:
            _, ip_proximo = rota
            mensagem = f"!{self.ip_roteador};{ip_destino};{texto}"
            porta_proximo = self.portas_vizinhos.get(ip_proximo, self.porta)
            try:
                self.socket.sendto(mensagem.encode('utf-8'), (ip_proximo, porta_proximo))
                print(f"[MENSAGEM ENVIADA] Para {ip_destino} via {ip_proximo}:{porta_proximo}: {texto}")
            except Exception as e:
                print(f"[ERRO] Erro ao enviar mensagem: {e}")
        else:
            print(f"[ERRO] Rota não encontrada para {ip_destino}")
            
    def receber_mensagens(self):
        while self.rodando:
            try:
                data, addr = self.socket.recvfrom(1024)
                mensagem = data.decode('utf-8')
                ip_remetente = addr[0]
                porta_remetente = addr[1]
                
                # Salva porta do remetente se conhecido ou se não estava configurado
                if ip_remetente in self.vizinhos:
                    if ip_remetente not in self.portas_vizinhos or self.portas_vizinhos[ip_remetente] != porta_remetente:
                        self.portas_vizinhos[ip_remetente] = porta_remetente
                
                if mensagem.startswith('*'):
                    # Mensagem de anúncio de rotas
                    self.processar_mensagem_rotas(mensagem, ip_remetente)
                elif mensagem.startswith('@'):
                    # Anúncio de novo roteador
                    ip_novo = mensagem[1:]
                    # Se não conhecemos a porta, salva da mensagem recebida
                    if ip_novo not in self.portas_vizinhos:
                        self.portas_vizinhos[ip_novo] = porta_remetente
                    self.processar_anuncio_roteador(ip_novo)
                elif mensagem.startswith('!'):
                    self.processar_mensagem_texto(mensagem, ip_remetente)
            except socket.timeout:
                continue
            except Exception as e:
                if self.rodando:
                    print(f"[ERRO] Erro ao receber mensagem: {e}")
                    
    def atualizar_periodicamente(self):
        """Thread para atualização periódica de rotas"""
        while self.rodando:
            time.sleep(10)
            if self.rodando:
                # Envia keepalive para anunciar presença e atualizar tabela
                self.enviar_keepalive()
                
    def verificar_falhas_periodicamente(self):
        """Thread para verificação periódica de falhas"""
        while self.rodando:
            time.sleep(5)  
            if self.rodando:
                self.verificar_falhas_vizinhos()
                
    def exibir_tabela_periodicamente(self):
        """Thread para exibir tabela periodicamente"""
        while self.rodando:
            time.sleep(30)  
            if self.rodando:
                print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Estado atual da tabela de roteamento:")
                print(self.tabela.formatar_para_exibicao())
                
    def iniciar(self):
        self.rodando = True
        
        # Thread para receber mensagens
        thread_receber = threading.Thread(target=self.receber_mensagens, daemon=True)
        thread_receber.start()
        
        # Thread para atualização periódica
        thread_atualizar = threading.Thread(target=self.atualizar_periodicamente, daemon=True)
        thread_atualizar.start()
        
        # Thread para verificação de falhas
        thread_falhas = threading.Thread(target=self.verificar_falhas_periodicamente, daemon=True)
        thread_falhas.start()
        
        # Thread para exibir tabela periodicamente
        thread_exibir = threading.Thread(target=self.exibir_tabela_periodicamente, daemon=True)
        thread_exibir.start()
        
        # Anuncia entrada 
        time.sleep(1)
        self.anunciar_entrada_rede()
        
        print(f"\n[Roteador {self.ip_roteador} iniciado]")
        print("Comandos disponíveis:")
        print("  enviar <IP_DESTINO> <mensagem> - Envia mensagem de texto")
        print("  tabela - Exibe tabela de roteamento")
        print("  sair - Encerra o roteador")
        print("\nAguardando comandos...\n")
        
        # comandos principais 
        try:
            while self.rodando:
                try:
                    comando = input().strip()
                    if comando == "sair":
                        self.parar()
                    elif comando == "tabela":
                        print(self.tabela.formatar_para_exibicao())
                    elif comando.startswith("enviar "):
                        partes = comando.split(' ', 2)
                        if len(partes) == 3:
                            _, ip_destino, texto = partes
                            self.enviar_mensagem_texto(ip_destino, texto)
                        else:
                            print("Uso: enviar <IP_DESTINO> <mensagem>")
                    elif comando:
                        print(f"Comando desconhecido: {comando}")
                except EOFError:
                    # EOFError ocorre quando não há entrada disponível (ex: redirecionamento)
                    # Aguarda um pouco e continua o loop
                    time.sleep(0.1)
                    continue
        except KeyboardInterrupt:
            self.parar()
            
    def parar(self):
        self.rodando = False
        self.socket.close()
        print(f"\n[Roteador {self.ip_roteador} encerrado]")


def main():
    if len(sys.argv) < 2:
        print("Uso: python roteador.py <IP_ROTEADOR> [porta]")
        print("Exemplo: python roteador.py 192.168.1.1")
        sys.exit(1)
        
    ip_roteador = sys.argv[1]
    porta = int(sys.argv[2]) if len(sys.argv) > 2 else 6000
    
    roteador = Roteador(ip_roteador, porta)
    roteador.carregar_configuracao()
    roteador.iniciar()


if __name__ == "__main__":
    main()

