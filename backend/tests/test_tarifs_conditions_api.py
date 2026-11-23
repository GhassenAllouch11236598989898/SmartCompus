"""SA-21 — tarifs, conditions d'admission et comparaison (avec source et date de mise à jour)."""

import pytest

API = "/api/v1/formations"


def test_fees_all_years(client, program_id):
    r = client.get(f"{API}/{program_id('IIT-ING-GI')}/tarifs")
    assert r.status_code == 200
    body = r.json()
    assert body["formation"]["code"] == "IIT-ING-GI" and body["academic_year"] is None
    assert {f["academic_year"] for f in body["items"]} == {"2026-2027", "2025-2026"}
    assert all({"source", "updated_at", "currency", "amount"} <= f.keys() for f in body["items"])
    assert body["last_updated_at"]


def test_fees_filtered_by_year(client, program_id):
    r = client.get(f"{API}/{program_id('IIT-ING-GI')}/tarifs", params={"annee_academique": "2026-2027"})
    body = r.json()
    assert len(body["items"]) == 2
    assert body["totals"] == [{"academic_year": "2026-2027", "currency": "TND", "total": "7800.000"}]
    assert body["items"][0]["source"]["is_demo"] is True


def test_fees_unknown_year_is_empty(client, program_id):
    body = client.get(f"{API}/{program_id('IIT-ING-GI')}/tarifs", params={"annee_academique": "1999-2000"}).json()
    assert body["items"] == [] and body["totals"] == [] and body["last_updated_at"] is None


@pytest.mark.parametrize("year", ["2026", "26-27", "2026/2027"])
def test_fees_invalid_year(client, program_id, year):
    assert client.get(f"{API}/{program_id('IIT-ING-GI')}/tarifs", params={"annee_academique": year}).status_code == 422


def test_fees_and_conditions_404(client, program_id):
    assert client.get(f"{API}/999999/tarifs").status_code == 404
    assert client.get(f"{API}/999999/conditions-admission").status_code == 404
    assert client.get(f"{API}/{program_id('IIT-ING-GC')}/tarifs").status_code == 404  # brouillon


def test_admission_conditions(client, program_id):
    r = client.get(f"{API}/{program_id('IIT-ING-GI')}/conditions-admission", params={"annee_academique": "2026-2027"})
    assert r.status_code == 200
    body = r.json()
    kinds = [c["kind"] for c in body["conditions"]]
    assert kinds == ["dossier_review", "qcm", "interview", "equivalence"]
    assert body["prerequisites"] and body["last_updated_at"]
    assert all(c["source"]["title"] for c in body["conditions"])


def test_compare_two_and_three(client, program_id):
    ids = [program_id(c) for c in ("IIT-LIC-INFO", "IIT-PREPA-MP", "ISB-LIC-GEST")]
    r = client.get(f"{API}/comparer", params={"ids": ",".join(map(str, ids))})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["academic_year"] == "2026-2027"
    assert [f["formation"]["id"] for f in body["formations"]] == ids  # ordre conservé
    first = body["formations"][0]
    assert first["fees_total"] == "6200.000" and first["currency"] == "TND"
    assert first["admission_conditions"] and first["career_outcomes"] and first["formation"]["source"]
    assert body["last_updated_at"]
    r = client.get(f"{API}/comparer", params={"ids": f"{ids[0]},{ids[1]}", "annee_academique": "2025-2026"})
    assert r.status_code == 200 and r.json()["academic_year"] == "2025-2026"


@pytest.mark.parametrize("ids", ["1", "1,2,3,4", "1,1", "a,b", "", "0,1", "-1,2"])
def test_compare_invalid(client, ids):
    r = client.get(f"{API}/comparer", params={"ids": ids})
    assert r.status_code == 422
    assert r.json()["error"]["code"] == "validation_error"


def test_compare_missing_required_param(client):
    assert client.get(f"{API}/comparer").status_code == 422


def test_compare_unknown_or_hidden(client, program_id):
    ok, draft = program_id("IIT-ING-GI"), program_id("IIT-ING-GC")
    r = client.get(f"{API}/comparer", params={"ids": f"{ok},999999"})
    assert r.status_code == 404 and r.json()["error"]["details"] == {"missing_ids": [999999]}
    assert client.get(f"{API}/comparer", params={"ids": f"{ok},{draft}"}).status_code == 404
