#!/usr/bin/env python3
import asyncio
from camadafisica import ZyboSerialDriver
from tcp import Servidor        # copie o arquivo do T2
from ip import IP               # copie o arquivo do T3
from slip import CamadaEnlace   # copie o arquivo do T4
import re

## Implementação da camada de aplicação

# Este é um exemplo de um programa que faz eco, ou seja, envia de volta para
# o cliente tudo que for recebido em uma conexão.

def validar_nome(nome):
    return re.match(br'^[a-zA-Z][a-zA-Z0-9_-]*$', nome) is not None


def sair(conexao):
    print(conexao, 'conexão fechada')
    for x in servidor.canais:
        if conexao in servidor.canais[x]:       #retirando usuario de todos os canais
            servidor.canais[x].remove(conexao)
    enviados = []
    for i in servidor.canais:
        for membro in servidor.canais[i]:
            if membro not in enviados:
                enviados.append(membro)     #garantindo que a mensagem nao seja repetida
                membro.enviar(b':%s QUIT :Connection closed\r\n' % (conexao.apl))
    if hasattr(conexao, 'apl'):
        del servidor.apls[conexao.apl.lower()]     #apagando da lista de apelidos                
    conexao.fechar()

def insereApl(apelido, conexao):
    servidor.apls[apelido.lower()] = conexao
    
def subApl(aplAnt, apelido, conexao):
    servidor.apls[apelido.lower()] = conexao
    del servidor.apls[aplAnt.lower()]
    return    

def dados_recebidos(conexao, dados): 
    if dados == b'':
        return sair(conexao) 
    dados = tratamento(conexao, dados)
    comandos(conexao, dados)
    #print(conexao, dados)
    
def nick(conexao, dados):
    apelido = (dados.replace(b'\r', b'').replace(b'\n', b'')).split(b' ', 1)[1]
    if apelido.lower() in servidor.apls:
            if hasattr(conexao, 'apl'):
                conexao.enviar(b':server 433 %s %s :Nickname is already in use\r\n' % (conexao.apl, apelido))
            else:
                conexao.enviar(b':server 433 * %s :Nickname is already in use\r\n' % (apelido))
            return  
    if validar_nome(apelido): 
        if hasattr(conexao, 'apl'):
            subApl(conexao.apl, apelido, conexao)
            conexao.enviar(b':%s NICK %s\r\n' % (conexao.apl, apelido))
        else:
            insereApl(apelido, conexao)
            conexao.enviar(b':server 001 %s :Welcome\r\n:server 422 %s :MOTD File is missing\r\n' % (apelido, apelido))
        conexao.apl = apelido
        return          
    else:
        if hasattr(conexao, 'apl'):        
            conexao.enviar(b':server 432 %s %s :Erroneous nickname\r\n' %(conexao.apl, apelido))
        else:
            conexao.enviar(b':server 432 * %s :Erroneous nickname\r\n' %(apelido))     
        
              
def msg_send(destinatario, remetente, mensagem):
    if destinatario[0] == 35:
        if destinatario.lower() in servidor.canais:
            for membro in servidor.canais[destinatario.lower()]:
                if membro.apl != remetente:
                    membro.enviar(b':%s PRIVMSG %s :%s\r\n' % (remetente.lower(), destinatario.lower(), mensagem))       
    elif destinatario.lower() in servidor.apls:
        servidor.apls[destinatario.lower()].enviar(b':%s PRIVMSG %s :%s\r\n' % (remetente.lower(), destinatario.lower(), mensagem)) 
    return                
                    
 
def join_canal(conexao, chn):
    if not chn in servidor.canais:
        servidor.canais[chn] = []       #criacao de canal caso nao exista                         
    if conexao not in servidor.canais[chn]:
        servidor.canais[chn].append(conexao)   #insercao no canal    
    if not hasattr(conexao, 'canal'):
        conexao.canal = []             #criando o vetor de canais de um ususario
    conexao.canal.append(chn) 
    membros = []
    
    for x in servidor.canais[chn]:
        x.enviar(b':%s JOIN :%s\r\n' % (conexao.apl, chn))
        membros.append(x.apl)
    membros = sorted(membros)
    membros_aux = []
    for y in membros:
        if 19 + len(b' '.join(membros_aux) )+ len(y) > 510:
            conexao.enviar(b':server 353 %s = %s :%s\r\n' % (conexao.apl, chn, b' '.join(membros_aux)))
            membros_aux = []        #canais que requerem quebra de linha 
        membros_aux.append(y)
    if len(membros) == 0:
        conexao.enviar(b':server 353 %s = %s :%s\r\n' % (conexao.apl, chn, b' '.join(membros))) #caso para canais vazios   
    else:
        conexao.enviar(b':server 353 %s = %s :%s\r\n' % (conexao.apl, chn, b' '.join(membros)))
    conexao.enviar(b':server 366 %s %s :End of /NAMES list.\r\n' % (conexao.apl, chn))
    return            
        
    
    
              
def sair_canal(conexao, chn):
    if not chn in servidor.canais:
        return
    if conexao not in servidor.canais[chn]:
        return
    for membro in servidor.canais[chn.lower()]:
        membro.enviar(b':%s PART %s\r\n' % (conexao.apl, chn))
    servidor.canais[chn.lower()].remove(conexao)
    conexao.canal.remove(chn)
    return    
    
        


def conexao_aceita(conexao):
    print(conexao, 'nova conexão')
    conexao.registrar_recebedor(dados_recebidos)
    
    
 
def tratamento(conexao, dados):
    residuo = hasattr(conexao, 'residual_dados')
    if not b'\n' in dados:
        if not residuo:
            conexao.residual_dados = dados
        else:
            conexao.residual_dados = conexao.residual_dados + dados
        return None
    elif dados[-1] != b'\n':
        dados_tratados = dados.split(b'\n')
        if residuo:
            residuo_aux = conexao.residual_dados
        conexao.residual_dados = dados_tratados[-1]
        if residuo:
            return (residuo_aux + b'\n'.join(dados_tratados[:-1])).split(b'\n')
        else:
            return dados_tratados[:-1]
    else:
        if residuo:
            return (conexao.residual_dados + b'\n'.join(dados.split(b'\n')[:-1])).split(b'\n')
        else:
            return dados.split(b'\n')[:-1]
    
                      
def comandos (conexao, dados):
    print(conexao, dados)
       
    if dados == None:
        return
       
    for line in dados:
        if dados != None:
            exec_comandos(conexao, line)
        else:
            return    

def exec_comandos(conexao, dados):
    dados_t = dados.split(b' ')
    comando = dados_t[0]
    if comando == b'PING':
        ping(conexao, dados)
    elif comando == b'NICK':
        nick(conexao, dados)
    elif comando == b'PRIVMSG':
        msg = dados.split(b':', 1)[1]
        msg_send(dados_t[1], conexao.apl, msg.replace(b'\r', b'').replace(b'\n', b'')) 
    elif comando == b'JOIN':
        canal = dados_t[1].replace(b'\r', b'').replace(b'\n', b'').lower()
        if canal[0] != 35 or not validar_nome(canal[1:]):
            conexao.enviar(b':server 403 canal :No such channel\r\n')
        else:     
            join_canal(conexao, canal)
    elif comando == b'PART':
        canal = dados_t[1].replace(b'\r', b'').replace(b'\n', b'').lower()
        if canal[0] != 35 or not validar_nome(canal[1:]):
            conexao.enviar(b':server 403 canal :No such channel\r\n')
        else:    
            sair_canal(conexao, canal)           
                
        

def ping(conexao, dados):
    conexao.enviar(b':server PONG server :' + dados.split(b' ', 1)[1] + b'\n') 

## Integração com as demais camadas

nossa_ponta = '192.168.200.4'
outra_ponta = '192.168.200.3'
porta_tcp = 7000

driver = ZyboSerialDriver()
linha_serial = driver.obter_porta(0)

enlace = CamadaEnlace({outra_ponta: linha_serial})
rede = IP(enlace)
rede.definir_endereco_host(nossa_ponta)
rede.definir_tabela_encaminhamento([
    ('0.0.0.0/0', outra_ponta)
])
servidor = Servidor(rede, porta_tcp)
servidor.apls = {}
servidor.canais = {}
servidor.registrar_monitor_de_conexoes_aceitas(conexao_aceita)
asyncio.get_event_loop().run_forever()
