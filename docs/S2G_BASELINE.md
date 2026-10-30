# План воспроизведения официального S2G-RAG

Источник: https://github.com/nianaaa/S2G-RAG . Проверены README.md, requirements.txt и run_S2G-RAG.py. Это не запуск и не собственная «облегчённая реализация» официального метода.

На отдельной Linux CUDA-машине, после проверки лицензий моделей/данных и выделения ресурсов:

```sh
git clone https://github.com/nianaaa/S2G-RAG.git
cd S2G-RAG
git rev-parse HEAD > SOURCE_COMMIT.txt
conda create -n s2g-rag python=3.10 -y
conda activate s2g-rag
# PyTorch устанавливается по официальной инструкции для имеющегося CUDA.
pip install transformers accelerate peft trl datasets pandas numpy scikit-learn openai pyserini pysbd beir tqdm sentencepiece protobuf
python run_S2G-RAG.py
```

Launcher интерактивный: выбрать уникальное имя эксперимента, hotpotqa/triviaqa/2wikimultihopqa, GPT=no, доступные CUDA devices, weighted training по протоколу baseline и top_docs. Он генерирует bash_scripts/<experiment>.sh. Изучить этот файл перед запуском. Подготовить пути к моделям, retrieval и CSV по README зафиксированного commit. Не исполнять непроверенные команды автоматически и не передавать платный ключ.

Launcher вызывает generation → prepare_training → training → inference. Поэтому «запустить baseline» — не то же, что импортировать Python-функцию. Необходимый VRAM и время не измерены; определить пилотным запуском на GPU-стенде. В readme и requirements есть различия состава зависимостей, поэтому после успешного setup зафиксировать отдельный lock/environment и полный hardware manifest.

Для честного сравнения нужны одинаковые вопросы, corpus/retriever, границы контекста и оценщик. Сначала воспроизвести авторский протокол на одном официальном наборе; затем отдельно адаптировать интерфейс к нашему version corpus, явно описав изменения. Сохранить число вызовов судьи, генератора и токены, а не только retrieval iterations.

Блокирующие факторы сейчас: нет выделенного CUDA-стенда/весов/подготовленного официального retrieval-корпуса; расход ресурсов несовместим с VPN-VPS. Никаких результатов S2G в наших таблицах нет.
