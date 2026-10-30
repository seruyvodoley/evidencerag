<script lang="ts">
  import { onMount, tick } from 'svelte';
  import { paths, routeFromPath } from './navigation';
  import type { View } from './navigation';
  type Doc = {id:string;title:string;filename:string;family:string;version:string;date:string;status:string;chunk_count:number};
  type Hit = {id:number;document:string;text:string;locator:string;page:number|null;title:string;version:string;date:string;family:string};
  type Demo = {id:string;name:string;description:string;questions:string[];count:number};
  type Result = {status:string;answer:{text:string;citations:number[]}|null;hits:Hit[];conflicts:any[];gaps:string[];trace:any[];elapsed_ms:number;limitations:string;lexical_coverage:number};
  let view = $state<View>(routeFromPath(window.location.pathname));
  let demos = $state<Demo[]>([]), docs = $state<Doc[]>([]);
  let question = $state(''), family = $state(''), version = $state(''), asOf = $state(''), strategy = $state('versioned');
  let result = $state<Result|null>(null), source = $state<any>(null), comparison = $state<any>(null);
  let left = $state(''), right = $state(''), selectedCorpus = $state('device');
  let busy = $state(false), error = $state(''), notice = $state(''), hasSession = $state(false);
  let uploadDialog: HTMLDialogElement;
  let uploadForm: HTMLFormElement;
  const statuses: Record<string,{title:string;description:string;kind:string}> = {
    no_results:{title:'Подходящих фрагментов не найдено',description:'Измените формулировку или добавьте документы. Отсутствие результата не доказывает отсутствие факта.',kind:'neutral'},
    insufficient:{title:'Недостаточно сведений для вывода',description:'Часть терминов вопроса не найдена. Ниже — доступные фрагменты; полнота их смысла не проверена.',kind:'warning'},
    unverified:{title:'Найдены фрагменты для проверки',description:'Слова вопроса встречаются в источниках. Этого недостаточно, чтобы автоматически подтвердить ответ.',kind:'neutral'},
    potential_conflict:{title:'Есть различия, влияющие на проверку',description:'В одинаковых полях найдены разные значения. Уточните редакцию или дату; это сигнал, а не доказательство смыслового противоречия.',kind:'warning'},
    confirmed_formal:{title:'Вывод по формальному правилу',description:'Сработало заранее заданное правило демонстрационного набора. Его условия и исходный фрагмент доступны для проверки.',kind:'success'}
  };
  const families = $derived([...new Set(docs.map(d=>d.family))]);
  const versions = $derived([...new Set(docs.filter(d=>!family||d.family===family).map(d=>d.version).filter(Boolean))]);
  const suggestions = $derived(demos.find(d=>d.id===selectedCorpus)?.questions || []);
  const selectedStatus = $derived(result ? statuses[result.status] || statuses.unverified : null);

  function prepareComparison() {
    if(!docs.some(d=>d.id===left)) left=docs[0]?.id||'';
    if(!docs.some(d=>d.id===right)) right=docs.find(d=>d.id!==left)?.id||'';
  }
  async function navigate(target: View) {
    if(window.location.pathname!==paths[target]) {
      history.replaceState({...history.state,scrollY:window.scrollY},'',window.location.href);
      history.pushState({scrollY:0},'',paths[target]);
    }
    view=target;
    if(target==='compare') prepareComparison();
    await tick();
    window.scrollTo({top:0,behavior:'instant'});
    document.getElementById('main')?.focus({preventScroll:true});
  }
  function followLink(event: MouseEvent, target: View) {
    // Preserve native new-tab, context-menu and modified-click behavior.
    if(event.button!==0||event.metaKey||event.ctrlKey||event.shiftKey||event.altKey)return;
    event.preventDefault();error='';notice='';
    void navigate(target);
  }
  async function api(path:string, options:RequestInit = {}) {
    const response = await fetch('/api'+path, options);
    let payload;
    try { payload=await response.json(); } catch { throw new Error("Сервер временно недоступен. Повторите запрос"); }
    if(!response.ok) {
      const message = typeof payload.detail === 'string' ? payload.detail : 'Проверьте поля формы и ограничения запроса';
      if(response.status===401) hasSession=false;
      throw new Error(message);
    }
    return payload;
  }
  async function run(action:()=>Promise<void>) {
    if(busy) return;
    busy=true; error=''; notice='';
    try { await action(); } catch(e) { error=e instanceof Error?e.message:'Не удалось выполнить действие'; } finally { busy=false; }
  }
  async function ensureSession() {
    if(!hasSession) {await api('/workspaces',{method:'POST'});hasSession=true;}
  }
  async function refresh() { docs=await api('/documents'); }
  async function openDemo(id:string) {
    await run(async()=>{
      await ensureSession(); await api('/demos/'+id+'/import',{method:'POST'}); await refresh();
      selectedCorpus=id;family=docs.some(d=>d.family===id)?id:'';version='';asOf='';result=null;source=null;await navigate('work');
      question=demos.find(d=>d.id===id)?.questions[0]||'';
      notice='Демонстрационные документы добавлены в ваше временное пространство.';
    });
  }
  async function search(q=question) {
    question=q;
    await run(async()=>{
      await ensureSession();
      result=await api('/search',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({question:q,strategy,family:family||null,version:version||null,as_of:asOf||null})});
      source=null;
    });
  }
  async function inspect(id:string, chunk?:number) {
    await run(async()=>{source=await api('/documents/'+id);source.selected=chunk;await tick();const target=document.getElementById(chunk?'chunk-'+chunk:'source-title');target?.scrollIntoView({block:'start'});target?.focus({preventScroll:true});});
  }
  async function deleteDoc(id:string) {
    if(!confirm('Удалить документ и все его фрагменты из рабочего пространства?'))return;
    await run(async()=>{await api('/documents/'+id,{method:'DELETE'});await refresh();source=null;result=null;comparison=null;notice='Документ и его поисковый индекс удалены.';});
  }
  async function upload(event:SubmitEvent) {
    event.preventDefault();
    await run(async()=>{
      await ensureSession();const form=new FormData(uploadForm);
      const file=form.get('file') as File;
      if(file.size>10_000_000)throw new Error('Файл должен быть не больше 10 МБ');
      const doc=await api('/documents',{method:'POST',body:form});await refresh();
      result=null;source=doc;uploadDialog.close();uploadForm.reset();await navigate('work');
      notice=doc.status==='needs_ocr'?'В PDF нет текстового слоя. Требуется распознавание; OCR пока не подключён.':'Документ обработан. Можно искать по его содержимому.';
    });
  }
  async function compareDocs() {
    await run(async()=>{comparison=await api('/compare',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({left,right})});});
  }
  async function clearWorkspace() {
    if(!confirm('Удалить всё рабочее пространство и все загруженные документы?'))return;
    await run(async()=>{await api('/workspace',{method:'DELETE'});hasSession=false;docs=[];source=null;result=null;comparison=null;await navigate('home');notice='Рабочее пространство удалено.';});
  }
  onMount(()=>{
    const previousRestoration=history.scrollRestoration;
    history.scrollRestoration='manual';
    let restoring=false, frame=0;
    const saveScroll=()=>{
      if(!restoring)history.replaceState({...history.state,scrollY:window.scrollY},'',window.location.href);
    };
    const restoreRoute=async()=>{
      restoring=true;
      const position=history.state?.scrollY||0;
      view=routeFromPath(window.location.pathname);
      if(view==='compare')prepareComparison();
      error='';notice='';
      await tick();
      window.scrollTo({top:position,behavior:'instant'});
      document.getElementById('main')?.focus({preventScroll:true});
      frame=requestAnimationFrame(()=>{restoring=false;});
    };
    window.addEventListener('popstate',restoreRoute);
    window.addEventListener('scroll',saveScroll,{passive:true});
    void run(async()=>{
      demos=await api('/demos');
      try{const s=await api('/session');docs=s.documents;hasSession=true;}catch{hasSession=false;}
      if(view==='compare')prepareComparison();
    });
    return ()=>{
      window.removeEventListener('popstate',restoreRoute);
      window.removeEventListener('scroll',saveScroll);
      cancelAnimationFrame(frame);
      history.scrollRestoration=previousRestoration;
    };
  });
</script>

<svelte:head><title>{view==='home'?'Основание — ответы начинаются с источников':view==='compare'?'Сравнение редакций — Основание':view==='research'?'Метод и ограничения — Основание':'Работа с документами — Основание'}</title></svelte:head>
<a class="skip" href="#main">Перейти к содержимому</a>
<header class="topbar">
  <a class="brand" href="/" onclick={(e)=>followLink(e,'home')} aria-label="Основание, главная"><svg viewBox="0 0 36 36" width="34" height="34" fill="none" aria-hidden="true"><path d="M13 5H5v26h8M23 5h8v26h-8M12 24l6-13 6 13M14 20h8" stroke="currentColor" stroke-width="2"/></svg><span>Основание<small>Документы. Источники. Выводы.</small></span></a>
  <nav aria-label="Главная навигация">
    <a href="/documents" class:active={view==='work'} aria-current={view==='work'?'page':undefined} onclick={(e)=>followLink(e,'work')}>Документы <span class="count">{docs.length}</span></a>
    <a href="/compare" class:active={view==='compare'} aria-current={view==='compare'?'page':undefined} onclick={(e)=>followLink(e,'compare')}>Сравнение редакций</a>
    <a href="/method" class:active={view==='research'} aria-current={view==='research'?'page':undefined} onclick={(e)=>followLink(e,'research')}>О методе</a>
  </nav>
  <span class="mode"><span class="dot"></span>Без внешней модели</span>
</header>
<div class="notifications" aria-live="polite" aria-atomic="true">
  {#if error}<p class="message error" role="alert">{error}</p>{/if}
  {#if notice}<p class="message">{notice}</p>{/if}
  {#if busy}<p class="loading">Выполняем запрос…</p>{/if}
</div>
<main id="main" tabindex="-1">
{#if view==='home'}
  <section class="hero wrap">
    <div class="hero-copy">
      <span class="product-tag">Проверяемый поиск по документам</span>
      <h1>У каждого вывода<br/>есть основание.</h1>
      <p class="intro">Найдите нужное в документах, сравните редакции и проверьте, на чём держится ответ. Если сведений не хватает — вы об этом узнаете.</p>
      <div class="hero-actions"><button class="primary" disabled={busy} onclick={()=>openDemo('device')}>Открыть демонстрацию <span aria-hidden="true">↗</span></button><button class="secondary" onclick={()=>uploadDialog.showModal()}>Загрузить документ</button></div>
      <p class="fine">Без регистрации и платных API. Ваши документы доступны только в вашем браузерном сеансе.</p>
    </div>
    <div class="specimen" aria-label="Пример реальных фрагментов демонстрационной инструкции">
      <div class="specimen-head"><span class="file-symbol" aria-hidden="true">▤</span><span>Метеостанция «Север»<small>Авторский демонстрационный документ</small></span><span class="archive-tab">Две редакции</span></div>
      <div class="specimen-pages">
        <article class="paper old"><div class="paper-meta">Инструкция <span>v1.0</span></div><h2>Питание</h2><p>Ёмкость аккумулятора:<br/><mark class="removed">2400 мА·ч</mark></p><p>Разъём питания: Micro-USB</p><span class="paper-date">Действует с 01.02.2024</span></article>
        <article class="paper new"><div class="paper-meta">Инструкция <span>v2.0</span></div><h2>Питание</h2><p>Ёмкость аккумулятора:<br/><mark>3600 мА·ч</mark></p><p>Разъём питания: USB-C</p><span class="paper-date">Действует с 15.06.2025</span></article>
      </div>
      <div class="specimen-note"><span aria-hidden="true">↳</span><p>Один вопрос. Разные ответы.<br/><strong>Редакция источника имеет значение.</strong></p></div>
    </div>
  </section>
  <section class="demo-section wrap" aria-labelledby="demo-heading">
    <div class="section-heading"><div><h2 id="demo-heading">Начните с готовых документов</h2><p>Вымышленные примеры с настоящим поиском по содержимому.</p></div><span class="muted">Открытая галерея</span></div>
    <div class="demo-list">{#each demos as demo}<button class="demo-row" disabled={busy} onclick={()=>openDemo(demo.id)}><span class="demo-icon" aria-hidden="true">{demo.id==='device'?'⌁':demo.id==='api'?'{}':demo.id==='service'?'§':'≠'}</span><span class="demo-text"><strong>{demo.name}</strong><span>{demo.description}</span></span><span class="demo-meta">{demo.count} {demo.count===1?'документ':demo.id==='bundle'?'документа':'редакции'}<span>Открыть <span aria-hidden="true">↗</span></span></span></button>{/each}</div>
  </section>
  <section class="principles wrap"><h2>Не просто ответ.<br/>Возможность его проверить.</h2><div><h3>Первоисточник рядом</h3><p>Текст фрагмента, страница или раздел, дата и редакция. Каждую ссылку можно открыть.</p></div><div><h3>Пробелы видны</h3><p>Совпадение слов не означает доказательство. Поиск честно отделён от подтверждённого вывода.</p></div><div><h3>Ваше пространство</h3><p>Приватные документы хранятся до 24 часов. Удалить их раньше можно в любой момент.</p></div></section>
{:else if view==='work'}
  <div class="workspace">
    <aside class="library" aria-label="Ваши документы"><div class="library-title"><h2>Документы</h2><span>{docs.length}/20</span></div><button class="primary full" onclick={()=>uploadDialog.showModal()}>Добавить документ <span aria-hidden="true">+</span></button>
      {#if !docs.length}<p class="empty-small">Загрузите PDF, DOCX, TXT или Markdown. Или откройте набор ниже.</p>{/if}
      <div class="document-list">{#each docs as doc}<div class="document-item"><button class="document-open" onclick={()=>inspect(doc.id)}><span class="file-type">{doc.filename.split('.').pop()?.toUpperCase()}</span><strong>{doc.title}</strong><span>{doc.version?'Редакция '+doc.version:'Версия не указана'}</span><small>{doc.status==='needs_ocr'?'Требуется распознавание':doc.chunk_count+' фрагментов'}{doc.date?' · '+doc.date:''}</small></button><button class="delete" aria-label={'Удалить '+doc.title+' '+doc.version} onclick={()=>deleteDoc(doc.id)}>×</button></div>{/each}</div>
      <details class="demo-picker"><summary>Демонстрационные наборы</summary>{#each demos as demo}<button disabled={busy} onclick={()=>openDemo(demo.id)}>{demo.name}</button>{/each}</details>
      <div class="privacy-note"><strong>Временное пространство</strong><p>Удаление через 24 часа после создания. Содержимое не передаётся внешней модели. Не делитесь cookie сеанса.</p>{#if hasSession}<button class="text-button" onclick={clearWorkspace}>Удалить всё пространство</button>{/if}</div>
    </aside>
    <section class="work-main">
      <div class="work-heading"><div><p class="breadcrumb">Рабочее пространство</p><h1>Что говорят документы?</h1></div><span class="quiet-tag">Поиск по тексту</span></div>
      <form class="search-form" onsubmit={(e)=>{e.preventDefault();search();}}>
        <label for="question">Ваш вопрос</label><div class="query-box"><textarea id="question" name="question" rows="2" bind:value={question} maxlength="1000" minlength="2" required placeholder="Например, какая ёмкость аккумулятора?…"></textarea><button class="primary" disabled={busy}>{busy?'Поиск…':'Найти основания'}<span aria-hidden="true">↗</span></button></div>
        <div class="filters"><label>Набор<select aria-label="Набор" bind:value={family} onchange={()=>version=''}><option value="">Все документы</option>{#each families as f}<option value={f}>{demos.find(d=>d.id===f)?.name||f}</option>{/each}</select></label><label>Редакция<select aria-label="Редакция" bind:value={version}><option value="">Все редакции</option>{#each versions as v}<option value={v}>{v}</option>{/each}</select></label><label>По состоянию на<input type="date" bind:value={asOf} aria-describedby="date-note"/></label></div>
        <details class="settings"><summary>Параметры поиска</summary><label>Стратегия<select aria-label="Стратегия" bind:value={strategy}><option value="versioned">С учётом редакций</option><option value="adaptive">Адаптивная без анализа редакций</option><option value="fixed5">Первые 5 фрагментов</option><option value="fixed10">Первые 10 фрагментов</option></select></label><p id="date-note">Дата выбирает последнюю известную редакцию каждой группы на этот день. Без даты сравниваются все редакции. Неизвестные даты не подтверждают применимость.</p></details>
      </form>
      {#if !result}<div class="starter"><h2>Проверьте на примере</h2><p>Выберите вопрос или задайте свой. Источники будут показаны дословно.</p><div class="suggestions">{#each suggestions as q}<button disabled={busy} onclick={()=>search(q)}>{q}<span aria-hidden="true">↗</span></button>{/each}</div>{#if !docs.length}<button class="secondary" disabled={busy} onclick={()=>openDemo('device')}>Открыть инструкцию «Север»</button>{/if}</div>{/if}
      {#if result && selectedStatus}<section class="search-results" aria-live="polite"><div class={'result-status '+selectedStatus.kind}><span class="status-mark" aria-hidden="true">{selectedStatus.kind==='warning'?'!':selectedStatus.kind==='success'?'✓':'≡'}</span><div><h2>{selectedStatus.title}</h2><p>{selectedStatus.description}</p></div></div>
        {#if result.answer}<article class="formal-answer"><h3>Формальный вывод</h3><p>{result.answer.text}</p>{#each result.answer.citations as id}<button class="source-link" onclick={()=>{const h=result?.hits.find(h=>h.id===id);if(h)inspect(h.document,id);}}>Источник [{id}]</button>{/each}</article>{/if}
        {#if result.conflicts.length}<div class="conflicts"><h3>Различия полей в найденных источниках</h3>{#each result.conflicts as c}<details><summary>{c.field}</summary>{#each c.sources as s}<button class="conflict-source" onclick={()=>inspect(s.document,s.id)}><span>Редакция {s.version||'не указана'}</span><strong>{s.value}</strong><span>[{s.id}]</span></button>{/each}</details>{/each}<p class="fine">Различия могут быть законным изменением правил, а не противоречием. Учитывайте дату и условия применения.</p></div>{/if}
        <div class="evidence-heading"><h3>Найденные фрагменты <span class="count">{result.hits.length}</span></h3><span>{result.elapsed_ms.toFixed(1)} мс · {result.trace.length} итерации</span></div>
        <div class="hits">{#each result.hits as hit}<article class="hit"><div class="hit-meta"><button class="citation" onclick={()=>inspect(hit.document,hit.id)}>[{hit.id}]</button><strong>{hit.title}</strong><span class="version-tag">{hit.version||'Без версии'}</span></div><blockquote>{hit.text}</blockquote><div class="hit-footer"><span>{hit.locator}{hit.page?' · с. '+hit.page:''}{hit.date?' · '+hit.date:''}</span><button class="source-link" onclick={()=>inspect(hit.document,hit.id)}>Открыть источник</button></div></article>{/each}</div>
        <details class="trace"><summary>Как искала система</summary><p>{result.limitations}</p><p>Лексическое покрытие: {Math.round(result.lexical_coverage*100)}%. Это доля терминов вопроса, найденных в тексте, а не уверенность в ответе.</p>{#if result.gaps.length}<p>Не найдены термины: {result.gaps.join(', ')}.</p>{/if}{#each result.trace as step}<p>Шаг {step.iteration}: {step.query.join(', ')}. {step.reason==='lexical_coverage_reached'?'Термины найдены; смысл не проверен.':'Проверка недостающих терминов.'}</p>{/each}</details>
      </section>{/if}
      {#if source}<section class="source-panel" aria-labelledby="source-title"><div class="source-header"><div><p class="breadcrumb">Первоисточник</p><h2 id="source-title" tabindex="-1">{source.title}</h2><p>Редакция {source.version||'не указана'} · {source.date||'Дата не указана'}</p></div><button class="secondary" onclick={()=>source=null}>Закрыть</button></div><a class="download" href={'/api/documents/'+source.id+'/original'} download>Скачать оригинал ({source.filename})</a>{#if source.status==='needs_ocr'}<p class="message">В PDF нет текстового слоя. Требуется распознавание.</p>{/if}{#each source.chunks as chunk}<article class:selected={source.selected===chunk.id} id={'chunk-'+chunk.id} tabindex="-1"><h3>[{chunk.id}] {chunk.locator}</h3><p>{chunk.text}</p></article>{/each}</section>{/if}
    </section>
  </div>
{:else if view==='compare'}
  <section class="wrap compare-page"><p class="breadcrumb">Работа с редакциями</p><h1>Что изменилось в документе?</h1><p class="lead">Сравните исходные формулировки. Различия значений выделяются отдельно и требуют проверки применимости.</p>
    {#if docs.length<2}<div class="starter"><h2>Нужны две редакции</h2><p>При загрузке укажите одинаковую группу документов и разные версии.</p><button class="primary" disabled={busy} onclick={()=>openDemo('device')}>Добавить демонстрационные инструкции</button></div>{:else}<form class="compare-form" onsubmit={(e)=>{e.preventDefault();compareDocs();}}><label>Исходная редакция<select bind:value={left} required><option value="">Выберите документ</option>{#each docs as d}<option value={d.id}>{d.title} — {d.version||d.filename}</option>{/each}</select></label><span class="compare-symbol" aria-hidden="true">⇄</span><label>Новая редакция<select bind:value={right} required><option value="">Выберите документ</option>{#each docs as d}<option value={d.id}>{d.title} — {d.version||d.filename}</option>{/each}</select></label><button class="primary" disabled={busy||left===right}>Сравнить</button></form>{/if}
    {#if comparison}<div class="message">{comparison.limitation}</div><div class="diff-legend"><span class="deletion">Удалено</span><span class="addition">Добавлено</span><span>{comparison.changes.length} блоков изменений</span></div>{#if !comparison.changes.length}<p>Текстовых изменений не найдено.</p>{/if}{#each comparison.changes as change}<div class="diff-block"><div class="diff-old"><h3>Исходный текст</h3>{#each change.old as line}<p>{line||' '}</p>{/each}</div><div class="diff-new"><h3>Новый текст</h3>{#each change.new as line}<p>{line||' '}</p>{/each}</div></div>{/each}{#if comparison.affected_questions.length}<section class="affected"><h2>Что стоит перепроверить</h2>{#each comparison.affected_questions as q}<p>{q}</p>{/each}</section>{/if}{/if}
  </section>
{:else}
  <section class="wrap research-page"><p class="breadcrumb">Метод и ограничения</p><h1>Проверяемость начинается<br/>с честных границ.</h1><p class="lead">«Основание» — инструмент поиска и исследовательский прототип адаптивного формирования контекста. Текущий режим не выполняет смысловую верификацию произвольных утверждений.</p><div class="method-grid"><article><h2>Что происходит с вопросом</h2><ol><li>Слова нормализуются, фрагменты ранжируются по текстовому совпадению.</li><li>При нехватке терминов поиск расширяется в пределах бюджета.</li><li>Редакции сопоставляются по группе, версии и дате.</li><li>Разные значения явно подписанных полей становятся сигналами для проверки.</li></ol></article><article><h2>Что считается подтверждением</h2><p>Совпадение слов и высокая позиция в поиске — не доказательство. В этом режиме подтверждение возможно только для авторского формального правила, когда все его условия и цитаты присутствуют.</p><p>Без такого правила система показывает источники и отказывается от свободного вывода.</p></article><article><h2>Исследовательская гипотеза</h2><p>Проверяем, помогает ли учёт редакций уменьшить ошибки выбора источников при фиксированном бюджете поиска. Новизна и преимущество метода не установлены.</p><p>Реализованы четыре стратегии: первые 5 и 10 фрагментов, адаптивный поиск и поиск с учётом редакций. Демонстрационные корпуса синтетические.</p></article><article><h2>Приватность</h2><p>Пространство доступно по закрытому cookie текущего браузера. Срок хранения — 24 часа от создания. До 20 документов, до 10 МБ на файл и 40 МБ суммарно.</p><p>Внешняя модель отключена. Данные не используются для обучения. Для удаления откройте раздел «Документы».</p></article></div><h2>На какие исследования опираемся</h2><ul class="reading"><li><a href="https://research.google/pubs/sufficient-context-a-new-lens-on-retrieval-augmented-generation-systems/" target="_blank" rel="noreferrer">Sufficient Context (2025)</a> — различие релевантности и достаточности.</li><li><a href="https://aclanthology.org/2025.acl-long.319/" target="_blank" rel="noreferrer">Adaptive Retrieval Without Self-Knowledge? (2025)</a> — качество и стоимость адаптивного поиска.</li><li><a href="https://aclanthology.org/2026.acl-long.1185/" target="_blank" rel="noreferrer">S2G-RAG (2026)</a> — явное управление достаточностью и пробелами.</li><li><a href="https://arxiv.org/abs/2609.37469" target="_blank" rel="noreferrer">RINSE (2026)</a> — проверка недостающих свидетельств до генерации.</li><li><a href="https://doi.org/10.1145/3774904.3792289" target="_blank" rel="noreferrer">Conflict-Aware RAG (2026)</a> — обучение с сигналами конфликтов.</li></ul></section>
{/if}
</main>
<footer class="footer wrap"><span>Основание <span class="muted">/ EvidenceRAG</span></span><span>Исследовательский прототип · источники важнее уверенного тона</span><a class="text-button" href="/method" onclick={(e)=>followLink(e,'research')}>Метод и ограничения</a></footer>
<dialog bind:this={uploadDialog} class="upload-dialog"><div class="dialog-heading"><h2>Добавить документ</h2><button class="secondary" onclick={()=>uploadDialog.close()} aria-label="Закрыть окно загрузки">Закрыть</button></div><p>Только в ваше временное пространство. Внешняя модель отключена.</p><form bind:this={uploadForm} onsubmit={upload}><label>Файл<input name="file" type="file" required accept=".pdf,.docx,.txt,.md"/></label><p class="fine">PDF с текстом, DOCX, TXT или Markdown. До 10 МБ, 300 страниц, 180 000 символов. Для сканов потребуется OCR.</p><label>Название<input name="title" maxlength="160" placeholder="Например, инструкция к устройству…"/></label><label>Группа редакций<input name="family" maxlength="100" placeholder="Одинаковое имя для версий одного документа…"/></label><div class="form-pair"><label>Версия<input name="version" maxlength="40" placeholder="Например, 2.0…"/></label><label>Действует с<input name="date" type="date"/></label></div><p class="fine">Если дата не указана, система не будет предполагать её по времени загрузки. Версия может быть определена из имени вида v2.0.</p>{#if error}<p class="message error" role="alert">{error}</p>{/if}<button class="primary full" disabled={busy}>{busy?'Обработка…':'Загрузить и обработать'}</button></form></dialog>
