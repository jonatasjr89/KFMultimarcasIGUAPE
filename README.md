# Sistema de Estoque de Veículos KF Multimarcas

Sistema web para controlar entrada/saída de veículos (próprios e consignados),
organizar fotos por veículo e consultar a Tabela FIPE automaticamente.

## O que o sistema faz

- Cadastro de veículos com marca, modelo, ano, placa, renavam, cor
- Marcação de veículo como **próprio da loja** ou **consignado** (com dono e valor de repasse)
- Consulta automática da **Tabela FIPE** (marca → modelo → ano → valor)
- Upload de várias fotos por veículo, organizadas automaticamente numa pasta por veículo
- Controle de **entrada** (data de entrada) e **saída** (venda: valor, comprador, data)
- Painel com abas: Em estoque / Consignados / Vendidos / Todos
- Busca por placa, marca ou modelo

## Rodando no seu computador (para testar)

Você precisa ter o **Python** instalado (baixe em python.org, marcando a opção
"Add Python to PATH" durante a instalação no Windows).

Depois, abra o terminal (ou Prompt de Comando) na pasta do projeto e rode:

```
pip install -r requirements.txt
python app.py
```

Abra o navegador em `http://localhost:5000`.

Isso é só para testar no seu próprio computador. Para os computadores da loja
acessarem (mesmo estando em redes Wi-Fi diferentes), o sistema precisa estar
publicado na internet — veja abaixo.

## Publicando na internet (para todos os computadores da loja acessarem)

Como os computadores da loja não estão na mesma rede, a forma mais simples é
publicar o sistema num serviço de hospedagem. Recomendo o **Render**
(tem plano gratuito, suficiente para começar):

1. Crie uma conta em https://render.com (pode usar login do GitHub)
2. Suba esta pasta para um repositório no GitHub (crie uma conta gratuita em
   https://github.com se ainda não tiver)
3. No Render, clique em "New +" → "Web Service", conecte o repositório
4. Configure:
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `gunicorn app:app`
5. Nas variáveis de ambiente (Environment), adicione:
   - `SECRET_KEY` = uma frase aleatória qualquer, só sua
   - `FLASK_DEBUG` = `0`
6. Clique em "Create Web Service" e aguarde a publicação

O Render vai te dar um endereço tipo `https://sua-loja.onrender.com` —
esse é o link que você acessa de qualquer computador ou celular, em
qualquer rede, para usar o sistema.

**Atenção sobre fotos e banco de dados no plano gratuito do Render:** no
plano gratuito, os arquivos (fotos e banco de dados SQLite) podem ser
apagados quando o serviço reinicia. Para manter os dados de forma
permanente, adicione um "Persistent Disk" (funcionalidade paga, bem barata)
apontando para a pasta `static/fotos` e `instance`. Se preferir, me avise
que te ajudo a configurar isso passo a passo quando chegar a hora, ou a
migrar as fotos para um serviço de armazenamento em nuvem (ex: Cloudinary,
que tem plano gratuito feito sob medida para fotos).

## Estrutura do projeto

```
app.py              -> rotas e lógica do sistema
database.py         -> criação e conexão do banco de dados (SQLite)
templates/           -> páginas HTML
static/css/          -> estilo visual
static/fotos/<id>/   -> fotos de cada veículo, em pasta separada por veículo
instance/estoque.db  -> banco de dados (criado automaticamente na 1ª execução)
```

## Sobre a consulta FIPE

A busca é feita por **marca → modelo → ano**, usando a API pública e gratuita
da FIPE (fipe.parallelum.com.br). Não é possível buscar diretamente por placa
— a tabela FIPE é uma referência de mercado por modelo/ano, não por veículo
específico. Se no futuro você quiser consulta automática por placa, é
possível integrar um serviço pago de consulta veicular; posso te ajudar
com isso depois.
