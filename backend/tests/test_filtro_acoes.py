"""
TDD - testes de filtros de busca de acoes (GET /api/acoes).

Padrao de fixtures:
  - app: Flask app com SQLite in-memory, app_context ja ativo ao fazer yield.
  - client: test client derivado do app.
  - organizadora: User(role='organizadora') persistido; usar .id como primitivo.

Setup de dados: sempre usar `with app.app_context()` e retornar IDs (str/int),
nunca objetos ORM fora do contexto que os criou.

NOTA: o teste de debounce (300ms) e responsabilidade do frontend (JS).
O backend garante resposta <=500ms com indices adequados.
"""

import time
import uuid
from datetime import datetime, timedelta, timezone

import pytest

from mamobi.models import Event, EventCategory, User, db


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_category(app, name="Saude", icon="heart", color="#FF0000") -> int:
    """Cria uma EventCategory e retorna seu id (int)."""
    with app.app_context():
        cat = EventCategory(name=name, icon=icon, color=color)
        db.session.add(cat)
        db.session.commit()
        return cat.id


def _make_event(app, cat_id: int, organizer_id: str, **overrides) -> str:
    """Cria um Event e retorna seu id (str)."""
    defaults = dict(
        id=str(uuid.uuid4()),
        title="Evento Padrao",
        description="Descricao padrao do evento",
        event_datetime=datetime.now(timezone.utc) + timedelta(days=7),
        location_name="Praca Central",
        category_id=cat_id,
        organizer_id=organizer_id,
        status="scheduled",
    )
    defaults.update(overrides)
    with app.app_context():
        ev = Event(**defaults)
        db.session.add(ev)
        db.session.commit()
        return ev.id


# ---------------------------------------------------------------------------
# Teste 1 - sem filtros retorna todos os eventos
# ---------------------------------------------------------------------------

def test_list_acoes_sem_filtros_retorna_todos(app, client, organizadora):
    cat_id = _make_category(app, name="Geral")
    _make_event(app, cat_id, organizadora.id, title="Evento A")
    _make_event(app, cat_id, organizadora.id, title="Evento B")

    resp = client.get("/api/acoes")

    assert resp.status_code == 200
    data = resp.get_json()
    assert "data" in data
    assert "total" in data
    assert data["total"] >= 2


# ---------------------------------------------------------------------------
# Teste 2 (TDD spec) - busca textual por titulo
# ---------------------------------------------------------------------------

def test_busca_textual_retorna_resultado_por_titulo(app, client, organizadora):
    cat_id = _make_category(app, name="Educacao")
    _make_event(app, cat_id, organizadora.id, title="Oficina de Horta Urbana")
    _make_event(app, cat_id, organizadora.id, title="Palestra de Saude Mental")

    resp = client.get("/api/acoes?q=horta")

    assert resp.status_code == 200
    data = resp.get_json()
    assert data["total"] >= 1
    titulos = [item["title"].lower() for item in data["data"]]
    assert all("horta" in t for t in titulos)


# ---------------------------------------------------------------------------
# Teste 3 (TDD spec) - busca textual por descricao
# ---------------------------------------------------------------------------

def test_busca_textual_retorna_resultado_por_descricao(app, client, organizadora):
    cat_id = _make_category(app, name="Meio Ambiente")
    _make_event(
        app, cat_id, organizadora.id,
        title="Evento Generico",
        description="Este evento trata de compostagem comunitaria",
    )
    _make_event(
        app, cat_id, organizadora.id,
        title="Outro Evento",
        description="Sem relacao com o tema buscado",
    )

    resp = client.get("/api/acoes?q=compostagem")

    assert resp.status_code == 200
    data = resp.get_json()
    assert data["total"] >= 1
    descricoes = [(item.get("description") or "").lower() for item in data["data"]]
    assert all("compostagem" in d for d in descricoes)


# ---------------------------------------------------------------------------
# Teste 4 (TDD spec) - filtro de categoria exclui outras categorias
# ---------------------------------------------------------------------------

def test_filtro_categoria_exclui_outras(app, client, organizadora):
    cat1_id = _make_category(app, name="Educacao2", color="#0000FF")
    cat2_id = _make_category(app, name="Esporte2", color="#00FF00")

    _make_event(app, cat1_id, organizadora.id, title="Aula de Leitura")
    _make_event(app, cat2_id, organizadora.id, title="Futebol Comunitario")

    resp = client.get(f"/api/acoes?categoria={cat1_id}")

    assert resp.status_code == 200
    data = resp.get_json()
    assert data["total"] >= 1
    assert all(item["category_id"] == cat1_id for item in data["data"])
    assert not any(item["category_id"] == cat2_id for item in data["data"])


# ---------------------------------------------------------------------------
# Teste 5 - filtro de periodo: de
# ---------------------------------------------------------------------------

def test_filtro_periodo_de(app, client, organizadora):
    agora = datetime.now(timezone.utc)
    cat_id = _make_category(app, name="Periodo1")
    _make_event(
        app, cat_id, organizadora.id,
        title="Evento Proximo",
        event_datetime=agora + timedelta(days=3),
    )
    _make_event(
        app, cat_id, organizadora.id,
        title="Evento Distante",
        event_datetime=agora + timedelta(days=30),
    )

    de = (agora + timedelta(days=20)).strftime("%Y-%m-%d")
    resp = client.get(f"/api/acoes?de={de}")

    assert resp.status_code == 200
    data = resp.get_json()
    titulos = [item["title"] for item in data["data"]]
    assert "Evento Distante" in titulos
    assert "Evento Proximo" not in titulos


# ---------------------------------------------------------------------------
# Teste 6 - filtro de periodo: ate
# ---------------------------------------------------------------------------

def test_filtro_periodo_ate(app, client, organizadora):
    agora = datetime.now(timezone.utc)
    cat_id = _make_category(app, name="Periodo2")
    _make_event(
        app, cat_id, organizadora.id,
        title="Evento Esta Semana",
        event_datetime=agora + timedelta(days=3),
    )
    _make_event(
        app, cat_id, organizadora.id,
        title="Evento Proximo Mes",
        event_datetime=agora + timedelta(days=35),
    )

    ate = (agora + timedelta(days=10)).strftime("%Y-%m-%d")
    resp = client.get(f"/api/acoes?ate={ate}")

    assert resp.status_code == 200
    data = resp.get_json()
    titulos = [item["title"] for item in data["data"]]
    assert "Evento Esta Semana" in titulos
    assert "Evento Proximo Mes" not in titulos


# ---------------------------------------------------------------------------
# Teste 7 - filtros combinados aplicam AND
# ---------------------------------------------------------------------------

def test_filtros_combinados_aplicam_and(app, client, organizadora):
    agora = datetime.now(timezone.utc)
    cat_id = _make_category(app, name="Cultura2", color="#FF00FF")
    outra_cat_id = _make_category(app, name="Outra", color="#AAAAAA")

    # Deve aparecer: titulo contem 'sarau', categoria correta, dentro do periodo
    _make_event(
        app, cat_id, organizadora.id,
        title="Sarau Cultural",
        event_datetime=agora + timedelta(days=5),
    )
    # Excluido pelo periodo (fora do ate)
    _make_event(
        app, cat_id, organizadora.id,
        title="Sarau Tardio",
        event_datetime=agora + timedelta(days=40),
    )
    # Excluido pela categoria
    _make_event(
        app, outra_cat_id, organizadora.id,
        title="Sarau Outra Categoria",
        event_datetime=agora + timedelta(days=5),
    )

    ate = (agora + timedelta(days=10)).strftime("%Y-%m-%d")
    resp = client.get(f"/api/acoes?q=sarau&categoria={cat_id}&ate={ate}")

    assert resp.status_code == 200
    data = resp.get_json()
    assert data["total"] == 1
    assert data["data"][0]["title"] == "Sarau Cultural"


# ---------------------------------------------------------------------------
# Teste 8 - limpar filtros restaura listagem completa
# ---------------------------------------------------------------------------

def test_limpar_filtros_restaura_listagem(app, client, organizadora):
    cat_id = _make_category(app, name="Limpar")
    _make_event(app, cat_id, organizadora.id, title="Acao Alpha Unica")
    _make_event(app, cat_id, organizadora.id, title="Acao Beta Diferente")

    total_filtrado = client.get("/api/acoes?q=alpha").get_json()["total"]
    total_limpo = client.get("/api/acoes").get_json()["total"]

    assert total_filtrado < total_limpo


# ---------------------------------------------------------------------------
# Teste 9 - filtro por responsavel
# ---------------------------------------------------------------------------

def test_filtro_responsavel(app, client, organizadora):
    cat_id = _make_category(app, name="Responsavel")

    # Segundo organizador criado diretamente
    with app.app_context():
        org2 = User(
            id=str(uuid.uuid4()),
            phone="+5511777770099",
            full_name="Segunda Organizadora",
            neighborhood="Grajaú",
            role="organizadora",
            is_active=True,
        )
        db.session.add(org2)
        db.session.commit()
        org2_id = org2.id

    _make_event(app, cat_id, organizadora.id, title="Evento da Primeira")
    _make_event(app, cat_id, org2_id, title="Evento da Segunda")

    resp = client.get(f"/api/acoes?responsavel={organizadora.id}")

    assert resp.status_code == 200
    data = resp.get_json()
    assert data["total"] >= 1
    assert all(item["organizer_id"] == organizadora.id for item in data["data"])
    assert not any(item["organizer_id"] == org2_id for item in data["data"])


# ---------------------------------------------------------------------------
# Teste 10 - paginacao
# ---------------------------------------------------------------------------

def test_paginacao_retorna_subset(app, client, organizadora):
    cat_id = _make_category(app, name="Paginacao")
    for i in range(5):
        _make_event(app, cat_id, organizadora.id, title=f"Evento Pag {i}")

    resp = client.get("/api/acoes?page=1&per_page=2")

    assert resp.status_code == 200
    data = resp.get_json()
    assert len(data["data"]) == 2
    assert data["total"] >= 5
    assert data["page"] == 1
    assert data["per_page"] == 2


# ---------------------------------------------------------------------------
# Teste 11 - parametros invalidos retornam 400
# ---------------------------------------------------------------------------

def test_categoria_invalida_retorna_400(client):
    resp = client.get("/api/acoes?categoria=nao-e-numero")
    assert resp.status_code == 400


def test_data_de_invalida_retorna_400(client):
    resp = client.get("/api/acoes?de=ontem")
    assert resp.status_code == 400


def test_data_ate_invalida_retorna_400(client):
    resp = client.get("/api/acoes?ate=32/13/2025")
    assert resp.status_code == 400


# ---------------------------------------------------------------------------
# Teste 12 - resposta em menos de 500ms (criterio de aceitacao)
# ---------------------------------------------------------------------------

def test_resposta_em_menos_de_500ms(app, client, organizadora):
    cat_id = _make_category(app, name="Performance")
    for i in range(10):
        _make_event(app, cat_id, organizadora.id, title=f"Evento Perf {i}")

    inicio = time.monotonic()
    resp = client.get("/api/acoes?q=perf")
    duracao_ms = (time.monotonic() - inicio) * 1000

    assert resp.status_code == 200
    assert duracao_ms < 500, f"Resposta levou {duracao_ms:.0f}ms (limite: 500ms)"


# ---------------------------------------------------------------------------
# Teste 13 - response inclui filtros ativos (para URL compartilhavel)
# ---------------------------------------------------------------------------

def test_response_inclui_filtros_ativos(client):
    resp = client.get("/api/acoes?q=saude&categoria=1")

    assert resp.status_code == 200
    data = resp.get_json()
    assert "filters" in data, "Response deve incluir os filtros ativos"
    assert data["filters"]["q"] == "saude"
    assert data["filters"]["categoria"] == 1