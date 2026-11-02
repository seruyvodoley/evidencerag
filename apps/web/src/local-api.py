"""Local browser equivalents for the existing FastAPI JSON endpoints."""
from __future__ import annotations

import base64
import difflib
import hashlib
import json
import re
import time
from datetime import date as Date
from pathlib import Path

from evidencerag.parser import parse
from evidencerag.retrieval import analyze_field_changes, retrieve, stable_evidence_id
from evidencerag.research_rag import (
    AuthoredOrStructuredAnswerGenerator, AuthoredOrStructuredEvaluator,
    EvidenceStoreBackend, FormalRequirement, FormalRule, SearchBudget, SearchRequest,
    run_pipeline,
)
from evidencerag.store import EvidenceStore

STORE = EvidenceStore("/browser/evidence.sqlite3")
CATALOG = []
DEMO_FILES = {}


def configure(catalog_json: str, files_json: str):
    global CATALOG, DEMO_FILES
    CATALOG = json.loads(catalog_json)
    DEMO_FILES = json.loads(files_json)


def _response(status, payload):
    return json.dumps({"status": status, "payload": payload}, ensure_ascii=False, separators=(",", ":"))


def _valid_date(value):
    if value:
        try:
            Date.fromisoformat(value)
        except ValueError:
            raise ValueError("Дата должна иметь формат ГГГГ-ММ-ДД")
    return value


def _workspace(token):
    ws = STORE.workspace(token)
    if not ws:
        raise PermissionError("Рабочее пространство не найдено. Создайте новое")
    return ws


def _trusted_demo_metadata(filename, raw):
    for corpus in CATALOG:
        for document in corpus["documents"]:
            official = DEMO_FILES.get(document["filename"])
            if document["filename"] == filename and official is not None and raw == official.encode("utf-8"):
                return {"demo": True, "formal_rules": document.get("formal_rules", [])}
    return {}


def handle(method, path, request_json, token):
    try:
        payload = json.loads(request_json or "{}")
        if method == "GET" and path == "/demos":
            return _response(200, [{"id": c["id"], "name": c["name"], "description": c["description"],
                                    "questions": c["questions"], "count": len(c["documents"])} for c in CATALOG])

        if method == "POST" and path == "/workspaces":
            token = STORE.create_workspace()
            with STORE.connect() as db:
                db.execute("UPDATE workspaces SET expires=? WHERE id=?", (time.time() + 315360000, __import__("hashlib").sha256(token.encode()).hexdigest()))
            return _response(200, {"token": token, "expires_in": 315360000, "mode": "browser-local"})

        ws = _workspace(token)
        if method == "GET" and path == "/session":
            with STORE.connect() as db:
                expires = db.execute("SELECT expires FROM workspaces WHERE id=?", (ws,)).fetchone()[0]
            return _response(200, {"expires_at": expires, "mode": "browser-local", "documents": STORE.documents(ws)})

        if method == "GET" and path == "/documents":
            return _response(200, STORE.documents(ws))

        if method == "DELETE" and path == "/workspace":
            with STORE.connect() as db:
                db.execute("DELETE FROM workspaces WHERE id=?", (ws,))
            return _response(200, {"deleted": True})

        if method == "GET" and path == "/workspace/export":
            documents = []
            for item in STORE.documents(ws):
                doc = STORE.document(ws, item["id"], original=True)
                documents.append({"filename": doc["filename"], "title": doc["title"], "family": doc["family"],
                                  "version": doc["version"], "date": doc["date"], "metadata": json.loads(doc["metadata"] or "{}"),
                                  "original_b64": base64.b64encode(doc["original"]).decode("ascii")})
            archive = {"format": "evidencerag-browser-workspace", "version": 1,
                       "exported_at": Date.today().isoformat(), "documents": documents}
            return _response(200, archive)

        if method == "POST" and path == "/workspace/import":
            if payload.get("format") != "evidencerag-browser-workspace" or payload.get("version") != 1:
                return _response(422, {"detail": "Неизвестный формат архива рабочего пространства"})
            documents = payload.get("documents")
            if not isinstance(documents, list) or len(documents) > 20:
                return _response(422, {"detail": "Архив должен содержать не более 20 документов"})
            decoded = []
            total = 0
            for item in documents:
                if not isinstance(item, dict) or not isinstance(item.get("filename"), str) or not isinstance(item.get("original_b64"), str):
                    return _response(422, {"detail": "Документ в архиве имеет неверный формат"})
                try:
                    raw = base64.b64decode(item["original_b64"], validate=True)
                except Exception:
                    return _response(422, {"detail": "Оригинал документа повреждён или закодирован неверно"})
                if not raw or len(raw) > 10_000_000:
                    return _response(413, {"detail": "Каждый файл в архиве должен быть не больше 10 МБ"})
                total += len(raw)
                if total > 40_000_000:
                    return _response(413, {"detail": "Архив превышает лимит пространства 40 МБ"})
                decoded.append((item, raw))
            new_token = STORE.create_workspace()
            new_ws = STORE.workspace(new_token)
            try:
                for item, raw in decoded:
                    filename = Path(item["filename"].replace("\\", "/")).name[:160]
                    suffix = Path(filename).suffix.lower()
                    if suffix not in {".pdf", ".docx", ".txt", ".md"}:
                        raise ValueError("Архив содержит неподдерживаемый тип файла")
                    parsed = parse(raw, suffix)
                    date = _valid_date(str(item.get("date", ""))[:10])
                    metadata = _trusted_demo_metadata(filename, raw)
                    STORE.add(new_ws, filename, raw, parsed, str(item.get("title", filename))[:160],
                              str(item.get("family", ""))[:100], str(item.get("version", ""))[:40], date, metadata)
            except Exception:
                with STORE.connect() as db:
                    db.execute("DELETE FROM workspaces WHERE id=?", (new_ws,))
                raise
            return _response(200, {"token": new_token, "imported": len(decoded), "staged": True})

        if method == "POST" and path == "/workspace/import/finalize":
            old_token = payload.get("old_token")
            old_ws = STORE.workspace(old_token)
            with STORE.connect() as db:
                db.execute("UPDATE workspaces SET expires=? WHERE id=?", (time.time() + 315360000, ws))
                if old_ws and old_ws != ws:
                    db.execute("DELETE FROM workspaces WHERE id=?", (old_ws,))
            return _response(200, {"imported": len(STORE.documents(ws))})

        demo_match = re.fullmatch(r"/demos/([^/]+)/import", path)
        if method == "POST" and demo_match:
            corpus_id = demo_match.group(1)
            corpus = next((c for c in CATALOG if c["id"] == corpus_id), None)
            if not corpus:
                return _response(404, {"detail": "Демонстрационный набор не найден"})
            existing = {(d["family"], d["version"]) for d in STORE.documents(ws)}
            added = []
            for doc in corpus["documents"]:
                if (doc["family"], doc["version"]) in existing:
                    continue
                raw = DEMO_FILES[doc["filename"]].encode("utf-8")
                added.append(STORE.add(ws, doc["filename"], raw, parse(raw, ".md"), doc["title"], doc["family"],
                                       doc["version"], doc["date"], {"demo": True, "formal_rules": doc.get("formal_rules", [])}))
            return _response(200, {"added": added})

        if method == "POST" and path == "/documents":
            filename = Path(str(payload.get("filename", "document")).replace("\\", "/")).name[:160]
            suffix = Path(filename).suffix.lower()
            if suffix not in {".pdf", ".docx", ".txt", ".md"}:
                return _response(415, {"detail": "Поддерживаются PDF, DOCX, TXT и Markdown"})
            raw = base64.b64decode(payload.get("file_b64", ""), validate=True)
            if not raw or len(raw) > 10_000_000:
                return _response(413, {"detail": "Нужен непустой файл не более 10 МБ"})
            date = _valid_date(str(payload.get("date", ""))[:10])
            try:
                parsed = parse(raw, suffix)
            except Exception as error:
                if isinstance(error, (ValueError, UnicodeError)):
                    detail = str(error)
                else:
                    detail = "Невозможно прочитать файл: проверьте формат, пароль и ограничения"
                return _response(422, {"detail": detail})
            title = str(payload.get("title", "")).strip()[:160] or filename
            family = str(payload.get("family", "")).strip()[:100] or (str(payload.get("title", "")).strip()[:100] or Path(filename).stem)
            inferred = re.search(r"(?:v|версия[-_ ]?)(\d+(?:\.\d+)*)", filename, re.I)
            version = str(payload.get("version", "")).strip()[:40] or (inferred.group(1) if inferred else "")
            ident = STORE.add(ws, filename, raw, parsed, title, family, version, date)
            return _response(200, STORE.document(ws, ident))

        doc_match = re.fullmatch(r"/documents/([^/]+)(/original)?", path)
        if doc_match:
            ident, original = doc_match.group(1), bool(doc_match.group(2))
            if method == "GET":
                doc = STORE.document(ws, ident, original=original)
                if not doc:
                    return _response(404, {"detail": "Документ не найден"})
                if original:
                    return _response(200, {"filename": doc["filename"], "data_b64": base64.b64encode(doc["original"]).decode("ascii")})
                return _response(200, doc)
            if method == "DELETE" and not original:
                if not STORE.delete(ws, ident):
                    return _response(404, {"detail": "Документ не найден"})
                return _response(200, {"deleted": True})

        if method == "POST" and path == "/search":
            if payload.get("as_of"):
                _valid_date(payload["as_of"])
            result = retrieve(STORE, ws, **payload)
            return _response(200, result)

        if method == "POST" and path == "/research":
            request = SearchRequest(payload.get("question", ""), payload.get("family"), payload.get("version"), payload.get("as_of"))
            budget = SearchBudget(max_iterations=int(payload.get("max_iterations", 3)),
                                  max_chunks=int(payload.get("max_chunks", 20)),
                                  time_budget_ms=int(payload.get("time_budget_ms", 500)),
                                  initial_top_k=int(payload.get("initial_top_k", 5)))
            rules = []
            for corpus in CATALOG:
                for document in corpus["documents"]:
                    for rule in document.get("formal_rules", []):
                        requirements = tuple(FormalRequirement(
                            claim_id=f'{document["filename"]}-{index + 1}', claim_text=quote,
                            exact_quote=quote, search_query=quote,
                            allowed_versions=(str(rule["version"]),) if rule.get("version") else ())
                            for index, quote in enumerate(rule.get("required_text", [])))
                        if requirements:
                            rules.append(FormalRule(rule["question"], requirements))
            trace = run_pipeline(request, EvidenceStoreBackend(STORE, ws), AuthoredOrStructuredEvaluator(tuple(rules)),
                                 AuthoredOrStructuredAnswerGenerator(), budget)
            display = retrieve(STORE, ws, request.question, strategy="evidencerag", family=request.family,
                               version=request.version, as_of=request.as_of,
                               max_iterations=budget.max_iterations, max_chunks=budget.max_chunks,
                               time_budget_ms=budget.time_budget_ms)
            # Include every exact source selected by the structured controller,
            # including a linked amendment stored under a separate family.
            selected_ids = {item["evidence_id"] for item in trace["selected_evidence"]}
            indexed_hits = {hit["evidence_id"]: hit for hit in display.get("hits", [])
                            if "evidence_id" in hit}
            for summary in STORE.documents(ws):
                document = STORE.document(ws, summary["id"])
                for chunk in document["chunks"]:
                    hit = {**chunk, "document": document["id"], "title": document["title"], "family": document["family"],
                           "version": document["version"], "date": document["date"],
                           "digest": document["digest"]}
                    evidence_id = stable_evidence_id(hit)
                    if evidence_id in selected_ids:
                        indexed_hits[evidence_id] = {**hit, "evidence_id": evidence_id}
            if selected_ids:
                display["hits"] = list(indexed_hits.values())
            display["research_trace"] = trace
            return _response(200, display)

        if method == "POST" and path == "/compare":
            left, right = STORE.document(ws, payload.get("left", "")), STORE.document(ws, payload.get("right", ""))
            if not left or not right:
                return _response(404, {"detail": "Оба документа должны принадлежать вашему пространству"})
            a = "\n\n".join(c["text"] for c in left["chunks"]).splitlines()
            b = "\n\n".join(c["text"] for c in right["chunks"]).splitlines()
            matcher = difflib.SequenceMatcher(None, a, b, autojunk=False)
            changes = [{"kind": tag, "old": a[i:j], "new": b[k:l]} for tag, i, j, k, l in matcher.get_opcodes() if tag != "equal"]
            hits = [{**c, "family": d["family"], "document": d["id"], "version": d["version"], "date": d["date"]}
                    for d in [left, right] for c in d["chunks"]]
            conflicts, version_differences = analyze_field_changes(hits)
            related = conflicts + version_differences
            return _response(200, {"left": left["title"], "right": right["title"], "changes": changes,
                                   "conflicts": conflicts, "version_differences": version_differences,
                                   "affected_questions": [f'Какое значение поля «{c["field"]}» применимо к нужной дате и редакции?' for c in related],
                                   "limitation": "Текстовые изменения и различия полей. Смысловые противоречия автоматически не доказаны."})

        return _response(404, {"detail": "Локальный маршрут не найден"})
    except PermissionError as error:
        return _response(401, {"detail": str(error)})
    except ValueError as error:
        return _response(422, {"detail": str(error)})
    except Exception as error:
        message = str(error).lower()
        if "quota" in message or "sqlite_full" in message or "database or disk is full" in message or "no space left" in message:
            detail = "В браузере закончилось свободное место. Экспортируйте документы или освободите место и повторите."
            return _response(507, {"detail": detail})
        return _response(500, {"detail": "Локальная обработка не завершилась. Проверьте файл и свободное место браузера.", "debug": repr(error)})
