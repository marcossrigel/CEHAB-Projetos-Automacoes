# 🤖 Automações da CEHAB
Esse repositório, tem por finalidade apresentar os códigos que eu andei desenvolvendo ao longo da minha jornada como estagiário e como comissionado aqui na CEHAB. Ao todo me envolvi com  06 projetos de automações todos eles com responsabilidades únicas que facilitam o dia-a-dia do setor da G.O.P e outros setores também.

##  🤖 Robo Despacho 
Muito importante para o setor, pois ele cria documentos SEI capturando dados de uma planilha de acompanhamento, identifica processos pendentes, localiza a solicitação que vem de outro setor correspondente a um determinado SEI e cria um despacho a partir de um modelo. O robô preenche dados como número do processo, boletim de medição, valor por extenso e fonte de recursos. Após a criação, registra na planilha que o documento está apto para ser assinado.

* OBS: o que seria um SEI? significa Sistema Eletrônico de Informações. É um portal usado por órgãos públicos para criar documentos, organizar processos administrativos e encaminhá-los entre setores. o SEI tem um papel fundamental dentro da empresa.
* Por exemplo: 00609111527401.001239/2026-55, isso é um SEI, dentro dele existem pastas e arquivos governamentais

## 🤖 Robo Solicitacao Pagamentos BM
Esse é responsável por, consultar os processos monitorados no Google Sheets e cruza seus dados com relatórios extraídos do eFisco. O robô verifica número do processo, boletim de medição, período e valor para identificar pagamentos realizados ou apontar etapas pendentes, como liquidação e liberação da programação de desembolso. Ao final, atualiza a situação de cada registro na planilha.

* OBS: eFisco é outro sistema eletrônico muito importante, foi desenvolvido pela Secretaria da Fazendo de Pernambuco (Sefaz-PE), é um sistema corporativo do Estado de Pernambuco usado em atividades tributárias, financeiras, orçamentárias e de planejamento, é nesse ambiente que eu baixo planilhas como OB_Geral, Empenho Geral, Licitação, Previsão de Desenbolso e etc.

## 🤖 Robos Pendências Seplag/Sefaz e Destaques Orçamentários

Executam suas tarefas de maneira semelhante mas para planilhas diferentes, as duas automações, verificam se novos documentos foram incluídos nos processos ainda não concluídos e registra o último documento encontrado. Quando detecta novidades, o robô envia um resumo ao grupo responsável pelo WhatsApp, com o processo, destinatário, o objeto e os documentos adicionados.
