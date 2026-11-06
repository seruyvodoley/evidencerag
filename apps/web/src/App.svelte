<script lang="ts">
  import { onMount, tick } from 'svelte';
  import { paths, routeFromPath } from './navigation';
  import type { View } from './navigation';
  import { localApi, downloadLocalOriginal } from './browser-local-api';
  import { extractDocumentZip } from './archive-import';
  const LOCAL_EXECUTION = import.meta.env.VITE_LOCAL_EXECUTION === 'true';
  type Doc = {id:string;title:string;filename:string;family:string;version:string;date:string;status:string;chunk_count:number;metadata?:string};
  type Hit = {id:number;document:string;text:string;locator:string;page:number|null;title:string;version:string;date:string;family:string;evidence_id?:string;research_role?:string};
  type Demo = {id:string;name:string;description:string;questions:string[];count:number};
  type Result = {status:string;answer:{text:string;citations:number[]}|null;hits:Hit[];conflicts:any[];version_differences?:any[];gaps:string[];trace:any[];elapsed_ms:number;limitations:string;lexical_coverage:number;research_trace?:any};
  let view = $state<View>(routeFromPath(window.location.pathname));
  let demos = $state<Demo[]>([]), docs = $state<Doc[]>([]);
  let question = $state(''), family = $state(''), version = $state(''), asOf = $state(''), strategy = $state('versioned');
  let result = $state<Result|null>(null), source = $state<any>(null), comparison = $state<any>(null);
  let left = $state(''), right = $state(''), selectedCorpus = $state('device');
  let busy = $state(false), busyMessage = $state('Выполняем запрос…'), error = $state(''), notice = $state(''), hasSession = $state(false);
  let cookieNoticeVisible = $state(!LOCAL_EXECUTION);
  let uploadDialog: HTMLDialogElement;
  let metadataDialog: HTMLDialogElement;
  let uploadForm: HTMLFormElement;
  let uploadItems = $state<any[]>([]);
  let uploadDropActive = $state(false);
  let editingDoc = $state<Doc|null>(null);
  let editFields = $state({title:'',family:'',version:'',date:'',document_type:'unknown',amends_document_id:''});
  const statuses: Record<string,{title:string;description:string;kind:string}> = {
    no_results:{title:'Подходящих фрагментов не найдено',description:'Измените формулировку или добавьте документы. Отсутствие результата не доказывает отсутствие факта.',kind:'neutral'},
    insufficient:{title:'Недостаточно сведений для вывода',description:'Часть терминов вопроса не найдена. Ниже — доступные фрагменты; полнота их смысла не проверена.',kind:'warning'},
    unverified:{title:'Найдены фрагменты для проверки',description:'Слова вопроса встречаются в источниках. Этого недостаточно, чтобы автоматически подтвердить ответ.',kind:'neutral'},
    potential_conflict:{title:'В одной редакции есть несогласованные значения',description:'В пределах одной редакции поле указано по-разному. Это буквальный сигнал конфликта; смысл и приоритет источников не установлены.',kind:'warning'},
    versioned_difference:{title:'Значения менялись между редакциями',description:'Найдены разные значения в версиях документа. Это история изменений, а не подтверждённое противоречие. Уточните дату применения.',kind:'warning'},
    confirmed_formal:{title:'Вывод по формальному правилу',description:'Сработало заранее заданное правило демонстрационного набора. Его условия и исходный фрагмент доступны для проверки.',kind:'success'}
  };
  const families = $derived([...new Set(docs.map(d=>d.family))]);
  const versions = $derived([...new Set(docs.filter(d=>!family||d.family===family).map(d=>d.version).filter(Boolean))]);
  const suggestions = $derived(demos.find(d=>d.id===selectedCorpus)?.questions || []);
  const selectedStatus = $derived(result?.research_trace
    ? result.research_trace.answer.status==='answered'
      ? {title:'Ответ составлен по найденным источникам',description:'Каждая характеристика извлечена по явной связи с текстом и датой редакции. Это проверка правил, не семантическая модель.',kind:'success'}
      : result.research_trace.assessment.status==='conflicting'
        ? {title:'Найдены конкурирующие действующие значения',description:'Система не выбирает одно из значений без явного приоритета источника.',kind:'warning'}
        : result.research_trace.assessment.status==='insufficient'
          ? {title:'Не хватает подтверждений для части вопроса',description:'Ниже указано, какая характеристика или дата применимости не установлена.',kind:'warning'}
          : result.research_trace.assessment.status==='applicability_uncertain'
            ? {title:'Применимость редакции не установлена',description:'Даты или связанные редакции не позволяют безопасно выбрать действующее требование.',kind:'warning'}
            : result.research_trace.assessment.status==='unsupported'
              ? {title:'Этот тип вопроса пока не поддерживается',description:'Поиск может показать источники, но система не умеет надёжно разложить вопрос на проверяемые утверждения.',kind:'neutral'}
              : {title:'Найденные сведения требуют проверки',description:'Структурных правил оказалось недостаточно для безопасного ответа.',kind:'neutral'}
    : result ? statuses[result.status] || statuses.unverified : null);

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
  function saveBlob(blob:Blob,filename:string) {
    const url=URL.createObjectURL(blob),anchor=document.createElement('a');anchor.href=url;anchor.download=filename;anchor.className='download-anchor';
    document.body.append(anchor);anchor.click();anchor.remove();setTimeout(()=>URL.revokeObjectURL(url),3000);
  }
  async function api(path:string, options:RequestInit = {}, progress?:(message:string)=>void) {
    if(LOCAL_EXECUTION) {
      const response=await localApi(path,options,message=>{busyMessage=message;progress?.(message);});
      if(!response.ok) {
        const message=typeof response.payload?.detail==='string'?response.payload.detail:'Проверьте поля формы и ограничения запроса';
        if(response.status===401) hasSession=false;
        throw new Error(message);
      }
      if(path==='/workspaces'&&response.payload?.token) hasSession=true;
      return response.payload;
    }
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
    busy=true; busyMessage='Выполняем запрос…'; error=''; notice='';
    try { await action(); } catch(e) { error=e instanceof Error?e.message:'Не удалось выполнить действие'; } finally { busy=false; }
  }
  function iterationWord(count:number) {
    const lastTwo=count%100, last=count%10;
    if(lastTwo>=11&&lastTwo<=14)return 'итераций';
    if(last===1)return 'итерация';
    if(last>=2&&last<=4)return 'итерации';
    return 'итераций';
  }
  function confirmedClaimsLabel(count:number) {
    const lastTwo=count%100, last=count%10;
    if(lastTwo===1)return `${count} подтверждённое утверждение`;
    if(lastTwo>=2&&lastTwo<=4)return `${count} подтверждённых утверждения`;
    return `${count} подтверждённых утверждений`;
  }
  function documentWord(count:number) {
    const lastTwo=count%100,last=count%10;
    if(lastTwo>=11&&lastTwo<=14)return 'документов';
    if(last===1)return 'документ';
    if(last>=2&&last<=4)return 'документа';
    return 'документов';
  }
  async function ensureSession(progress?:(message:string)=>void) {
    if(!hasSession) {await api('/workspaces',{method:'POST'},progress);hasSession=true;}
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
      const body={question:q,strategy:strategy==='research'?'evidencerag':strategy,family:family||null,version:version||null,as_of:asOf||null};
      result=await api(LOCAL_EXECUTION&&strategy==='research'?'/research':'/search',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
      source=null;
    });
  }
  function downloadResearchTrace(trace:any) {
    const blob=new Blob([JSON.stringify(trace,null,2)],{type:'application/json'});
    saveBlob(blob,'evidencerag-trace-'+new Date().toISOString().slice(0,10)+'.json');
  }
  async function inspect(id:string, chunk?:number) {
    await run(async()=>{source=await api('/documents/'+id);source.selected=chunk;await tick();const target=document.getElementById(chunk?'chunk-'+chunk:'source-title');target?.scrollIntoView({block:'start'});target?.focus({preventScroll:true});});
  }
  async function downloadOriginal(doc:any) {
    if(!LOCAL_EXECUTION)return;
    await run(async()=>{
      const {filename,blob}=await downloadLocalOriginal('/documents/'+doc.id+'/original');
      saveBlob(blob,filename);
    });
  }
  async function deleteDoc(id:string) {
    if(!confirm('Удалить документ и все его фрагменты из рабочего пространства?'))return;
    await run(async()=>{await api('/documents/'+id,{method:'DELETE'});await refresh();source=null;result=null;comparison=null;notice='Документ и его поисковый индекс удалены.';});
  }
  async function analyzeFiles(files: FileList | File[]) {
    const list = Array.from(files);
    if (!list.length) return;
    error=''; uploadDialog.showModal();
    if(uploadItems.length+list.length>20||uploadItems.reduce((n,item)=>n+(item.file?.size||0),0)+list.reduce((n,file)=>n+file.size,0)>25_000_000){error='Очередь ограничена 20 элементами и 25 МБ исходных файлов.';return;}
    for (const selected of list) {
      let candidates: File[];
      try { candidates = selected.name.toLowerCase().endsWith('.zip') ? await extractDocumentZip(selected) : [selected]; }
      catch(e) { uploadItems.push({file:selected,status:'error',message:e instanceof Error?e.message:'Не удалось прочитать архив'}); continue; }
      if(uploadItems.length+candidates.length>20||uploadItems.reduce((n,item)=>n+(item.file?.size||0),0)+candidates.reduce((n,file)=>n+file.size,0)>25_000_000){uploadItems.push({file:selected,status:'error',message:'Очередь ограничена 20 документами и 25 МБ.'});continue;}
      const pendingItems = candidates.map((file) => {
        const item:any={file,status:'analyzing',metadata:{title:file.name.replace(/\.[^.]+$/,''),family:file.name.replace(/\.[^.]+$/,''),version:'',date:'',document_type:'unknown'},proposals:null};
        uploadItems.push(item);
        return item;
      });
      for (const item of pendingItems) {
        const file:File=item.file;
        try {
          if(file.size>10_000_000) throw new Error('Файл должен быть не больше 10 МБ.');
          busyMessage='Готовим локальную обработку…';
          await ensureSession((message)=>item.stage=message);
          const form=new FormData();form.append('file',file);
          const proposal=await api('/documents/analyze',{method:'POST',body:form},(message)=>item.stage=message);
          item.proposals=proposal.proposals;
          for(const key of ['title','family','version','date','document_type']) item.metadata[key]=proposal.proposals[key]?.value||'';
          item.status='ready';
        } catch(e) { item.status='error';item.message=e instanceof Error?e.message:'Не удалось проанализировать файл'; }
      }
    }
  }
  function selectedFiles(event:Event) { const input=event.currentTarget as HTMLInputElement;if(input.files) void analyzeFiles(input.files);input.value=''; }
  function droppedFiles(event:DragEvent) { event.preventDefault();uploadDropActive=false;if(event.dataTransfer?.files)void analyzeFiles(event.dataTransfer.files); }
  async function retryUpload(item:any) { item.status='analyzing';item.stage='Повторный анализ…';try{const form=new FormData();form.append('file',item.file);const proposal=await api('/documents/analyze',{method:'POST',body:form},(message)=>item.stage=message);item.proposals=proposal.proposals;for(const key of ['title','family','version','date','document_type'])item.metadata[key]=proposal.proposals[key]?.value||'';item.status='ready';}catch(e){item.status='error';item.message=e instanceof Error?e.message:'Не удалось обработать файл';} }
  async function upload(event:SubmitEvent) {
    event.preventDefault();
    const ready=uploadItems.filter(item=>item.status==='ready');
    if(!ready.length){error='Добавьте файлы для обработки.';return;}
    if(docs.length+ready.length>20){error='В рабочем пространстве может быть не более 20 документов.';return;}
    await run(async()=>{
      await ensureSession();const form=new FormData();
      for(const item of ready) form.append('files',item.file);
      form.append('metadata',JSON.stringify(ready.map(item=>item.metadata)));
      const response=await api('/documents/batch',{method:'POST',body:form});
      await refresh();result=null;source=null;uploadDialog.close();uploadForm.reset();uploadItems=[];await navigate('work');
      notice=`Добавлено документов: ${response.added.length}.`;
    });
  }
  function metadataObject(doc:Doc) { try{return JSON.parse(doc.metadata||'{}');}catch{return {};} }
  function metadataSuggestionEntries(doc:Doc) { return Object.entries(metadataObject(doc).metadata_proposals?.proposals||{}); }
  function openMetadataEditor(doc:Doc) {
    const metadata=metadataObject(doc);editingDoc=doc;
    editFields={title:doc.title,family:doc.family,version:doc.version,date:doc.date,
      document_type:metadata.document_type||'unknown',amends_document_id:metadata.amends_document_id||''};
    void tick().then(()=>metadataDialog?.showModal());
  }
  function closeMetadataEditor() { metadataDialog?.close();editingDoc=null; }
  async function saveMetadataEdit() {
    if(!editingDoc)return;
    const id=editingDoc.id;
    await run(async()=>{await api('/documents/'+id,{method:'PATCH',headers:{'Content-Type':'application/json'},body:JSON.stringify(editFields)});await refresh();result=null;comparison=null;source=null;closeMetadataEditor();notice='Сведения обновлены, связи редакций перестроены.';});
  }
  async function compareDocs() {
    await run(async()=>{comparison=await api('/compare',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({left,right})});});
  }
  async function clearWorkspace() {
    if(!confirm('Удалить всё рабочее пространство и все загруженные документы?'))return;
    await run(async()=>{await api('/workspace',{method:'DELETE'});hasSession=false;docs=[];source=null;result=null;comparison=null;await navigate('home');notice='Рабочее пространство удалено.';});
  }
  async function exportWorkspace() {
    await run(async()=>{
      const archive=await api('/workspace/export');
      const blob=new Blob([JSON.stringify(archive,null,2)],{type:'application/json'});
      saveBlob(blob,'osnovanie-workspace-'+new Date().toISOString().slice(0,10)+'.json');notice='Экспорт рабочего пространства скачан.';
    });
  }
  async function importWorkspace(event:Event) {
    const input=event.currentTarget as HTMLInputElement,file=input.files?.[0];
    if(!file)return;
    input.value='';
    if(file.size>55_000_000){error='Архив больше 55 МБ.';return;}
    let archive:any;
    try{archive=JSON.parse(await file.text());}catch{error='Файл не содержит корректный JSON-архив.';return;}
    if(archive?.format!=='evidencerag-browser-workspace'||archive?.version!==1||!Array.isArray(archive?.documents)){error='Формат архива рабочего пространства не распознан.';return;}
    if(!confirm('Импорт заменит текущее локальное пространство. Продолжить?'))return;
    await run(async()=>{
      await ensureSession();
      const imported=await api('/workspace/import',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(archive)});
      await refresh();source=null;result=null;comparison=null;notice='Импорт завершён. Документов: '+imported.imported+'.';
    });
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

<svelte:head><title>{view==='home'?'Основание — ответы начинаются с источников':view==='compare'?'Сравнение редакций — Основание':view==='research'?'Метод и ограничения — Основание':view==='cookies'?'Политика cookie — Основание':'Работа с документами — Основание'}</title></svelte:head>
<a class="skip" href="#main">Перейти к содержимому</a>
<header class="topbar">
  <a class="brand" href={paths.home} onclick={(e)=>followLink(e,'home')} aria-label="Основание, главная"><svg viewBox="0 0 36 36" width="34" height="34" fill="none" aria-hidden="true"><path d="M13 5H5v26h8M23 5h8v26h-8M12 24l6-13 6 13M14 20h8" stroke="currentColor" stroke-width="2"/></svg><span>Основание<small>Документы. Источники. Выводы.</small></span></a>
  <nav aria-label="Главная навигация">
    <a href={paths.work} class:active={view==='work'} aria-current={view==='work'?'page':undefined} onclick={(e)=>followLink(e,'work')}>Документы <span class="count">{docs.length}</span></a>
    <a href={paths.compare} class:active={view==='compare'} aria-current={view==='compare'?'page':undefined} onclick={(e)=>followLink(e,'compare')}>Сравнение редакций</a>
    <a href={paths.research} class:active={view==='research'} aria-current={view==='research'?'page':undefined} onclick={(e)=>followLink(e,'research')}>О методе</a>
  </nav>
  <span class="mode"><span class="dot"></span>{LOCAL_EXECUTION?'Локально в браузере':'Без внешней модели'}</span>
</header>
{#if cookieNoticeVisible}
  <aside class="cookie-notice wrap" role="status" aria-labelledby="cookie-notice-title">
    <div class="cookie-copy"><strong id="cookie-notice-title">Для рабочего пространства нужен один cookie</strong><p>Он создаётся только после начала работы и хранится не дольше 24 часов. Аналитики, рекламы и сторонних cookie нет.</p></div>
    <div class="cookie-actions"><a href={paths.cookies} onclick={(e)=>followLink(e,'cookies')}>Подробнее</a><button class="secondary" onclick={()=>cookieNoticeVisible=false}>Понятно</button></div>
  </aside>
{/if}
<div class="notifications" aria-live="polite" aria-atomic="true">
  {#if error}<p class="message error" role="alert">{error}</p>{/if}
  {#if notice}<p class="message">{notice}</p>{/if}
  {#if busy}<p class="loading">{busyMessage}</p>{/if}
</div>
<main id="main" tabindex="-1">
{#if view==='home'}
  <section class="hero wrap">
    <div class="hero-copy">
      <span class="product-tag">Проверяемый поиск по документам</span>
      <h1>У каждого вывода<br/>есть основание.</h1>
      <p class="intro">Найдите нужное в документах, сравните редакции и проверьте, на чём держится ответ. Если сведений не хватает — вы об этом узнаете.</p>
      <div class="hero-actions"><button class="primary" disabled={busy} onclick={()=>openDemo('device')}>Открыть демонстрацию <span aria-hidden="true">↗</span></button><button class="secondary" onclick={()=>uploadDialog.showModal()}>Загрузить документ</button></div>
      <p class="fine">{LOCAL_EXECUTION?'Без регистрации и API. Документы и поиск остаются в локальном хранилище браузера.':'Без регистрации и платных API. Ваши документы доступны только в вашем браузерном сеансе.'}</p>
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
  <section class="principles wrap"><h2>Не просто ответ.<br/>Возможность его проверить.</h2><div><h3>Первоисточник рядом</h3><p>Текст фрагмента, страница или раздел, дата и редакция. Каждую ссылку можно открыть.</p></div><div><h3>Пробелы видны</h3><p>Совпадение слов не означает доказательство. Поиск честно отделён от подтверждённого вывода.</p></div><div><h3>Ваше пространство</h3><p>{LOCAL_EXECUTION?'Документы хранятся в профиле браузера, пока вы не удалите их или браузер не очистит хранилище. Можно экспортировать резервную копию.':'Приватные документы хранятся до 24 часов. Удалить их раньше можно в любой момент.'}</p></div></section>
{:else if view==='work'}
  <div class="workspace">
    <aside class="library" aria-label="Ваши документы"><div class="library-title"><h2>Документы</h2><span>{docs.length}/20</span></div><button class="primary full" onclick={()=>uploadDialog.showModal()}>Добавить документ <span aria-hidden="true">+</span></button>
      {#if !docs.length}<p class="empty-small">Загрузите PDF, DOCX, TXT или Markdown. Или откройте набор ниже.</p>{/if}
      <div class="document-list">{#each docs as doc}<div class="document-item"><button class="document-open" onclick={()=>inspect(doc.id)}><span class="file-type">{doc.filename.split('.').pop()?.toUpperCase()}</span><strong>{doc.title}</strong><span>{doc.version?'Редакция '+doc.version:'Версия не указана'}</span><small>{doc.status==='needs_ocr'?'Требуется распознавание':doc.chunk_count+' фрагментов'}{doc.date?' · '+doc.date:''}</small></button><button class="text-button" aria-label={'Изменить сведения '+doc.title} onclick={()=>openMetadataEditor(doc)}>Сведения</button><button class="delete" aria-label={'Удалить '+doc.title+' '+doc.version} onclick={()=>deleteDoc(doc.id)}>×</button></div>{/each}</div>
      <details class="demo-picker"><summary>Демонстрационные наборы</summary>{#each demos as demo}<button disabled={busy} onclick={()=>openDemo(demo.id)}>{demo.name}</button>{/each}</details>
      {#if LOCAL_EXECUTION}<div class="workspace-tools"><button class="secondary" disabled={busy||!hasSession} onclick={exportWorkspace}>Экспортировать</button><label class="secondary import-button" class:disabled={busy}>Импортировать<input type="file" accept="application/json,.json" disabled={busy} onchange={importWorkspace}/></label></div>{/if}
      <div class="privacy-note"><strong>{LOCAL_EXECUTION?'Локальное пространство':'Временное пространство'}</strong><p>{LOCAL_EXECUTION?'Документы сохраняются в этом браузерном профиле и остаются после обновления страницы. При создании пространства сайт просит браузер защитить хранилище от автоматической очистки. Это не резервная копия: регулярно экспортируйте важные документы.':'Удаление через 24 часа после создания. Содержимое не передаётся внешней модели. Не делитесь cookie сеанса.'}</p>{#if hasSession}<button class="text-button" onclick={clearWorkspace}>Удалить всё пространство</button>{/if}</div>
    </aside>
    <section class="work-main">
      <div class="work-heading"><div><p class="breadcrumb">Рабочее пространство</p><h1>Что говорят документы?</h1></div><span class="quiet-tag">Поиск по тексту</span></div>
      <form class="search-form" onsubmit={(e)=>{e.preventDefault();search();}}>
        <label for="question">Ваш вопрос</label><div class="query-box"><textarea id="question" name="question" rows="2" bind:value={question} maxlength="1000" minlength="2" required placeholder="Например, какая ёмкость аккумулятора?…"></textarea><button class="primary" disabled={busy}>{busy?'Поиск…':'Найти основания'}<span aria-hidden="true">↗</span></button></div>
        <div class="filters"><label>Набор<select aria-label="Набор" bind:value={family} onchange={()=>version=''}><option value="">Все документы</option>{#each families as f}<option value={f}>{demos.find(d=>d.id===f)?.name||f}</option>{/each}</select></label><label>Редакция<select aria-label="Редакция" bind:value={version}><option value="">Все редакции</option>{#each versions as v}<option value={v}>{v}</option>{/each}</select></label><label>По состоянию на<input type="date" bind:value={asOf} aria-describedby="date-note"/></label></div>
        <details class="settings"><summary>Параметры поиска</summary><label>Стратегия<select aria-label="Стратегия" bind:value={strategy}><option value="versioned">С учётом редакций</option><option value="adaptive">Размер контекста по перепаду BM25</option><option value="fixed5">Первые 5 фрагментов</option><option value="fixed10">Первые 10 фрагментов</option>{#if LOCAL_EXECUTION}<option value="research">EvidenceRAG: контроллер достаточности</option>{/if}</select></label><p id="date-note">Дата выбирает последнюю известную полную редакцию группы на этот день. Без даты система показывает историю версий. Адаптивный режим отбирает фрагменты по перепаду BM25; это не проверка смысловой достаточности. Неизвестные даты не подтверждают применимость.{#if LOCAL_EXECUTION} Режим EvidenceRAG запускает отдельный версионный контроллер; без подтверждённого оценщика он воздерживается от семантического вывода.{/if}</p></details>
      </form>
      {#if !result}<div class="starter"><h2>Проверьте на примере</h2><p>Выберите вопрос или задайте свой. Источники будут показаны дословно.</p><div class="suggestions">{#each suggestions as q}<button disabled={busy} onclick={()=>search(q)}>{q}<span aria-hidden="true">↗</span></button>{/each}</div>{#if !docs.length}<button class="secondary" disabled={busy} onclick={()=>openDemo('device')}>Открыть инструкцию «Север»</button>{/if}</div>{/if}
      {#if result && selectedStatus}<section class="search-results" aria-live="polite">
        <div class={'result-status '+selectedStatus.kind}><span class="status-mark" aria-hidden="true">{selectedStatus.kind==='warning'?'!':selectedStatus.kind==='success'?'✓':'≡'}</span><div><h2>{selectedStatus.title}</h2><p>{selectedStatus.description}</p></div></div>
        {#if result.research_trace?.answer.status==='answered'}<article class="formal-answer verified-answer"><h3>Краткий ответ</h3><p>{result.research_trace.answer.text||result.research_trace.answer.claims.map((claim:any)=>claim.text).join('; ')}</p><div class="answer-claims">{#each result.research_trace.answer.claims as claim}<div class="answer-claim"><p><strong>{claim.text}</strong>{#if claim.effective_date}<span class="claim-date">Действует с {claim.effective_date}</span>{/if}</p>{#each claim.citations as citation}<button class="source-link" onclick={()=>{const h=result?.hits.find(h=>h.evidence_id===citation.id);if(h)inspect(h.document,h.id);}}>Открыть подтверждающий фрагмент</button>{/each}</div>{/each}</div></article>{/if}
        {#if result.research_trace?.assessment.missing_information?.length}<section class="missing-facts"><h3>Что осталось неподтверждённым</h3>{#each result.research_trace.assessment.missing_information as gap}<p>{gap.description}</p>{/each}</section>{/if}
        {#if result.research_trace?.answer.status==='refused' && result.research_trace.assessment.supported_claims?.length}<section class="partial-facts"><h3>Что уже подтверждено</h3>{#each result.research_trace.assessment.supported_claims as claim}<div class="answer-claim"><p><strong>{claim.text}</strong>{#if claim.effective_date}<span class="claim-date">Действует с {claim.effective_date}</span>{/if}</p><button class="source-link" onclick={()=>{const h=result?.hits.find(h=>h.evidence_id===claim.evidence_ids[0]);if(h)inspect(h.document,h.id);}}>Открыть подтверждающий фрагмент</button></div>{/each}</section>{/if}
        {#if result.research_trace?.assessment.conflicting_claims?.length}<section class="missing-facts" aria-labelledby="research-conflicts"><h3 id="research-conflicts">Неразрешённые противоречия</h3>{#each result.research_trace.assessment.conflicting_claims as conflict}<p>{conflict.description}</p>{/each}</section>{/if}
        {#if result.research_trace?.assessment.version_constraints?.applied_amendment_evidence_ids?.length}<section class="partial-facts applied-amendments"><h3>Применённые поправки</h3>{#each result.research_trace.assessment.version_constraints.applied_amendment_evidence_ids as evidenceId}{@const amendment=result.hits.find((hit:any)=>hit.evidence_id===evidenceId)}<div class="answer-claim"><p><strong>{amendment?.title||'Связанный источник'}</strong>{#if amendment?.date}<span class="claim-date">от {amendment.date}</span>{/if}</p>{#if amendment}<button class="source-link" onclick={()=>inspect(amendment.document,amendment.id)}>Открыть текст поправки</button>{/if}</div>{/each}</section>{/if}
        {#if result.answer && !result.research_trace}<article class="formal-answer"><h3>Формальный вывод</h3><p>{result.answer.text}</p>{#each result.answer.citations as id}<button class="source-link" onclick={()=>{const h=result?.hits.find(h=>h.id===id);if(h)inspect(h.document,id);}}>Источник [{id}]</button>{/each}</article>{/if}
        {#if result.version_differences?.length}<div class="conflicts version-differences"><h3>Изменения между редакциями</h3>{#each result.version_differences as c}<details><summary>{c.field}</summary>{#each c.sources as s}<button class="conflict-source" onclick={()=>inspect(s.document,s.id)}><span>{s.date||'Дата неизвестна'} · редакция {s.version||'не указана'}</span><strong>{s.value}</strong><span>[{s.id}]</span></button>{/each}</details>{/each}<p class="fine">Буквальные значения различаются. Система не устанавливает, какое из них применимо и отменяет ли новая редакция старую.</p></div>{/if}
        {#if result.conflicts.length}<div class="conflicts"><h3>Несогласованные значения в одной редакции</h3>{#each result.conflicts as c}<details><summary>{c.field}</summary>{#each c.sources as s}<button class="conflict-source" onclick={()=>inspect(s.document,s.id)}><span>Редакция {s.version||'не указана'} · {s.date||'дата неизвестна'}</span><strong>{s.value}</strong><span>[{s.id}]</span></button>{/each}</details>{/each}<p class="fine">Найденные формулировки указывают на расхождение внутри редакции. Система не определяет смысловую совместимость или приоритет разделов.</p></div>{/if}
        <div class="evidence-heading"><h3>Найденные фрагменты <span class="count">{result.hits.length}</span></h3><span>{(result.research_trace?.elapsed_ms ?? result.elapsed_ms).toFixed(1)} мс · {result.research_trace?.trace.length ?? result.trace.length} {iterationWord(result.research_trace?.trace.length ?? result.trace.length)}{#if result.research_trace} · {confirmedClaimsLabel(result.research_trace.assessment.supported_claims.length)}{/if}</span></div>
        <div class="hits">{#each result.hits as hit}<article class="hit"><div class="hit-meta"><button class="citation" onclick={()=>inspect(hit.document,hit.id)}>[{hit.id}]</button><strong>{hit.title}</strong><span class="version-tag">{hit.version||'Без версии'}</span>{#if hit.research_role}<span class="version-tag">{hit.research_role==='revision_audit'?'аудит редакций':'участвовал в оценке'}</span>{/if}</div><blockquote>{hit.text}</blockquote><div class="hit-footer"><span>{hit.locator}{hit.page?' · с. '+hit.page:''}{hit.date?' · '+hit.date:''}</span><button class="source-link" onclick={()=>inspect(hit.document,hit.id)}>Открыть источник</button></div></article>{/each}</div>
        {#if !result.research_trace}<details class="trace"><summary>Как искала система</summary><p>{result.limitations}</p><p>Лексическое покрытие: {Math.round(result.lexical_coverage*100)}%. Это доля терминов вопроса, найденных в тексте, а не уверенность в ответе.</p>{#if result.gaps.length}<p>Не найдены термины: {result.gaps.join(', ')}.</p>{/if}{#each result.trace as step}<p>Шаг {step.iteration}: {step.query.join(', ')}. {step.reason==='lexical_coverage_reached'?'Термины найдены; смысл не проверен.':'Проверка недостающих терминов.'}</p>{/each}</details>{/if}
        {#if result.research_trace}<details class="trace research-trace"><summary>Трасса контроллера EvidenceRAG · {result.research_trace.termination}</summary><p>Оценщик: {result.research_trace.evaluator}. Оценка: {result.research_trace.assessment.status}. Ответ: {result.research_trace.answer.status==='answered'?'структурные правила и источники сверены; смысловая модель не применялась':result.research_trace.answer.refusal_reason}.</p><p>Бюджет: {result.research_trace.budget.max_iterations} итераций · {result.research_trace.budget.max_chunks} фрагментов · {result.research_trace.budget.time_budget_ms} мс. Время всего контроллера: {result.research_trace.elapsed_ms.toFixed(1)} мс.</p>{#each result.research_trace.trace as step}<article><strong>Итерация {step.iteration}: {step.action}</strong><p>Запрос: {step.query}</p><p>Найдено новых фрагментов: {step.new_evidence_chunk_count}; новых структурных утверждений: {step.new_evidence_claim_count}.</p><p>{step.assessment.reasoning_summary}</p><p>Причина: {step.reason}</p></article>{/each}<button class="text-button" onclick={()=>downloadResearchTrace(result?.research_trace)}>Скачать JSON-трассу</button></details>{/if}
      </section>{/if}
      {#if source}<section class="source-panel" aria-labelledby="source-title"><div class="source-header"><div><p class="breadcrumb">Первоисточник</p><h2 id="source-title" tabindex="-1">{source.title}</h2><p>Редакция {source.version||'не указана'} · {source.date||'Дата не указана'}</p></div><button class="secondary" onclick={()=>source=null}>Закрыть</button></div><a class="download" href={LOCAL_EXECUTION?'#':'/api/documents/'+source.id+'/original'} onclick={LOCAL_EXECUTION?(e)=>{e.preventDefault();void downloadOriginal(source)}:undefined} download={LOCAL_EXECUTION?undefined:true}>Скачать оригинал ({source.filename})</a>{#if source.status==='needs_ocr'}<p class="message">В PDF нет текстового слоя. Требуется распознавание.</p>{/if}{#each source.chunks as chunk}<article class:selected={source.selected===chunk.id} id={'chunk-'+chunk.id} tabindex="-1"><h3>[{chunk.id}] {chunk.locator}</h3><p>{chunk.text}</p></article>{/each}</section>{/if}
    </section>
  </div>
{:else if view==='compare'}
  <section class="wrap compare-page"><p class="breadcrumb">Работа с редакциями</p><h1>Что изменилось в документе?</h1><p class="lead">Сравните исходные формулировки. Различия значений выделяются отдельно и требуют проверки применимости.</p>
    {#if docs.length<2}<div class="starter"><h2>Нужны две редакции</h2><p>При загрузке укажите одинаковую группу документов и разные версии.</p><button class="primary" disabled={busy} onclick={()=>openDemo('device')}>Добавить демонстрационные инструкции</button></div>{:else}<form class="compare-form" onsubmit={(e)=>{e.preventDefault();compareDocs();}}><label>Исходная редакция<select bind:value={left} required><option value="">Выберите документ</option>{#each docs as d}<option value={d.id}>{d.title} — {d.version||d.filename}</option>{/each}</select></label><span class="compare-symbol" aria-hidden="true">⇄</span><label>Новая редакция<select bind:value={right} required><option value="">Выберите документ</option>{#each docs as d}<option value={d.id}>{d.title} — {d.version||d.filename}</option>{/each}</select></label><button class="primary" disabled={busy||left===right}>Сравнить</button></form>{/if}
    {#if comparison}<div class="message">{comparison.limitation}</div><div class="diff-legend"><span class="deletion">Удалено</span><span class="addition">Добавлено</span><span>{comparison.changes.length} блоков изменений</span></div>{#if !comparison.changes.length}<p>Текстовых изменений не найдено.</p>{/if}{#each comparison.changes as change}<div class="diff-block"><div class="diff-old"><h3>Исходный текст</h3>{#each change.old as line}<p>{line||' '}</p>{/each}</div><div class="diff-new"><h3>Новый текст</h3>{#each change.new as line}<p>{line||' '}</p>{/each}</div></div>{/each}{#if comparison.affected_questions.length}<section class="affected"><h2>Что стоит перепроверить</h2>{#each comparison.affected_questions as q}<p>{q}</p>{/each}</section>{/if}{/if}
  </section>
{:else if view==='research'}
  <section class="wrap research-page"><p class="breadcrumb">Метод и ограничения</p><h1>Проверяемость начинается<br/>с честных границ.</h1><p class="lead">«Основание» — инструмент поиска и исследовательский прототип адаптивного формирования контекста. Смысловую проверку произвольных утверждений система не выполняет.</p><div class="method-grid"><article><h2>Что происходит с вопросом</h2><ol><li>Русские слова нормализуются; фрагменты ранжируются SQLite FTS5/BM25.</li><li>Стратегия с адаптивным размером контекста отсекает фрагменты по перепаду BM25. Это эвристика релевантности, а не проверка достаточности.</li><li>В режиме EvidenceRAG ограниченные правила связывают явные атрибуты с датированными фрагментами и частичными поправками.</li><li>Неизвестные даты и конкурирующие применимые значения приводят к неопределённости или отказу.</li></ol></article><article><h2>Что считается подтверждением</h2><p>Совпадение слов и высокая позиция в поиске — не доказательство. Авторские правила и ограниченные грамматические шаблоны связывают явные значения с цитатами и датами редакций.</p><p>Это механическая проверка правил, не семантическая модель. Она не подтверждает произвольные формулировки, сложные отрицания или юридическую силу источника.</p></article><article><h2>Исследовательская гипотеза</h2><p>Проверяем, помогает ли явное сохранение истории редакций уменьшить ошибки выбора источников и стоимость контекста. Новизна и преимущество метода не установлены.</p><p>Экспериментальные конфигурации включают fixed-k, score-gap adaptive-k, итеративный поиск без подключённого судьи достаточности и прототип EvidenceRAG. Все демонстрационные корпуса синтетические; качество ответов и семантическая достаточность не измерены.</p></article><article><h2>Приватность</h2><p>{LOCAL_EXECUTION?'Рабочее пространство хранится в OPFS браузера, а случайный указатель на него — в IndexedDB. Очистка данных сайта может удалить документы. Приложение не отправляет их на собственный API и не загружает внешнюю модель.':'Пространство доступно по закрытому cookie текущего браузера. Срок хранения — 24 часа от создания. До 20 документов, до 10 МБ на файл и 40 МБ суммарно.'}</p><p>{LOCAL_EXECUTION?'Для удаления откройте раздел «Документы». Важные данные регулярно экспортируйте.':'Внешняя модель отключена. Данные не используются для обучения. Для удаления откройте раздел «Документы».'}</p></article></div><h2>На какие исследования опираемся</h2><ul class="reading"><li><a href="https://research.google/pubs/sufficient-context-a-new-lens-on-retrieval-augmented-generation-systems/" target="_blank" rel="noreferrer">Sufficient Context (2025)</a> — отдельная оценка достаточности контекста.</li><li><a href="https://aclanthology.org/2025.acl-long.319/" target="_blank" rel="noreferrer">Adaptive Retrieval Without Self-Knowledge? (ACL 2025)</a> — сравнение adaptive retrieval и uncertainty-based методов.</li><li><a href="https://aclanthology.org/2025.emnlp-main.1017/" target="_blank" rel="noreferrer">Adaptive-k (EMNLP 2025)</a> — выбор размера контекста по сходству фрагментов.</li><li><a href="https://aclanthology.org/2026.acl-long.1185/" target="_blank" rel="noreferrer">S2G-RAG (ACL 2026)</a> — обученный судья достаточности, структурированные пробелы и компактный контекст.</li><li><a href="https://aclanthology.org/2026.findings-emnlp.398/" target="_blank" rel="noreferrer">TimelyRAG (Findings EMNLP 2026)</a> — семантическое и временное ранжирование в редакциях с перекрывающимися изменениями.</li></ul></section>
{:else}
  <section class="wrap cookie-page">
    <p class="breadcrumb">Приватность и технологии сайта</p>
    <h1>{LOCAL_EXECUTION?'Локальное хранение':'Политика cookie'}</h1>
    {#if LOCAL_EXECUTION}
      <p class="lead">В локальном режиме сайт не создаёт cookie и не отправляет документы на сервер. Рабочее пространство хранится в OPFS, а указатель на него — в IndexedDB этого браузерного профиля.</p>
      <section class="cookie-detail"><h2>Что важно знать</h2><p>Документы, индекс и поисковые запросы обрабатываются в браузере на этом устройстве. Они не отправляются приложением на backend или внешние API. Локальные данные доступны только в текущем браузерном профиле. Очистка данных сайта, удаление профиля или политика браузера могут удалить документы без возможности восстановления. Сохраняйте экспортную копию после добавления важных документов.</p><p>Для доставки статических файлов GitVerse технически получает IP-адрес и параметры HTTP-запроса. Их обработка на стороне хостинга регулируется <a href="https://gitverse.ru/files/politika-konfidencialnosti.pdf" target="_blank" rel="noreferrer">политикой конфиденциальности GitVerse</a>; проект не управляет журналами и сроками хранения хостинга. Приложение не использует аналитику, рекламу, сторонние cookie или внешние модели.</p></section>
      <section class="cookie-detail"><h2>Удаление</h2><p>Удалите отдельный документ или всё рабочее пространство через раздел «Документы». Для удаления резервных копий браузера также используйте настройки хранения самого браузера.</p></section>
      <p class="cookie-updated">Редакция от 31 октября 2026 года.</p>
    {:else}
    <p class="lead">На сайте нет рекламных или аналитических cookie. Для временного рабочего пространства используется один необходимый cookie.</p>
    <section class="cookie-detail" aria-labelledby="cookie-purpose">
      <h2 id="cookie-purpose">Что сохраняется</h2>
      <dl class="cookie-table">
        <div><dt>Название</dt><dd><code>evidence_session</code></dd></div>
        <div><dt>Для чего</dt><dd>Связывает ваш браузер с созданным вами временным пространством и не даёт другим посетителям открыть его документы.</dd></div>
        <div><dt>Когда появляется</dt><dd>Только когда вы начинаете действие, которому нужно рабочее пространство: открываете демонстрационный набор, ищете или загружаете документ.</dd></div>
        <div><dt>Срок</dt><dd>Не более 24 часов. После этого сеанс истекает, а документы и индекс удаляются автоматически.</dd></div>
        <div><dt>Защита</dt><dd>Cookie недоступен JavaScript (<code>HttpOnly</code>), передаётся только по HTTPS (<code>Secure</code>) и ограничен сайтом (<code>SameSite=Strict</code>). В адресную строку он не попадает.</dd></div>
      </dl>
    </section>
    <section class="cookie-detail">
      <h2>Чего сайт не использует</h2>
      <p>Нет аналитики, рекламных идентификаторов, профилирования и сторонних cookie. Интерфейс не сохраняет данные в <code>localStorage</code> или <code>sessionStorage</code>. Содержимое документов не отправляется внешним моделям.</p>
    </section>
    <section class="cookie-detail">
      <h2>Управление cookie</h2>
      <p>Плашка cookie — информационная: кнопка «Понятно» лишь скрывает её до перезагрузки страницы и не является согласием на обработку данных. Если очистить cookie в браузере, доступ к временному пространству потеряется; его данные удалятся по истечении срока хранения.</p>
      <p>Подробнее о технической реализации и временном хранении документов — на странице <a href={paths.research} onclick={(e)=>followLink(e,'research')}>«Метод и ограничения»</a>.</p>
    </section>
    <p class="cookie-updated">Редакция от 31 октября 2026 года.</p>
    {/if}
  </section>
{/if}
</main>
<footer class="footer wrap"><span>Основание <span class="muted">/ EvidenceRAG</span></span><span>Исследовательский прототип · источники важнее уверенного тона</span><div class="footer-links"><a class="text-button" href={paths.research} onclick={(e)=>followLink(e,'research')}>Метод и ограничения</a><a class="text-button" href={paths.cookies} onclick={(e)=>followLink(e,'cookies')}>Cookie</a></div></footer>
<dialog bind:this={uploadDialog} class="upload-dialog"><div class="dialog-heading"><h2>Добавить документы</h2><button class="secondary" onclick={()=>{uploadDialog.close();uploadItems=[];error='';}} aria-label="Закрыть окно загрузки">Закрыть</button></div><p>Выберите файлы или ZIP. Названия, версии и даты будут предложены по содержимому; каждый файл можно исправить перед добавлением.</p><form bind:this={uploadForm} onsubmit={upload}><label class="drop-zone" class:active={uploadDropActive} ondragover={(e)=>{e.preventDefault();uploadDropActive=true;}} ondragleave={()=>uploadDropActive=false} ondrop={droppedFiles}>Перетащите сюда документы или выберите их<input name="files" type="file" multiple accept=".pdf,.docx,.txt,.md,.zip" onchange={selectedFiles}/></label><p class="fine">PDF, DOCX, TXT или Markdown: до 10 МБ на файл. ZIP: до 25 МБ, до 20 документов и 25 МБ после распаковки. Архивы внутри ZIP не принимаются. Для сканов PDF требуется OCR.</p>
  {#if uploadItems.length}<div class="upload-queue" aria-label="Очередь документов">{#each uploadItems as item,index}<article class="upload-item"><div class="upload-item-heading"><strong>{item.file.name}</strong><span>{item.status==='ready'?'Готов к добавлению':item.status==='analyzing'?(item.stage||'Анализ…'):'Ошибка'}</span>{#if item.status==='error'}<button type="button" class="text-button" onclick={()=>retryUpload(item)}>Повторить</button>{/if}<button type="button" class="delete" aria-label="Убрать из очереди" onclick={()=>uploadItems.splice(index,1)}>×</button></div>{#if item.status==='ready'}<div class="upload-fields"><label>Название<input bind:value={item.metadata.title} maxlength="160"/></label><label>Группа редакций<input bind:value={item.metadata.family} maxlength="100"/></label><div class="form-pair"><label>Версия<input bind:value={item.metadata.version} maxlength="40"/></label><label>Действует с<input type="date" bind:value={item.metadata.date}/></label></div><details><summary>Дополнительные сведения</summary><label>Тип документа<select bind:value={item.metadata.document_type}><option value="unknown">Не определён</option><option value="full_edition">Полная редакция</option><option value="amendment">Поправка</option></select></label></details><small>Происхождение: {Object.entries(item.proposals||{}).map(([key,value]:any)=>`${key}: ${value.source}`).join(' · ')}. Пустая дата означает, что применимость не установлена.</small></div>{:else if item.message}<p class="message error">{item.message}</p>{/if}</article>{/each}</div>{/if}
  {#if error}<p class="message error" role="alert">{error}</p>{/if}<button type="button" class="secondary full" onclick={()=>uploadItems=[]} disabled={!uploadItems.length||busy}>Очистить очередь</button><button class="primary full" disabled={busy||!uploadItems.some(item=>item.status==='ready')}>{busy?busyMessage:`Добавить ${uploadItems.filter(item=>item.status==='ready').length} ${documentWord(uploadItems.filter(item=>item.status==='ready').length)}`}</button></form></dialog>
<dialog class="upload-dialog" bind:this={metadataDialog} onclose={()=>editingDoc=null}>
  {#if editingDoc}<div class="dialog-heading"><h2>Сведения документа</h2><button type="button" class="secondary" onclick={closeMetadataEditor}>Закрыть</button></div><form onsubmit={(event)=>{event.preventDefault();void saveMetadataEdit();}}>
    <label>Название<input bind:value={editFields.title} maxlength="160" required/></label><label>Группа редакций<input bind:value={editFields.family} maxlength="100"/></label><div class="form-pair"><label>Версия<input bind:value={editFields.version} maxlength="40"/></label><label>Действует с<input type="date" bind:value={editFields.date}/></label></div>
    <label>Тип документа<select bind:value={editFields.document_type}><option value="unknown">Не определён</option><option value="full_edition">Полная редакция</option><option value="amendment">Поправка</option></select></label><label>Изменяет документ<select bind:value={editFields.amends_document_id}><option value="">Связь не указана</option>{#each docs.filter(doc=>doc.id!==editingDoc?.id) as target}<option value={target.id}>{target.title} · {target.version||target.filename}</option>{/each}</select></label>
    <details><summary>Источник предложенных сведений</summary>{#each metadataSuggestionEntries(editingDoc) as entry}<p><strong>{entry[0]}</strong>: {(entry[1] as any).source||'не указан'}{(entry[1] as any).quote?` · «${(entry[1] as any).quote}»`:''}</p>{/each}</details>
    {#if error}<p class="message error" role="alert">{error}</p>{/if}<button type="submit" class="primary full" disabled={busy}>{busy?'Сохраняем…':'Сохранить сведения'}</button>
  </form>{/if}
</dialog>
