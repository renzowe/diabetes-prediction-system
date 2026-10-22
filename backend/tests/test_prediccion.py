import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

from app.schemas.diabetes import EvaluacionEntrada
from app.services.recomendaciones import CATALOGO, FUENTES, Perfil, seleccionar

RAIZ = Path(__file__).resolve().parents[2]
MODELOS = RAIZ / "models" / "nhanes"


def test_estado_informa_el_modelo_cargado(client):
    r = client.get("/")
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "ok"
    assert data["modelo"]["archivo"] == "regresion_logistica.joblib"
    assert "HbA1c" in data["modelo"]["desenlace"]


def test_predict_devuelve_probabilidad_intervalo_factores_y_recomendaciones(client, payload_perfil_alto):
    r = client.post("/predict", json=payload_perfil_alto)
    assert r.status_code == 200
    data = r.json()
    inferior, superior = data["intervalo"]
    assert 0 < inferior <= data["probabilidad"] <= superior < 1
    assert data["imc"] == round(95 / 1.69**2, 2)
    assert "No es un diagnóstico" in data["mensaje"]
    assert "No son consejos de salud ni efectos causales" in data["nota_factores"]
    assert "No indica un rango de su HbA1c" in data["nota_intervalo"]
    assert 2 <= len(data["recomendaciones"]) <= 3
    assert "nivel_riesgo" not in data  # sin categorias de riesgo (plan de tesis, 4.6.1)


def test_api_reproduce_exactamente_el_modelo_congelado(client, payload_perfil_alto):
    """La probabilidad de la API debe ser la misma que da el modelo de notebooks/nhanes/03."""
    artefacto = joblib.load(MODELOS / json.loads((MODELOS / "seleccion.json").read_text())["seleccionado"])
    p = payload_perfil_alto
    fila = pd.DataFrame([{
        "edad": p["edad"], "hombre": 1.0, "imc": p["peso_kg"] / (p["talla_cm"] / 100) ** 2, "cintura": p["cintura_cm"],
        "hta": 1.0, "familiar_dm": 1.0, "actividad": 0.0, "fuma": 1.0,
    }])[artefacto["predictores"]]
    esperada = artefacto["modelo"].predict_proba(fila)[0, 1]

    obtenida = client.post("/predict", json=p).json()["probabilidad"]
    assert abs(obtenida - esperada) < 1e-3  # la API redondea a 4 decimales; el IMC, a 2


def test_datos_que_no_sabe_se_imputan_como_en_el_entrenamiento(client, payload_perfil_alto):
    """Sin cintura ni antecedente familiar, la API debe coincidir con el pipeline (que imputa los NaN)."""
    modelo = client.app.state.modelo
    datos = EvaluacionEntrada(**{**payload_perfil_alto, "cintura_cm": None, "familiar_diabetes": None})
    esperada = modelo._pipeline.predict_proba(modelo.fila(datos))[0, 1]
    assert abs(modelo.predecir(datos).probabilidad - esperada) < 1e-12
    assert client.post("/predict", json={**payload_perfil_alto, "cintura_cm": None, "familiar_diabetes": None}).status_code == 200


def test_shap_suma_exactamente_el_log_odds(client, payload_perfil_alto):
    """En el modelo lineal, intercepto + suma de los valores SHAP de todos los factores = log-odds."""
    modelo = client.app.state.modelo
    resultado = modelo.predecir(EvaluacionEntrada(**payload_perfil_alto))
    assert set(resultado.contribuciones) == {"edad", "sexo", "composicion_corporal", "hipertension",
                                             "antecedente_familiar", "actividad", "tabaquismo"}
    log_odds = modelo.intercepto + sum(resultado.contribuciones.values())
    assert abs(1 / (1 + np.exp(-log_odds)) - resultado.probabilidad) < 1e-12


def test_intervalo_coincide_con_el_bootstrap_del_notebook(client, payload_perfil_alto):
    """El perfil de 50 años del notebook 04 tiene 54.8 % (51.7-57.6)."""
    r = client.post("/predict", json=payload_perfil_alto).json()
    assert round(100 * r["probabilidad"], 1) == 54.8
    assert [round(100 * v, 1) for v in r["intervalo"]] == [51.7, 57.6]


def test_factores_mostrados_son_los_principales_y_ordenados(client, payload_perfil_alto):
    factores = client.post("/predict", json=payload_perfil_alto).json()["factores"]
    assert 1 <= len(factores) <= 3
    magnitudes = [abs(f["contribucion"]) for f in factores]
    assert magnitudes == sorted(magnitudes, reverse=True)
    assert all(m >= 0.05 for m in magnitudes)
    assert [f["factor"] for f in factores] == ["Edad", "Composición corporal", "Tabaco"]


def test_contribucion_negativa_se_explica_pero_no_genera_consejo(client, payload_perfil_bajo):
    data = client.post("/predict", json=payload_perfil_bajo).json()
    assert any(f["efecto"] == "disminuye" for f in data["factores"])
    ids = [r["id"] for r in data["recomendaciones"]]
    assert not {"actividad_fisica", "peso", "tabaco"} & set(ids)  # activa, IMC < 25 y no fuma
    assert ids == ["tamizaje_futuro", "sintomas"]


def test_perfil_alto_prioriza_modificables_y_la_prueba(client, payload_perfil_alto):
    ids = [r["id"] for r in client.post("/predict", json=payload_perfil_alto).json()["recomendaciones"]]
    # Contribuciones: composicion corporal 0.345 > tabaco 0.207 > actividad 0.120. Como corresponde la
    # prueba de tamizaje, solo entran los dos modificables con mayor contribucion.
    assert ids == ["peso", "tabaco", "prueba_tamizaje"]


def test_ningun_mensaje_promete_reducir_el_riesgo():
    prohibidas = ["reducirá", "reduce su riesgo", "disminuirá", "evitará", "garantiza", "previene la diabetes"]
    for r in CATALOGO:
        assert not any(p in r.texto.lower() for p in prohibidas), r.id
        assert r.fuentes and all(f in FUENTES for f in r.fuentes)


def test_seleccion_siempre_da_dos_o_tres_mensajes():
    for edad in (20, 34, 35, 69):
        for imc in (20.0, 26.0, 35.0):
            for hta in (False, True):
                for familiar in (None, False, True):
                    for activo in (False, True):
                        for fuma in (False, True):
                            perfil = Perfil(edad, imc, hta, familiar, activo, fuma)
                            contribuciones = {"actividad": -0.1 if activo else 0.1, "composicion_corporal": 0.2, "tabaquismo": 0.1}
                            elegidas = seleccionar(perfil, contribuciones)
                            assert 2 <= len(elegidas) <= 3
                            assert len({r.id for r in elegidas}) == len(elegidas)
                            if activo:
                                assert "actividad_fisica" not in {r.id for r in elegidas}


def test_criterio_de_tamizaje_ada():
    def aplica(**kw):
        base = dict(edad=30, imc=22.0, hipertension=False, familiar_diabetes=False, actividad_fisica=True, fuma=False)
        return "prueba_tamizaje" in {r.id for r in seleccionar(Perfil(**{**base, **kw}), {})}

    assert aplica(edad=35)
    assert not aplica()
    assert not aplica(imc=27.0)                        # sobrepeso sin otro factor de riesgo
    assert aplica(imc=27.0, familiar_diabetes=True)
    assert aplica(imc=27.0, actividad_fisica=False)
    assert aplica(imc=27.0, hipertension=True)


def test_filtro_rechaza_diagnostico_previo_y_embarazo(client, payload_perfil_bajo):
    for cambio in ({"diagnostico_previo": True}, {"embarazo": True}):
        r = client.post("/predict", json={**payload_perfil_bajo, **cambio})
        assert r.status_code == 422
        assert "sin diagnóstico previo" in r.text


def test_predict_rechaza_edad_fuera_del_rango_del_modelo(client, payload_perfil_bajo):
    for edad in (19, 70):
        assert client.post("/predict", json={**payload_perfil_bajo, "edad": edad}).status_code == 422


def test_predict_rechaza_imc_no_plausible(client, payload_perfil_bajo):
    r = client.post("/predict", json={**payload_perfil_bajo, "peso_kg": 200, "talla_cm": 125})  # IMC = 128
    assert r.status_code == 422


def test_predict_rechaza_campo_faltante(client, payload_perfil_bajo):
    payload = payload_perfil_bajo.copy()
    del payload["actividad_fisica"]
    assert client.post("/predict", json=payload).status_code == 422


def test_predict_guarda_la_evaluacion_con_intervalo_y_mensajes(client, payload_perfil_alto, auth_headers):
    client.post("/predict", json={**payload_perfil_alto, "participante_codigo": "TEST_GUARDA"})
    registros = client.get("/resultados/evaluaciones?participante_codigo=TEST_GUARDA", headers=auth_headers).json()
    assert len(registros) == 1
    r = registros[0]
    assert r["modelo_archivo"] == "regresion_logistica.joblib"
    assert r["intervalo_inferior"] < r["probabilidad"] < r["intervalo_superior"]
    assert r["recomendaciones"].endswith("prueba_tamizaje")
    assert 0 < r["tiempo_prediccion_ms"] < 2000


def test_documento_del_catalogo_coincide_con_los_mensajes_de_la_web():
    """docs/catalogo_recomendaciones.md se entrega al juicio de expertos: debe tener los mismos textos."""
    documento = (RAIZ / "docs" / "catalogo_recomendaciones.md").read_text(encoding="utf-8")
    for r in CATALOGO:
        assert r.texto in documento, r.id
    for referencia in FUENTES.values():
        assert referencia in documento


def test_aviso_de_edad_solo_de_60_a_69(client, payload_perfil_alto):
    """Aviso añadido tras la evaluación final: no cambia la probabilidad, solo se muestra desde los 60 años."""
    joven = client.post("/predict", json={**payload_perfil_alto, "edad": 59}).json()
    mayor = client.post("/predict", json={**payload_perfil_alto, "edad": 60}).json()
    assert joven["aviso_edad"] is None
    assert "distingue poco" in mayor["aviso_edad"]
    modelo = client.app.state.modelo
    esperada = modelo._pipeline.predict_proba(modelo.fila(EvaluacionEntrada(**{**payload_perfil_alto, "edad": 60})))[0, 1]
    assert abs(mayor["probabilidad"] - esperada) < 1e-3


def test_documento_del_catalogo_incluye_el_aviso_de_edad():
    from app.services.predictor import AVISO_EDAD

    documento = (RAIZ / "docs" / "catalogo_recomendaciones.md").read_text(encoding="utf-8")
    assert AVISO_EDAD in documento
