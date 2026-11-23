"""Análisis adicional posterior a la evaluación final: comparación con el ADA Risk Test (versión A, Bang et al., 2009).

Reglas registradas en docs/analisis_adicional_ada.md (commit 433b8df), antes de calcular. No modifica el modelo congelado.
Se ejecuta una sola vez, desde notebooks/nhanes/:  python 06_adicional_ada_risk_test.py
La versión B (con diabetes gestacional) NO se calcula: el punto de la tarjeta oficial de la ADA no se confirmó.
"""
import json
import subprocess
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from scipy import stats
from sklearn.metrics import roc_auc_score

import preparacion_nhanes as pn
from preparacion_nhanes import DESENLACE

SALIDA = Path("../../resultados/nhanes/06_ada_risk_test")
MODELOS = Path("../../models/nhanes")
SHA256_PRUEBA = "c48492938873def3d096e59c8d465e32843fdd574d3dd2b349e90754d58ee62c"  # protocolo, sección 15
SEMILLA, N_BOOTSTRAP = 42, 2000
if (SALIDA / "registro_ejecucion.json").exists():
    raise RuntimeError("El análisis adicional ya se ejecutó; las reglas permiten una sola ejecución.")

# --- datos y modelo congelado (se verifica su huella, igual que en la evaluación final)
registro_modelos = pd.read_csv(MODELOS / "registro_modelos.csv").set_index("archivo")
assert pn.sha256(MODELOS / "regresion_logistica.joblib") == registro_modelos.loc["regresion_logistica.joblib", "sha256"]
assert pn.sha256(pn.RUTA_PRUEBA) == SHA256_PRUEBA
art = joblib.load(MODELOS / "regresion_logistica.joblib")
t = pd.read_csv(pn.RUTA_PRUEBA)
y = t[DESENLACE].astype(int).to_numpy()
p_modelo = art["modelo"].predict_proba(t[art["predictores"]])[:, 1]
cong = t["conglomerado"].to_numpy()
print(f"Prueba: {len(t):,} participantes | AUC del modelo congelado: {roc_auc_score(y, p_modelo):.4f}")

# --- puntaje ADA (versión A, Bang et al. 2009, tabla 2) ---------------------------------------------
edad, hombre, imc, cintura = t["edad"], t["hombre"], t["imc"], t["cintura"]
pts_edad = np.select([edad >= 60, edad >= 50, edad >= 40], [3, 2, 1], default=0).astype(float)
pts_edad[edad.isna()] = np.nan


def categoria_peso():
    cat_imc = np.select([imc >= 40, imc >= 30, imc >= 25], [3, 2, 1], default=0).astype(float)
    cat_imc[imc.isna()] = np.nan
    cat_cin = np.where(
        hombre == 1,
        np.select([cintura >= 127, cintura >= 101.6, cintura >= 94], [3, 2, 1], default=0),
        np.select([cintura >= 124.5, cintura >= 88.9, cintura >= 80], [3, 2, 1], default=0)).astype(float)
    cat_cin[cintura.isna() | hombre.isna()] = np.nan
    return np.fmax(cat_imc, cat_cin)  # la categoría más alta de las medidas disponibles; NaN solo si faltan ambas


pts_peso = categoria_peso()
pts = pd.DataFrame({
    "edad": pts_edad, "sexo": hombre.astype(float), "familiar": t["familiar_dm"].astype(float),
    "hta": t["hta"].astype(float), "peso": pts_peso, "actividad": -t["actividad"].astype(float)})
completo = pts.notna().all(axis=1).to_numpy()
puntaje_cc = pts.sum(axis=1, skipna=False).to_numpy()          # casos completos
puntaje_sens = pts.fillna(0).sum(axis=1).to_numpy()            # sensibilidad: faltantes = 0
print(f"Casos completos: {completo.sum():,} de {len(t):,} ({100 * completo.mean():.1f} %); excluidos: {(~completo).sum():,}")

# --- remuestreos por conglomerado: los mismos de la evaluación final (semilla 42, 2,000) ---------------
rng = np.random.default_rng(SEMILLA)
lista = np.unique(cong)
filas_de = {c: np.flatnonzero(cong == c) for c in lista}
REMUESTREOS = [np.concatenate([filas_de[c] for c in rng.choice(lista, len(lista), replace=True)]) for _ in range(N_BOOTSTRAP)]


def _rangos(x):
    orden = np.argsort(x)
    z, n = x[orden], len(x)
    r_ord = np.zeros(n)
    i = 0
    while i < n:
        j = i
        while j < n and z[j] == z[i]:
            j += 1
        r_ord[i:j] = 0.5 * (i + j - 1) + 1
        i = j
    r = np.empty(n)
    r[orden] = r_ord
    return r


def delong(y_real, p1, p2):
    pos, neg = y_real == 1, y_real == 0
    m, n = pos.sum(), neg.sum()
    P = np.vstack([p1, p2])
    tx = np.array([_rangos(k[pos]) for k in P])
    ty = np.array([_rangos(k[neg]) for k in P])
    tz = np.array([_rangos(np.concatenate([k[pos], k[neg]])) for k in P])
    aucs = tz[:, :m].sum(axis=1) / m / n - (m + 1) / 2 / n
    v01, v10 = (tz[:, :m] - tx) / n, 1 - (tz[:, m:] - ty) / m
    cov = np.cov(v01) / m + np.cov(v10) / n
    var = cov[0, 0] + cov[1, 1] - 2 * cov[0, 1]
    z = (aucs[0] - aucs[1]) / np.sqrt(var)
    return aucs[0] - aucs[1], 2 * stats.norm.sf(abs(z))


def analizar(mascara, puntaje, nombre):
    yy, pm, ps = y[mascara], p_modelo[mascara], puntaje[mascara]
    d, p = delong(yy, pm, ps)
    assert abs(d - (roc_auc_score(yy, pm) - roc_auc_score(yy, ps))) < 1e-10
    aucs_m, aucs_e, difs = [], [], []
    for i in REMUESTREOS:
        i = i[mascara[i]]
        if 0 < y[i].sum() < len(i):
            am, ae = roc_auc_score(y[i], p_modelo[i]), roc_auc_score(y[i], puntaje[i])
            aucs_m.append(am), aucs_e.append(ae), difs.append(am - ae)
    q = lambda v: np.percentile(v, [2.5, 97.5])
    return {"analisis": nombre, "n": int(mascara.sum()), "casos": int(yy.sum()),
            "AUC_modelo": roc_auc_score(yy, pm), "AUC_modelo_IC95": "%.3f–%.3f" % tuple(q(aucs_m)),
            "AUC_escala_ADA": roc_auc_score(yy, ps), "AUC_escala_IC95": "%.3f–%.3f" % tuple(q(aucs_e)),
            "dif_modelo_menos_escala": d, "dif_IC95_bootstrap": "%.4f a %.4f" % tuple(q(difs)),
            "p_DeLong_pareado": p}


res = pd.DataFrame([analizar(completo, puntaje_cc, "Principal: casos completos"),
                    analizar(np.ones(len(t), bool), puntaje_sens, "Sensibilidad: todos, faltantes = 0")])
SALIDA.mkdir(parents=True, exist_ok=True)
res.to_csv(SALIDA / "comparacion_modelo_vs_ada.csv", index=False)

# --- descriptivo (casos completos): puntos de corte publicados y grupos de edad --------------------------
yc, sc = y[completo], puntaje_cc[completo]
desc = []
for corte in (5, 4):
    pos = sc >= corte
    vp, fp, vn, fn = (pos & (yc == 1)).sum(), (pos & (yc == 0)).sum(), (~pos & (yc == 0)).sum(), (~pos & (yc == 1)).sum()
    desc.append({"corte": f">= {corte}", "porcentaje_clasificado_alto": pos.mean(), "sensibilidad": vp / (vp + fn),
                 "especificidad": vn / (vn + fp), "VPP": vp / (vp + fp), "VPN": vn / (vn + fn)})
pd.DataFrame(desc).to_csv(SALIDA / "descriptivo_cortes.csv", index=False)
edades = {"20-39": t["edad"].between(20, 39), "40-59": t["edad"].between(40, 59), "60-69": t["edad"].between(60, 69)}
por_edad = [{"grupo": g, "n": int((m.to_numpy() & completo).sum()),
             "AUC_modelo": roc_auc_score(y[m.to_numpy() & completo], p_modelo[m.to_numpy() & completo]),
             "AUC_escala_ADA": roc_auc_score(y[m.to_numpy() & completo], puntaje_cc[m.to_numpy() & completo])}
            for g, m in edades.items()]
pd.DataFrame(por_edad).to_csv(SALIDA / "descriptivo_por_edad.csv", index=False)
pd.DataFrame(pts.assign(puntaje=puntaje_cc)[completo]["puntaje"].value_counts().sort_index()).rename(
    columns={"count": "n"}).to_csv(SALIDA / "distribucion_puntaje.csv")

commit = subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True).stdout.strip()
(SALIDA / "registro_ejecucion.json").write_text(json.dumps({
    "analisis": "adicional posterior a la evaluación final; reglas en docs/analisis_adicional_ada.md",
    "commit": commit, "version": "A (Bang et al. 2009); versión B no calculada",
    "datos_sha256": pn.sha256(pn.RUTA_PRUEBA), "modelo_sha256": registro_modelos.loc["regresion_logistica.joblib", "sha256"]}, indent=2))
pd.set_option("display.width", 250, "display.max_columns", 30)
print(res.T.to_string())
print(pd.DataFrame(desc).round(3).to_string())
print(pd.DataFrame(por_edad).round(3).to_string())
