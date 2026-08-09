import os
import uuid
from datetime import date
from urllib.parse import quote

import requests
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, send_from_directory

from database import get_db, init_db

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FOTOS_DIR = os.path.join(BASE_DIR, "static", "fotos")
EXTENSOES_PERMITIDAS = {"jpg", "jpeg", "png", "webp"}
FIPE_BASE = "https://fipe.parallelum.com.br/api/v2/cars"

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "troque-esta-chave-em-producao")
app.config["MAX_CONTENT_LENGTH"] = 20 * 1024 * 1024  # 20MB por upload

os.makedirs(FOTOS_DIR, exist_ok=True)
init_db()


def extensao_valida(nome_arquivo):
    return "." in nome_arquivo and nome_arquivo.rsplit(".", 1)[1].lower() in EXTENSOES_PERMITIDAS


def buscar_veiculo(veiculo_id):
    conn = get_db()
    veiculo = conn.execute("SELECT * FROM veiculos WHERE id = ?", (veiculo_id,)).fetchone()
    fotos = conn.execute(
        "SELECT * FROM fotos WHERE veiculo_id = ? ORDER BY id", (veiculo_id,)
    ).fetchall()
    conn.close()
    return veiculo, fotos


# ---------------------------------------------------------------------------
# Páginas
# ---------------------------------------------------------------------------

@app.route("/")
def index():
    filtro = request.args.get("filtro", "estoque")  # estoque | consignados | vendidos | todos
    busca = request.args.get("q", "").strip()

    sql = "SELECT * FROM veiculos WHERE 1=1"
    params = []

    if filtro == "estoque":
        sql += " AND status = 'disponivel'"
    elif filtro == "consignados":
        sql += " AND status = 'disponivel' AND tipo = 'consignado'"
    elif filtro == "vendidos":
        sql += " AND status = 'vendido'"
    # filtro == 'todos' -> sem filtro extra

    if busca:
        sql += " AND (placa LIKE ? OR marca LIKE ? OR modelo LIKE ?)"
        termo = f"%{busca}%"
        params += [termo, termo, termo]

    sql += " ORDER BY criado_em DESC"

    conn = get_db()
    veiculos = conn.execute(sql, params).fetchall()

    contagem = conn.execute(
        """
        SELECT
            SUM(CASE WHEN status = 'disponivel' THEN 1 ELSE 0 END) AS estoque,
            SUM(CASE WHEN status = 'disponivel' AND tipo = 'consignado' THEN 1 ELSE 0 END) AS consignados,
            SUM(CASE WHEN status = 'vendido' THEN 1 ELSE 0 END) AS vendidos,
            COUNT(*) AS todos
        FROM veiculos
        """
    ).fetchone()

    fotos_capa = {}
    for v in veiculos:
        foto = conn.execute(
            "SELECT arquivo FROM fotos WHERE veiculo_id = ? ORDER BY id LIMIT 1", (v["id"],)
        ).fetchone()
        if foto:
            fotos_capa[v["id"]] = foto["arquivo"]
    conn.close()

    return render_template(
        "index.html",
        veiculos=veiculos,
        contagem=contagem,
        filtro=filtro,
        busca=busca,
        fotos_capa=fotos_capa,
    )


@app.route("/novo", methods=["GET", "POST"])
def novo_veiculo():
    if request.method == "POST":
        dados = request.form
        conn = get_db()
        cur = conn.execute(
            """
            INSERT INTO veiculos (
                placa, renavam, marca, modelo, ano_fabricacao, ano_modelo, cor,
                tipo, consignado_nome, consignado_contato, consignado_valor_repasse,
                valor_anuncio, data_entrada, observacoes,
                fipe_marca_codigo, fipe_modelo_codigo, fipe_ano_codigo,
                valor_fipe, valor_fipe_mes_referencia
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """,
            (
                dados.get("placa", "").upper().strip(),
                dados.get("renavam", "").strip(),
                dados.get("marca", "").strip(),
                dados.get("modelo", "").strip(),
                dados.get("ano_fabricacao") or None,
                dados.get("ano_modelo") or None,
                dados.get("cor", "").strip(),
                dados.get("tipo", "proprio"),
                dados.get("consignado_nome", "").strip(),
                dados.get("consignado_contato", "").strip(),
                dados.get("consignado_valor_repasse") or None,
                dados.get("valor_anuncio") or None,
                dados.get("data_entrada") or date.today().isoformat(),
                dados.get("observacoes", "").strip(),
                dados.get("fipe_marca_codigo") or None,
                dados.get("fipe_modelo_codigo") or None,
                dados.get("fipe_ano_codigo") or None,
                dados.get("valor_fipe") or None,
                dados.get("valor_fipe_mes_referencia") or None,
            ),
        )
        veiculo_id = cur.lastrowid
        conn.commit()
        conn.close()
        flash("Veículo cadastrado com sucesso.", "sucesso")
        return redirect(url_for("ver_veiculo", veiculo_id=veiculo_id))

    return render_template("form_veiculo.html", veiculo=None)


@app.route("/veiculo/<int:veiculo_id>")
def ver_veiculo(veiculo_id):
    veiculo, fotos = buscar_veiculo(veiculo_id)
    if veiculo is None:
        flash("Veículo não encontrado.", "erro")
        return redirect(url_for("index"))
    return render_template("veiculo.html", veiculo=veiculo, fotos=fotos)


@app.route("/pesquisa-fipe")
def pesquisa_fipe():
    return render_template("pesquisa_fipe.html")


# ---------------------------------------------------------------------------
# Catálogo público (para compartilhar com clientes)
# ---------------------------------------------------------------------------

WHATSAPP_LOJAS = [
    {"nome": "KF Multimarcas – Loja 1", "numero": "5513981455229"},
    {"nome": "KF Avenida – Loja 2", "numero": "5513996683982"},
]


@app.route("/catalogo")
def catalogo_publico():
    conn = get_db()
    veiculos = conn.execute(
        "SELECT id, marca, modelo, ano_fabricacao, ano_modelo, valor_anuncio FROM veiculos "
        "WHERE status = 'disponivel' ORDER BY criado_em DESC"
    ).fetchall()
    fotos_capa = {}
    for v in veiculos:
        foto = conn.execute(
            "SELECT arquivo FROM fotos WHERE veiculo_id = ? ORDER BY id LIMIT 1", (v["id"],)
        ).fetchone()
        if foto:
            fotos_capa[v["id"]] = foto["arquivo"]
    conn.close()
    return render_template("catalogo.html", veiculos=veiculos, fotos_capa=fotos_capa)


@app.route("/catalogo/<int:veiculo_id>")
def catalogo_veiculo(veiculo_id):
    conn = get_db()
    veiculo = conn.execute(
        "SELECT id, marca, modelo, ano_fabricacao, ano_modelo, valor_anuncio FROM veiculos "
        "WHERE id = ? AND status = 'disponivel'", (veiculo_id,)
    ).fetchone()
    fotos = []
    if veiculo:
        fotos = conn.execute(
            "SELECT * FROM fotos WHERE veiculo_id = ? ORDER BY id", (veiculo_id,)
        ).fetchall()
    conn.close()
    if veiculo is None:
        flash("Este veículo não está mais disponível.", "erro")
        return redirect(url_for("catalogo_publico"))

    mensagem = f"Olá! Tenho interesse no {veiculo['marca']} {veiculo['modelo']} ({veiculo['ano_modelo'] or veiculo['ano_fabricacao'] or ''}) que vi no catálogo."
    links_whatsapp = [
        {"nome": loja["nome"], "link": f"https://wa.me/{loja['numero']}?text={quote(mensagem)}"}
        for loja in WHATSAPP_LOJAS
    ]
    return render_template("catalogo_veiculo.html", veiculo=veiculo, fotos=fotos, links_whatsapp=links_whatsapp)


@app.route("/veiculo/<int:veiculo_id>/editar", methods=["GET", "POST"])
def editar_veiculo(veiculo_id):
    veiculo, _ = buscar_veiculo(veiculo_id)
    if veiculo is None:
        flash("Veículo não encontrado.", "erro")
        return redirect(url_for("index"))

    if request.method == "POST":
        dados = request.form
        conn = get_db()
        conn.execute(
            """
            UPDATE veiculos SET
                placa=?, renavam=?, marca=?, modelo=?, ano_fabricacao=?, ano_modelo=?, cor=?,
                tipo=?, consignado_nome=?, consignado_contato=?, consignado_valor_repasse=?,
                valor_anuncio=?, observacoes=?
            WHERE id=?
            """,
            (
                dados.get("placa", "").upper().strip(),
                dados.get("renavam", "").strip(),
                dados.get("marca", "").strip(),
                dados.get("modelo", "").strip(),
                dados.get("ano_fabricacao") or None,
                dados.get("ano_modelo") or None,
                dados.get("cor", "").strip(),
                dados.get("tipo", "proprio"),
                dados.get("consignado_nome", "").strip(),
                dados.get("consignado_contato", "").strip(),
                dados.get("consignado_valor_repasse") or None,
                dados.get("valor_anuncio") or None,
                dados.get("observacoes", "").strip(),
                veiculo_id,
            ),
        )
        conn.commit()
        conn.close()
        flash("Dados atualizados.", "sucesso")
        return redirect(url_for("ver_veiculo", veiculo_id=veiculo_id))

    return render_template("form_veiculo.html", veiculo=veiculo)


@app.route("/veiculo/<int:veiculo_id>/atualizar-fipe", methods=["POST"])
def atualizar_fipe(veiculo_id):
    dados = request.form
    conn = get_db()
    conn.execute(
        """
        UPDATE veiculos SET
            valor_fipe=?, valor_fipe_mes_referencia=?,
            fipe_marca_codigo=?, fipe_modelo_codigo=?, fipe_ano_codigo=?
        WHERE id=?
        """,
        (
            dados.get("valor_fipe") or None,
            dados.get("valor_fipe_mes_referencia") or None,
            dados.get("fipe_marca_codigo") or None,
            dados.get("fipe_modelo_codigo") or None,
            dados.get("fipe_ano_codigo") or None,
            veiculo_id,
        ),
    )
    conn.commit()
    conn.close()
    flash("Valor FIPE atualizado.", "sucesso")
    return redirect(url_for("ver_veiculo", veiculo_id=veiculo_id))


@app.route("/veiculo/<int:veiculo_id>/saida", methods=["POST"])
def registrar_saida(veiculo_id):
    dados = request.form
    conn = get_db()
    conn.execute(
        """
        UPDATE veiculos SET
            status='vendido', valor_venda=?, comprador_nome=?, data_saida=?
        WHERE id=?
        """,
        (
            dados.get("valor_venda") or None,
            dados.get("comprador_nome", "").strip(),
            dados.get("data_saida") or date.today().isoformat(),
            veiculo_id,
        ),
    )
    conn.commit()
    conn.close()
    flash("Saída registrada. Veículo marcado como vendido.", "sucesso")
    return redirect(url_for("ver_veiculo", veiculo_id=veiculo_id))


@app.route("/veiculo/<int:veiculo_id>/reabrir", methods=["POST"])
def reabrir_veiculo(veiculo_id):
    conn = get_db()
    conn.execute(
        "UPDATE veiculos SET status='disponivel', valor_venda=NULL, comprador_nome=NULL, data_saida=NULL WHERE id=?",
        (veiculo_id,),
    )
    conn.commit()
    conn.close()
    flash("Veículo voltou para o estoque.", "sucesso")
    return redirect(url_for("ver_veiculo", veiculo_id=veiculo_id))


@app.route("/veiculo/<int:veiculo_id>/excluir", methods=["POST"])
def excluir_veiculo(veiculo_id):
    conn = get_db()
    conn.execute("DELETE FROM veiculos WHERE id=?", (veiculo_id,))
    conn.commit()
    conn.close()
    pasta = os.path.join(FOTOS_DIR, str(veiculo_id))
    if os.path.isdir(pasta):
        for f in os.listdir(pasta):
            os.remove(os.path.join(pasta, f))
        os.rmdir(pasta)
    flash("Veículo excluído.", "sucesso")
    return redirect(url_for("index"))


# ---------------------------------------------------------------------------
# Fotos
# ---------------------------------------------------------------------------

@app.route("/veiculo/<int:veiculo_id>/fotos", methods=["POST"])
def upload_fotos(veiculo_id):
    arquivos = request.files.getlist("fotos")
    pasta = os.path.join(FOTOS_DIR, str(veiculo_id))
    os.makedirs(pasta, exist_ok=True)

    conn = get_db()
    salvas = 0
    for arquivo in arquivos:
        if arquivo and arquivo.filename and extensao_valida(arquivo.filename):
            ext = arquivo.filename.rsplit(".", 1)[1].lower()
            nome_final = f"{uuid.uuid4().hex}.{ext}"
            arquivo.save(os.path.join(pasta, nome_final))
            conn.execute(
                "INSERT INTO fotos (veiculo_id, arquivo) VALUES (?, ?)",
                (veiculo_id, nome_final),
            )
            salvas += 1
    conn.commit()
    conn.close()

    if salvas:
        flash(f"{salvas} foto(s) adicionada(s).", "sucesso")
    else:
        flash("Nenhuma foto válida enviada (use jpg, png ou webp).", "erro")
    return redirect(url_for("ver_veiculo", veiculo_id=veiculo_id))


@app.route("/veiculo/<int:veiculo_id>/fotos/<int:foto_id>/excluir", methods=["POST"])
def excluir_foto(veiculo_id, foto_id):
    conn = get_db()
    foto = conn.execute("SELECT * FROM fotos WHERE id=? AND veiculo_id=?", (foto_id, veiculo_id)).fetchone()
    if foto:
        caminho = os.path.join(FOTOS_DIR, str(veiculo_id), foto["arquivo"])
        if os.path.exists(caminho):
            os.remove(caminho)
        conn.execute("DELETE FROM fotos WHERE id=?", (foto_id,))
        conn.commit()
    conn.close()
    return redirect(url_for("ver_veiculo", veiculo_id=veiculo_id))


@app.route("/fotos/<int:veiculo_id>/<path:nome_arquivo>")
def servir_foto(veiculo_id, nome_arquivo):
    return send_from_directory(os.path.join(FOTOS_DIR, str(veiculo_id)), nome_arquivo)


# ---------------------------------------------------------------------------
# Proxy da API da tabela FIPE (evita CORS e centraliza chamadas)
# ---------------------------------------------------------------------------

def _proxy_fipe(caminho):
    try:
        resp = requests.get(f"{FIPE_BASE}/{caminho}", timeout=10)
        return jsonify(resp.json()), resp.status_code
    except requests.exceptions.RequestException:
        return jsonify({"erro": "Não foi possível consultar a FIPE agora. Verifique a internet e tente de novo."}), 502
    except ValueError:
        return jsonify({"erro": "A FIPE retornou uma resposta inesperada. Tente novamente em instantes."}), 502


@app.route("/api/fipe/marcas")
def fipe_marcas():
    return _proxy_fipe("brands")


@app.route("/api/fipe/modelos/<marca_id>")
def fipe_modelos(marca_id):
    return _proxy_fipe(f"brands/{marca_id}/models")


@app.route("/api/fipe/anos/<marca_id>/<modelo_id>")
def fipe_anos(marca_id, modelo_id):
    return _proxy_fipe(f"brands/{marca_id}/models/{modelo_id}/years")


@app.route("/api/fipe/valor/<marca_id>/<modelo_id>/<ano_id>")
def fipe_valor(marca_id, modelo_id, ano_id):
    return _proxy_fipe(f"brands/{marca_id}/models/{modelo_id}/years/{ano_id}")


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    debug = os.environ.get("FLASK_DEBUG", "1") == "1"
    app.run(host="0.0.0.0", port=port, debug=debug)
