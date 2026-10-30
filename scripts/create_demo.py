"""Author-owned fictional corpora, CC0. No external documents or measurements."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
corpora = [
    {'id': 'device', 'name': 'Метеостанция «Север»', 'description': 'Две инструкции: зарядка, температура, защита от воды. Изменения редакции влияют на ответ.',
     'questions': ['Какая ёмкость аккумулятора?', 'Какой диапазон рабочей температуры?', 'Можно ли погружать станцию в воду?', 'Сколько стоит замена дисплея?'],
     'versions': [('1.0', '2024-02-01', [
         ('Питание', 'Ёмкость аккумулятора: 2400 мА·ч\nРазъём питания: Micro-USB\nНапряжение питания: 5 В\nДля зарядки используйте комплектный кабель. Не заряжайте мокрое устройство.'),
         ('Условия эксплуатации', 'Рабочая температура: от −10 до +40 °C\nЗащита от воды: IP54\nПогружение в воду: запрещено\nДатчик устанавливается на высоте двух метров в тени. Не размещайте его рядом с источником тепла.'),
         ('Измерения', 'Интервал измерений: 60 секунд\nТочность температуры: ±0,5 °C\nРадиус связи: 30 метров\nПоказания отображаются на основном экране. Первое измерение доступно спустя пять минут после включения.'),
         ('Обслуживание', 'Гарантия: 12 месяцев\nОчищайте корпус сухой тканью. Сброс настроек удаляет сохранённую историю. Стоимость запасных частей в инструкции не установлена.')]),
       ('2.0', '2025-06-15', [
         ('Питание', 'Ёмкость аккумулятора: 3600 мА·ч\nРазъём питания: USB-C\nНапряжение питания: 5 В\nДля зарядки используйте сертифицированный кабель. Не заряжайте мокрое устройство.'),
         ('Условия эксплуатации', 'Рабочая температура: от −20 до +50 °C\nЗащита от воды: IP67\nПогружение в воду: допускается до 1 метра на 30 минут при закрытой заглушке\nДатчик устанавливается на высоте двух метров в тени.'),
         ('Измерения', 'Интервал измерений: 30 секунд\nТочность температуры: ±0,3 °C\nРадиус связи: 50 метров\nДля отображения истории подключите устройство к локальной сети. Первое измерение доступно через две минуты.'),
         ('Обслуживание', 'Гарантия: 24 месяца\nПеред очисткой отключите питание. Историю можно экспортировать в CSV. Цены ремонта не включены в эту инструкцию.')])]},
    {'id': 'api', 'name': 'API «Лист»', 'description': 'Техническая документация: лимиты запросов, авторизация, форматы и несовместимые изменения.',
     'questions': ['Какой лимит запросов в минуту?', 'Как передать ключ доступа?', 'Какой SLA гарантирует API?'],
     'versions': [('1.0', '2024-09-01', [
         ('Запросы', 'Лимит запросов: 60 в минуту\nМаксимальный размер страницы: 50 записей\nФормат ответа: JSON\nПосле превышения лимита сервер отвечает HTTP 429. Повторять запрос рекомендуется после Retry-After.'),
         ('Авторизация', 'Способ авторизации: заголовок X-API-Key\nСрок действия ключа: 30 дней\nНе передавайте ключ в параметрах URL. Ключ создаётся в личном кабинете и показывается один раз.'),
         ('Методы', 'Метод списка: GET /v1/leaves\nУдаление записи: DELETE /v1/leaves/{id}\nПоле времени: created_at\nФильтрация доступна по дате создания. Удаление необратимо. Гарантия доступности в этом документе не определена.')]),
       ('2.0', '2025-10-01', [
         ('Запросы', 'Лимит запросов: 120 в минуту\nМаксимальный размер страницы: 100 записей\nФормат ответа: JSON\nПри HTTP 429 учитывайте Retry-After. Клиенты должны ограничивать число повторных запросов.'),
         ('Авторизация', 'Способ авторизации: заголовок Authorization Bearer\nСрок действия ключа: 90 дней\nСтарый X-API-Key больше не поддерживается. Ключи храните на сервере, вне клиентского приложения.'),
         ('Методы', 'Метод списка: GET /v2/leaves\nУдаление записи: DELETE /v2/leaves/{id}\nПоле времени: createdAt\nНовая пагинация использует курсоры. Имена полей изменились. Условия SLA в этой редакции не заданы.')])]},
    {'id': 'service', 'name': 'Правила мастерской «Контур»', 'description': 'Редакции условий обслуживания с датами, исключениями и недостающими сведениями.',
     'questions': ['Какой срок возврата?', 'Какой срок диагностики?', 'Есть ли доставка в Норильск?'],
     'versions': [('2024', '2024-01-01', [
         ('Возврат', 'Срок возврата: 14 дней\nДокумент для возврата: чек или подтверждение оплаты\nВозврат допускается при сохранении комплектности. Индивидуальные заказы регулируются отдельным соглашением.'),
         ('Ремонт', 'Срок диагностики: 3 рабочих дня\nГарантия ремонта: 90 дней\nДиагностика начинается после регистрации устройства. При отсутствии деталей срок ремонта согласовывается отдельно.'),
         ('Доставка', 'Самовывоз: по будням с 10:00 до 18:00\nДокументы для выдачи: номер заказа и удостоверение личности\nПеречень городов доставки и её стоимость не определены в этих правилах.')]),
       ('2025', '2025-01-01', [
         ('Возврат', 'Срок возврата: 30 дней\nДокумент для возврата: чек или подтверждение оплаты\nНовые правила применяются к заказам с 1 января 2025 года. Сохраняйте упаковку и комплектность.'),
         ('Ремонт', 'Срок диагностики: 2 рабочих дня\nГарантия ремонта: 180 дней\nСогласование ремонта выполняется письменно. Дополнительные работы без согласия заказчика не производятся.'),
         ('Доставка', 'Самовывоз: ежедневно с 10:00 до 20:00\nДокументы для выдачи: номер заказа и удостоверение личности\nГорода доставки определяются отдельным договором. Этот договор не включён в демонстрационный набор.')])]},
    {'id': 'conflict', 'name': 'Несогласованные правила архива', 'description': 'Учебный случай: два несовместимых значения в одной редакции. Система должна показать сигнал, а не выбрать произвольно.',
     'questions': ['Какой срок хранения?', 'Кто отвечает за архив?'],
     'versions': [('draft', '2025-03-01', [('Регламент', 'Срок хранения: 30 дней\nОтветственный за архив: администратор\nПо окончании срока материалы удаляются.'), ('Приложение', 'Срок хранения: 90 дней\nОтветственный за архив: оператор\nПриложение не устанавливает приоритет между разделами.')])]}
]
evaluation = []
for corpus in corpora:
    for version, date, sections in corpus.pop('versions'):
        text = f"# {corpus['name']}\n\nРедакция {version}. Действует с {date}.\n\n" + '\n\n'.join(f'## {title}\n\n{body}' for title, body in sections)
        name = f"{corpus['id']}-{version}.md"
        (ROOT / 'datasets/demo' / name).write_text(text)
        corpus.setdefault('documents', []).append({'filename': name, 'title': corpus['name'], 'family': corpus['id'], 'version': version, 'date': date})
        for si, (heading, body) in enumerate(sections):
            for li, line in enumerate(body.splitlines()):
                if ': ' not in line:
                    continue
                field, answer = line.split(': ', 1)
                # Labels refer to exact source substrings; they never feed retrieval.
                evaluation.append({'id': f'{corpus["id"]}-{version}-{si}-{li}', 'split': ['train','dev','test'][(len(evaluation) // 3) % 3],
                    'question': f'{field}?', 'family': corpus['id'], 'version': version, 'as_of': None,
                    'gold_answer': answer, 'required': [line], 'sufficient': corpus['id'] != 'conflict',
                    'conflict': corpus['id'] == 'conflict', 'category': 'same_version_conflict' if corpus['id'] == 'conflict' else 'explicit_field',
                    'abstention_reasons': ['potential_conflict'] if corpus['id'] == 'conflict' else []})
    if corpus['id'] != 'conflict':
        evaluation.append({'id': f'{corpus["id"]}-missing', 'split':'test', 'question': corpus['questions'][-1], 'family':corpus['id'], 'version':None, 'as_of': None, 'gold_answer':None, 'required':[], 'sufficient':False, 'conflict':False, 'category':'missing_information', 'abstention_reasons':['insufficient','no_results','unverified','potential_conflict']})
        evaluation.append({'id':f'{corpus["id"]}-versions', 'split':'test', 'question':corpus['questions'][0], 'family':corpus['id'], 'version':None, 'as_of': None, 'gold_answer':None, 'required':[], 'sufficient':False, 'conflict':True, 'category':'version_change', 'abstention_reasons':['potential_conflict']})
        latest = corpus['documents'][-1]
        evaluation.append({'id':f'{corpus["id"]}-date', 'split':'test', 'question':corpus['questions'][0], 'family':corpus['id'], 'version':None, 'as_of':latest['date'], 'gold_answer':None, 'required':[], 'sufficient':True, 'conflict':False, 'category':'date_scope', 'abstention_reasons':[]})
# One explicitly authored formal rule, available only in the public demo data.
corpora[0]['documents'][1]['formal_rules'] = [{'question':'Какая ёмкость аккумулятора?', 'version':'2.0', 'required_text':['Ёмкость аккумулятора: 3600 мА·ч'], 'answer':'Ёмкость аккумулятора в редакции 2.0 — 3600 мА·ч.'}]
(ROOT/'datasets/demo/catalog.json').write_text(json.dumps(corpora, ensure_ascii=False, indent=2))
(ROOT/'datasets/evaluation/cases.json').write_text(json.dumps(evaluation, ensure_ascii=False, indent=2))
(ROOT/'datasets/demo/LICENSE').write_text('CC0 1.0 Universal. All fictional demonstration documents and authored evaluation labels in this repository are dedicated to the public domain. https://creativecommons.org/publicdomain/zero/1.0/\n')
print(f'{sum(len(c["documents"]) for c in corpora)} documents, {len(evaluation)} authored synthetic cases')
# Group-disjoint split assignment avoids putting the same document family in all splits.
for case in evaluation:
    case['split'] = 'train' if case['family']=='device' else 'dev' if case['family']=='api' else 'test'
# Paired high-overlap gap and multi-source examples. They are intentionally small fixtures.
bundle={'id':'bundle','name':'Комплект поставки «Полюс»','description':'Несколько документов, отвлекающие условия и вопрос без достаточных сведений.','questions':['Какой аккумулятор и срок доставки у комплекта Полюс?', 'Какова цена аккумулятора комплекта Полюс?'], 'documents':[]}
for slug, title, text in [
 ('passport','Паспорт комплекта «Полюс»','# Комплект Полюс\n\nАккумулятор комплекта Полюс: 4800 мА·ч\n\nЗарядка выполняется только при положительной температуре.'),
 ('shipping','Доставка комплекта «Полюс»','# Доставка Полюс\n\nСрок доставки комплекта Полюс: 7 рабочих дней\n\nСрок отсчитывается после подтверждения оплаты.'),
 ('notes','Уточнения к комплекту «Полюс»','# Сведения о цене аккумулятора комплекта Полюс\n\nЦена аккумулятора комплекта Полюс в этом документе не указана. Для заказа обратитесь в мастерскую.\n\nСрок доставки другой модели: 2 дня')]:
    filename=f'bundle-{slug}.md';(ROOT/'datasets/demo'/filename).write_text(text)
    bundle['documents'].append({'filename':filename,'title':title,'family':f'bundle-{slug}','version':'1.0','date':'2025-02-01'})
corpora.append(bundle)
evaluation.extend([
 {'id':'bundle-multisource','split':'test','question':bundle['questions'][0],'family':None,'version':'1.0','as_of':None,'gold_answer':None,'required':['Аккумулятор комплекта Полюс: 4800 мА·ч','Срок доставки комплекта Полюс: 7 рабочих дней'],'sufficient':True,'conflict':False,'category':'multi_document','abstention_reasons':[]},
 {'id':'bundle-lexical-gap','split':'test','question':bundle['questions'][1],'family':'bundle-notes','version':'1.0','as_of':None,'gold_answer':None,'required':[],'sufficient':False,'conflict':False,'category':'high_overlap_gap','abstention_reasons':['insufficient','unverified']}
])
(ROOT/'datasets/demo/catalog.json').write_text(json.dumps(corpora, ensure_ascii=False, indent=2))
(ROOT/'datasets/evaluation/cases.json').write_text(json.dumps(evaluation, ensure_ascii=False, indent=2))
print(f'Final: {sum(len(c["documents"]) for c in corpora)} documents, {len(evaluation)} synthetic cases, group-disjoint splits')
