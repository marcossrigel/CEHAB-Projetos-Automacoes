import os
import gspread
import re
import time
import sys
import unicodedata

from urllib.parse import urlparse, parse_qs
from num2words import num2words
from dotenv import load_dotenv
from selenium.common.exceptions import UnexpectedAlertPresentException
from selenium.webdriver.common.alert import Alert
from selenium.webdriver.common.keys import Keys
from seleniumbase import Driver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from oauth2client.service_account import ServiceAccountCredentials
from selenium.webdriver.common.by import By
from datetime import datetime

PLANILHA_ID = os.getenv("PLANILHA_ID")
ABA = "BMs 2026"

if getattr(sys, "frozen", False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))


CREDENCIAIS_GOOGLE = os.path.join(
    BASE_DIR,
    "arquivos_json",
    "credenciais_sheets.json"
)

ENV_PATH = os.path.join(
    BASE_DIR,
    "arquivos_json",
    "arquivo.env"
)

def conectar_planilha():

    scope = [
        "https://spreadsheets.google.com/feeds",
        "https://www.googleapis.com/auth/drive"
    ]

    creds = ServiceAccountCredentials.from_json_keyfile_name(
        CREDENCIAIS_GOOGLE,
        scope
    )

    client = gspread.authorize(creds)

    planilha = client.open_by_key(
        PLANILHA_ID
    )

    worksheet = planilha.worksheet(
        ABA
    )

    return worksheet

def atualizar_planilha_enviado(linha_planilha):

    worksheet = conectar_planilha()

    data_hoje = datetime.now().strftime(
        "%d/%m/%Y"
    )

    worksheet.update_cell(
        linha_planilha,
        26,  
        "AGUARDANDO ASSINATURA"
    )

    worksheet.update_cell(
        linha_planilha,
        27,  
        "GAC"
    )

    worksheet.update_cell(
        linha_planilha,
        28,  
        data_hoje
    )

    worksheet.update_cell(
        linha_planilha,
        39,  
        "SIM"
    )

    print(
        f"PLANILHA ATUALIZADA "
        f"(linha {linha_planilha})"
    )

def obter_aguardando_sei():

    worksheet = conectar_planilha()

    registros = worksheet.get_all_records()

    lista = []

    for idx, linha in enumerate(
        registros,
        start=2
    ):

        status = str(
            linha.get(
                "STATUS",
                ""
            )
        ).strip().upper()

        if status == "AGUARDANDO SEI":

            lista.append({

                "linha_planilha": idx,

                "numero_sei":
                linha.get(
                    "N° do SEI",
                    ""
                ),

                "fonte":
                linha.get(
                    "FONTE",
                    ""
                ),

                "fonte_recurso":
                linha.get(
                    "Fonte de Recursos",
                    ""
                ),

                "ficha_financeira":
                linha.get(
                    "Ficha Financeira",
                    ""
                ),

                "resolucao":
                linha.get(
                    "RESOLUÇÃO",
                    ""
                ),

                "responsavel":
                linha.get(
                    "RESPONSÁVEL",
                    ""
                ),

                "linha_completa":
                worksheet.row_values(idx)
            })

    return lista

def iniciar_robo():

    load_dotenv(ENV_PATH)

    usuario = os.getenv(
        "SEI_USER"
    )

    senha = os.getenv(
        "SEI_PASS"
    )

    browser = Driver(
        uc=False,
        headless=True,
        log_cdp=False
    )

    browser.get(
        "https://sei.pe.gov.br/sip/login.php?sigla_orgao_sistema=GOVPE&sigla_sistema=SEI"
    )

    browser.sleep(3)

    browser.find_element(
        "css selector",
        "#selOrgao"
    ).send_keys(
        "CEHAB"
    )

    browser.find_element(
        "xpath",
        '//*[@id="txtUsuario"]'
    ).send_keys(
        usuario
    )

    browser.find_element(
        "xpath",
        '//*[@id="pwdSenha"]'
    ).send_keys(
        senha
    )

    browser.find_element(
        "xpath",
        '//*[@id="sbmAcessar"]'
    ).click()

    browser.sleep(5)

    return browser

def verificar_recebidos(browser, numero_sei):

    try:
        tabela = browser.find_element(
            "xpath",
            '//*[@id="tblProcessosRecebidos"]'
        )

        html = tabela.get_attribute(
            "outerHTML"
        )

        from bs4 import BeautifulSoup

        soup = BeautifulSoup(
            html,
            "html.parser"
        )

        links = soup.find_all("a")

        for link in links:

            processo = link.get_text(
                strip=True
            )

            if processo == numero_sei:

                print(
                    f"{numero_sei} ENCONTRADO"
                )

                campo_pesquisa = browser.find_element(
                    "xpath",
                    '//*[@id="txtPesquisaRapida"]'
                )

                campo_pesquisa.clear()

                campo_pesquisa.send_keys(
                    numero_sei
                )

                print(
                    f"{numero_sei} DIGITADO "
                    f"NA PESQUISA"
                )

                lupa = browser.find_element(
                    "xpath",
                    '//*[@id="spnInfraUnidade"]/img'
                )

                lupa.click()
                browser.sleep(5)

                return True

        print(f"{numero_sei} NÃO ENCONTRADO")
        print("========================================================================================")

        return False

    except Exception as erro:

        print(
            f"ERRO VERIFICAR RECEBIDOS: "
            f"{erro}"
        )

        return False

def normalizar_texto(valor):
    texto = unicodedata.normalize("NFKD", str(valor or ""))
    texto = "".join(
        caractere for caractere in texto
        if not unicodedata.combining(caractere)
    )
    return re.sub(r"\s+", " ", texto).strip().upper()


def listar_solicitacoes(browser):
    browser.switch_to.default_content()
    browser.switch_to.frame(
        browser.find_element(By.ID, "ifrArvore")
    )

    solicitacoes = []

    for link in browser.find_elements(By.TAG_NAME, "a"):
        texto = link.text.strip()

        if "CEHAB - SOLICITAÇÃO DE DISPONIBILIDADE FINANCEIRA" not in texto.upper():
            continue

        numero = re.search(r"(\d{8})(?:\))?\s*$", texto)

        if numero:
            solicitacoes.append({
                "texto": texto,
                "numero": numero.group(1),
            })

    browser.switch_to.default_content()
    return solicitacoes


def selecionar_solicitacao(dados, solicitacoes, lista):
    numero_sei = str(dados["numero_sei"]).strip()

    linhas_do_sei = sorted(
        item["linha_planilha"]
        for item in lista
        if str(item["numero_sei"]).strip() == numero_sei
    )

    print(
        f"Encontrou {len(solicitacoes)}x "
        "CEHAB - SOLICITAÇÃO DE DISPONIBILIDADE FINANCEIRA"
    )

    if len(linhas_do_sei) != len(solicitacoes):
        print(
            f"SEI {numero_sei}: {len(linhas_do_sei)} linhas na planilha "
            f"e {len(solicitacoes)} solicitações no SEI. "
            "Processamento interrompido para evitar associação errada."
        )
        return None

    indice = linhas_do_sei.index(dados["linha_planilha"])
    solicitacao = solicitacoes[indice]

    print(
        f"LINHA {dados['linha_planilha']} -> "
        f"SOLICITAÇÃO {solicitacao['numero']}"
    )

    return solicitacao


def criar_documento(browser, dados, solicitacao):

    try:

        browser.switch_to.default_content()

        iframes = browser.find_elements(
            "tag name",
            "iframe"
        )

        browser.switch_to.frame(
            iframes[0]
        )

        # A solicitação já foi escolhida para esta linha da planilha.
        # Não procurar a última solicitação da árvore novamente.
        numero = str(solicitacao["numero"]).strip()

        if not re.fullmatch(r"\d{8}", numero):
            print(
                f"NÚMERO DA SOLICITAÇÃO INVÁLIDO: "
                f"{solicitacao!r}"
            )
            return None

        print(
            f"CRIANDO DISPONIBILIDADE PARA: "
            f"{solicitacao['texto']}"
        )

        browser.switch_to.default_content()

        browser.switch_to.frame(
            iframes[1]
        )

        botao = browser.find_element(
            "xpath",
            '//img[@title="Incluir Documento"]'
        )

        browser.execute_script(
            "arguments[0].click();",
            botao
        )

        browser.sleep(3)

        iframe_visualizacao = browser.find_element(
            "id",
            "ifrVisualizacao"
        )

        browser.switch_to.frame(
            iframe_visualizacao
        )

        documento_gop = browser.find_element(
            "xpath",
            '//*[@id="tblSeries"]/tbody/tr[2]/td/a[2]'
        )

        browser.execute_script(
            "arguments[0].click();",
            documento_gop
        )

        browser.sleep(5)

        campo_destinatario = browser.find_element(
            "id",
            "txtDestinatario"
        )

        campo_destinatario.send_keys(
            "GAC"
        )

        browser.sleep(1)

        campo_destinatario.send_keys(
            Keys.ESCAPE
        )

        responsavel = str(
            dados.get("responsavel", "")
        ).strip()

        while True:

            interessados = browser.find_elements(
                By.XPATH,
                '//*[@id="selInteressados"]/option'
            )

            if not interessados:
                break

            interessado_existente = interessados[0]

            print(
                f"REMOVENDO INTERESSADO PRÉ-DEFINIDO: "
                f"{interessado_existente.text}"
            )

            browser.execute_script(
                "arguments[0].selected = true;",
                interessado_existente
            )

            botao_remover = browser.find_element(
                By.XPATH,
                '//*[@id="imgRemoverInteressados"]'
            )

            browser.execute_script(
                "arguments[0].click();",
                botao_remover
            )

            browser.sleep(1)

        print(
            "INTERESSADOS PRÉ-DEFINIDOS REMOVIDOS"
        )

        if responsavel:

            campo_interessado = browser.find_element(
                By.XPATH,
                '//*[@id="txtInteressado"]'
            )

            campo_interessado.clear()

            campo_interessado.send_keys(
                responsavel
            )

            print(
                f"BUSCANDO RESPONSÁVEL: {responsavel}"
            )

            browser.sleep(2)

            campo_interessado.send_keys(
                Keys.ARROW_DOWN
            )

            browser.sleep(1)

            campo_interessado.send_keys(
                Keys.ENTER
            )

            browser.sleep(2)

            print(
                f"RESPONSÁVEL SELECIONADO: {responsavel}"
            )

        else:

            print(
                "RESPONSÁVEL VAZIO - "
                "INTERESSADOS PERMANECERÁ VAZIO"
            )

        radio_publico = browser.find_element(
            "id",
            "optPublico"
        )

        browser.execute_script(
            "arguments[0].click();",
            radio_publico
        )

        browser.sleep(1)

        botao_salvar = browser.find_element(
            "id",
            "btnSalvar"
        )

        browser.execute_script(
            "arguments[0].click();",
            botao_salvar
        )

        browser.sleep(5)

        browser.switch_to.default_content()

        return numero

    except Exception as erro:

        print(
            f"ERRO: {erro}"
        )

        return None

def listar_ids_gop(browser):
    browser.switch_to.default_content()
    browser.switch_to.frame(
        browser.find_element(By.ID, "ifrArvore")
    )

    ids = set()

    for link in browser.find_elements(By.TAG_NAME, "a"):
        texto = link.text.strip()

        if "CEHAB - DISPONIBILIDADE FINANCEIRA - GOP" in texto.upper():
            numero = re.search(r"(\d{8})\s*$", texto)

            if numero:
                ids.add(numero.group(1))

    browser.switch_to.default_content()
    return ids


def capturar_id_documento(browser, ids_anteriores):
    try:
        ids_novos = listar_ids_gop(browser) - ids_anteriores

        if len(ids_novos) != 1:
            print(
                "NÃO FOI POSSÍVEL IDENTIFICAR UM ÚNICO "
                f"DOCUMENTO GOP NOVO: {ids_novos}"
            )
            return None

        id_documento = ids_novos.pop()

        browser.switch_to.frame(
            browser.find_element(By.ID, "ifrArvore")
        )

        for link in browser.find_elements(By.TAG_NAME, "a"):
            texto = link.text.strip()

            if (
                "CEHAB - DISPONIBILIDADE FINANCEIRA - GOP" in texto.upper()
                and re.search(rf"{id_documento}\s*$", texto)
            ):
                browser.execute_script("arguments[0].click();", link)
                browser.sleep(4)
                browser.switch_to.default_content()

                print(f"ID DO DOCUMENTO NOVO: {id_documento}")
                return id_documento

        browser.switch_to.default_content()
        return None

    except Exception as erro:
        browser.switch_to.default_content()
        print(f"ERRO AO CAPTURAR ID: {erro}")
        return None


def abrir_editar_conteudo(browser):

    try:

        def procurar_botao_em_frames(nivel=0, caminho="raiz", diagnostico=False):

            # O SEI pode renderizar o comando como img, a, button ou input.
            candidatos = browser.find_elements(
                By.XPATH,
                "//*[@title or @alt or self::button or self::a]"
            )

            for elemento in candidatos:

                try:
                    descricao = " ".join([
                        elemento.get_attribute("title") or "",
                        elemento.get_attribute("alt") or "",
                        elemento.text or ""
                    ]).strip().lower()

                    if "editar conteúdo" in descricao or "editar conteudo" in descricao:

                        print(
                            f"BOTÃO EDITAR CONTEÚDO ENCONTRADO EM: "
                            f"{caminho}"
                        )

                        browser.execute_script(
                            "arguments[0].click();",
                            elemento
                        )

                        return True

                except Exception:
                    continue

            if nivel >= 6:
                return False

            frames = browser.find_elements(
                By.TAG_NAME,
                "iframe"
            )

            if diagnostico:
                print(
                    f"IFRAMES EM {caminho}: {len(frames)}"
                )

            for indice in range(len(frames)):

                try:
                    # Recarrega a lista para evitar referência obsoleta.
                    frames_atuais = browser.find_elements(
                        By.TAG_NAME,
                        "iframe"
                    )

                    if indice >= len(frames_atuais):
                        break

                    frame = frames_atuais[indice]
                    frame_id = frame.get_attribute("id") or "sem-id"
                    frame_nome = frame.get_attribute("name") or "sem-name"
                    novo_caminho = (
                        f"{caminho} > iframe[{indice}] "
                        f"id={frame_id} name={frame_nome}"
                    )

                    if diagnostico:
                        print(f"ANALISANDO {novo_caminho}")

                    browser.switch_to.frame(frame)

                    if procurar_botao_em_frames(
                        nivel + 1,
                        novo_caminho,
                        diagnostico
                    ):
                        return True

                    browser.switch_to.parent_frame()

                except Exception as erro_frame:
                    if diagnostico:
                        print(
                            f"NÃO FOI POSSÍVEL ANALISAR "
                            f"{caminho} > iframe[{indice}]: {erro_frame}"
                        )

                    browser.switch_to.default_content()
                    return False

            return False

        limite = time.time() + 30
        tentativa = 0

        while time.time() < limite:

            tentativa += 1

            for janela in browser.window_handles:

                browser.switch_to.window(janela)
                browser.switch_to.default_content()

                diagnostico = tentativa in (1, 5, 10)

                if procurar_botao_em_frames(
                    diagnostico=diagnostico
                ):
                    browser.sleep(5)
                    browser.switch_to.default_content()
                    print("EDITOR DE CONTEÚDO ABERTO")
                    return True

            browser.sleep(1)

        browser.switch_to.default_content()
        print(
            "BOTÃO EDITAR CONTEÚDO NÃO FOI ENCONTRADO "
            "EM NENHUMA JANELA/IFRAME"
        )
        return False

    except Exception as erro:

        browser.switch_to.default_content()

        print(
            f"ERRO AO ABRIR EDITAR CONTEÚDO: {erro}"
        )

        return False

def editar_mensagem(browser,dados,documento,id_documento):

    try:

        todas_janelas = browser.window_handles

        browser.switch_to.window(
            todas_janelas[-1]
        )

        browser.sleep(3)

        numero_bm = str(
            dados["linha_completa"][13]
        ).strip()

        valor = str(
            dados["linha_completa"][14]
        ).strip()

        numero_sei = str(
            dados["numero_sei"]
        ).strip()

        fonte = str(
            dados["fonte"]
        ).strip().zfill(10)

        ficha_financeira = str(
            dados["ficha_financeira"]
        ).strip()

        resolucao = str(
            dados.get("resolucao", "")
        ).strip()

        numero_solicitacao = str(
            documento
        ).strip()

        numero_documento = str(
            id_documento
        ).strip()

        iframes = browser.find_elements(
            By.TAG_NAME,
            "iframe"
        )

        for frame in iframes:

            try:

                browser.switch_to.default_content()

                browser.switch_to.window(
                    todas_janelas[-1]
                )

                browser.switch_to.frame(
                    frame
                )

                html = browser.execute_script(
                    "return document.body.innerHTML;"
                )

                if (
                    "disponibilidade orçamentária"
                    not in html.lower()
                ):
                    continue

                novo_html = html
                novo_html = novo_html.replace(
                    "Processo nº",
                    f"Processo nº: {numero_sei}"
                )

                novo_html = novo_html.replace(
                    "Despacho:",
                    f"Despacho: {numero_documento}"
                )

                novo_html = novo_html.replace(
                    "@nome_destinatario@",
                    "GAC"
                )

                novo_html = novo_html.replace(
                    "XX (),",
                    f"{numero_solicitacao},"
                )

                novo_html = novo_html.replace(
                    "BM <b>XX</b>",
                    f"BM <b>{numero_bm}</b>"
                )

                valor_float = float(
                    valor.replace(".", "").replace(",", ".")
                )

                valor_extenso = num2words(
                    valor_float,
                    lang="pt_BR",
                    to="currency"
                )

                novo_html = novo_html.replace(
                    "R$ X.XXX,XX",
                    f"R$ {valor} ({valor_extenso})"
                )

                texto_fonte = ""

                if fonte:
                    texto_fonte = fonte

                if ficha_financeira:
                    if texto_fonte:
                        texto_fonte += f" ({ficha_financeira})"
                    else:
                        texto_fonte = ficha_financeira

                novo_html = novo_html.replace(
                    "XXXXXXXXXX",
                    texto_fonte
                )
                novo_html = novo_html.replace(
                    "(Tipo da Fonte Ex.: Tesouro do Estado)",
                    ""
                )
                novo_html = novo_html.replace(
                    " .",
                    "."
                )

                texto_gefin = f"""
                    <br>
                    <hr style="border:1px solid #777;">
                    <br>

                    <p><strong>À GEFIN,</strong></p>

                    <p>{resolucao.replace(chr(10), "<br>")}</p>

                    <br>
                    """

                novo_html = novo_html.replace(
                    "Atenciosamente,",
                    texto_gefin +
                    '<div style="text-align:center;">Atenciosamente,</div>'
                )
                
                novo_html = re.sub(
                    r'([^<>]+?)\s+registrado\(a\)\s+civilmente\s+como\s+[^<]+',
                    lambda m: f'<strong>{m.group(1).strip()}</strong>',
                    novo_html,
                    flags=re.IGNORECASE
                )

                browser.execute_script(
                    """
                    document.body.innerHTML = arguments[0];
                    """,
                    novo_html
                )

                browser.find_element(
                    By.TAG_NAME,
                    "body"
                ).click()

                browser.sleep(2)

                browser.switch_to.default_content()

                browser.switch_to.default_content()

                browser.switch_to.window(
                    todas_janelas[-1]
                )

                browser.switch_to.frame(
                    frame
                )

                body = browser.find_element(
                    By.TAG_NAME,
                    "body"
                )

                body.click()

                browser.sleep(1)

                browser.execute_script(f"""
                var numero = "{numero_solicitacao}";
                var body = document.body;

                function localizar(node) {{

                    if(node.nodeType === 3) {{

                        var pos = node.textContent.indexOf(numero);

                        if(pos >= 0) {{

                            var range = document.createRange();

                            range.setStart(node, pos);
                            range.setEnd(node, pos + numero.length);

                            var sel = window.getSelection();

                            sel.removeAllRanges();
                            sel.addRange(range);

                            return true;
                        }}
                    }}

                    for(var i=0;i<node.childNodes.length;i++) {{

                        if(localizar(node.childNodes[i]))
                            return true;
                    }}

                    return false;
                }}

                localizar(body);
                """)

                browser.sleep(2)

                browser.switch_to.default_content()

                botao_link = browser.find_element(
                    By.XPATH,
                    '//*[@id="cke_119"]/span[1]'
                )

                browser.execute_script(
                    "arguments[0].click();",
                    botao_link
                )

                browser.sleep(2)

                campo_protocolo = WebDriverWait(
                    browser,
                    20
                ).until(
                    EC.visibility_of_element_located(
                        (
                            By.XPATH,
                            "//*[contains(@id,'textInput')]"
                        )
                    )
                )

                campo_protocolo.clear()

                campo_protocolo.send_keys(
                    numero_solicitacao
                )

                browser.sleep(1)

                ok = WebDriverWait(
                    browser,
                    20
                ).until(
                    EC.element_to_be_clickable(
                        (
                            By.XPATH,
                            "//*[contains(@id,'label') and normalize-space()='OK']"
                        )
                    )
                )

                browser.execute_script(
                    "arguments[0].click();",
                    ok
                )

                browser.sleep(2)

                browser.sleep(2)

                salvar = browser.find_element(
                    By.XPATH,
                    '//*[@id="cke_83_label"]'
                )

                browser.execute_script(
                    "arguments[0].click();",
                    salvar
                )

                browser.sleep(5)

                browser.close()

                janelas_restantes = browser.window_handles

                if janelas_restantes:
                    browser.switch_to.window(janelas_restantes[-1])
                    browser.switch_to.default_content()

                return True

            except UnexpectedAlertPresentException:

                try:
                    alert = browser.switch_to.alert

                    print(f"ALERTA: {alert.text}")

                    alert.accept()

                except:
                    pass

                browser.switch_to.default_content()

                return False

        print(
            "EDITOR NÃO ENCONTRADO"
        )

        return False

    except Exception as erro:

        print(
            f"ERRO EDITAR MENSAGEM: {erro}"
        )

        return False

def verificar_gop_existente(browser):

    try:

        browser.switch_to.default_content()

        iframes = browser.find_elements(
            "tag name",
            "iframe"
        )

        browser.switch_to.frame(
            iframes[0]
        )

        links = browser.find_elements(
            By.TAG_NAME,
            "a"
        )

        documentos = []

        for link in links:

            texto = link.text.strip()

            if texto:
                documentos.append((texto, link))

        indice_ultima_solicitacao = None
        texto_ultima_solicitacao = None

        for indice, (texto, _link) in enumerate(documentos):

            if (
                "CEHAB - SOLICITAÇÃO DE DISPONIBILIDADE FINANCEIRA"
                in texto.upper()
            ):

                indice_ultima_solicitacao = indice
                texto_ultima_solicitacao = texto

        if indice_ultima_solicitacao is None:

            print("NENHUMA SOLICITAÇÃO ENCONTRADA")

            browser.switch_to.default_content()

            return None

        print(
            f"ÚLTIMA SOLICITAÇÃO: "
            f"{texto_ultima_solicitacao}"
        )

        documentos_depois = documentos[
            indice_ultima_solicitacao + 1:
        ]

        numero_solicitacao = re.search(
            r"(\d{8})",
            texto_ultima_solicitacao
        )

        for texto, link in documentos_depois:

            if (
                "CEHAB - DISPONIBILIDADE FINANCEIRA - GOP"
                in texto.upper()
            ):

                print(
                    f"GOP ENCONTRADA APÓS A ÚLTIMA SOLICITAÇÃO: "
                    f"{texto}"
                )

                numero_documento = re.search(
                    r"(\d{8})$",
                    texto
                )

                if not numero_solicitacao or not numero_documento:
                    browser.switch_to.default_content()
                    return None

                browser.execute_script(
                    "arguments[0].click();",
                    link
                )

                browser.sleep(4)

                browser.switch_to.default_content()

                return {
                    "documento": numero_solicitacao.group(1),
                    "id_documento": numero_documento.group(1)
                }

        print(
            "ÚLTIMA SOLICITAÇÃO AINDA NÃO POSSUI "
            "DOCUMENTO DE DISPONIBILIDADE"
        )

        browser.switch_to.default_content()

        return None

    except Exception as erro:

        browser.switch_to.default_content()

        print(
            f"ERRO VERIFICAR GOP: {erro}"
        )

        return None

def formatar_responsavel(responsavel):

    responsavel = str(responsavel or "").strip()

    if not responsavel:
        return ""

    if responsavel.lower() == "julio.galvao":
        cargo = "Gerente de Orçamento"
    else:
        cargo = "Assessor Administrativo"

    return f"{responsavel} {cargo}"


def voltar_recebidos(browser):

    try:

        # Procura a janela do SEI que contém o botão
        for janela in browser.window_handles:

            browser.switch_to.window(janela)
            browser.switch_to.default_content()

            try:

                botao = WebDriverWait(
                    browser,
                    10
                ).until(
                    EC.element_to_be_clickable(
                        (
                            By.XPATH,
                            '//*[@id="lnkControleProcessos"]'
                        )
                    )
                )

                browser.execute_script(
                    "arguments[0].click();",
                    botao
                )

                browser.sleep(5)

                print("RETORNOU PARA CONTROLE DE PROCESSOS")

                return True

            except Exception:
                continue

        print("BOTÃO CONTROLE DE PROCESSOS NÃO ENCONTRADO")
        return False

    except Exception as erro:

        print(
            f"ERRO AO VOLTAR PARA CONTROLE DE PROCESSOS: {erro}"
        )

        return False

def capturar_link_processo(browser):

    try:

        url = browser.current_url

        parametros = parse_qs(
            urlparse(url).query
        )

        id_procedimento = parametros.get(
            "id_protocolo",
            [None]
        )[0]

        if not id_procedimento:
            return None

        link = (
            "https://sei.pe.gov.br/sei/controlador.php"
            "?acao=procedimento_trabalhar"
            f"&id_procedimento={id_procedimento}"
        )

        return link

    except Exception as erro:

        print(f"ERRO AO CAPTURAR LINK: {erro}")

        return None

if __name__ == "__main__":

    print("Iniciando...")
    data_hoje = datetime.now().strftime("%d/%m/%Y")
    print(f"RELATÓRIO ROBÔ DESPACHO ({data_hoje})")


    print("========================================================================================")
    
    while True:

        try:

            browser = iniciar_robo()

            lista = obter_aguardando_sei()

            print()
            print("SEIS EM MONITORAMENTO:")
            print()

            for item in lista:

                print(
                    f"[{item['linha_planilha']}] "
                    f"{item['numero_sei']}"
                )

            print()
            print(
                f"TOTAL: {len(lista)} PROCESSOS"
            )

            print(
                "=" * 88
            )

            if not lista:

                print(
                    "NENHUM AGUARDANDO SEI"
                )

                browser.quit()

                time.sleep(10)

                continue

            for dados in lista:

                print("=" * 88)

                print(
                    f"VERIFICANDO "
                    f"{dados['numero_sei']}"
                )

                encontrado = verificar_recebidos(
                    browser,
                    dados["numero_sei"]
                )

                if not encontrado:

                    continue

                solicitacoes = listar_solicitacoes(browser)
                solicitacao = selecionar_solicitacao(dados, solicitacoes, lista)

                if solicitacao is None:
                    voltar_recebidos(browser)
                    continue

                ids_anteriores = listar_ids_gop(browser)

                documento = criar_documento(browser, dados, solicitacao)

                if not documento:
                    voltar_recebidos(browser)
                    continue

                id_documento = capturar_id_documento(browser, ids_anteriores)

                if not id_documento:
                    print("ID DO DOCUMENTO NÃO ENCONTRADO")
                    voltar_recebidos(browser)
                    continue

                # Abre o editor do documento criado
                editor_aberto = abrir_editar_conteudo(browser)

                if not editor_aberto:

                    print(
                        f"NÃO FOI POSSÍVEL ABRIR O EDITOR DO "
                        f"DOCUMENTO {id_documento}"
                    )

                    voltar_recebidos(browser)

                    continue


                sucesso = editar_mensagem(
                    browser,
                    dados,
                    documento,
                    id_documento
                )

                if sucesso:

                    atualizar_planilha_enviado(
                        dados["linha_planilha"]
                    )

                else:

                    print(
                        f"ERRO AO EDITAR {dados['numero_sei']}"
                    )

                voltar_recebidos(browser)

                print("=" * 88)

                time.sleep(30)

        except Exception as erro:

            print(
                f"ERRO GERAL: {erro}"
            )

            try:
                browser.quit()
            except:
                pass

            time.sleep(10)
