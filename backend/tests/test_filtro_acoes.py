"""
NOTA sobre debounce: o teste "debounce previne mais de 1 req por 300ms"
e responsabilidade do frontend (JS). O backend nao tem como testar isso
em pytest. O que o backend garante eh que retorna dentro de 500ms e que
o rate limiter existe caso necessario.
"""

import time
from datetime import datetime, timedelta, timezone

import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_event(client, db_session, overrides=None):
    """Cria um evento via banco diretamente para isolar o teste de filtros."""
    from maes_mobilizadoras.models import Event, EventCategory, User

    cat = db_session.query(EventCategory).first()
    if not cat:
        cat = EventCategory(name="Saude", icon="heart", color="#FF0000")
        db_session.add(cat)
        db_session.flush()

    user = db_session.query(User).first()
    if not user:
        user = User(
            phone="+5511999990001",
            full_name="Mae Teste",
            neighborhood="Parelheiros",
            role="organizadora",
        )
        db_session.add(user)
        db_session.flush()

    defaults = dict(
        title="Feira de Saude",
        description="Consultas gratuitas no bairro",
        event_datetime=datetime.now(timezone.utc) + timedelta(days=7),
        location_name="Praca Central",
        category_id=cat.id,
        organizer_id=user.id,
        status="scheduled",
    )
    if overrides:
        defaults.update(overrides)

    ev = Event(**defaults)
    db_session.add(ev)
    db_session.commit()
    return ev


# ---------------------------------------------------------------------------
# Teste 1 - sem filtros retorna todos os eventos
# ---------------------------------------------------------------------------

def test_list_acoes_sem_filtros_retorna_todos(client, db_session):
    _make_event(client, db_session, {"title": "Evento A"})
    _make_event(client, db_session, {"title": "Evento B"})

    resp = client.get("/api/acoes")

    assert resp.status_code == 200
    data = resp.get_json()
    assert "data" in data
    assert "total" in data
    assert data["total"] >= 2


# ---------------------------------------------------------------------------
# Teste 2 (TDD spec) - busca textual retorna por termo no titulo
# ---------------------------------------------------------------------------

def test_busca_textual_retorna_resultado_por_titulo(client, db_session):
    _make_event(client, db_session, {"title": "Oficina de Horta Urbana"})
    _make_event(client, db_session, {"title": "Palestra de Saude Mental"})

    resp = client.get("/api/acoes?q=horta")

    assert resp.status_code == 200
    data = resp.get_json()
    titulos = [item["title"] for item in data["data"]]
    assert any("Horta" in t for t in titulos)
    assert all("Horta" in t or "horta" in t.lower()
               for t in titulos), "Deve retornar apenas eventos com 'horta'"


# ---------------------------------------------------------------------------
# Teste 3 (TDD spec) - busca textual retorna por termo na descricao
# ---------------------------------------------------------------------------

def test_busca_textual_retorna_resultado_por_descricao(client, db_session):
    _make_event(client, db_session, {
        "title": "Evento Generico",
        "description": "Este evento trata de compostagem comunitaria",
    })
    _make_event(client, db_session, {
        "title": "Outro Evento",
        "description": "Sem relacao com o tema buscado",
    })

    resp = client.get("/api/acoes?q=compostagem")

    assert resp.status_code == 200
    data = resp.get_json()
    assert len(data["data"]) >= 1
    descricoes = [item.get("description", "") or "" for item in data["data"]]
    assert any("compostagem" in d.lower() for d in descricoes)


# ---------------------------------------------------------------------------
# Teste 4 (TDD spec) - filtro de categoria exclui outras categorias
# ---------------------------------------------------------------------------

def test_filtro_categoria_exclui_outras(client, db_session):
    from maes_mobilizadoras.models import EventCategory

    cat1 = EventCategory(name="Educacao", icon="book", color="#0000FF")
    cat2 = EventCategory(name="Esporte", icon="ball", color="#00FF00")
    db_session.add_all([cat1, cat2])
    db_session.flush()

    _make_event(client, db_session, {"title": "Aula de Leitura", "category_id": cat1.id})
    _make_event(client, db_session, {"title": "Futebol Comunitario", "category_id": cat2.id})

    resp = client.get(f"/api/acoes?categoria={cat1.id}")

    assert resp.status_code == 200
    data = resp.get_json()
    assert all(item["category_id"] == cat1.id for item in data["data"])
    assert not any(item["category_id"] == cat2.id for item in data["data"])


# ---------------------------------------------------------------------------
# Teste 5 - filtro de periodo (de/ate)
# ---------------------------------------------------------------------------

def test_filtro_periodo_de(client, db_session):
    agora = datetime.now(timezone.utc)
    _make_event(client, db_session, {
        "title": "Evento Proximo",
        "event_datetime": agora + timedelta(days=3),
    })
    _make_event(client, db_session, {
        "title": "Evento Distante",
        "event_datetime": agora + timedelta(days=30),
    })

    de = (agora + timedelta(days=20)).strftime("%Y-%m-%d")
    resp = client.get(f"/api/acoes?de={de}")

    assert resp.status_code == 200
    data = resp.get_json()
    titulos = [item["title"] for item in data["data"]]
    assert "Evento Distante" in titulos
    assert "Evento Proximo" not in titulos


def test_filtro_periodo_ate(client, db_session):
    agora = datetime.now(timezone.utc)
    _make_event(client, db_session, {
        "title": "Evento Esta Semana",
        "event_datetime": agora + timedelta(days=3),
    })
    _make_event(client, db_session, {
        "title": "Evento Proximo Mes",
        "event_datetime": agora + timedelta(days=35),
    })

    ate = (agora + timedelta(days=10)).strftime("%Y-%m-%d")
    resp = client.get(f"/api/acoes?ate={ate}")

    assert resp.status_code == 200
    data = resp.get_json()
    titulos = [item["title"] for item in data["data"]]
    assert "Evento Esta Semana" in titulos
    assert "Evento Proximo Mes" not in titulos


# ---------------------------------------------------------------------------
# Teste 6 - filtros combinados funcionam corretamente (AND)
# ---------------------------------------------------------------------------

def test_filtros_combinados_aplicam_and(client, db_session):
    from maes_mobilizadoras.models import EventCategory

    cat = EventCategory(name="Cultura", icon="music", color="#FF00FF")
    db_session.add(cat)
    db_session.flush()

    agora = datetime.now(timezone.utc)
    _make_event(client, db_session, {
        "title": "Sarau Cultural",
        "category_id": cat.id,
        "event_datetime": agora + timedelta(days=5),
    })
    _make_event(client, db_session, {
        "title": "Sarau Esportivo",
        "category_id": cat.id,
        "event_datetime": agora + timedelta(days=40),
    })
    _make_event(client, db_session, {
        "title": "Peca Teatral",
        "event_datetime": agora + timedelta(days=5),
    })

    ate = (agora + timedelta(days=10)).strftime("%Y-%m-%d")
    resp = client.get(f"/api/acoes?q=sarau&categoria={cat.id}&ate={ate}")

    assert resp.status_code == 200
    data = resp.get_json()
    assert len(data["data"]) == 1
    assert data["data"][0]["title"] == "Sarau Cultural"


# ---------------------------------------------------------------------------
# Teste 7 - limpar filtros (GET sem params) restaura listagem completa
# ---------------------------------------------------------------------------

def test_limpar_filtros_restaura_listagem(client, db_session):
    _make_event(client, db_session, {"title": "Acao Alpha"})
    _make_event(client, db_session, {"title": "Acao Beta"})

    resp_filtrado = client.get("/api/acoes?q=alpha")
    assert resp_filtrado.get_json()["total"] < 2

    resp_limpo = client.get("/api/acoes")
    assert resp_limpo.get_json()["total"] >= 2


# ---------------------------------------------------------------------------
# Teste 8 - filtro por responsavel
# ---------------------------------------------------------------------------

def test_filtro_responsavel(client, db_session):
    from maes_mobilizadoras.models import User

    org1 = User(
        phone="+5511888880001",
        full_name="Organizadora Um",
        neighborhood="Parelheiros",
        role="organizadora",
    )
    org2 = User(
        phone="+5511888880002",
        full_name="Organizadora Dois",
        neighborhood="Grajaú",
        role="organizadora",
    )
    db_session.add_all([org1, org2])
    db_session.flush()

    _make_event(client, db_session, {"title": "Evento da Um", "organizer_id": org1.id})
    _make_event(client, db_session, {"title": "Evento da Dois", "organizer_id": org2.id})

    resp = client.get(f"/api/acoes?responsavel={org1.id}")

    assert resp.status_code == 200
    data = resp.get_json()
    assert all(item["organizer_id"] == org1.id for item in data["data"])


# ---------------------------------------------------------------------------
# Teste 9 - paginacao
# ---------------------------------------------------------------------------

def test_paginacao_retorna_subset(client, db_session):
    for i in range(5):
        _make_event(client, db_session, {"title": f"Evento Pag {i}"})

    resp = client.get("/api/acoes?page=1&per_page=2")

    assert resp.status_code == 200
    data = resp.get_json()
    assert len(data["data"]) == 2
    assert data["total"] >= 5
    assert data["page"] == 1
    assert data["per_page"] == 2


# ---------------------------------------------------------------------------
# Teste 10 - parametro invalido retorna 400
# ---------------------------------------------------------------------------

def test_categoria_invalida_retorna_400(client, db_session):
    resp = client.get("/api/acoes?categoria=nao-e-numero")
    assert resp.status_code == 400


def test_data_invalida_retorna_400(client, db_session):
    resp = client.get("/api/acoes?de=ontem")
    assert resp.status_code == 400


# ---------------------------------------------------------------------------
# Teste 11 - resposta em menos de 500ms (criterio de aceitacao)
# ---------------------------------------------------------------------------

def test_resposta_em_menos_de_500ms(client, db_session):
    for i in range(10):
        _make_event(client, db_session, {"title": f"Evento Perf {i}"})

    inicio = time.monotonic()
    resp = client.get("/api/acoes?q=perf")
    duracao_ms = (time.monotonic() - inicio) * 1000

    assert resp.status_code == 200
    assert duracao_ms < 500, f"Resposta levou {duracao_ms:.0f}ms (limite: 500ms)"


# ---------------------------------------------------------------------------
# Teste 12 - URL compartilhavel: params preservados no response (header/meta)
#
# O backend nao controla a URL do frontend, mas o response deve incluir
# os filtros ativos para que o frontend possa reconstruir a URL.
# ---------------------------------------------------------------------------

def test_response_inclui_filtros_ativos(client, db_session):
    resp = client.get("/api/acoes?q=saude&categoria=1")

    assert resp.status_code == 200
    data = resp.get_json()
    assert "filters" in data, "Response deve incluir os filtros ativos aplicados"
    assert data["filters"]["q"] == "saude"
    assert data["filters"]["categoria"] == 1