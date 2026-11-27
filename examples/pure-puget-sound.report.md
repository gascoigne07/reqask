# Отчёт о проверке требований: pure-puget-sound.pdf

Отчёт сформирован агентом reqask автоматически по ISO/IEC/IEEE 29148:2018 и IEEE 830. Модель: claude-haiku-5-5. Дата: 2026-11-27 03:29:53 +0500.

**Вердикт: Не рекомендуется начинать.**

- Готовность к разработке: **Нет**
- Готовность к тестированию: **Нет**
- Требований: 29, с дефектами: 29. Замечаний: CRITICAL 7, MAJOR 61, MINOR 12. Вопросов автору: 15.
- Отметка «замечаний не найдено» не доказывает, что требование верное. Что агент не проверяет: [раздел 6](#limits).

**Блокеры:**

- [S-01](#s-01) · [REQ-16](#req-16), [REQ-17](#req-17) · Право просмотра оценок другим актором: в 3.5.2 запрещено, в 3.5.3 разрешено при оспаривании
- [S-02](#s-02) · [REQ-10](#req-10), [REQ-12](#req-12) · Термин «page» определён по-разному в разных разделах
- [S-20](#s-20) · [REQ-01](#req-01) · Состав релиза зависит от срока и бюджета, которые в документе не заданы
- [D-03](#d-03) · [REQ-02](#req-02) · Из-за where appropriate нельзя определить, в каких случаях загрузка должна быть разрешена, поэтому тест не имеет критерия успеха
- [D-13](#d-13) · [REQ-07](#req-07) · Критерий «conducive to speech» не даёт способа проверить, что аудио сохранено в нужном формате
- [D-22](#d-22) · [REQ-11](#req-11) · Строка 186 говорит, что поиск заменяет иерархические ссылки
- [D-53](#d-53) · [REQ-25](#req-25) · Основная фраза требует доступности 24 часа в сутки и 7 дней в неделю, а пояснение признает достаточным 99% времени доступности и не исключает плановые простои

**Главные вопросы автору ТЗ:**

- [Q-01](#q-01) · заказчику (бизнес): Кому доступна история изменений оценки: только курсовому администратору или также студенту, чью оценку меняли?
- [Q-02](#q-02) · аналитику: Что считается страницей для веб-лент в 3.3.1: отдельный блок курса или любая отдельная страница?
- [Q-03](#q-03) · заказчику (бизнес): Кто определяет, на каких страницах допустима загрузка файлов и голосовых клипов: заданный перечень типов страниц или курсовой администратор?
- [Q-04](#q-04) · заказчику (бизнес): До какой даты определяется состав приоритета 3 в релизе, если срок и бюджет в документе не заданы?
- [Q-05](#q-05) · заказчику (бизнес): Строка 186 говорит о замене иерархических ссылок, строка 187 о поиске в дополнение к иерархии: что верно?

Все вопросы в [разделе 7](#questions), для отправки автору: файл `report.questions.md`.

## 1. Паспорт прогона

| Прогон | Значение |
| :--- | :--- |
| Документ | pure-puget-sound.pdf, формат pdf, строк 258 |
| Чтение PDF | страницы без текста: 3; удалено строк колонтитулов: 52 |
| SHA-256 документа | `bc8fea411b7e40f114e453f09451cd3777da5f218f0d1414fbb640ec5ed9dce8` |
| Дата и время | 2026-11-27 03:29:53 +0500 |
| Длительность | 762.5 с |
| Модель | claude-haiku-5-5 (провайдер: anthropic) |
| Версия агента | 0.1.0, коммит b9ec28d |
| Режим | живой прогон, часть ответов из кэша; формат ответа JSON: parse |
| Стандарты | ISO/IEC/IEEE 29148:2018 п. 5.2.5 и 5.2.6; IEEE Std 830-1998 п. 4.3 |
| Обращений к модели | 13, из кэша 1, повторов при сбоях 0 |
| Токены | вход 251591, выход 193561, всего 445152 |

| Самопроверка прогона | Значение |
| :--- | :--- |
| Покрытие нарезкой | строк с текстом 197, в требованиях 72 (37%), отмечены как не требования 125 (заголовки, вводный текст, шаблоны, см. раздел 2), не разобраны 0 |
| Цитаты | точных 105, нечётких 0, не найдено 0; замечаний в карантине 0, противоречий только с вопросом 0, свёрнуто в системные 0, отброшено без опоры на текст 0 (ни найденной цитаты, ни ссылки на требование или раздел; в отчёт не вошли) |
| Критик | проверено CRITICAL и MAJOR 80: оставлено 68, понижено 0, снято 1, слито 11, без решения 0, решений отклонено кодом 22; повтор по замечаниям без решения: решено 1 |
| Ответы модели | исправлений JSON 0, отброшено дефектов проверкой 0, оценок 0; оценок не вернула модель 0, pass заменён на fail по дефекту 0; CRITICAL и MAJOR без вопроса 0; уровень поднят кодом по виду расхождения 1 |
| Обрезки ответа | обрезано по лимиту длины 0; делений куска нарезки или порции пополам 0; повторов после обрезки 0 |
| Сводные вопросы | от модели; отброшено проверкой 0, слито дублей 0, добавлено кодом для CRITICAL 0 |
| Шаги | выполнено 8, частично 0, не выполнено 0 |
| Правила | подсказок словаря 12, подтверждено моделью 7 (58%); строк с незаполненными местами (TODO, TBD и подобные) 2: 109, 227; есть в замечаниях 2 |

<details><summary>Журнал шагов</summary>

| Шаг | Что | Итог | Вызовов | Секунд | Результат |
| :-- | :--- | :--- | :-- | :-- | :--- |
| 0 | Чтение документа | выполнен | 0 | 0.0 | строк 258, формат pdf |
| 3 | Нарезка требований (258 строк) | выполнен | 0 | 0.0 | требований 29, пропущено фрагментов 56 |
| 4 | Проверка каждого требования | выполнен | 7 | 476.8 | дефектов 63, без проверки 0 |
| 5 | Набор требований целиком (три прохода) | выполнен | 3 | 151.2 | замечаний 29, из них граничных случаев 10, анализов по критериям 8 |
| 6 | Нумерация и свёртка замечаний, итог сверки цитат | выполнен | 0 | 0.0 | замечаний 92, свёрнуто в системные 0; сверка цитат на шагах 4 и 5: точных 105, нечётких 0, не найдено 0; в карантине 0, противоречий только с вопросом 0, отброшено без опоры 0 |
| 7 | Критик | выполнен | 2 | 75.9 | проверено 80 (групп кандидатов на слияние 21): оставлено 68, понижено 0, снято 1, слито 11, без решения 0, отклонено кодом 22 |
| 8 | Итог и сводные вопросы | выполнен | 1 | 58.7 | решение: Не рекомендуется начинать; вопросов 15 |
| 9 | Отчёт | выполнен | 0 | 0.0 | записаны: pure-puget-sound.report.md, pure-puget-sound.report.questions.md, pure-puget-sound.report.json |

</details>

## 2. Нарезка на требования

Выделено требований: **29**. Номер из документа стоит у 21 требований, это номера пунктов списка. Границы заданы номерами строк, текст требований вырезан из документа кодом. Дословный текст каждого требования стоит в разделе 3.

<details><summary>Таблица нарезки: 29 требований</summary>

| ID | ID в документе | Раздел | Строки | Суть |
| :--- | :--- | :--- | :--- | :--- |
| [REQ-01](#req-01) | без номера | 3. Specific Requirements | 156, стр. 8 | Релиз доставляет приоритеты 1 и 2 и часть приоритета 3 |
| [REQ-02](#req-02) | без номера | 3.1 Multiple File Transfer | 158-160, стр. 8 | Система должна захватывать и управлять файлами, где уместно |
| [REQ-03](#req-03) | 3.1.1 | 3.1 Multiple File Transfer | 162-163, стр. 9 | Множественная загрузка файлов настраивается на уровне страницы |
| [REQ-04](#req-04) | без номера | 3.2 Audio Recording | 165-166, стр. 9 | Система должна фиксировать и организовывать голосовые клипы |
| [REQ-05](#req-05) | 3.2.1 | 3.2 Audio Recording | 168-172, стр. 9 | Актор организует голосовые клипы в портфолио |
| [REQ-06](#req-06) | 3.2.2 | 3.2 Audio Recording | 173-174, стр. 9 | Актор скачивает голосовые клипы в гибком формате |
| [REQ-07](#req-07) | 3.2.3 | 3.2 Audio Recording | 175-176, стр. 9 | Аудиоклипы хранятся в формате, пригодном для речи |
| [REQ-08](#req-08) | 3.2.4 | 3.2 Audio Recording | 177-178, стр. 10 | Актор удаляет записанные голосовые клипы |
| [REQ-09](#req-09) | без номера | 3.3 Web Feeds | 180-181, стр. 10 | Система отображает веб-ленты для элементов страниц курса |
| [REQ-10](#req-10) | 3.3.1 | 3.3 Web Feeds | 183-184, стр. 10 | Веб-ленты включаются и выключаются для каждой страницы |
| [REQ-11](#req-11) | без номера | 3.4 Search | 186-187, стр. 10 | Поиск как способ навигации вместо иерархических ссылок |
| [REQ-12](#req-12) | 3.4.1 | 3.4 Search | 189-194, стр. 10 | Актор ищет страницы в курсе, включая отдельную страницу поиска |
| [REQ-13](#req-13) | 3.4.2 | 3.4 Search | 195-196, стр. 11 | Поле поиска на каждой странице после входа актора |
| [REQ-14](#req-14) | без номера | 3.5 Gradebook | 198, стр. 11 | Курсовой администратор выставляет оценки за задания |
| [REQ-15](#req-15) | 3.5.1 | 3.5 Gradebook | 200-201, стр. 11 | Оценка задания по соотношению баллов с отзывом и временной меткой |
| [REQ-16](#req-16) | 3.5.2 | 3.5 Gradebook | 202-203, стр. 11 | Оценки показываются только владельцу и администратору курса |
| [REQ-17](#req-17) | 3.5.3 | 3.5 Gradebook | 204-205, стр. 11 | Система ведёт историю изменений оценок за задание |
| [REQ-18](#req-18) | без номера | 3.6 Social Networking Applications | 207, стр. 12 | Социальные компоненты должны интегрироваться в Moodle |
| [REQ-19](#req-19) | 3.6.1 | 3.6 Social Networking Applications | 209-210, стр. 12 | Вики для совместного создания связанных документов |
| [REQ-20](#req-20) | 3.6.2 | 3.6 Social Networking Applications | 211-212, стр. 12 | Блог-движок с общей аутентификацией и уведомлениями |
| [REQ-21](#req-21) | 3.7.1 | 3.7 Notifications | 216-218, стр. 12 | E-mail и SMS уведомления об изменениях страниц |
| [REQ-22](#req-22) | 4.1.1 | 4.1 Usability | 221-224, стр. 12 | Простой адаптивный интерфейс с единой административной точкой настройки |
| [REQ-23](#req-23) | 4.2.1 | 4.2 Reliability | 226-227, стр. 13 | Резервное копирование по настраиваемому расписанию, ежедневно |
| [REQ-24](#req-24) | без номера | 4.2 Reliability | 228, стр. 13 | Восстановление данных из резервной копии в течение шести часов |
| [REQ-25](#req-25) | 4.2.2 | 4.2 Reliability | 230-233, стр. 13 | Доступность системы круглосуточно при 99% времени работы |
| [REQ-26](#req-26) | 4.3.1 | 4.3 Performance | 235-237, стр. 13 | Поддержка не менее 1000 одновременных пользователей |
| [REQ-27](#req-27) | 4.4.1 | 4.4 Supportability | 239-241, стр. 13 | Поддержка системы без существенной модификации |
| [REQ-28](#req-28) | 4.6.1 | 4.6 On-line User Documentation and Help System Requirements | 244-246, стр. 14 | Релевантная онлайн-документация доступна на каждой странице |
| [REQ-29](#req-29) | 4.6.2 | 4.6 On-line User Documentation and Help System Requirements | 247-250, стр. 14 | Администраторы получают поисковую документацию по обслуживанию |

</details>

Не вошли в требования (эти строки видит проверка набора в разделе 4):

- служебные сведения: строки 3-21
- история изменений: строки 22-40
- заголовки: строки 41-102, 103-105, 108, 114-115, 117, 119, 121, 123-124, 126, 131-132, 137, 140-141, 143, 145, 147, 149, 157, 164, 179, 185, 197, 206, 213, 219-220, 225, 234, 238, 242-243, 251-255, 256-258
- вводный и поясняющий текст: строки 106-107, 109-113, 116, 118, 120, 122, 125, 127-130, 133-136, 138-139, 142, 144, 146, 148, 150-155, 214
- прочее: строки 161, 167, 182, 188, 199, 208, 215, 229

## 3. Проверка каждого требования

Значки: ✅ замечаний не найдено, ❌ нарушен, ➖ не применим, ❔ нельзя оценить по тексту. Шесть основных критериев показаны всегда, уместность уровня, атомарность и корректность только при нарушении.

**Дефект описан в общем замечании, на которое ссылается строка (2):**

- <a id="req-01"></a>**REQ-01 · строка 156 · страница 8 · 3. Specific Requirements**: слито критиком: [D-01](#d-01) в [S-20](#s-20), [D-02](#d-02) в [S-20](#s-20); ❌ Однозначность: Срок и бюджет не заданы, поэтому объём Priority 3 не определён; ❔ Осуществимость: Осуществимость зависит от срока и бюджета, которые в документе не заданы; ❌ Проверяемость: Набор требований Priority 3 не фиксирован, выполнение проверить нельзя.
  > The initial production release of the University of Puget Sound’s enhancements to Moodle will deliver the Priority 1 (Core) and Priority 2 set of requirements, along with such Priority 3 requirements as can be developed within the project timeframe and budget constraints.
- <a id="req-08"></a>**REQ-08 · 3.2.4 · строки 177-178 · страница 10 · 3.2 Audio Recording**: слито критиком: [D-16](#d-16) в [S-10](#s-10); ❌ Полнота: Не описано, что происходит с клипом, прикреплённым к странице или заданию.
  ```text
  3.2.4 The system must allow actors to delete recorded clips.
  Since voice clips should be stored in a portfolio for each actor during his or her existence in the course management system, he or she should be able to examine his or her portfolio to select and delete clips if he or she chooses to. This allows him or her to manage archived voice clips and to create a cohesive portfolio that actors in the role of professor can use to judge improvement over time.
  ```

### <a id="req-02"></a>REQ-02 · строки 158-160 · страница 8 · 3.1 Multiple File Transfer
```text
The system must be able to capture and manage files where appropriate.
One of the fundamental tasks of the system is to allow actors to upload and manage files on certain pages of the system. These might include assignment submission pages, forum pages, wiki pages, and announcement pages. An actor in the role of course administrator should be able to optionally upload multiple files where he or she finds that such as feature would be useful—such as on a devoted project page.
For this requirement, page refers to any distinct upload point (e.g., an assignment, a wiki page, a forum post, etc.).
```

Оценки: ✅ Необх. ❌ Однозн. ❌ Полн. ❔ Осущ. ❌ Пров. ✅ Непрот.
- ❌ Однозначность: Фраза where appropriate не определяет, на каких страницах и когда допускается загрузка
- ❔ Осуществимость: Технические и ресурсные ограничения в тексте не описаны, оценить нельзя

<a id="d-03"></a>**D-03 [CRITICAL] Проверяемость.** Из-за where appropriate нельзя определить, в каких случаях загрузка должна быть разрешена, поэтому тест не имеет критерия успеха. Цитата: `capture and manage files where appropriate` (строка 158). Последствие: Невозможно проверить требование тестом, так как ожидаемый результат не определён.
- Критик слил сюда: [D-04](#d-04), их текст в [приложении Б](#appendix-b).
- Вопрос заказчику (бизнес): Кто решает, уместна ли загрузка на странице: система по заданному перечню типов страниц или курсовой администратор? См. [Q-03](#q-03).

<a id="d-05"></a>**D-05 [MAJOR] Полнота.** Требование не задаёт ограничения на типы и размер файлов, их число и поведение при ошибке загрузки. Цитата: `The system must be able to capture and manage files` (строка 158). Последствие: Нельзя реализовать проверку файлов и описать тест на граничные значения.
- Вопрос аналитику: Какой максимальный размер одного загружаемого файла задать, в мегабайтах?

**Готовая формулировка:** The system must be able to capture and manage files on <list of page types that accept uploads>, with a maximum file size of <N MB> per file, and the behavior for a file over this limit must be <behavior when file exceeds limit>.

### <a id="req-03"></a>REQ-03 · 3.1.1 · строки 162-163 · страница 9 · 3.1 Multiple File Transfer
```text
3.1.1 The system must allow for multiple file upload to be configured on a per-page basis.
Actors in the capacity of course administrator or professor should be able to enable multiple file uploads on a page of his or her choosing. For collaborative projects, it becomes important for actors to be able to upload more than one file to a given page, especially in the case of an assignment submission where the assignment might include multiple parts. Such a construct should be offered to the actor during a page’s creation and editing stages.
```

Оценки: ✅ Необх. ❌ Однозн. ❌ Полн. ✅ Осущ. ✅ Пров. ✅ Непрот.

<a id="d-06"></a>**D-06 [MAJOR] Однозначность.** Слово construct не говорит, какой элемент управления показать. Место показа описано только как creation and editing stages. Цитата: `Such a construct should be offered to the actor` (строка 163). Последствие: Нельзя спроектировать форму страницы и проверить, где доступна настройка.
- Вопрос аналитику: Какой элемент интерфейса включает множественную загрузку на странице: флажок в форме страницы?

<a id="d-07"></a>**D-07 [MAJOR] Полнота.** Не задано максимальное число файлов в одной загрузке, поэтому граница диапазона не определена. Цитата: `allow for multiple file upload to be configured` (строка 162). Последствие: Нельзя написать граничный тест и оценить объём хранения файлов.
- Вопрос заказчику (бизнес): Какое максимальное число файлов задать в одной загрузке: заданное число, например 5?

**Готовая формулировка:** The system must allow for multiple file upload to be configured on a per-page basis, with a maximum of <maximum number of files per upload> files, and the setting must be offered to the actor as <UI control> during page creation and editing.

### <a id="req-04"></a>REQ-04 · строки 165-166 · страница 9 · 3.2 Audio Recording
```text
The system must be able to capture and organize voice clips that can be used where appropriate.
One of the shortcomings of the current courseware system is that the foreign language department is unable to capture and track voice clips—recorded by students—for oral homework over the course of a student’s education.
```

Оценки: ✅ Необх. ❌ Однозн. ✅ Полн. ✅ Осущ. ❔ Пров. ✅ Непрот.
- ❔ Проверяемость: Без условия использования нельзя определить критерий успешного выполнения

<a id="d-08"></a>**D-08 [MAJOR] Однозначность.** Слово «appropriate» оставляет на усмотрение реализатора, на каких страницах клипы допустимы. Строка 166 описывает только устные домашние задания и не задаёт условие. Цитата: `that can be used where appropriate` (строка 165). Последствие: Нельзя определить, для каких страниц или заданий реализовывать сохранение и использование клипов.
- Вопрос заказчику (бизнес): На какие типы страниц или заданий распространяется использование голосовых клипов: заданный перечень типов страниц или все страницы с загрузкой файлов? См. [Q-03](#q-03).

**Готовая формулировка:** The system must be able to capture and organize voice clips that can be used on <list of page types>.

### <a id="req-05"></a>REQ-05 · 3.2.1 · строки 168-172 · страница 9 · 3.2 Audio Recording
```text
3.2.1 The system must allow actors to organize their voice clips into a portfolio.
Equal and finite drive space needs to be allotted to each actor in the role of professor or administrator to allow for the storing of voice clips recorded and submitted by all actors in the roles of students. Actors in the role of professor or system administrator should be allowed to partition this space for actors in the roles of students. This can be done one of two ways: 1) the actor can be allowed to preview the voice clip before it is archived and determine whether or not he or she would like that clip to be archived, or 2) a newly created voice clip can be automatically archived. The first option would allow the actor to throw out an audio clip that is deemed to be unsuitable or inappropriate for an assignment without having to take it out of an archive of voice clips. The actor should have the option to have the voice clip be archived after a preview has taken place. The second option would automatically archive a voice clip once submitted but would require that the actor interact with the archived file. Thus, if the actor chooses to delete the file, it would need to be deleted from the archive of voice clips.
Maintaining an archive of voice clips makes it possible for comparisons to be made between clips to determine whether an actor is improving his or her language skills over multiple courses.
The actor should be able to optionally attach one of his or her archived items to any page where uploads are permitted.
The term archive used above may also be referred to as a portfolio.
```

Оценки: ✅ Необх. ❌ Однозн. ❌ Полн. ❌ Атом. ✅ Осущ. ❔ Пров. ✅ Непрот.
- ❌ Однозначность: Текст называет два способа архивации и не выбирает, какой обязателен
- ❌ Полнота: Объём дискового пространства не задан, поведение при заполнении не описано
- ❔ Проверяемость: Проверка квоты зависит от объёма, который документ не задаёт

<a id="d-11"></a>**D-11 [MINOR] Атомарность.** В требовании 3.2.1 объединены квота хранилища, способ архивации и прикрепление архивного клипа к страницам. Это разные возможности. Цитата: `The actor should be able to optionally attach one of his or her archived items to any page where uploads are permitted.` (строка 171).

Слито критиком: [D-09](#d-09) в [S-18](#s-18), [D-10](#d-10) в [S-17](#s-17).

**Готовая формулировка:** 3.2.1 The system must allow actors to organize their voice clips into a portfolio. Each actor in the role of professor or system administrator must be allotted <storage size in MB> of drive space for voice clips recorded and submitted by actors in the role of student. The actor must archive a voice clip by <archiving method>.

### <a id="req-06"></a>REQ-06 · 3.2.2 · строки 173-174 · страница 9 · 3.2 Audio Recording
```text
3.2.2 The system must allow actors to download their voice clips in a flexible format.
Voice clips should be optionally downloadable in a format such as MPEG Audio (mp3) format, since it is widely supported across different web browsers and operating systems. Voice clips should be downloadable for archival purposes or for the purpose of presenting them to other actors.
```

Оценки: ✅ Необх. ❌ Однозн. ✅ Полн. ✅ Осущ. ❔ Пров. ✅ Непрот.
- ❔ Проверяемость: Без перечня форматов нельзя проверить, что нужный формат доступен для загрузки

<a id="d-12"></a>**D-12 [MAJOR] Однозначность.** Слово «flexible» не определено: документ не перечисляет допустимые форматы. В следующем абзаце mp3 приведён как пример («such as»), а не как перечень. Цитата: `in a flexible format` (строка 173). Последствие: Нельзя определить, какие форматы загрузки реализовать и проверить.
- Вопрос заказчику (бизнес): Какие форматы должны поддерживаться для загрузки голосовых клипов: только MPEG Audio (mp3) или заданный перечень форматов? См. [Q-10](#q-10).

**Готовая формулировка:** 3.2.2 The system must allow actors to download their voice clips in <list of audio formats>.

### <a id="req-07"></a>REQ-07 · 3.2.3 · строки 175-176 · страница 9 · 3.2 Audio Recording
```text
3.2.3 The system must store audio clips in a format conducive to speech.
Voice clips should be stored in a format optimized for speech since this feature is meant to catalog voice recordings. Recordings should only be converted to MPEG Audio (mp3) format when they are being downloaded; a separate viewer should be provided in a cross-platform language for listening to clips in Moodle.
```

Оценки: ✅ Необх. ❌ Однозн. ✅ Полн. ❌ Атом. ✅ Осущ. ❌ Пров. ✅ Непрот.
- ❌ Однозначность: Термин «conducive to speech» не определяет конкретный формат хранения

<a id="d-13"></a>**D-13 [CRITICAL] Проверяемость.** Критерий «conducive to speech» не даёт способа проверить, что аудио сохранено в нужном формате. Тест не может однозначно признать требование выполненным. Цитата: `a format conducive to speech` (строка 175). Последствие: Невозможно написать тест, который подтверждает выполнение требования.
- Критик слил сюда: [D-14](#d-14), их текст в [приложении Б](#appendix-b).
- Вопрос архитектору: Какой конкретный кодек и контейнер должна использовать система для хранения аудиозаписей? См. [Q-07](#q-07).

<a id="d-15"></a>**D-15 [MAJOR] Атомарность.** В пояснении содержится отдельное требование к просмотрщику аудио, которое не входит в формулировку требования 3.2.3. Цитата: `a separate viewer should be provided in a cross-platform language` (строка 176). Последствие: Неясно, входит ли просмотрщик в объём работ по требованию хранения.
- Вопрос заказчику (бизнес): Нужен ли отдельный просмотрщик аудиозаписей как обязательная часть системы: да или нет?

**Готовая формулировка:** The system must store audio clips in <audio codec and container>.

### <a id="req-09"></a>REQ-09 · строки 180-181 · страница 10 · 3.3 Web Feeds
```text
The system must be able to display web feeds, such as RSS 2.0 feeds, for all pages of the course management system where elements such as forum posts, assignment postings, announcements, wiki alterations and other blocks of information that an actor may view are added. Actors in the role of course administrators should have the ability to determine which of these components have feeds and to whom these feeds should pertain.
If actors are unable to be notified in some way of new content in Moodle, they are unable to efficiently keep track of a course’s current affairs. For this requirement, page refers to any distinct block (e.g., assignments, wikis, forum threads, etc.).
```

Оценки: ✅ Необх. ❌ Однозн. ✅ Полн. ❌ Атом. ✅ Осущ. ❌ Пров. ✅ Непрот.

<a id="d-17"></a>**D-17 [MAJOR] Однозначность.** Фраза «and other blocks of information» открывает список элементов, для которых нужны ленты. Определение page в строке 181 с «etc.» тоже не закрывает список. Цитата: `and other blocks of information that an actor may view` (строка 180). Последствие: Нельзя понять, для каких элементов реализовывать ленты и что проверять.
- Вопрос заказчику (бизнес): Какой полный перечень элементов курса должен иметь веб-ленту: только перечисленные в строке 180 или ещё другие (назвать)?

<a id="d-18"></a>**D-18 [MAJOR] Однозначность.** Выражение «to whom these feeds should pertain» не объясняет, кто получает ленту и как это задаётся. Цитата: `to whom these feeds should pertain` (строка 180). Последствие: Нельзя реализовать настройку получателей лент и проверить её.
- Вопрос заказчику (бизнес): Кто получает ленту элемента: все участники курса, которые видят этот элемент, или только роли, которые выбирает администратор курса?

<a id="d-19"></a>**D-19 [MAJOR] Проверяемость.** Слова «such as» оставляют набор форматов лент открытым, поэтому тест не знает, какие форматы проверять. Цитата: `such as RSS 2.0 feeds` (строка 180). Последствие: Нельзя определить, какие форматы лент нужно проверить при приёмке.
- Вопрос аналитику: Какие форматы лент должна отдавать система: только RSS 2.0 или также другие (назвать)? См. [Q-08](#q-08).

<a id="d-20"></a>**D-20 [MINOR] Атомарность.** Во втором предложении соединены показ лент и отдельная настройка администратора курса. Цитата: `Actors in the role of course administrators should have the ability to determine which of these components have feeds` (строка 180).

**Готовая формулировка:** The system must be able to display web feeds in <feed format(s)> for all pages of the course management system where <closed list of elements> are added. Actors in the role of course administrator must be able to determine which of these components have feeds and <feed recipients>.

### <a id="req-10"></a>REQ-10 · 3.3.1 · строки 183-184 · страница 10 · 3.3 Web Feeds
```text
3.3.1 The system must allow web feeds to be turned on or off on a per-page basis.
Actors in the course administrator role may not feel the need to provide web feeds for every page in their course. During the creation and editing of a page, that actor should be able to toggle web feed availability.
```

Оценки: ✅ Необх. ✅ Однозн. ❌ Полн. ✅ Осущ. ✅ Пров. ✅ Непрот.

<a id="d-21"></a>**D-21 [MAJOR] Полнота.** Требование не говорит, в каком состоянии находится веб-лента страницы сразу после создания. Пояснение описывает только переключение. Цитата: `turned on or off on a per-page basis` (строка 183). Последствие: Нельзя реализовать значение по умолчанию и проверить его при создании страницы.
- Вопрос заказчику (бизнес): Какое состояние веб-ленты страницы задано по умолчанию: включена или выключена?

**Готовая формулировка:** The system must allow web feeds to be turned on or off on a per-page basis, with the default state <on or off>.

### <a id="req-11"></a>REQ-11 · строки 186-187 · страница 10 · 3.4 Search
```text
The system must be able to use search functionality as a way to navigate Moodle pages instead of using hierarchical links.
Moodle can be difficult to navigate and requires too many clicks to be efficiently used. Too many steps to complete basic actions—such as submitting an assignment—lead to frustration on the part of the actor. A search utility enables actors to find what they are looking for quickly in addition to having a hierarchical approach to finding functions of the course management system. For this requirement, page refers to any distinct page, such as an assignment, a wiki page, or a forum post.
```

Оценки: ✅ Необх. ❌ Однозн. ✅ Полн. ✅ Осущ. ✅ Пров. ❌ Непрот.

<a id="d-22"></a>**D-22 [CRITICAL] Непротиворечивость.** Строка 186 говорит, что поиск заменяет иерархические ссылки. Строка 187 говорит, что поиск добавляется к иерархическому подходу «in addition to having a hierarchical approach». Цитата: `instead of using hierarchical links` (строка 186). Последствие: Нельзя определить, нужно ли убирать иерархическую навигацию, поэтому проектирование меню невозможно.
- Вопрос заказчику (бизнес): Заменяет ли поиск иерархические ссылки (строка 186: «instead of using hierarchical links») или дополняет их (строка 187: «in addition to having a hierarchical approach»)? См. [Q-05](#q-05).

<a id="d-23"></a>**D-23 [MAJOR] Однозначность.** Слово «quickly» оценочное: нет предельного времени поиска или числа шагов, поэтому понять требование можно по-разному. Цитата: `find what they are looking for quickly` (строка 187). Последствие: Нельзя проверить, достаточно ли быстр поиск, и заложить время ответа в проект.
- Вопрос заказчику (бизнес): Какое предельное время получения результатов поиска задать, в секундах? См. [Q-15](#q-15).

**Готовая формулировка:** The system must be able to use search functionality as a way to navigate Moodle pages <instead of or in addition to> hierarchical links, so that an actor finds a page within <N seconds>.

### <a id="req-12"></a>REQ-12 · 3.4.1 · строки 189-194 · страница 10 · 3.4 Search
```text
3.4.1 An actor must be able to search through pages in a course.
Actors should be able to search for pages at the course level, since most actors will be searching for material in a given course. The search feature should be present in two ways.
First, it should be present in the form of a search box and a “Search” button on the top or bottom of every page. More information on this topic is given in sub-section 3.4.2 below.
Second, a single page should be dedicated specifically to the task of searching the course management system. In addition to the basic search field, this page should allow an actor to filter out certain results (such as forum posts or grades, etc.) and search specific sections (or components) of the course management system. Results should appear in categories (e.g.,
Assignments, Wiki Pages, Forum Posts, etc.) based on relevance. In this case, relevance is determined by results that having the highest number terms matching the search terms. When the actor clicks a search result link, they should be taken to the page corresponding to the search result.
In addition, the search page described above might allow for the possibility of searching the world wide web using a standard search engine such as Google.
```

Оценки: ✅ Необх. ❌ Однозн. ❌ Полн. ❌ Атом. ✅ Осущ. ✅ Пров. ✅ Непрот.

<a id="d-24"></a>**D-24 [MAJOR] Однозначность.** Список фильтров задан словами «such as» и «etc.», поэтому состав фильтров не определён. Категории результатов в скобках тоже открыты через «etc.». Цитата: `such as forum posts or grades, etc.` (строка 192). Последствие: Нельзя спроектировать набор фильтров и категорий и проверить их полноту.
- Вопрос заказчику (бизнес): Какой полный перечень типов результатов, по которым фильтруется поиск курса?

<a id="d-25"></a>**D-25 [MAJOR] Однозначность.** Фраза «might allow for the possibility» не говорит, входит ли поиск в интернете в требование. Цитата: `the search page described above might allow for the possibility` (строка 194). Последствие: Нельзя решить, нужна ли интеграция с внешней поисковой системой.
- Вопрос заказчику (бизнес): Должен ли поиск в интернете через внешнюю поисковую систему входить в это требование: да или нет? См. [Q-11](#q-11).

<a id="d-26"></a>**D-26 [MAJOR] Полнота.** Не описано, что показывает система, если ни один результат не найден, и как выглядит пустой результат по категориям. Цитата: `Results should appear in categories` (строка 192). Последствие: Нельзя реализовать и проверить сценарий пустого результата поиска.
- Вопрос аналитику: Что показывает система, если ни один результат не найден: текст сообщения или пустую страницу?

<a id="d-27"></a>**D-27 [MINOR] Атомарность.** Пояснение описывает поле поиска, отдельную страницу поиска и поиск в интернете, что относится к разным возможностям. Цитата: `The search feature should be present in two ways.` (строка 190).

**Готовая формулировка:** An actor must be able to search through pages in a course. Search results must be filtered by <list of result types> and grouped into categories <list of categories>, ordered by relevance (number of matching terms). If no results are found, the system displays <empty-result behavior>. Searching the world wide web is <included or excluded>.

### <a id="req-13"></a>REQ-13 · 3.4.2 · строки 195-196 · страница 11 · 3.4 Search
```text
3.4.2 The system must display a search box on every page after an actor has logged in.
Actors should be able to search from any page. If the actor is hierarchically outside of a particular course, each of his or her courses should be searched and results should be grouped by course. If the actor is hierarchically inside of a course, that course should be searched with an option to search all courses.
```

Оценки: ✅ Необх. ❌ Однозн. ❌ Полн. ✅ Осущ. ✅ Пров. ✅ Непрот.

<a id="d-28"></a>**D-28 [MAJOR] Однозначность.** Не определено, какие страницы считаются вне курса. Из текста неясно, относится ли это к главной странице системы или к любой странице без курса. Цитата: `If the actor is hierarchically outside of a particular course` (строка 196). Последствие: Нельзя однозначно реализовать выбор области поиска для каждой страницы.
- Вопрос аналитику: Какие страницы считаются вне курса: только главная страница системы или любая страница, не входящая в курс?

<a id="d-29"></a>**D-29 [MAJOR] Полнота.** Не указано, по умолчанию поиск идёт внутри курса или по всем курсам, и как выглядит этот параметр для пользователя. Цитата: `with an option to search all courses` (строка 196). Последствие: Нельзя реализовать и проверить исходное состояние поиска внутри курса.
- Вопрос заказчику (бизнес): По умолчанию поиск внутри курса идёт только в этом курсе или по всем курсам? См. [Q-12](#q-12).

**Готовая формулировка:** The system must display a search box on every page after an actor has logged in. Actors should be able to search from any page. If the actor is outside of a particular course <list of pages that count as outside a course>, each of his or her courses should be searched and results should be grouped by course. If the actor is inside of a course, <default search scope: that course or all courses> should be searched, with an option to search all courses.

### <a id="req-14"></a>REQ-14 · строка 198 · страница 11 · 3.5 Gradebook
> The system must allow actors in the capacity of course administrator to post grades associated with assignments for a particular actor in the capacity of student. Actors in the role of professor may want to optionally grade assignments online since they are being submitted electronically by actors in the role of student.

Оценки: ✅ Необх. ❌ Однозн. ✅ Полн. ✅ Осущ. ✅ Пров. ✅ Непрот.

<a id="d-30"></a>**D-30 [MAJOR] Однозначность.** Фраза «may want to optionally» описывает возможное желание, а не требование. Непонятно, должна ли система поддерживать онлайн-оценивание. Цитата: `may want to optionally grade assignments online` (строка 198). Последствие: Нельзя решить, входит ли онлайн-выставление оценок в объём работ.
- Вопрос заказчику (бизнес): Должна ли система обязательно поддерживать онлайн-выставление оценок за задания, сданные электронно?

**Готовая формулировка:** The system must allow actors in the capacity of course administrator to post grades associated with assignments for a particular actor in the capacity of student. The system must allow actors in the role of professor to grade assignments online <state whether online grading is required or optional>.

### <a id="req-15"></a>REQ-15 · 3.5.1 · строки 200-201 · страница 11 · 3.5 Gradebook
```text
3.5.1 A course administrator must be able to grade an assignment.
Course administrators should be able to post grades for an assignment based on the ratio of points earned to points possible. The course administrator should also be able to attach feedback in the form of text or an attachment (as described above). Time stamps should be attached to the last time the grade was modified so that actors may examine when particular grades were submitted and how an actor in the role of student has improved or lessened his performance in the course.
```

Оценки: ✅ Необх. ❌ Однозн. ✅ Полн. ❌ Атом. ✅ Осущ. ✅ Пров. ✅ Непрот.

<a id="d-31"></a>**D-31 [MAJOR] Однозначность.** Ссылка «as described above» указывает на описание, которого в разделе 3.5 нет. Формат отзыва остаётся неопределённым. Цитата: `attach feedback in the form of text or an attachment (as described above)` (строка 201). Последствие: Нельзя определить ограничения для текстового отзыва и вложения.
- Вопрос аналитику: Какой раздел документа описывает отзыв, на который ссылается «as described above»?

<a id="d-33"></a>**D-33 [MINOR] Атомарность.** В одном требовании объединены выставление оценки, прикрепление отзыва и отметки времени. Это три отдельные возможности. Цитата: `The course administrator should also be able to attach feedback` (строка 201).

Снято критиком: [D-32](#d-32), см. [приложение Б](#appendix-b).

**Готовая формулировка:** A course administrator must be able to grade an assignment. The course administrator should be able to post grades for an assignment based on the ratio of points earned to points possible. The course administrator should also be able to attach feedback in the form of text or an attachment <define feedback format or the section that describes it>. The system should store time stamps for <last modification only or every modification> of each grade so that actors may examine when grades were submitted and how an actor in the role of student has improved or lessened his performance in the course.

### <a id="req-16"></a>REQ-16 · 3.5.2 · строки 202-203 · страница 11 · 3.5 Gradebook
```text
3.5.2 The system should display grade information to the appropriate actor.
The system should display grade information such as the grade for each assignment, averages, and overall grade to the actor to whom the grades belong. No other actor should be able to view another’s grades except an actor in the role of course administrator for the course to which the grades belong.
```

Оценки: ✅ Необх. ❌ Однозн. ✅ Полн. ✅ Осущ. ❌ Пров. ✅ Непрот.

<a id="d-34"></a>**D-34 [MAJOR] Проверяемость.** Слово «such as» делает перечень показываемых данных открытым. Нельзя проверить, что показано всё нужное. Цитата: `grade information such as the grade for each assignment` (строка 203). Последствие: Нельзя составить тест, который подтвердит полный состав отображаемых данных.
- Вопрос заказчику (бизнес): Полный ли перечень показываемых данных: оценка за каждое задание, средние значения и итоговая оценка?

<a id="d-35"></a>**D-35 [MAJOR] Однозначность.** Не указано, по каким оценкам считается среднее и как вычисляется итоговая оценка. Цитата: `averages, and overall grade` (строка 203). Последствие: Нельзя реализовать расчёт средних значений и итоговой оценки.
- Вопрос заказчику (бизнес): По каким оценкам считается среднее: по заданиям одного студента в курсе или по всем студентам курса?

**Готовая формулировка:** The system should display grade information to the actor to whom the grades belong. The system should display <complete list of grade items> to that actor. No other actor should be able to view another’s grades except an actor in the role of course administrator for the course to which the grades belong. <averages basis and overall grade calculation rule to be defined>.

### <a id="req-17"></a>REQ-17 · 3.5.3 · строки 204-205 · страница 11 · 3.5 Gradebook
```text
3.5.3 The system should maintain a grade history.
The system should maintain a history of grades for a particular assignment if the course administrator changes them. This way, another actor can review the grade information if their score on an assignment has changed and they wish to dispute it. Course administrators can also track how they have changed a score over time using the timestamps associated with each change to the gradebook.
```

Оценки: ✅ Необх. ❌ Однозн. ❌ Полн. ✅ Осущ. ✅ Пров. ✅ Непрот.
- ❌ Однозначность: Не определено, какие участники «another actor» могут просматривать историю

<a id="d-37"></a>**D-37 [MAJOR] Полнота.** Не указано, какие данные фиксируются при каждом изменении: старое и новое значение, время, автор изменения. Не задан и срок хранения истории. Цитата: `maintain a history of grades for a particular assignment` (строка 205). Последствие: Нельзя спроектировать структуру истории и проверить её содержимое.
- Вопрос аналитику: Какие данные сохраняются при каждом изменении оценки: старое и новое значение с временем изменения?

Слито критиком: [D-36](#d-36) в [S-01](#s-01).

**Готовая формулировка:** The system should maintain a history of grades for a particular assignment if the course administrator changes them, storing <data stored for each change>. This way, <roles allowed to review the history> can review the grade information if their score on an assignment has changed and they wish to dispute it. Course administrators can also track how they have changed a score over time using the timestamps associated with each change to the gradebook.

### <a id="req-18"></a>REQ-18 · строка 207 · страница 12 · 3.6 Social Networking Applications
> The social, collaborative components of Moodle are not very robust. There are better, freelyavailable solutions which should be integrated into Moodle to provide the best functionality possible for all actors without having to use 3rd party services.

Оценки: ❔ Необх. ❌ Уровень ❌ Однозн. ✅ Полн. ❔ Осущ. ❌ Пров. ✅ Непрот.
- ❔ Необходимость: Из текста не видно, зачем интегрировать внешние решения вместо текущих компонентов
- ❔ Осуществимость: Наличие и совместимость подходящих решений в тексте не описаны
- ❌ Проверяемость: Критерий «best functionality possible» не имеет конечной проверки

<a id="d-38"></a>**D-38 [MAJOR] Уместность уровня.** Требование навязывает интеграцию внешних решений, не описав потребность, которую она должна закрыть. Цитата: `which should be integrated into Moodle` (строка 207). Последствие: Нельзя оценить, достигается ли цель другими способами, например собственной реализацией.
- Вопрос заказчику (бизнес): Нужна ли именно интеграция внешних решений, или допустима собственная реализация тех же функций?

<a id="d-39"></a>**D-39 [MAJOR] Однозначность.** Слова «not very robust» и «better» не задают измеримого критерия качества. Непонятно, по чему решения считаются лучше текущих. Цитата: `The social, collaborative components of Moodle are not very robust.` (строка 207); `to provide the best functionality possible for all actors` (строка 207). Последствие: Нельзя определить, какие решения удовлетворяют требованию.
- Критик слил сюда: [D-40](#d-40), их текст в [приложении Б](#appendix-b).
- Вопрос заказчику (бизнес): По каким функциям решения должны превосходить текущие компоненты Moodle: назовите перечень функций?

**Готовая формулировка:** The social, collaborative components of Moodle should provide <list of social and collaborative functions> for all actors without having to use 3rd party services.

### <a id="req-19"></a>REQ-19 · 3.6.1 · строки 209-210 · страница 12 · 3.6 Social Networking Applications
```text
3.6.1 The system must provide a wiki where actors can collaboratively create networks of documents.
A freely available wiki should provide a simple markup language that actors can use to style their input, as well as link to other pages in the wiki. More importantly, having the wiki inside Moodle reduces confusion and allows for the integration of notifications and logins.
```

Оценки: ✅ Необх. ❌ Однозн. ✅ Полн. ✅ Осущ. ✅ Пров. ✅ Непрот.

<a id="d-41"></a>**D-41 [MINOR] Однозначность.** Слово simple не задаёт, какой синтаксис разметки ожидается. Формулировка оценочная и не проверяется. Цитата: `should provide a simple markup language` (строка 210).
- Как исправить: Заменить simple перечнем нужных возможностей разметки или убрать слово.

### <a id="req-20"></a>REQ-20 · 3.6.2 · строки 211-212 · страница 12 · 3.6 Social Networking Applications
```text
3.6.2 The system must provide a blog engine.
A freely available blog engine should provide all modern blog functionality, such as tagging, drafting, and comments. These blogs should share authentication and notification with Moodle.
```

Оценки: ✅ Необх. ❌ Однозн. ✅ Полн. ✅ Осущ. ✅ Пров. ✅ Непрот.

<a id="d-42"></a>**D-42 [MAJOR] Однозначность.** Фраза all modern blog functionality не определяет набор функций, а перечень через such as не закрыт. Без списка нельзя понять, что обязательно реализовать. Цитата: `should provide all modern blog functionality, such as tagging, drafting, and comments` (строка 212). Последствие: Нельзя определить объём реализации блога и набор проверок приёмки.
- Вопрос заказчику (бизнес): Какой набор функций блога обязателен: только теги, черновики и комментарии из текста или полный набор современных функций блога?

**Готовая формулировка:** The system must provide a blog engine that supports <list of required blog functions>. These blogs should share authentication and notification with Moodle.

### <a id="req-21"></a>REQ-21 · 3.7.1 · строки 216-218 · страница 12 · 3.7 Notifications
```text
3.7.1 The system must provide both e-mail and SMS notifications for pages.
For this requirement, page refers to any distinct page (e.g., an assignment, a wiki page, a forum post, etc.). When a page is created, the actor in the role of course administrator should be able to toggle whether notifications are turned on. By default, they should be turned on for announcements. If notifications are turned off, actors in the capacity of student should be able to subscribe to notifications.
Students should be able to select in their preferences whether notifications are sent to their mobile telephone (via SMS) or e-mail account. They should also be able to manage their notification subscriptions (for example, remove themselves from notifications).
```

Оценки: ✅ Необх. ✅ Однозн. ❌ Полн. ✅ Осущ. ✅ Пров. ✅ Непрот.

<a id="d-43"></a>**D-43 [MAJOR] Полнота.** Текст описывает включение уведомлений при создании страницы, но не говорит, какое событие запускает отправку уведомления. Не задано, при создании, при изменении или при публикации объявления. Цитата: `should be able to toggle whether notifications are turned on` (строка 217). Последствие: Нельзя реализовать логику отправки и проверить момент уведомления.
- Вопрос заказчику (бизнес): Какое событие запускает уведомление о странице: создание страницы или любое её изменение?

**Готовая формулировка:** The system must provide both e-mail and SMS notifications for pages. Notifications are sent when <triggering event of a page>. When a page is created, the actor in the role of course administrator should be able to toggle whether notifications are turned on. By default, they should be turned on for announcements. If notifications are turned off, actors in the capacity of student should be able to subscribe to notifications. Students should be able to select in their preferences whether notifications are sent to their mobile telephone (via SMS) or e-mail account. They should also be able to manage their notification subscriptions (for example, remove themselves from notifications).

### <a id="req-22"></a>REQ-22 · 4.1.1 · строки 221-224 · страница 12 · 4.1 Usability
```text
4.1.1 As far as possible, the system should provide a simple, responsive interface.
Although any courseware solution may be composed of diverse systems, applications, and processes, the underlying architecture should be transparent to the administrators. The system should be configurable from a single source at a central administrative position, and should provide a central, easy-to-use interface that will allow administrators to configure the user interface and features in a way that reduces page clutter.
A system will be considered to meet this requirement if it has a single administrative interface rather than individual links for editing each page. Furthermore, this interface must allow administrators to easily change themes and other setting that affect page layout across the entire courseware system.
Priority: 3
```

Оценки: ✅ Необх. ❌ Однозн. ✅ Полн. ❌ Атом. ✅ Осущ. ❌ Пров. ❌ Непрот.

<a id="d-44"></a>**D-44 [MAJOR] Однозначность.** Слова simple и responsive не задают измеримого признака. Формулировка оценочная, и два разных читателя проверят интерфейс по-разному. Цитата: `provide a simple, responsive interface` (строка 221). Последствие: Нельзя определить, соответствует ли интерфейс требованию.
- Вопрос заказчику (бизнес): Какой измеримый признак простоты интерфейса принять: максимальное число кликов до базового действия, например 3?

<a id="d-45"></a>**D-45 [MAJOR] Проверяемость.** Оговорка As far as possible делает обязательность неопределённой, и нет порога, по которому проверяется интерфейс. Цитата: `As far as possible, the system should provide a simple, responsive interface.` (строка 221). Последствие: Нельзя провести приёмку, потому что неясно, что считать выполнением.
- Вопрос заказчику (бизнес): Обязательно ли выполнение этого требования без исключений или допускается отступление по согласованному перечню?

<a id="d-46"></a>**D-46 [MAJOR] Атомарность.** В одном требовании объединены простота и отзывчивость интерфейса и централизованная настройка из одного источника. Каждое свойство можно проверить отдельно. Цитата: `The system should be configurable from a single source at a central administrative position` (строка 222). Последствие: Нельзя назначить отдельную приёмку и исполнителя каждому свойству.
- Вопрос заказчику (бизнес): Нужна ли централизованная настройка из одного источника отдельным требованием?

<a id="d-47"></a>**D-47 [MAJOR] Непротиворечивость.** Текст требования говорит о простом и отзывчивом интерфейсе, а критерий соответствия проверяет наличие единого административного интерфейса. Цитата: `A system will be considered to meet this requirement if it has a single administrative interface` (строка 223). Последствие: Нельзя понять, что именно принимать как выполненное требование.
- Вопрос заказчику (бизнес): Что проверяет требование: простоту и отзывчивость пользовательского интерфейса или наличие единого административного интерфейса?

**Готовая формулировка:** The system should provide a user interface with <measurable simplicity criterion> and <measurable responsiveness criterion>. The system should be configurable from a single central administrative interface.

### <a id="req-23"></a>REQ-23 · 4.2.1 · строки 226-227 · страница 13 · 4.2 Reliability
```text
4.2.1 The system must be backed up on a configurable schedule.
Back-up requirements will need to be determined, based on individual components of the system. The system should be backed up with a frequency that ensures system and course data is protected. Since assignments will be submitted via the system, it should be backed up on a nightly basis, with options for weekly, off-site backup when necessary.
```

Оценки: ✅ Необх. ❌ Однозн. ❌ Полн. ✅ Осущ. ❌ Пров. ✅ Непрот.
- ❌ Полнота: Перечень компонентов и периодичность копирования не заданы

<a id="d-49"></a>**D-49 [MAJOR] Однозначность.** Фраза when necessary не задаёт условие запуска внешней еженедельной копии. Один и тот же текст читается как всегда или по решению администратора. Цитата: `with options for weekly, off-site backup when necessary` (строка 227). Последствие: Нельзя реализовать условие запуска внешней копии и проверить его.
- Вопрос заказчику (бизнес): Когда делается еженедельная внешняя копия: всегда по расписанию или по решению администратора?

<a id="d-50"></a>**D-50 [MAJOR] Проверяемость.** Фраза ensures data is protected не задаёт порога допустимой потери данных, поэтому выполнение нельзя проверить. Цитата: `with a frequency that ensures system and course data is protected` (строка 227). Последствие: Нельзя доказать, что частота копирования достаточна.
- Вопрос заказчику (бизнес): Какой максимальный период потери данных допустим между копиями, в часах (например, 24)?

Слито критиком: [D-48](#d-48) в [S-04](#s-04).

**Готовая формулировка:** The system must be backed up on a configurable schedule of <backup frequency per component>, with a maximum data loss of <N hours>. Assignment data must be backed up nightly. Off-site weekly backup is performed when <condition for off-site backup>.

### <a id="req-24"></a>REQ-24 · строка 228 · страница 13 · 4.2 Reliability
> The system must have the ability and capacity to restore back-up data within six hours so that the system is never offline for an inordinate period of time.

Оценки: ✅ Необх. ❌ Однозн. ❌ Полн. ✅ Осущ. ✅ Пров. ✅ Непрот.

<a id="d-51"></a>**D-51 [MAJOR] Однозначность.** Фраза inordinate period of time не задаёт допустимое время простоя. Цель требования нельзя проверить. Цитата: `so that the system is never offline for an inordinate period of time` (строка 228). Последствие: Нельзя определить допустимый простой системы и критерий приёмки.
- Вопрос заказчику (бизнес): Какое максимальное время простоя системы допустимо: задать значение в часах?

<a id="d-52"></a>**D-52 [MAJOR] Полнота.** Не указано, от какого момента отсчитываются шесть часов и какой объём данных восстанавливается. Срок нельзя измерить без точки отсчёта. Цитата: `restore back-up data within six hours` (строка 228). Последствие: Нельзя реализовать и проверить срок восстановления.
- Вопрос заказчику (бизнес): От какого момента отсчитываются шесть часов восстановления: от обнаружения сбоя или от запроса администратора? См. [Q-14](#q-14).

**Готовая формулировка:** The system must have the ability to restore back-up data of <data volume> within six hours of <start event>, with a maximum system downtime of <N hours>.

### <a id="req-25"></a>REQ-25 · 4.2.2 · строки 230-233 · страница 13 · 4.2 Reliability
```text
4.2.2 The system should be available 24 hours a day, 7 days a week.
This statement provides a general sense of system availability. It is not intended to demand the system maintain reliability, or to require the system to be highly available. It should not exclude maintenance windows, or scheduled downtime. It is only intended to convey the expectation that our customers should have access to the system during off-hours as well as business hours.
99% up-time should be considered sufficient to meet this requirement.
Priority: 1
```

Оценки: ❔ Необх. ✅ Однозн. ✅ Полн. ✅ Осущ. ❌ Пров. ❌ Непрот.
- ❔ Необходимость: Пояснение прямо отрицает требование высокой доступности, нужность автор должен подтвердить
- ❌ Проверяемость: Не задан период измерения и способ учета плановых простоев, поэтому проверить нельзя

<a id="d-53"></a>**D-53 [CRITICAL] Непротиворечивость.** Основная фраза требует доступности 24 часа в сутки и 7 дней в неделю, а пояснение признает достаточным 99% времени доступности и не исключает плановые простои. Это разные наблюдаемые уровни доступности. Цитата: `The system should be available 24 hours a day, 7 days a week.` (строка 230). Последствие: Нельзя определить, какой уровень доступности реализовать и проверять.
- Вопрос заказчику (бизнес): Какой уровень доступности верен: 24 часа в сутки и 7 дней в неделю (строка 230) или 99% времени доступности (строка 232)? См. [Q-06](#q-06).

Слито критиком: [D-54](#d-54) в [S-13](#s-13).

**Готовая формулировка:** The system must be available at least <N percent> of the time, 24 hours a day, 7 days a week, measured over <measurement period>, with <scheduled downtime rule>.

### <a id="req-26"></a>REQ-26 · 4.3.1 · строки 235-237 · страница 13 · 4.3 Performance
```text
4.3.1 The system should support at least 1000 concurrent users.
This statement provides a general sense of reliability when the system is under load. It is important that a substantial number of actors be able to access the system at the same time, since a courseware system is important to the courses that employ it. The times when the system will be under the most stress are likely during midterm and finals weeks. Therefore, it must be able to handle at least 1,000 concurrent users.
Priority: 1
```

Оценки: ✅ Необх. ❌ Однозн. ✅ Полн. ✅ Осущ. ❌ Пров. ❌ Непрот.

<a id="d-55"></a>**D-55 [MAJOR] Однозначность.** Термин concurrent users не определен: неясно, это одновременные сессии, активные пользователи или запросы. Цитата: `The system should support at least 1000 concurrent users.` (строка 235). Последствие: Нельзя определить, какую нагрузку тестировать и под какую ее проектировать.
- Вопрос аналитику: Что считается одновременным пользователем: пользователь с активной сессией в заданный момент или отправивший запрос в заданный интервал? См. [Q-13](#q-13).

<a id="d-56"></a>**D-56 [MAJOR] Проверяемость.** Не задан критерий успеха: время ответа, доля ошибок и профиль нагрузки не указаны, поэтому тест не даст однозначного результата. Цитата: `The system should support at least 1000 concurrent users.` (строка 235). Последствие: Нельзя определить, что система выдержала заданную нагрузку.
- Вопрос тестировщику: Задать предельное время ответа системы при заданном числе одновременных пользователей, в секундах.

<a id="d-57"></a>**D-57 [MAJOR] Непротиворечивость.** Основное требование использует should, а пояснение использует must. Это разный уровень обязательности одного и того же порога. Цитата: `it must be able to handle at least 1,000 concurrent users.` (строка 236). Последствие: Нельзя понять, является ли порог 1000 пользователей обязательным условием приемки.
- Вопрос заказчику (бизнес): Является ли поддержка 1000 одновременных пользователей обязательной (must) или желательной (should)?

**Готовая формулировка:** The system must support at least <N> concurrent users, where a concurrent user is <definition>, with a response time of no more than <N seconds> under <load profile>.

### <a id="req-27"></a>REQ-27 · 4.4.1 · строки 239-241 · страница 13 · 4.4 Supportability
```text
4.4.1 The system must be maintainable without substantial modification.
Due to limited staff in the Office of Information Services, it is important that the system be mostly self-sustaining. This will reduce the number of FTE hours spent maintaining the system and simplify maintenance tasks.
Priority: 3
```

Оценки: ✅ Необх. ❌ Однозн. ✅ Полн. ✅ Осущ. ❌ Пров. ✅ Непрот.

<a id="d-58"></a>**D-58 [MAJOR] Однозначность.** Слова substantial modification не определены, поэтому граница допустимой доработки неясна. Цитата: `The system must be maintainable without substantial modification.` (строка 239). Последствие: Нельзя понять, какие изменения считаются допустимыми без существенной модификации.
- Вопрос заказчику (бизнес): Задать предельные трудозатраты на изменение системы, которое еще не считается существенной модификацией, в часах.

<a id="d-59"></a>**D-59 [MAJOR] Проверяемость.** Нет измеримого критерия сопровождаемости и способа ее проверки, например осмотра или замера трудозатрат. Цитата: `The system must be maintainable without substantial modification.` (строка 239). Последствие: Нельзя доказать выполнение требования на приемке.
- Вопрос тестировщику: Задать предельное время на типовое изменение системы, в часах, при котором требование считается выполненным.

**Готовая формулировка:** The system must be maintainable such that a <type of change> requires no more than <N hours> of effort by <role>.

### <a id="req-28"></a>REQ-28 · 4.6.1 · строки 244-246 · страница 14 · 4.6 On-line User Documentation and Help System Requirements
```text
4.6.1 Relevant, online documentation for users should be available on each page.
Users must have easy access to help while interacting with the system. Adequate user documentation should be provided to minimize the number of calls to the Help Desk about problems with the system. Modifications should be reported via the main page to inform actors of unexpected changes. This electronic documentation should be supplemented with phone and on-site support provided by the Office of Information Services.
Priority: 3
```

Оценки: ✅ Необх. ❌ Однозн. ✅ Полн. ❌ Атом. ✅ Осущ. ❔ Пров. ✅ Непрот.
- ❔ Проверяемость: Без определения релевантности проверку нельзя оценить по тексту

<a id="d-60"></a>**D-60 [MAJOR] Однозначность.** Слово Relevant не определено, поэтому неясно, какая документация считается релевантной. В пояснении оценочные слова easy и Adequate тоже не определены. Цитата: `Relevant, online documentation for users should be available on each page.` (строка 244). Последствие: Нельзя определить состав документации, которую нужно разместить на каждой странице.
- Вопрос заказчику (бизнес): Какая документация считается релевантной: контекстная справка по текущей странице или общее руководство пользователя?

<a id="d-61"></a>**D-61 [MINOR] Атомарность.** В пояснении заданы отдельные требования: уведомления об изменениях на главной странице и поддержка по телефону и на месте. Цитата: `Modifications should be reported via the main page` (строка 245).

**Готовая формулировка:** Online documentation for users covering <content scope> must be available on each page.

### <a id="req-29"></a>REQ-29 · 4.6.2 · строки 247-250 · страница 14 · 4.6 On-line User Documentation and Help System Requirements
```text
4.6.2 System administrators must have access to comprehensive, searchable documentation.
A comprehensive database of maintenance tasks and help files should be compiled to make the courseware system easier to maintain from an IT staff point-of-view. Search results should be displayed based on relevance.
This documentation must cover all procedures necessary for regular maintenance with links to additional information, all common errors, and links or documentation for advanced troubleshooting.
Priority: 3
```

Оценки: ✅ Необх. ❌ Однозн. ✅ Полн. ✅ Осущ. ❌ Пров. ✅ Непрот.

<a id="d-62"></a>**D-62 [MAJOR] Однозначность.** Слово comprehensive не определено, поэтому неясно, какой объем документации считается полным. Также не определены common errors и advanced troubleshooting из строки 249. Цитата: `System administrators must have access to comprehensive, searchable documentation.` (строка 247). Последствие: Нельзя определить, какой объем справки считать достаточным для приемки.
- Вопрос аналитику: Перечислить процедуры регулярного обслуживания, которые документация обязана покрывать.

<a id="d-63"></a>**D-63 [MAJOR] Проверяемость.** Нет перечня процедур и типовых ошибок, поэтому полноту покрытия по словам all procedures и all common errors нельзя сверить. Цитата: `This documentation must cover all procedures necessary for regular maintenance` (строка 249). Последствие: Нельзя проверить, что документация покрывает все нужные процедуры и ошибки.
- Вопрос аналитику: Задать перечень типовых ошибок, которые документация обязана описывать, в виде списка.

**Готовая формулировка:** System administrators must have access to searchable documentation that covers <list of maintenance procedures>, <list of common errors>, and <advanced troubleshooting scope>.

## 4. Проверка набора требований целиком

### 4.1. Системная полнота

**Анализ.**

- Полнота набора (ISO 29148 п. 5.2.6; IEEE 830 п. 4.3.3): **нарушен**. Проверены пустые разделы, пометки TODO и «to be determined», негативные сценарии и нефункциональные требования. Раздел 4.7 Interfaces и 4.9 Applicable Standards пусты, в 1.2 стоит TODO, в 4.2.1 стоит «to be determined». Сценарии сбоя резервного копирования и восстановления не описаны.
- Валидируемость (ISO 29148 п. 5.2.6): **нарушен**. Раздела критериев приёмки в документе нет, поэтому покрытие требований критериями не проверить. Цель из раздела 2.2 сформулирована качественно (улучшение учебного опыта) и не имеет измеримого показателя.
- Прослеживаемость (IEEE 830 п. 4.3.8): **частично**. У большинства требований есть номера 3.x.y и 4.x.y, но ряд обязательных формулировок без номера и без ссылки. Версия документа указана двумя разными значениями: 1.0 на титуле и 1.4 в истории изменений.

#### <a id="s-03"></a>S-03 [MAJOR] В разделе 1.2 не указана версия Moodle, оставлена пометка TODO
- Пробел · Полнота набора · раздел «1.2 Scope».
- Цитата: `(version TODO: Version of` (строка 109).
- Что не так: Пометка TODO оставляет место незаполненным: версия базовой платформы, для которой описаны доработки, не задана. Последствие: Нельзя определить, к какой версии Moodle относятся требования и совместимы ли доработки с ней.
- Вопрос заказчику (бизнес): Какую версию Moodle указать в разделе 1.2: номер версии, на которую рассчитаны доработки?
- Как исправить: Указать конкретную версию Moodle, на которую рассчитаны доработки, и убрать пометку TODO.

#### <a id="s-04"></a>S-04 [MAJOR] Требования к резервному копированию отложены: «will need to be determined»
- Пробел · Полнота набора · [REQ-23](#req-23) · раздел «4.2 Reliability».
- Цитата: `Back-up requirements will need to be determined, based on individual components of the system.` (строка 227).
- Что не так: Состав и параметры резервного копирования по компонентам системы не заданы, а текст сам признаёт, что их нужно определить. Последствие: Нельзя проверить, какие данные копируются, с какой полнотой и какой срок хранения копий обеспечивается.
- Критик слил сюда: [D-48](#d-48), их текст в [приложении Б](#appendix-b).
- Вопрос архитектору: Какой срок хранения резервных копий задать, в днях (например, 30)?
- Как исправить: Определить перечень компонентов, подлежащих копированию, и параметры копий для каждого из них.

#### <a id="s-05"></a>S-05 [MAJOR] Раздел 4.7 Interfaces содержит только заголовки подразделов без требований
- Пробел · Полнота набора · раздел «4.7 Interfaces».
- Цитаты: `4.7.1 User Interfaces` (строка 96); `4.7.4 Communications Interfaces` (строка 99).
- Что не так: Все четыре подраздела интерфейсов пусты: пользовательские, аппаратные, программные и коммуникационные интерфейсы не описаны. Последствие: Внешние связи системы и требования к аппаратной части нельзя проверить и согласовать с инфраструктурой университета.
- Вопрос архитектору: Есть ли аппаратные ограничения клиентских устройств студентов и преподавателей, которые нужно записать в 4.7.2 Hardware Interfaces: да или нет?
- Как исправить: Описать требования по каждому подразделу интерфейсов или явно указать, что подраздел не применим.

#### <a id="s-06"></a>S-06 [MAJOR] Не описано поведение при сбое восстановления из резервной копии
- Пробел · Полнота набора · [REQ-23](#req-23), [REQ-24](#req-24) · раздел «4.2 Reliability».
- Цитата: `The system must have the ability and capacity to restore back-up data within six hours so that the system is never offline for an inordinate period of time.` (строка 228).
- Что не так: Требование задаёт срок восстановления, но не описывает, что происходит, если восстановление не завершено в срок или копия повреждена. Последствие: Нельзя определить поведение системы в аварийной ситуации и проверить отказоустойчивость восстановления.
- Вопрос архитектору: Что система делает при восстановлении дольше шести часов: откатывает данные к исходному состоянию или продолжает работу без восстановления?
- Как исправить: Описать действия системы при превышении шести часов и при повреждённой копии.

#### <a id="s-07"></a>S-07 [MAJOR] Оценка за задание при нулевом или не заданном максимуме баллов
- Пробел · Полнота набора · [REQ-15](#req-15) · раздел «3.5.1».
- Цитата: `Course administrators should be able to post grades for an assignment based on the ratio of points earned to points possible.` (строка 201).
- Что не так: Оценка считается как отношение набранных баллов к возможным. Не описано, что происходит, если возможные баллы равны нулю или не заданы, и что при наборе баллов больше возможных. Последствие: Нельзя реализовать расчёт оценки и проверку ввода: неясно, сохраняется ли оценка, выводится ли ошибка и какой процент получает студент.
- Вопрос заказчику (бизнес): Что система делает, если максимум баллов за задание равен нулю или не задан: запрещает выставление оценки или сохраняет оценку без процента?
- Как исправить: Описать правило для нулевого и незаданного максимума баллов и для баллов выше максимума.

#### <a id="s-08"></a>S-08 [MAJOR] Одновременное изменение одной оценки двумя администраторами курса
- Пробел · Полнота набора · [REQ-14](#req-14), [REQ-17](#req-17) · раздел «3.5.3».
- Цитата: `The system should maintain a history of grades for a particular assignment if the course administrator changes them.` (строка 205).
- Что не так: Не описано, какое значение оценки сохраняется, если два администратора курса меняют оценку одного студента за одно задание почти одновременно, и как это попадает в историю. Последствие: Нельзя определить итоговую оценку и порядок записей в истории, а значит и проверку истории изменений.
- Вопрос аналитику: При одновременном изменении оценки двумя администраторами курса сохраняется последнее сохранённое значение или система отклоняет второе изменение с сообщением?
- Как исправить: Описать правило разрешения конфликта одновременных изменений и порядок записей в истории.

#### <a id="s-09"></a>S-09 [MAJOR] Доступ к оценкам после снятия роли администратора или выхода студента из курса
- Пробел · Полнота набора · [REQ-16](#req-16) · раздел «3.5.2».
- Цитата: `No other actor should be able to view another’s grades except an actor in the role of course administrator for the course to which the grades belong.` (строка 203).
- Что не так: Не описано, сохраняется ли право просмотра оценок у администратора, которого сняли с курса, и видит ли студент свои оценки после завершения курса или исключения из него. Последствие: Нельзя определить права доступа к оценкам в момент смены роли или статуса участника и проверить их тестами.
- Вопрос заказчику (бизнес): Теряет ли администратор курса доступ к оценкам курса сразу после снятия роли в этом курсе: да или нет?
- Как исправить: Описать права доступа к оценкам при отзыве роли администратора и при исключении студента из курса.

#### <a id="s-10"></a>S-10 [MAJOR] Удаление голосового клипа, прикреплённого к странице
- Пробел · Полнота набора · [REQ-05](#req-05), [REQ-08](#req-08) · раздел «3.2.4».
- Цитаты: `The actor should be able to optionally attach one of his or her archived items to any page where uploads are permitted.` (строка 171); `The system must allow actors to delete recorded clips.` (строка 177).
- Что не так: Не описано, что происходит с клипом, если он уже прикреплён к странице и актор удаляет его из портфолио: остаётся ли прикрепление, исчезает ли клип на странице. Последствие: Нельзя реализовать удаление клипа без понимания судьбы ссылок на него и того, что увидят другие акторы на странице.
- Критик слил сюда: [D-16](#d-16), их текст в [приложении Б](#appendix-b).
- Вопрос заказчику (бизнес): Что происходит с прикреплённым клипом при его удалении из портфолио: клип удаляется со страницы вместе с прикреплением или прикрепление сохраняется как пустая ссылка?
- Как исправить: Описать поведение удаления клипа, который прикреплён к одной или нескольким страницам.

#### <a id="s-11"></a>S-11 [MAJOR] Уведомление по SMS при отсутствии или недоступности номера телефона
- Пробел · Полнота набора · [REQ-21](#req-21) · раздел «3.7.1».
- Цитата: `Students should be able to select in their preferences whether notifications are sent to their mobile telephone (via SMS) or e-mail account.` (строка 218).
- Что не так: Не описано, что делает система, если студент выбрал SMS, но номер телефона не указан или SMS не доставлено. Последствие: Нельзя определить, будет ли уведомление продублировано на e-mail, потеряно или повторено, а значит нельзя реализовать обработку ошибки доставки.
- Вопрос заказчику (бизнес): Если студент выбрал SMS, а номер телефона не указан или SMS не доставлено, система отправляет уведомление на e-mail или не отправляет его вовсе?
- Как исправить: Описать поведение при выборе SMS без номера и при неуспешной доставке SMS.

#### <a id="s-12"></a>S-12 [MAJOR] Уведомления подписчикам при удалении страницы или выключении уведомлений
- Пробел · Полнота набора · [REQ-21](#req-21) · раздел «3.7.1».
- Цитата: `If notifications are turned off, actors in the capacity of student should be able to subscribe to notifications.` (строка 217).
- Что не так: Не описано, что происходит с уже оформленными подписками, если страницу удалили или администратор выключил уведомления после того, как студенты подписались. Последствие: Нельзя определить, получат ли подписчики уведомление об удалении или изменении страницы и будут ли подписки сохраняться.
- Вопрос заказчику (бизнес): Что происходит с подписками студентов, если администратор выключил уведомления на странице, на которую они уже подписаны: подписки сохраняются или снимаются?
- Как исправить: Описать судьбу подписок при удалении страницы и при выключении уведомлений.

#### <a id="s-13"></a>S-13 [MAJOR] Период, за который измеряется доступность 99%
- Пробел · Полнота набора · [REQ-25](#req-25) · раздел «4.2.2».
- Цитата: `99% up-time should be considered sufficient to meet this requirement.` (строка 232).
- Что не так: Не задан период, за который считается доля времени работы: сутки, месяц или год. Не сказано, учитываются ли плановые окна обслуживания при подсчёте. Последствие: Нельзя проверить выполнение требования по доступности и определить, нарушено ли оно при конкретном простое.
- Критик слил сюда: [D-54](#d-54), их текст в [приложении Б](#appendix-b).
- Вопрос заказчику (бизнес): За какой период измеряется доступность 99%: задать период, в днях или месяцах, и учитываются ли плановые окна обслуживания?
- Как исправить: Задать период измерения доступности и правило учёта плановых простоев.

#### <a id="s-14"></a>S-14 [MAJOR] Работа системы при числе пользователей выше 1000
- Пробел · Полнота набора · [REQ-26](#req-26) · раздел «4.3.1».
- Цитата: `Therefore, it must be able to handle at least 1,000 concurrent users.` (строка 236).
- Что не так: Требование задаёт нижнюю границу нагрузки, но не описано поведение системы при превышении 1000 одновременных пользователей: отказ, очередь или деградация. Последствие: Нельзя спроектировать ограничение нагрузки и сообщение пользователю при пиковых нагрузках в периоды экзаменов, о которых сказано в документе.
- Вопрос заказчику (бизнес): Что система делает при числе одновременных пользователей выше поддерживаемого значения: отклоняет новые входы с сообщением или продолжает работать с замедлением? См. [Q-09](#q-09).
- Как исправить: Описать поведение системы при числе одновременных пользователей выше поддерживаемого.

#### <a id="s-21"></a>S-21 [MAJOR] Версия документа на титуле не совпадает с последней версией в истории
- Противоречие · Прослеживаемость · раздел «Revision History».
- Цитаты: `Version 1.0` (строка 18); `| | | 11/2/2007 | | | 1.4 |` (строка 38).
- Что не так: Титул указывает версию 1.0, а история изменений заканчивается версией 1.4. Последствие: Нельзя однозначно сослаться на версию документа из проекта, кода и тестов.
- Вопрос аналитику: Какой номер версии верный для документа: 1.0 с титула (строка 18) или 1.4 из истории (строка 38)?
- Как исправить: Привести номер версии на титуле в соответствие с историей изменений.

#### <a id="s-22"></a>S-22 [MAJOR] Критерии приёмки для требований не заданы ни в одном разделе
- Пробел · Валидируемость · раздел «3. Specific Requirements».
- Цитата: `3. Specific Requirements` (строка 62).
- Что не так: Для требований раздела 3 нет критериев приёмки: проверяемые условия выполнения не записаны. Последствие: Нельзя показать, что реализация набора приводит к заявленной цели, и нельзя принять систему по требованиям.
- Вопрос тестировщику: По какому проверяемому признаку принимается 3.3.1: переключатель веб-лент сохраняется для каждой страницы курса?
- Как исправить: Для каждого требования задать проверяемое условие приёмки или ссылку на него.

#### <a id="s-23"></a>S-23 [MAJOR] Цель улучшения учебного опыта не имеет измеримого показателя
- Прочее · Валидируемость · раздел «2.2 Product Characteristics».
- Цитата: `Our goal is to refine parts of Moodle to provide functionality that improves the overall learning experience of students` (строка 138).
- Что не так: Цель описана качественно, без показателя, по которому можно судить о её достижении. Последствие: Нельзя подтвердить, что выполнение набора требований достигает цели.
- Вопрос заказчику (бизнес): Какой показатель подтверждает цель: задать значение порога, например, долю студентов, пользующихся новыми функциями, в процентах?
- Как исправить: Задать измеримый показатель цели с порогом значения и способом измерения.

#### <a id="s-24"></a>S-24 [MINOR] Поиск с пустым запросом и без результатов
- Пробел · Полнота набора · [REQ-12](#req-12) · раздел «3.4.1».
- Цитаты: `Results should appear in categories (e.g., Assignments, Wiki Pages, Forum Posts, etc.) based on relevance.` (строка 192); `When the actor clicks a search result link, they should be taken to the page corresponding to the search result.` (строка 193).
- Что не так: Не описано поведение поиска при пустой строке запроса и при отсутствии результатов по категориям.
- Как исправить: Описать вывод при пустом запросе и при отсутствии результатов в категории.

#### <a id="s-25"></a>S-25 [MINOR] Веб-лента после выключения для страницы с уже подписанными актерами
- Пробел · Полнота набора · [REQ-10](#req-10) · раздел «3.3.1».
- Цитаты: `The system must allow web feeds to be turned on or off on a per-page basis.` (строка 183); `During the creation and editing of a page, that actor should be able to toggle web feed availability.` (строка 184).
- Что не так: Не описано, что происходит с лентой, которую уже получают акторы, если администратор выключил ленту на странице во время работы курса.
- Как исправить: Описать поведение ленты, которую выключили после её подключения.

#### <a id="s-29"></a>S-29 [MINOR] Часть обязательных формулировок без идентификатора требования
- Прочее · Прослеживаемость · [REQ-02](#req-02), [REQ-04](#req-04), [REQ-09](#req-09), [REQ-11](#req-11), [REQ-14](#req-14), [REQ-18](#req-18), [REQ-24](#req-24) · раздел «3. Specific Requirements».
- Цитаты: `The system must be able to capture and manage files where appropriate.` (строка 158); `The system must be able to display web feeds, such as RSS 2.0 feeds,` (строка 180); `The system must be able to use search functionality as a way to navigate Moodle pages instead of using hierarchical links.` (строка 186).
- Что не так: Формулировки с модальными глаголами не имеют номера 3.x.y или 4.x.y и не выделены как отдельные требования.
- Как исправить: Присвоить каждой обязательной формулировке уникальный идентификатор.

### 4.2. Взаимная непротиворечивость

**Анализ.**

- Согласованность (ISO 29148 п. 5.2.6; IEEE 830 п. 4.3.4): **нарушен**. Сравнил правила доступа к оценкам в 3.5.2 и 3.5.3, способы архивации клипов в 3.2.1, ссылки на брейнсторминг в 1.4.1 и 2.4 и версию Moodle в 1.2. Найдены противоречие в праве просмотра оценок другим актором, нерешённый выбор между двумя способами архивации и противоречие в ссылке на документ. Числа в 4.2 и 4.3 совпадают между текстом и критериями.
- Понятность (ISO 29148 п. 5.2.6): **частично**. Сравнил, что ожидается от системы и как она связана с окружением: SMS и e-mail, API Moodle, сторонние wiki и блоги, пустые разделы 4.5 и 4.7. Ожидаемое поведение в целом ясно, но способ связи с внешними сервисами и ограничения окружения не описаны.

#### <a id="s-01"></a>S-01 [CRITICAL] Право просмотра оценок другим актором: в 3.5.2 запрещено, в 3.5.3 разрешено при оспаривании
- Противоречие · Согласованность · [REQ-16](#req-16), [REQ-17](#req-17) · раздел «3.5.3».
- Цитаты: `No other actor should be able to view another’s grades except an actor in the role of course administrator for the course to which the grades belong.` (строка 203); `This way, another actor can review the grade information if their score on an assignment has changed and they wish to dispute it.` (строка 205).
- Что не так: В 3.5.2 просмотр чужих оценок запрещён всем, кроме курсового администратора. В 3.5.3 другой актор может просматривать информацию об оценках, если хочет оспорить свою оценку. Последствие: Нельзя реализовать правило доступа к истории оценок: неясно, кто её видит и видит ли студент собственную историю.
- Критик слил сюда: [D-36](#d-36), их текст в [приложении Б](#appendix-b).
- Вопрос заказчику (бизнес): Кому доступна история изменений оценки: только курсовому администратору или также студенту, чью оценку меняли? См. [Q-01](#q-01).
- Как исправить: Указать в 3.5.3 единое правило доступа к истории изменений оценок и согласовать его с ограничением из 3.5.2.

#### <a id="s-15"></a>S-15 [MAJOR] Связь системы с SMS, e-mail, API Moodle и сторонними сервисами не описана
- Пробел · Понятность · [REQ-21](#req-21), [REQ-19](#req-19), [REQ-20](#req-20) · раздел «4.7 Interfaces».
- Цитаты: `The system must provide both e-mail and SMS notifications for pages.` (строка 216); `Puget Sound and that any enhancements to the system will utilize the existing APIs made available by` (строка 112); `There are better, freelyavailable solutions which should be integrated into Moodle to provide the best functionality possible for all actors without having to use 3rd party services.` (строка 207).
- Что не так: В 3.7.1 требуются SMS и e-mail уведомления, но не сказано, через какой сервис они отправляются. В 1.2 говорится об использовании API Moodle, а в 3.6 о сторонних решениях для wiki и блогов без уточнения, какие именно и как интегрируются. Раздел 4.7 Interfaces пуст. Последствие: Нельзя определить состав внешних интеграций, их зависимости и объём работ по интеграции.
- Вопрос архитектору: Через какой сервис отправляются SMS-уведомления: собственный шлюз университета или внешний провайдер (назвать провайдера)?
- Как исправить: Описать в 4.7 внешние сервисы и API, через которые работают уведомления, wiki и блоги, и то, что система от них получает и отдаёт.

#### <a id="s-16"></a>S-16 [MAJOR] Раздел 4.5 Design Constraints пуст, ограничения окружения не описаны
- Пробел · Понятность · раздел «4.5 Design Constraints».
- Цитата: `4.5 Design Constraints` (строка 93).
- Что не так: Раздел 4.5 назван, но содержит только заголовок без ограничений. Последствие: Нельзя понять, какие ограничения окружения и платформы обязательны при доработке Moodle.
- Вопрос архитектору: Какие ограничения проектирования обязательны для доработки Moodle: перечислить их.
- Как исправить: Заполнить 4.5 ограничениями проектирования или явно указать, что ограничений нет.

#### <a id="s-17"></a>S-17 [MAJOR] Способ архивации голосовых клипов не выбран: предпросмотр или автоматическая архивация
- Прочее · Согласованность · [REQ-05](#req-05) · раздел «3.2.1».
- Цитата: `This can be done one of two ways: 1) the actor can be allowed to preview the voice clip before it is archived and determine whether or not he or she would like that clip to be archived, or 2) a newly created voice clip can be automatically archived.` (строка 169).
- Что не так: В 3.2.1 описаны два несовместимых способа архивации клипов: с предпросмотром и решением актора либо автоматически после создания. Документ не говорит, какой из них обязателен. Последствие: Нельзя определить, появляется ли клип в архиве сразу или только после решения актора, и как работает удаление из архива.
- Критик слил сюда: [D-10](#d-10), их текст в [приложении Б](#appendix-b).
- Вопрос заказчику (бизнес): Какой способ архивации клипов обязателен: предпросмотр с решением актора перед архивацией или автоматическая архивация сразу после создания клипа?
- Как исправить: Выбрать один способ архивации и описать его поведение, либо явно указать, что выбор способа остаётся за настройкой.

#### <a id="s-18"></a>S-18 [MAJOR] Объём дискового пространства для клипов не задан числом
- Пробел · Согласованность · [REQ-05](#req-05) · раздел «3.2.1».
- Цитата: `Equal and finite drive space needs to be allotted to each actor in the role of professor or administrator` (строка 169).
- Что не так: В 3.2.1 сказано, что пространство должно быть равным и конечным, но его размер не задан ни в одной строке документа. Последствие: Нельзя проверить выделение пространства и поведение системы при его исчерпании.
- Критик слил сюда: [D-09](#d-09), их текст в [приложении Б](#appendix-b).
- Вопрос заказчику (бизнес): Какой объём дискового пространства выделяется каждому преподавателю или администратору под клипы: задать значение в гигабайтах?
- Как исправить: Указать размер пространства на одного преподавателя или администратора и единицу измерения.

#### <a id="s-26"></a>S-26 [MINOR] Раздел 1.4.1 утверждает, что брейнсторминг не упоминается дальше, но 2.4 на него ссылается
- Противоречие · Согласованность · раздел «1.4.1».
- Цитаты: `This document does not make any further reference to the requirements brainstorming document.` (строка 125); `which is summarized in Moodle Requirements Brainstorming.pdf (referenced in section 1.4.1).` (строка 148).
- Что не так: В 1.4.1 сказано, что документ больше не ссылается на брейнсторминг, но в 2.4 такая ссылка есть.
- Вопрос аналитику: Нужна ли ссылка на брейнсторминг в разделе 2.4: да или нет?
- Как исправить: Убрать одно из утверждений или исправить формулировку в 1.4.1 или 2.4.

#### <a id="s-27"></a>S-27 [MINOR] В разделе 1.2 не указана версия Moodle, оставлена пометка TODO
- Прочее · Согласованность · раздел «1.2».
- Цитата: `This documents deals with the immediate requirements for the development of core functionality currently unavailable in Moodle, the existing courseware system candidate (version TODO: Version of` (строка 109).
- Что не так: В разделе области действия осталась незаполненная пометка TODO вместо номера версии Moodle.
- Вопрос заказчику (бизнес): Какая версия Moodle принята за основу: указать номер версии?
- Как исправить: Указать номер версии Moodle, для которой составлен набор требований.

### 4.3. Осуществимость и стандарты

**Анализ.**

- Осуществимость набора (ISO 29148 п. 5.2.6): **частично**. Документ ссылается на RSS 2.0 (строка 180), MPEG Audio mp3 (строки 174 и 176), сторонние API Moodle (строка 112) и поисковую систему Google (строка 194). Раздел 4.9 Applicable Standards пуст, поэтому сверить требования с этими стандартами и форматами по документу нельзя. Срок и бюджет, по которым отбирается приоритет 3, не заданы числами, поэтому осуществимость релиза не оценить.
- Ранжированность (IEEE 830 п. 4.3.5): **частично**. Приоритеты 1-3 заданы для групп требований (строки 161, 167, 182, 199, 208, 215, 224, 229, 233, 237, 241, 246, 250), уровень 4 определён, но ни одному требованию не назначен. Стабильность требований в документе не указана, поэтому оценить её по тексту нельзя.
- Модифицируемость (IEEE 830 п. 4.3.7): **частично**. Перекрёстные ссылки есть (например, на подраздел 3.4.2 в строке 191 и на раздел 1.4.1 в строке 148). Термин «page» определён в четырёх местах с разным смыслом, а поиск описан дважды. Часть требований объединена в одном пункте с несколькими обязанностями.

#### <a id="s-02"></a>S-02 [CRITICAL] Термин «page» определён по-разному в разных разделах
- Противоречие · Модифицируемость · [REQ-10](#req-10), [REQ-12](#req-12) · раздел «3.3 Web Feeds».
- Цитаты: `For this requirement, page refers to any distinct block (e.g., assignments, wikis, forum threads, etc.).` (строка 181); `For this requirement, page refers to any distinct page, such as an assignment, a wiki page, or a forum post.` (строка 187).
- Что не так: В строке 181 «page» означает отдельный блок, в строке 187 отдельную страницу. Определение повторяется в каждом разделе с другим смыслом. Последствие: Нельзя однозначно определить, к каким элементам относится переключение веб-лент для каждой страницы (3.3.1) и поиск по страницам (3.4.1).
- Уровень поднят кодом с MAJOR до CRITICAL: два места документа задают разное поведение.
- Вопрос аналитику: Что считается «страницей» для переключения веб-лент в 3.3.1: отдельный блок (строка 181) или любая отдельная страница (строка 187)? См. [Q-02](#q-02).
- Как исправить: Задать одно определение термина «page» в разделе определений и ссылаться на него из требований.

#### <a id="s-19"></a>S-19 [MAJOR] Раздел 4.9 Applicable Standards пуст, стандарты и форматы не зафиксированы
- Пробел · Осуществимость набора · [REQ-06](#req-06), [REQ-07](#req-07), [REQ-21](#req-21) · раздел «4.9 Applicable Standards».
- Цитата: `4.9 Applicable Standards` (строка 101).
- Что не так: В документе упоминаются RSS 2.0, MPEG Audio mp3 и уведомления SMS и e-mail, но обязательные стандарты и форматы в 4.9 не перечислены. Последствие: Нельзя проверить, какие форматы обязательны, и подтвердить, что требования осуществимы в принятых стандартах.
- Вопрос аналитику: Должен ли RSS 2.0 (строка 180) быть обязательным форматом веб-лент: да или нет? См. [Q-08](#q-08).
- Как исправить: Перечислить обязательные стандарты и форматы в 4.9 с указанием, к каким требованиям они относятся.

#### <a id="s-20"></a>S-20 [CRITICAL] Состав релиза зависит от срока и бюджета, которые в документе не заданы
- Пробел · Осуществимость набора · [REQ-01](#req-01) · раздел «3. Specific Requirements».
- Цитаты: `as can be developed within the project timeframe and budget constraints` (строка 156); `such Priority 3 requirements as can be developed` (строка 156).
- Что не так: Объём приоритета 3 определяется сроком и бюджетом проекта, но ни срок, ни бюджет в документе не указаны. Последствие: Нельзя оценить, реализуем ли релиз с приоритетами 1 и 2 и частью приоритета 3 при заданных ограничениях.
- Критик слил сюда: [D-01](#d-01), [D-02](#d-02), их текст в [приложении Б](#appendix-b).
- Уровень поднят до CRITICAL при слиянии с более критичным повтором.
- Вопрос заказчику (бизнес): Какую дату окончания проекта задать, в формате ДД.ММ.ГГГГ, до которой определяется состав приоритета 3? См. [Q-04](#q-04).
- Как исправить: Указать срок и бюджет проекта или правило отбора требований приоритета 3 в релиз.

#### <a id="s-28"></a>S-28 [MINOR] Требование к поисковой строке дано в двух подразделах
- Прочее · Модифицируемость · [REQ-12](#req-12), [REQ-13](#req-13) · раздел «3.4 Search».
- Цитаты: `First, it should be present in the form of a search box and a “Search” button on the top or bottom of every page.` (строка 191); `The system must display a search box on every page after an actor has logged in.` (строка 195).
- Что не так: Требование к поисковой строке записано в 3.4.1 и в 3.4.2 отдельно, при этом формулировки различаются по месту размещения.
- Как исправить: Оставить требование к строке поиска только в 3.4.2 и ссылаться на него из 3.4.1.

<a id="summary"></a>
## 5. Сводка

| Показатель | Значение |
| :--- | :---: |
| Требований всего | 29 |
| без своих замечаний | 0 |
| с дефектами | 29 |
| Замечаний всего | 80 |
| в отдельных требованиях | 51 |
| по набору | 29 |
| CRITICAL (критичный) | 7 |
| MAJOR (существенный) | 61 |
| MINOR (незначительный) | 12 |
| Вопросов автору | 15 |

### Блокеры

**Противоречия**

1. [S-01](#s-01) · [REQ-16](#req-16), [REQ-17](#req-17) · Право просмотра оценок другим актором: в 3.5.2 запрещено, в 3.5.3 разрешено при оспаривании
2. [S-02](#s-02) · [REQ-10](#req-10), [REQ-12](#req-12) · Термин «page» определён по-разному в разных разделах
3. [D-22](#d-22) · [REQ-11](#req-11) · Строка 186 говорит, что поиск заменяет иерархические ссылки
4. [D-53](#d-53) · [REQ-25](#req-25) · Основная фраза требует доступности 24 часа в сутки и 7 дней в неделю, а пояснение признает достаточным 99% времени доступности и не исключает плановые простои

**Непроверяемые и неоднозначные формулировки**

5. [D-03](#d-03) · [REQ-02](#req-02) · Из-за where appropriate нельзя определить, в каких случаях загрузка должна быть разрешена, поэтому тест не имеет критерия успеха
6. [D-13](#d-13) · [REQ-07](#req-07) · Критерий «conducive to speech» не даёт способа проверить, что аудио сохранено в нужном формате

**Неполные формулировки и пробелы**

7. [S-20](#s-20) · [REQ-01](#req-01) · Состав релиза зависит от срока и бюджета, которые в документе не заданы

## 6. Вердикт

**Не рекомендуется начинать.**

Правило. «Не рекомендуется начинать», если есть хотя бы одно замечание CRITICAL, которое не снято критиком и не ушло в карантин из-за ненайденной цитаты. «Условно допускается», если CRITICAL нет, но есть MAJOR. «Допускается», если есть только MINOR или замечаний нет. Готовность к тестированию считается отдельно: «Нет», если есть CRITICAL по проверяемости, однозначности, полноте, согласованности или валидируемости; «Да, с оговорками», если есть другие CRITICAL или MAJOR; иначе «Да». Если отчёт неполный, а CRITICAL не найден, решение «Не вынесен», готовность «Не определена».

Решение «Не рекомендуется начинать» подтверждается: из 29 требований у многих нельзя определить условие или порог проверки, а в тексте есть прямые противоречия. Главные препятствия: противоречия по поиску и доступности (D-22, D-53), доступу к оценкам и определению page (S-01, S-02), а также неизмеримые формулировки, такие как where appropriate, conducive to speech и quickly (D-03, D-13, D-23). Тестировать нельзя без числовых порогов по нагрузке, времени восстановления и размеру файлов (D-56, D-52, D-05), а срок релиза опирается на бюджет и срок, которых нет (S-20). Пустые разделы 4.5, 4.7 и 4.9 и незакрытые пробелы по резервному копированию (S-05, S-16, S-19, S-04) тоже мешают разработке.

Что исправить в первую очередь:

1. Выбрать одно значение для каждого из четырёх противоречий (поиск, доступность, доступ к истории оценок, определение page) и переписать строки 181, 187, 203, 230-232 в соответствии с выбором. ([D-22](#d-22), [D-53](#d-53), [S-01](#s-01), [S-02](#s-02))
2. Заменить where appropriate, conducive to speech и срок релиза конкретными условиями, кодеком и датой или списком требований приоритета 3. ([D-03](#d-03), [D-13](#d-13), [S-20](#s-20))
3. Задать числовые пороги: размер и число файлов, время поиска, время простоя, время ответа, трудозатраты на изменение. ([D-05](#d-05), [D-07](#d-07), [D-23](#d-23), [D-51](#d-51), [D-56](#d-56), [D-59](#d-59))
4. Для каждого требования добавить проверяемый критерий приёмки и закрыть открытые перечни через such as и etc. полным списком. ([S-22](#s-22), [S-23](#s-23), [D-24](#d-24), [D-34](#d-34), [D-42](#d-42))
5. Описать резервное копирование: условие внешней копии, срок хранения, точку отсчёта восстановления и поведение при сбое восстановления. ([S-04](#s-04), [S-06](#s-06), [D-49](#d-49), [D-52](#d-52))
6. Указать событие, запускающее уведомление, правило резервного канала при недоступном SMS и сервис, через который отправляются SMS. ([D-43](#d-43), [S-11](#s-11), [S-12](#s-12), [S-15](#s-15))
7. Заполнить разделы 4.5, 4.7 и 4.9 или написать «требований нет», исправить версии документа и Moodle и ссылку на брейнсторминг. ([S-05](#s-05), [S-16](#s-16), [S-19](#s-19), [S-21](#s-21), [S-03](#s-03), [S-27](#s-27), [S-26](#s-26))

<a id="limits"></a>
### Что агент не проверяет

- Отметка «замечаний не найдено» у критерия значит, что агент не нашёл по нему нарушений. Доказательством того, что требование верное, она не служит.
- Нужно ли требование и верно ли оно передаёт цель бизнеса, без автора ТЗ проверить нельзя: агент видит только текст документа. Необходимость и корректность оценены по этому тексту.
- Осуществимость по срокам, оборудованию, бюджету и людям не проверяется: таких данных агент не получает, критерии осуществимости оценены только по тексту требований.
- Цитаты сверяются с документом кодом, смысл замечания нет. Замечание с точной цитатой тоже может быть ошибочным.
- Часть дефектов агент пропускает. Состав замечаний меняется от прогона к прогону даже на том же документе: модель отвечает не одинаково.
- Отчёт не заменяет ревью человеком: решение о передаче в разработку принимает команда.

<a id="questions"></a>
## 7. Вопросы к автору ТЗ

Вопросы собраны по адресату, а номера идут по важности, поэтому внутри раздела номера не подряд.

### Вопросы заказчику (бизнес)

#### <a id="q-03"></a>Q-03 · заказчику (бизнес) · блокирует разработку
**Кто определяет, на каких страницах допустима загрузка файлов и голосовых клипов: заданный перечень типов страниц или курсовой администратор?**
- Сейчас в документе: `capture and manage files where appropriate` (строка 158); `that can be used where appropriate` (строка 165).
- Суть: строки 158 и 165 используют where appropriate без условия
- Варианты:
  1. Перечень типов страниц задаёт система. Последствие: загрузка включена только на перечисленных типах страниц.
  2. Курсовой администратор выбирает страницы. Последствие: загрузка доступна на любой странице по решению администратора.
- Без ответа: нельзя проверить условие разрешения загрузки.
- Закрывает замечания: [D-03](#d-03), [D-08](#d-08).

#### <a id="q-01"></a>Q-01 · заказчику (бизнес) · блокирует разработку
**Кому доступна история изменений оценки: только курсовому администратору или также студенту, чью оценку меняли?**
- Сейчас в документе: `No other actor should be able to view another’s grades except an actor in the role of course administrator for the course to which the grades belong.` (строка 203); `This way, another actor can review the grade information if their score on an assignment has changed and they wish to dispute it.` (строка 205).
- Суть: строка 203 запрещает просмотр чужих оценок, строка 205 разрешает оспаривание
- Варианты:
  1. Курсовому администратору и студенту, чью оценку меняли. Последствие: студент видит историю своей оценки и может её оспорить.
  2. Только курсовому администратору, как в 3.5.2. Последствие: студент не видит историю и не может оспорить изменение.
- Рекомендуем: вариант 1, потому что строка 205 прямо даёт оспаривание через историю изменений.
- Без ответа: нельзя реализовать права доступа к истории оценок.
- Закрывает замечания: [S-01](#s-01).

#### <a id="q-04"></a>Q-04 · заказчику (бизнес) · блокирует разработку
**До какой даты определяется состав приоритета 3 в релизе, если срок и бюджет в документе не заданы?**
- Сейчас в документе: `as can be developed within the project timeframe and budget constraints` (строка 156); `such Priority 3 requirements as can be developed` (строка 156).
- Суть: строка 156 опирается на срок и бюджет, которых в документе нет
- Варианты:
  1. Задать дату окончания проекта, формат ДД.ММ.ГГГГ. Последствие: состав приоритета 3 фиксируется по дате и остатку бюджета.
  2. Перечислить требования приоритета 3 в релизе явно. Последствие: состав релиза не зависит от срока, тест сверяет список.
- Без ответа: нельзя спланировать состав релиза приоритета 3.
- Закрывает замечания: [S-20](#s-20).

#### <a id="q-05"></a>Q-05 · заказчику (бизнес) · блокирует разработку
**Строка 186 говорит о замене иерархических ссылок, строка 187 о поиске в дополнение к иерархии: что верно?**
- Сейчас в документе: `instead of using hierarchical links` (строка 186).
- Суть: строки 186 и 187 противоречат друг другу
- Варианты:
  1. Поиск заменяет иерархические ссылки. Последствие: иерархические ссылки навигации убираются из интерфейса.
  2. Поиск дополняет иерархические ссылки. Последствие: иерархическая навигация остаётся, поиск добавляется рядом.
- Без ответа: нельзя спроектировать навигацию и тесты поиска.
- Закрывает замечания: [D-22](#d-22).

#### <a id="q-06"></a>Q-06 · заказчику (бизнес) · блокирует разработку
**Какой уровень доступности системы верен: круглосуточная работа 24/7 или 99% времени доступности?**
- Сейчас в документе: `The system should be available 24 hours a day, 7 days a week.` (строка 230).
- Суть: строка 230 требует 24/7, строка 232 считает достаточным 99%
- Варианты:
  1. Оба места верны: 24/7 как ориентир, 99% как порог. Последствие: тест проверяет 99% доступности за заданный период.
  2. Только 99% времени доступности. Последствие: допустим простой около 1% времени, проверяется процент.
  3. Только 24 часа в сутки и 7 дней в неделю. Последствие: тест проверяет круглосуточный доступ без процента простоя.
- Рекомендуем: вариант 1, потому что строка 231 называет 24/7 общим ориентиром, строка 232 задаёт порог.
- Без ответа: нельзя задать критерий проверки доступности.
- Закрывает замечания: [D-53](#d-53).

#### <a id="q-09"></a>Q-09 · заказчику (бизнес) · нужен до начала спринта
**Что система делает при числе одновременных пользователей выше поддерживаемого значения?**
- Сейчас в документе: `Therefore, it must be able to handle at least 1,000 concurrent users.` (строка 236).
- Суть: строка 236 задаёт минимум 1000, поведение выше порога не описано
- Варианты:
  1. Отклоняет новые входы с сообщением. Последствие: новый пользователь получает отказ при высокой нагрузке.
  2. Продолжает работать с замедлением. Последствие: все сессии работают, время ответа растёт, тест проверяет деградацию.
- Без ответа: нельзя задать поведение при перегрузке и сценарий нагрузочного теста.
- Закрывает замечания: [S-14](#s-14).

#### <a id="q-10"></a>Q-10 · заказчику (бизнес) · нужен до начала спринта
**Какой формат получает пользователь при скачивании голосового клипа: только mp3 или заданный список форматов?**
- Сейчас в документе: `in a flexible format` (строка 173).
- Суть: строка 173 говорит flexible format, строка 174 приводит mp3 как пример
- Варианты:
  1. Только MPEG Audio mp3. Последствие: скачивание отдаёт mp3, тест проверяет один формат.
  2. Заданный список форматов, назвать их. Последствие: тест проверяет каждый формат из списка.
- Рекомендуем: вариант 1, потому что строка 176 говорит, что клипы конвертируются в mp3 при скачивании.
- Без ответа: нельзя реализовать и проверить формат скачивания.
- Закрывает замечания: [D-12](#d-12).

#### <a id="q-11"></a>Q-11 · заказчику (бизнес) · нужен до начала спринта
**Входит ли поиск в интернете через внешнюю поисковую систему в требование 3.4.1?**
- Сейчас в документе: `the search page described above might allow for the possibility` (строка 194).
- Варианты:
  1. Да, поиск через внешнюю поисковую систему входит. Последствие: в поиске появляется запрос во внешнюю сеть.
  2. Нет, поиск ограничен страницами Moodle. Последствие: поиск по всей сети не реализуется и не тестируется.
- Рекомендуем: вариант 2, потому что 3.4.1 ограничивает поиск страницами курса.
- Без ответа: нельзя реализовать вторую страницу поиска.
- Закрывает замечания: [D-25](#d-25).

#### <a id="q-12"></a>Q-12 · заказчику (бизнес) · нужен до начала спринта
**По умолчанию поиск из курса ищет только в этом курсе или по всем курсам?**
- Сейчас в документе: `with an option to search all courses` (строка 196).
- Суть: строка 196 задаёт опцию поиска по всем курсам без умолчания
- Варианты:
  1. Только в текущем курсе. Последствие: поиск по всем курсам выполняется отдельным действием.
  2. По всем курсам, текущий курс выбирается опцией. Последствие: результаты сразу включают все курсы актёра.
- Без ответа: нельзя реализовать значение поиска по умолчанию.
- Закрывает замечания: [D-29](#d-29).

#### <a id="q-14"></a>Q-14 · заказчику (бизнес) · нужен до начала спринта
**От какого момента отсчитываются шесть часов восстановления данных из резервной копии?**
- Сейчас в документе: `restore back-up data within six hours` (строка 228).
- Суть: строка 228 задаёт шесть часов без точки отсчёта
- Варианты:
  1. От обнаружения сбоя. Последствие: срок считается от момента, когда сбой замечен.
  2. От запроса администратора на восстановление. Последствие: срок считается от команды, а не от сбоя.
- Без ответа: нельзя измерить срок восстановления в тесте.
- Закрывает замечания: [D-52](#d-52).

#### <a id="q-15"></a>Q-15 · заказчику (бизнес) · нужен до начала спринта
**Какое предельное время получения результатов поиска задать, в секундах?**
- Сейчас в документе: `find what they are looking for quickly` (строка 187).
- Суть: строка 187 говорит quickly без числового порога
- Варианты:
  1. Задать предельное время в секундах, например 3. Последствие: тест проверяет ответ поиска за заданное время.
  2. Оставить без предельного времени. Последствие: тест не сможет признать поиск быстрым.
- Без ответа: нельзя задать критерий приёмки поиска.
- Закрывает замечания: [D-23](#d-23).

### Вопросы аналитику

#### <a id="q-02"></a>Q-02 · аналитику · блокирует разработку
**Что считается страницей для веб-лент в 3.3.1: отдельный блок курса или любая отдельная страница?**
- Сейчас в документе: `For this requirement, page refers to any distinct block (e.g., assignments, wikis, forum threads, etc.).` (строка 181); `For this requirement, page refers to any distinct page, such as an assignment, a wiki page, or a forum post.` (строка 187).
- Суть: строка 181 определяет page как блок, строка 187 как любую страницу
- Варианты:
  1. Отдельный блок: задание, вики, ветка форума. Последствие: лента задаётся на уровне блока, а не страницы.
  2. Любая отдельная страница курса. Последствие: переключатель лент появляется на каждой странице курса.
- Без ответа: нельзя реализовать переключатель лент для 3.3.1.
- Закрывает замечания: [S-02](#s-02).

#### <a id="q-08"></a>Q-08 · аналитику · нужен до начала спринта
**Какие форматы веб-лент обязательны: только RSS 2.0 или также другие форматы?**
- Сейчас в документе: `such as RSS 2.0 feeds` (строка 180); `4.9 Applicable Standards` (строка 101).
- Суть: строка 180 приводит RSS 2.0 как пример, стандарт не задан
- Варианты:
  1. Только RSS 2.0. Последствие: тест проверяет один формат ленты.
  2. RSS 2.0 и другие форматы, назвать их. Последствие: тест проверяет перечисленные форматы.
- Без ответа: нельзя определить набор форматов лент для реализации.
- Закрывает замечания: [D-19](#d-19), [S-19](#s-19).

#### <a id="q-13"></a>Q-13 · аналитику · нужен до начала спринта
**Что считается одновременным пользователем: активная сессия в момент замера или запрос за заданный интервал?**
- Сейчас в документе: `The system should support at least 1000 concurrent users.` (строка 235).
- Суть: строка 235 использует concurrent users без определения
- Варианты:
  1. Пользователь с активной сессией в момент замера. Последствие: нагрузочный тест считает открытые сессии.
  2. Пользователь, отправивший запрос за интервал. Последствие: тест считает пользователей по числу запросов за интервал.
- Без ответа: нельзя построить нагрузочный сценарий для 4.3.1.
- Закрывает замечания: [D-55](#d-55).

### Вопросы архитектору

#### <a id="q-07"></a>Q-07 · архитектору · блокирует разработку
**Какой кодек и контейнер использовать для хранения аудиозаписей в портфолио?**
- Сейчас в документе: `a format conducive to speech` (строка 175).
- Суть: строка 175 говорит только optimized for speech, без формата
- Варианты:
  1. Задать конкретный кодек и контейнер. Последствие: тест сверяет формат хранения с заданным значением.
  2. Оставить формат хранения на усмотрение разработчика. Последствие: тест не может признать хранение в нужном формате.
- Рекомендуем: вариант 1, потому что без заданного формата тест не сможет признать 3.2.3 выполненным.
- Без ответа: нельзя реализовать хранение аудио и тест 3.2.3.
- Закрывает замечания: [D-13](#d-13).

## Приложение А. Критерии и уровни критичности

Для отдельного требования:

- **Необходимость** (ISO 29148 п. 5.2.5). Требование задаёт нужную возможность, характеристику или ограничение. Если его убрать, появится пробел, который не закрывают другие требования.
- **Уместность уровня** (ISO 29148 п. 5.2.5). Уровень детализации подходит документу. Требование говорит, что нужно получить, и не навязывает проектное или техническое решение без причины.
- **Однозначность** (ISO 29148 п. 5.2.5; IEEE 830 п. 4.3.2). Формулировку можно понять только одним способом. Нет оценочных слов, расплывчатых количеств, неясных ссылок, местоимений и терминов без определения.
- **Полнота** (ISO 29148 п. 5.2.5; IEEE 830 п. 4.3.3). В требовании есть всё нужное для реализации и проверки: условие, участник, действие, результат, значения и единицы, поведение при ошибках и на границах диапазонов.
- **Атомарность** (ISO 29148 п. 5.2.5). Требование описывает одну возможность, характеристику или ограничение, а не несколько сразу.
- **Осуществимость** (ISO 29148 п. 5.2.5). Требование можно выполнить при известных технических, правовых и ресурсных ограничениях с приемлемым риском.
- **Проверяемость** (ISO 29148 п. 5.2.5; IEEE 830 п. 4.3.6). Есть конечный способ доказать, что требование выполнено: тест, измерение, осмотр или анализ с однозначным критерием успеха.
- **Корректность** (ISO 29148 п. 5.2.5; IEEE 830 п. 4.3.1). Требование верно отражает потребность и не содержит фактических и технических ошибок, в том числе нарушений общепринятых стандартов, протоколов и практик безопасности.
- **Непротиворечивость** (IEEE 830 п. 4.3.4). Части требования не противоречат друг другу: условие, действие, значения, пример и описание говорят об одном и том же.

Для набора требований:

- **Полнота набора** (ISO 29148 п. 5.2.6; IEEE 830 п. 4.3.3, подраздел «Системная полнота»). Набор покрывает нужные функции, сценарии, данные, интерфейсы и нефункциональные свойства. Нет пустых разделов, заглушек и мест с пометкой «будет определено».
- **Согласованность** (ISO 29148 п. 5.2.6; IEEE 830 п. 4.3.4, подраздел «Взаимная непротиворечивость»). Требования не противоречат друг другу и не дублируются. Термины, единицы измерения, типы и значения одинаковы во всём наборе.
- **Осуществимость набора** (ISO 29148 п. 5.2.6, подраздел «Осуществимость и стандарты»). Весь набор можно реализовать при заданных ограничениях по срокам, технологиям и рискам.
- **Понятность** (ISO 29148 п. 5.2.6, подраздел «Взаимная непротиворечивость»). Из набора ясно, что ожидается от системы и как она связана с окружением и смежными системами.
- **Валидируемость** (ISO 29148 п. 5.2.6, подраздел «Системная полнота»). Можно показать, что выполнение набора приведёт к заявленной цели: цель измерима, критерии приёмки покрывают требования.
- **Ранжированность** (IEEE 830 п. 4.3.5, подраздел «Осуществимость и стандарты»). У требований указаны важность и (или) стабильность.
- **Модифицируемость** (IEEE 830 п. 4.3.7, подраздел «Осуществимость и стандарты»). Структура документа даёт вносить изменения без рассогласования: есть перекрёстные ссылки, нет избыточности, каждое требование записано отдельно.
- **Прослеживаемость** (IEEE 830 п. 4.3.8, подраздел «Системная полнота»). У каждого требования есть уникальный идентификатор и понятный источник, на требование можно сослаться из проекта, кода и тестов. Версия документа зафиксирована.

Уровни критичности:

- CRITICAL: разработку по такому тексту начинать нельзя. Сюда относятся прямое логическое противоречие, требование, которое нельзя проверить, грубое нарушение стандарта протокола или формата, не описанная обработка критической ошибки. Сюда же относится расхождение двух мест документа, если они задают разное наблюдаемое поведение, разный результат расчёта или разные единицы одной величины: по какому месту ни сделай, второе окажется нарушено.
- MAJOR: нужен ответ автора до начала работ. Сюда относятся неполный сценарий, пропущенный граничный случай, двусмысленная формулировка, расхождение типов и форматов одного поля, пустой раздел.
- Расхождение только в названиях, обозначениях и оформлении при одинаковом смысле не выше MAJOR.
- MINOR: разработку не блокирует. Сюда относятся опечатки, стиль, нет служебных сведений о документе.

<a id="appendix-b"></a>
## Приложение Б. Снятые, слитые и неподтверждённые замечания

- <a id="d-01"></a>**D-01 [CRITICAL] Проверяемость** · [REQ-01](#req-01) · Фраза «as can be developed» не задаёт перечень Priority 3 требований, поэтому результат релиза нельзя сверить с текстом. Причина: слито с другим замечанием [S-20](#s-20): Тот же дефект: состав приоритета 3 зависит от срока и бюджета, которые не заданы (строка 156). Исправление общее, оставлен набор.
- <a id="d-02"></a>**D-02 [MAJOR] Однозначность** · [REQ-01](#req-01) · Срок и бюджет, на которые ссылается фраза, в документе не заданы. Причина: слито с другим замечанием [S-20](#s-20): Срок и бюджет не заданы (строка 156). Исправление то же, что в замечании по набору.
- <a id="d-04"></a>**D-04 [MAJOR] Однозначность** · [REQ-02](#req-02) · Фраза where appropriate оставляет на усмотрение читателя, где система принимает файлы. Причина: слито с другим замечанием [D-03](#d-03): Та же фраза where appropriate в строке 158, исправление одно: задать условия.
- <a id="d-09"></a>**D-09 [MAJOR] Полнота** · [REQ-05](#req-05) · Объём дискового пространства не задан: слово «finite» без числа и единицы измерения. Причина: слито с другим замечанием [S-18](#s-18): Размер дискового пространства не задан (строка 169). Исправление то же, что в замечании по объёму.
- <a id="d-10"></a>**D-10 [MAJOR] Однозначность** · [REQ-05](#req-05) · Текст описывает два способа архивации, предварительный просмотр и автоматическую архивацию, и не выбирает обязательный. Причина: слито с другим замечанием [S-17](#s-17): Строка 169 даёт два способа архивации без выбора обязательного. Исправление то же, что в замечании по набору.
- <a id="d-14"></a>**D-14 [MAJOR] Однозначность** · [REQ-07](#req-07) · Формулировка «conducive to speech» не называет формат и допускает разные трактовки. Причина: слито с другим замечанием [D-13](#d-13): Та же фраза в строке 175, исправление одно: назвать формат.
- <a id="d-16"></a>**D-16 [MAJOR] Полнота** · [REQ-08](#req-08) · Требование не описывает последствия удаления клипа, уже прикреплённого к странице или сданного как задание. Причина: слито с другим замечанием [S-10](#s-10): Последствия удаления прикреплённого клипа не описаны. Исправление то же, что в замечании по набору.
- <a id="d-32"></a>**D-32 [MAJOR] Непротиворечивость** · [REQ-15](#req-15) · Отметка времени хранится только для последнего изменения, но цель требования состоит в просмотре, когда оценки выставлялись и как менялась успеваемость. Причина: снято критиком: Строка 205 задаёт историю изменений и временные метки для каждого изменения, поэтому вопрос снят.
  - Цитата модели: `Time stamps should be attached to the last time the grade was modified` (строка 201)
- <a id="d-36"></a>**D-36 [MAJOR] Однозначность** · [REQ-17](#req-17) · Фраза «another actor» не говорит, кто именно может просматривать историю: только студент, чья оценка менялась, или любой другой участник. Причина: слито с другим замечанием [S-01](#s-01): Неясно, кто может просматривать оценки другим актором. Исправление то же, что в замечании по набору.
- <a id="d-40"></a>**D-40 [MAJOR] Проверяемость** · [REQ-18](#req-18) · Формулировка «best functionality possible» не даёт способа доказать выполнение требования. Причина: слито с другим замечанием [D-39](#d-39): Та же фраза строки 207, исправление одно: задать измеримый критерий лучшести.
- <a id="d-48"></a>**D-48 [MAJOR] Полнота** · [REQ-23](#req-23) · Текст откладывает определение требований резервного копирования и не задаёт перечень компонентов с их периодичностью. Причина: слито с другим замечанием [S-04](#s-04): Состав и периодичность копий не заданы (строка 227). Исправление то же, что в замечании по набору.
- <a id="d-54"></a>**D-54 [MAJOR] Проверяемость** · [REQ-25](#req-25) · Не задан период, за который считаются 99% времени доступности, и не указано, как измеряется доступность. Причина: слито с другим замечанием [S-13](#s-13): Период и способ измерения 99% доступности не заданы (строка 232). Исправление то же, что в замечании по набору.
