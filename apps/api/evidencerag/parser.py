"""Bounded parser worker. Run in a subprocess; never interpret document instructions."""
import io
import json
import re
import sys
import zipfile

MAX_TEXT = 180_000
MAX_PAGES = 300


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
