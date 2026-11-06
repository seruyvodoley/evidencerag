"""Stage 011 metadata proposal and batched store regressions; suggestions stay editable."""

from evidencerag.parser import infer_metadata, parse
from evidencerag.store import EvidenceStore


def test_effective_date_is_only_inferred_from_explicit_effective_language():
    raw = ('# Положение о корпусе\n\nРедакция 2.1. Утверждено 4 мая 2026 года. '
           'Документ вступает в силу с 1 июня 2026 года. Исторический срок — 30 ноября 2025 года.').encode()
    parsed = parse(raw, '.md')
    proposals = infer_metadata('rules.md', raw, '.md', parsed)['proposals']
    assert proposals['title']['value'] == 'Положение о корпусе'
    assert proposals['version']['value'] == '2.1'
    assert proposals['date']['value'] == '2026-06-01'
    assert '1 июня 2026 года' in proposals['date']['quote']


def test_heading_year_proposes_version_and_groups_full_edition_with_amendment():
    base = '# Регламент корпуса речи 2026\n\nПолная редакция вступает в силу с 1 сентября 2026 года.'
    amendment = '# Поправка к регламенту корпуса речи 2026\n\nПоправка действует с 20 октября 2026 года.'
    full_meta = infer_metadata('full.md', base.encode(), '.md', parse(base.encode(), '.md'))['proposals']
    amendment_meta = infer_metadata('change.md', amendment.encode(), '.md', parse(amendment.encode(), '.md'))['proposals']
    assert full_meta['version']['value'] == amendment_meta['version']['value'] == '2026'
    assert full_meta['family']['value'] == amendment_meta['family']['value']


def test_unknown_or_conflicting_effective_date_is_not_fabricated():
    raw = 'Утверждено 4 мая 2026 года. Срок сдачи — 30 ноября 2026 года.'.encode()
    parsed = parse(raw, '.txt')
    proposal = infer_metadata('notes.txt', raw, '.txt', parsed)['proposals']['date']
    assert proposal['value'] == ''
    assert proposal['source'] == 'unresolved'


def test_batch_insert_and_metadata_edit_rebuild_revision_index_once(tmp_path):
    store = EvidenceStore(tmp_path / 'evidence.sqlite3')
    token = store.create_workspace()
    ws = store.workspace(token)
    base = b'# Base\n\nVersion 1.0'
    amendment = b'# Change\n\nChange regulation version 2026, clause 3: instead of WAV provide FLAC.'
    parsed_base = parse(base, '.md')
    parsed_amendment = parse(amendment, '.md')
    ids = store.add_many(ws, [
        ('base.md', base, parsed_base, 'Правила', 'Правила', '2026', '2026-01-01', {}),
        ('change.md', amendment, parsed_amendment, 'Изменение правил', 'Изменения', '1', '2026-02-01', {}),
    ])
    assert len(ids) == 2
    assert store.update_metadata(ws, ids[1], 'Поправка к Правилам', 'Поправка', '1', '2026-02-01',
                                 {'amends_document_id': ids[0], 'document_type': 'amendment'}) == 1
    with store.connect() as db:
        rows = db.execute('SELECT amendment_document,target_document,relation FROM revision_links WHERE workspace=?', (ws,)).fetchall()
    assert [(row['amendment_document'], row['target_document'], row['relation']) for row in rows] == [
        (ids[1], ids[0], 'explicit_metadata_target')]
