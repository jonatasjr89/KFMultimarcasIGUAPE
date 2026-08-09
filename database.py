import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "instance", "estoque.db")


def get_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    conn = get_db()
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS veiculos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            placa TEXT,
            renavam TEXT,
            marca TEXT NOT NULL,
            modelo TEXT NOT NULL,
            ano_fabricacao INTEGER,
            ano_modelo INTEGER,
            cor TEXT,
            tipo TEXT NOT NULL DEFAULT 'proprio',          -- proprio | consignado
            consignado_nome TEXT,
            consignado_contato TEXT,
            consignado_valor_repasse REAL,
            status TEXT NOT NULL DEFAULT 'disponivel',      -- disponivel | vendido
            valor_fipe REAL,
            valor_fipe_mes_referencia TEXT,
            valor_anuncio REAL,
            valor_venda REAL,
            comprador_nome TEXT,
            data_entrada TEXT,
            data_saida TEXT,
            observacoes TEXT,
            fipe_marca_codigo TEXT,
            fipe_modelo_codigo TEXT,
            fipe_ano_codigo TEXT,
            criado_em TEXT DEFAULT (datetime('now', 'localtime'))
        );

        CREATE TABLE IF NOT EXISTS fotos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            veiculo_id INTEGER NOT NULL REFERENCES veiculos(id) ON DELETE CASCADE,
            arquivo TEXT NOT NULL,
            criado_em TEXT DEFAULT (datetime('now', 'localtime'))
        );
        """
    )
    conn.commit()
    conn.close()
