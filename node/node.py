import redis
import random
import time
import os
import sys

class CSMA_CD_Node:
    def __init__(self, node_id):
        self.node_id = node_id
        self.redis = redis.Redis(host='redis', port=6379, decode_responses=True)
        self.collision_count = 0
        self.backoff_time = 0
        self.transmitting = False
        self.packet_size = 8 # Tamanho do pacote em unidades de tempo
        self.packet_remaining = 0
        
    def exponential_backoff(self):
        self.collision_count += 1
        max_backoff = min(2 ** self.collision_count, 1023)
        self.backoff_time = random.randint(1, max_backoff)
        print(f"Nó {self.node_id} em backoff por {self.backoff_time} unidades de tempo")
        
    def run(self):
        pubsub = self.redis.pubsub()
        pubsub.subscribe('transmissao')
        
        print(f"Nó {self.node_id} iniciado. Aguardando...")
        time.sleep(2)  # Espera inicialização do Redis
        
        while True:
            # Se está em backoff, espera uma unidade de tempo e decresce o tempo de backoff            
            if self.backoff_time > 0:                
                self.backoff_time -= 1
            # Se não, lê o meio
            else:
                msg = pubsub.get_message()
                # Se tem alguma mensagem no redis
                if msg and msg['type'] == 'message':
                    resposta = self.handle_message(msg)
                    if resposta == -1:
                        self.handle_collision() # O meio está ocupado por outro e o nó está transmitindo
                    elif resposta == 1:
                        pass # O meio está ocupado por outro
                    elif resposta == 0:
                        self.transmission_logic() # Transmite
                else:
                    # Se não tem mensagem nenhuma, deve ser a primeira mensagem da simulação
                    self.transmission_logic() # Transmite
            
            time.sleep(0.1)  # Unidade de tempo
    
    def handle_message(self, msg):
        # Se o meio está livre ou ocupado pelo próprio nó, pode transmitir
        if msg['data'] == "livre" or msg['data'] == str(self.node_id):
            return 0
        # Se o meio está em uso por outro nó
        else:
            # E o nó está transmitindo ao mesmo tempo, temos uma colisão
            if self.transmitting:
                return -1
            # Se não, não pode transmitir
            else:
                return 1                   
    
    def handle_collision(self):
        # Quando uma colisão é detectada, para de transmitir, começa o backoff e emite uma mensagem pra sinalizar colisão
        print(f"Nó {self.node_id} detectou colisão!")
        self.redis.publish('transmissao', self.node_id)
        self.transmitting = False
        self.packet_remaining = 0
        self.exponential_backoff()
    
    def transmission_logic(self):
        # Se não está transmitindo e o meio está livre, transmite com uma certa porcentagem de chance     
        if not self.transmitting:
            if random.random() < 0.3:
                self.start_transmission()
        # Se está transmitindo, continua
        elif self.transmitting:
            self.continue_transmission()
    
    def start_transmission(self):
        # Inicia nova transmissão
        self.redis.publish('transmissao', self.node_id)
        self.transmitting = True
        # Tamanho de pacote definido em unidades de tempo definido na inicialização
        self.packet_remaining = self.packet_size
        print(f"Nó {self.node_id} iniciou transmissão")
    
    def continue_transmission(self):
        self.redis.publish('transmissao', self.node_id)
        self.packet_remaining -= 1
        if self.packet_remaining == 0:
            self.complete_transmission()
    
    def complete_transmission(self):
        # Libera o meio para os outros nós com sucesso
        self.redis.publish('transmissao', "livre")
        self.transmitting = False
        self.backoff_time = 0
        self.collision_count = 0
        print(f"Nó {self.node_id} completou transmissão")
        '''
        Suspeito que tenha alguma peculiaridade na ordem dos processos do docker que faça
        com que 1 dos nós transmita várias vezes seguidas com frequência inesperada.
        Adicionando um período de cooldown pra melhor apresentar o algoritmo
        sem exceder o tempo de apresentação
        '''
        time.sleep(0.1)

if __name__ == '__main__':
    # Configuração inicial
    print("Aguardando Redis...")
    time.sleep(5)
       
    # Inicia nó
    node_id = os.getenv('NODE_ID', '1')
    print(f"Iniciando nó {node_id}")
    node = CSMA_CD_Node(node_id)
    node.run()
