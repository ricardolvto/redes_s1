class CamadaEnlace:

    ignore_checksum = False

    def __init__(self, linhas_seriais):
        """
        Inicia uma camada de enlace com um ou mais enlaces, cada um conectado
        a uma linha serial distinta. O argumento linhas_seriais é um dicionário
        no formato {ip_outra_ponta: linha_serial}. O ip_outra_ponta é o IP do
        host ou roteador que se encontra na outra ponta do enlace, escrito como
        uma string no formato 'x.y.z.w'. A linha_serial é um objeto da classe
        PTY (vide camadafisica.py) ou de outra classe que implemente os métodos
        registrar_recebedor e enviar.
        """
        self.enlaces = {}
        self.callback = None
        # Constrói um Enlace para cada linha serial
        for ip_outra_ponta, linha_serial in linhas_seriais.items():
            enlace = Enlace(linha_serial)
            self.enlaces[ip_outra_ponta] = enlace
            enlace.registrar_recebedor(self._callback)

    def registrar_recebedor(self, callback):
        """
        Registra uma função para ser chamada quando dados vierem da camada de enlace
        """
        self.callback = callback

    def enviar(self, datagrama, next_hop):
        """
        Envia datagrama para next_hop, onde next_hop é um endereço IPv4
        fornecido como string (no formato x.y.z.w). A camada de enlace se
        responsabilizará por encontrar em qual enlace se encontra o next_hop.
        """
        # Encontra o Enlace capaz de alcançar next_hop e envia por ele
        self.enlaces[next_hop].enviar(datagrama)

    def _callback(self, datagrama):
        if self.callback:
            self.callback(datagrama)


class Enlace:

    # SLIP: camada de enlace mais simples, pois não envolve nem endereçamento nem controle de acesso ao meio, pois é feito para um enlace ponto a
        # ponto (só envolve duas pontas, chamadas de A e B)
        # A pode transmitir ao mesmo tempo que B sem colisão, pois é full duplex (tem-se dois fios independentes)
        # Não precisa de endereçamento pois se o A estiver transmitindo e o B estiver recebendo sabe-se que só pode ser o A que está transmitindo e vice-versa,
             # sempre sabe-se de onde está vindo, não precisa de um endereço dentro do quadro
    # Linha serial é um fluxo de bytes continuo, por isso, tem um but final e inicial para delimitar o inicio e fim do pacote

    def __init__(self, linha_serial):
        self.linha_serial = linha_serial
        self.linha_serial.registrar_recebedor(self.__raw_recv)
        self.fluxo = b''

    def registrar_recebedor(self, callback):
        self.callback = callback

    def enviar(self, datagrama):
        # TODO: Preencha aqui com o código para enviar o datagrama pela linha
        # serial, fazendo corretamente a delimitação de quadros e o escape de
        # sequências especiais, de acordo com o protocolo CamadaEnlace (RFC 1055).
        datagrama = datagrama.replace(b'\xdb', b'\xdb\xdd')
        datagrama = datagrama.replace(b'\xc0', b'\xdb\xdc')
        datagrama = b'\xc0' + datagrama + b'\xc0' # datagrama é uma sequencia de bytes
        self.linha_serial.enviar(datagrama)
        pass

    def __raw_recv(self, dados):
        # TODO: Preencha aqui com o código para receber dados da linha serial.
        # Trate corretamente as sequências de escape. Quando ler um quadro
        # completo, repasse o datagrama contido nesse quadro para a camada
        # superior chamando self.callback. Cuidado pois o argumento dados pode
        # vir quebrado de várias formas diferentes - por exemplo, podem vir
        # apenas pedaços de um quadro, ou um pedaço de quadro seguido de um
        # pedaço de outro, ou vários quadros de uma vez só.

        # Esse método recebe do SO os dados dos bytes que estão sendo lidos da linha serial
        # Deve-se extrair o datagrama e chamar self.callback
        # Acumular em um buffer tudo que é recebido até conseguir separar um quadro
        # Espera-se o fim de um quadro, ou seja, 0xC0

        self.fluxo += dados #acumulando
        
        while self.fluxo.count(b'\xc0') != 0:
            datagrama, self.fluxo = self.fluxo.split(b'\xc0', 1)
            if len(datagrama) != 0:
                datagrama = datagrama.replace(b'\xdb\xdd', b'\xdb')
                datagrama = datagrama.replace(b'\xdb\xdc', b'\xc0')
                try:
                    self.callback(datagrama)
                except:
                    # ignora a exceção, mas mostra na tela
                    import traceback
                    traceback.print_exc()
                finally:
                    # faça aqui a limpeza necessária para garantir que não vão sobrar
                    # pedaços do datagrama em nenhum buffer mantido por você
                    pass
