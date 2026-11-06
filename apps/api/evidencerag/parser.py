"""Bounded parser worker. Run in a subprocess; never interpret document instructions."""
import io
import json
import re
import sys
import zipfile
from pathlib import Path

MAX_TEXT = 180_000
MAX_PAGES = 300

MONTHS = {'января':'01','февраля':'02','марта':'03','апреля':'04','мая':'05','июня':'06','июля':'07','августа':'08','сентября':'09','октября':'10','ноября':'11','декабря':'12'}

def infer_metadata(filename: str, data: bytes, suffix: str, parsed: dict) -> dict:
    """Conservative, editable suggestions. Only explicit effective-date language creates an applicability date."""
    text = '\n'.join(part['text'] for part in parsed.get('parts', []))
    candidates = []
    if suffix in {'.txt', '.md'}:
        for line in text.splitlines():
            line = line.strip().lstrip('#').strip()
            if line and len(line) >= 4:
                candidates.append(('document_heading', line[:160]))
                break
    embedded_title = ''
    try:
        if suffix == '.pdf':
            from pypdf import PdfReader
            embedded_title = str(PdfReader(io.BytesIO(data), strict=True).metadata.title or '').strip()
        elif suffix == '.docx':
            from docx import Document
            embedded_title = str(Document(io.BytesIO(data)).core_properties.title or '').strip()
    except Exception:
        embedded_title = ''
    if embedded_title:
        candidates.insert(0, ('embedded_document_metadata', embedded_title[:160]))
    if not candidates and text:
        first_line = next((line.strip() for line in text.splitlines() if len(line.strip()) >= 4), '')
        if first_line:
            candidates.append(('first_informative_line', first_line[:160]))
    title = candidates[0][1] if candidates else Path(filename).stem[:160]
    title_source = candidates[0][0] if candidates else 'filename_fallback'
    version_match = re.search(r'(?:редакци\w*\s+(?:от\s+)?|верси\w*\s*|\bv)((?:20\d{2})|(?:\d{1,2}(?:\.\d+){0,2}))', text, re.I)
    version_source = 'explicit_text'
    if not version_match:
        version_match = re.search(r'\b(20\d{2})\b', title)
        version_source = 'document_heading_year'
    if not version_match:
        version_match = re.search(r'(?:^|[_ .-])(?:v|версия[-_ ]?)(\d+(?:\.\d+)*)(?:$|[_ .-])', filename, re.I)
        version_source = 'filename_marker'
    version = version_match.group(1).strip() if version_match else ''
    effective = []
    date_re = r'(\d{4}-\d{2}-\d{2}|\d{1,2}\s+(?:января|февраля|марта|апреля|мая|июня|июля|августа|сентября|октября|ноября|декабря)\s+\d{4}(?:\s+года?)?)'
    for match in re.finditer(r'(?:вступает\s+в\s+силу\s+с|действует\s+с|начинает\s+действовать\s+с)\s+' + date_re, text, re.I):
        value = match.group(1)
        if re.fullmatch(r'\d{4}-\d{2}-\d{2}', value):
            normalized = value
        else:
            day, month, year = re.match(r'(\d{1,2})\s+(\w+)\s+(\d{4})', value, re.I).groups()
            normalized = f'{year}-{MONTHS[month.casefold()]}-{int(day):02d}'
        effective.append({'value': normalized, 'source': 'explicit_effective_date', 'quote': match.group(0)})
    unique = {item['value']: item for item in effective}
    date_value = next(iter(unique)) if len(unique) == 1 else ''
    type_ = 'amendment' if re.search(r'поправк\w*|изменени\w+\s+в\s+(?:регламент|положени|правил)', text, re.I) else ('full_edition' if re.search(r'полная\s+редакци|регламент|положение', text, re.I) else 'unknown')
    family = re.sub(r'^(?:поправка|изменение)(?:\s+к)?\s+', '', title, flags=re.I)
    family = re.sub(r'\bрегламенту\b', 'регламент', family, flags=re.I)
    family = re.sub(r'\bположению\b', 'положение', family, flags=re.I)
    family = re.sub(r'\b20\d{2}\b', '', family)
    family = ' '.join(re.sub(r'[^\wа-яё -]', ' ', family, flags=re.I).split())[:100] or title
    family = family[:1].lower() + family[1:] if family else title
    return {
        'proposals': {
            'title': {'value': title, 'source': title_source, 'quote': candidates[0][1] if candidates else Path(filename).stem},
            'family': {'value': family, 'source': 'normalized_title_suggestion', 'quote': title, 'status': 'suggested'},
            'version': {'value': version, 'source': version_source if version else 'unresolved', 'quote': version_match.group(0) if version_match else ''},
            'date': {'value': date_value, 'source': 'explicit_effective_date' if date_value else ('conflicting_explicit_dates' if len(unique)>1 else 'unresolved'), 'quote': '; '.join(x['quote'] for x in effective)},
            'document_type': {'value': type_, 'source': 'explicit_document_wording' if type_ != 'unknown' else 'unresolved', 'quote': ''},
        },
        'date_roles': [{'role': 'effective_from', **item} for item in effective],
        'unresolved_effective_dates': len(unique) > 1,
    }


def parse(data: bytes, suffix: str) -> dict:
    parts = []
    if suffix in {'.txt', '.md'}:
        text = data.decode('utf-8-sig')
        if '\x00' in text:
            raise ValueError('Это не текстовый UTF-8 файл')
        heading = 'Начало документа'
        for paragraph in re.split(r'\n\s*\n', text):
            if paragraph.lstrip().startswith('#'):
                heading = paragraph.splitlines()[0].lstrip('# ').strip()[:160]
            if paragraph.strip():
                parts.append({'text': paragraph.strip(), 'locator': heading, 'page': None})
    elif suffix == '.pdf':
        if not data.startswith(b'%PDF-'):
            raise ValueError('Некорректная сигнатура PDF')
        from pypdf import PdfReader
        reader = PdfReader(io.BytesIO(data), strict=True)
        if reader.is_encrypted:
            raise ValueError('Зашифрованный PDF: снимите пароль перед загрузкой')
        if len(reader.pages) > MAX_PAGES:
            raise ValueError('Не более 300 страниц')
        total = 0
        for number, page in enumerate(reader.pages, 1):
            text = page.extract_text() or ''
            total += len(text)
            if total > MAX_TEXT:
                raise ValueError('Слишком много текста: предел 180 000 символов')
            if text.strip():
                parts.append({'text': text.strip(), 'locator': f'Страница {number}', 'page': number})
        if not parts:
            return {'parts': [], 'status': 'needs_ocr'}
    elif suffix == '.docx':
        if not zipfile.is_zipfile(io.BytesIO(data)):
            raise ValueError('Некорректный DOCX')
        with zipfile.ZipFile(io.BytesIO(data)) as z:
            if len(z.infolist()) > 1000 or sum(i.file_size for i in z.infolist()) > 25_000_000:
                raise ValueError('Слишком большой распакованный DOCX')
            if any(i.flag_bits & 1 for i in z.infolist()):
                raise ValueError('Зашифрованный архив не поддерживается')
            if 'word/document.xml' not in z.namelist():
                raise ValueError('Отсутствует текст DOCX')
        from docx import Document
        from docx.table import Table
        from docx.text.paragraph import Paragraph
        doc = Document(io.BytesIO(data))
        heading = 'Начало документа'
        for index, block in enumerate(doc.iter_inner_content(), 1):
            if isinstance(block, Paragraph):
                if block.style and block.style.name.startswith('Heading'):
                    heading = block.text[:160]
                text = block.text
            elif isinstance(block, Table):
                text = '\n'.join(' | '.join(c.text for c in row.cells) for row in block.rows)
            else:
                continue
            if text.strip():
                parts.append({'text': text.strip(), 'locator': f'{heading} · блок {index}', 'page': None})
    else:
        raise ValueError('Поддерживаются PDF, DOCX, TXT и Markdown')
    if sum(len(p['text']) for p in parts) > MAX_TEXT:
        raise ValueError('Не более 180 000 символов текста')
    if not parts:
        raise ValueError('В документе нет доступного текста')
    chunks = []
    for part in parts:
        for start in range(0, len(part['text']), 1100):
            chunks.append({**part, 'text': part['text'][start:start + 1100], 'offset': start})
    return {'parts': chunks, 'status': 'ready'}


if __name__ == '__main__':
    try:
        if sys.platform.startswith('linux'):
            import resource
            resource.setrlimit(resource.RLIMIT_AS, (384 * 1024**2, 384 * 1024**2))
            resource.setrlimit(resource.RLIMIT_CPU, (12, 12))
        data = open(sys.argv[1], 'rb').read(10_000_001)
        if len(data) > 10_000_000:
            raise ValueError('Не более 10 МБ')
        print(json.dumps(parse(data, sys.argv[2]), ensure_ascii=False))
    except Exception:
        # Library exceptions may contain document text. Do not emit them.
        print(json.dumps({'error': 'Не удалось прочитать файл: он повреждён, зашифрован или превышает лимиты.'}))
        sys.exit(2)
