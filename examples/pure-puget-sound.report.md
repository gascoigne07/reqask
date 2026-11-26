# Отчёт о проверке требований: pure-puget-sound.pdf

Отчёт сформирован агентом reqask автоматически по ISO/IEC/IEEE 29148:2018 и IEEE 830. Модель: claude-haiku-5-5. Дата: 2026-11-26 23:32:19 +0500.

**Вердикт: Не рекомендуется начинать.**

- Готовность к разработке: **Нет**
- Готовность к тестированию: **Нет**
- Требований: 27, с дефектами: 24. Замечаний: CRITICAL 11, MAJOR 47, MINOR 9. Вопросов автору: 15.

**Блокеры:**

- [S-01](#s-01) · [REQ-11](#req-11), [REQ-12](#req-12) · Поиск одновременно заменяет и дополняет иерархические ссылки навигации
- [S-02](#s-02) · [REQ-10](#req-10), [REQ-20](#req-20) · Термин «страница» определён в разных разделах как блок и как отдельная страница
- [S-03](#s-03) · [REQ-12](#req-12), [REQ-13](#req-13) · Поле поиска описано в 3.4.1 и 3.4.2 с разным условием показа
- [D-03](#d-03) · [REQ-02](#req-02) · Формулировка не задаёт результат, который можно наблюдать и проверить.
- [D-05](#d-05) · [REQ-04](#req-04) · Формулировка не задаёт наблюдаемый результат захвата и организации клипов.
- и ещё 6, полный список в [разделе 5](#summary)

**Главные вопросы автору ТЗ:**

- [Q-01](#q-01) · заказчику (бизнес): Что считается страницей для лент и уведомлений: отдельный блок информации (строка 181) или страница целиком (строка 217)?
- [Q-02](#q-02) · заказчику (бизнес): Как архивируется голосовой клип: после предпросмотра по решению актора или автоматически сразу после отправки?
- [Q-03](#q-03) · заказчику (бизнес): Каким показателем измеряется сопровождаемость по 4.4.1: часами FTE в месяц или долей изменённого кода в процентах?
- [Q-04](#q-04) · аналитику: Какие процедуры регламентного обслуживания и ошибки обязана покрывать документация администратора: задать явный список?
- [Q-05](#q-05) · заказчику (бизнес): Где показывается поле поиска: на каждой странице после входа (строка 195) или на каждой странице, включая страницы до входа (строка 191)?

Все вопросы в [разделе 7](#questions), для отправки автору: файл `report.questions.md`.

## 1. Паспорт прогона

| Прогон | Значение |
| :--- | :--- |
| Документ | pure-puget-sound.pdf, формат pdf, строк 258 |
| Чтение PDF | страницы без текста: 3; удалено строк колонтитулов: 52 |
| SHA-256 документа | `bc8fea411b7e40f114e453f09451cd3777da5f218f0d1414fbb640ec5ed9dce8` |
| Дата и время | 2026-11-26 23:32:19 +0500 |
| Длительность | 200.3 с |
| Модель | claude-haiku-5-5 (провайдер: custom) |
| Версия агента | 0.1.0, коммит ddf8472, есть незакоммиченные правки |
| Режим | живой прогон, часть ответов из кэша; формат ответа JSON: parse |
| Стандарты | ISO/IEC/IEEE 29148:2018 п. 5.2.5 и 5.2.6; IEEE Std 830-1998 п. 4.3 |
| Обращений к модели | 3, из кэша 7, повторов при сбоях 0 |
| Токены | вход 61665, выход 52290, всего 113955 |

| Самопроверка прогона | Значение |
| :--- | :--- |
| Покрытие нарезкой | строк с текстом 197, в требованиях 67 (34%), отмечены как не требования 130, не разобраны 0 |
| Цитаты | точных 87, нечётких 0, не найдено 0; замечаний в карантине 0, противоречий только с вопросом 0, свёрнуто в системные 0, отброшено без опоры на текст 0 |
| Критик | проверено CRITICAL и MAJOR 72: оставлено 57, понижено 1, снято 2, слито 12, без решения 0, решений отклонено кодом 0 |
| Ответы модели | исправлений JSON 0, отброшено дефектов проверкой 0, оценок 0; оценок не вернула модель 0, pass заменён на fail по дефекту 0; CRITICAL и MAJOR без вопроса 0; уровень поднят кодом по виду расхождения 0 |
| Сводные вопросы | от модели; отброшено проверкой 1, слито дублей 0, добавлено кодом для CRITICAL 1 |
| Шаги | выполнено 8, частично 0, не выполнено 0, не включено 3 |
| Правила | подсказок словаря 8, подтверждено моделью 7 (88%); строк с незаполненными местами (TODO, TBD и подобные) 2: 109, 227; есть в замечаниях 2 |

<details><summary>Журнал шагов</summary>

| Шаг | Что | Итог | Вызовов | Секунд | Результат |
| :-- | :--- | :--- | :-- | :-- | :--- |
| 0 | Чтение документа | выполнен | 0 | 0.0 | строк 258, формат pdf |
| 1 | Структурные проверки кодом | не включён | 0 | 0.0 | желательная часть; словарь формулировок работает внутри шага 3 |
| 2 | Контекст документа | не включён | 0 | 0.0 | желательная часть |
| 3 | Нарезка требований (258 строк) | выполнен | 0 | 0.0 | требований 27, пропущено фрагментов 60 |
| 4 | Проверка каждого требования | выполнен | 1 | 84.9 | дефектов 66, без проверки 0 |
| 5 | Набор требований целиком (два прохода) | выполнен | 0 | 0.0 | замечаний 15, анализов по критериям 8 |
| 5в | Чек-лист ревью из документа | не включён | 0 | 0.0 | желательная часть |
| 6 | Сверка цитат с документом | выполнен | 0 | 0.0 | цитат точных 87, нечётких 0, не найдено 0; в карантине 0, противоречий только с вопросом 0, свёрнуто в системные 0, отброшено без опоры 0 |
| 7 | Критик | выполнен | 1 | 53.0 | проверено 72 (групп кандидатов на слияние 19): оставлено 57, понижено 1, снято 2, слито 12, без решения 0, отклонено кодом 0 |
| 8 | Итог и сводные вопросы | выполнен | 1 | 62.4 | решение: Не рекомендуется начинать; вопросов 15 |
| 9 | Отчёт | выполнен | 0 | 0.0 | записаны: pure-puget-sound.report.md, pure-puget-sound.report.questions.md, pure-puget-sound.report.json |

</details>

## 2. Нарезка на требования

Выделено требований: **27**, у 21 есть идентификатор в документе. Границы заданы номерами строк, текст требований вырезан из документа кодом. Дословный текст каждого требования стоит в разделе 3.

<details><summary>Таблица нарезки: 27 требований</summary>

| ID | ID в документе | Раздел | Строки | Суть |
| :--- | :--- | :--- | :--- | :--- |
| [REQ-01](#req-01) | без номера | 3. Specific Requirements | 156, стр. 8 | Первый релиз включает требования приоритетов 1 и 2 и возможные из приоритета 3 |
| [REQ-02](#req-02) | без номера | 3.1 Multiple File Transfer | 158, стр. 8 | Система захватывает и управляет файлами там, где это уместно |
| [REQ-03](#req-03) | 3.1.1 | 3.1 Multiple File Transfer | 162-163, стр. 9 | Множественная загрузка файлов настраивается для каждой страницы |
| [REQ-04](#req-04) | без номера | 3.2 Audio Recording | 165, стр. 9 | Система захватывает и организует голосовые клипы там, где уместно |
| [REQ-05](#req-05) | 3.2.1 | 3.2 Audio Recording | 168-172, стр. 9 | Актор организует свои голосовые клипы в портфолио |
| [REQ-06](#req-06) | 3.2.2 | 3.2 Audio Recording | 173-174, стр. 9 | Актор скачивает голосовые клипы в гибком формате, например mp3 |
| [REQ-07](#req-07) | 3.2.3 | 3.2 Audio Recording | 175-176, стр. 9 | Аудиоклипы хранятся в формате, оптимизированном для речи |
| [REQ-08](#req-08) | 3.2.4 | 3.2 Audio Recording | 177-178, стр. 10 | Актор удаляет записанные голосовые клипы из своего портфолио |
| [REQ-09](#req-09) | без номера | 3.3 Web Feeds | 180, стр. 10 | Система отображает веб-ленты для страниц с блоками информации |
| [REQ-10](#req-10) | 3.3.1 | 3.3 Web Feeds | 183-184, стр. 10 | Веб-ленты включаются и выключаются для каждой страницы |
| [REQ-11](#req-11) | без номера | 3.4 Search | 186, стр. 10 | Поиск используется для навигации по страницам вместо иерархических ссылок |
| [REQ-12](#req-12) | 3.4.1 | 3.4 Search | 189-194, стр. 10 | Актор ищет страницы в пределах курса с фильтрами и категориями результатов |
| [REQ-13](#req-13) | 3.4.2 | 3.4 Search | 195-196, стр. 11 | Поле поиска отображается на каждой странице после входа |
| [REQ-14](#req-14) | без номера | 3.5 Gradebook | 198, стр. 11 | Администратор курса публикует оценки за задания студентов |
| [REQ-15](#req-15) | 3.5.1 | 3.5 Gradebook | 200-201, стр. 11 | Администратор курса оценивает задание по отношению баллов с отметкой времени |
| [REQ-16](#req-16) | 3.5.2 | 3.5 Gradebook | 202-203, стр. 11 | Оценки видны только их владельцу и администратору курса |
| [REQ-17](#req-17) | 3.5.3 | 3.5 Gradebook | 204-205, стр. 11 | Система хранит историю изменений оценок за задание |
| [REQ-18](#req-18) | 3.6.1 | 3.6 Social Networking Applications | 209-210, стр. 12 | Система предоставляет wiki для совместного создания документов |
| [REQ-19](#req-19) | 3.6.2 | 3.6 Social Networking Applications | 211-212, стр. 12 | Система предоставляет блоговый движок с общей аутентификацией и уведомлениями |
| [REQ-20](#req-20) | 3.7.1 | 3.7 Notifications | 216-218, стр. 12 | Система отправляет уведомления по e-mail и SMS для страниц |
| [REQ-21](#req-21) | 4.1.1 | 4.1 Usability | 221-224, стр. 12 | Простой адаптивный интерфейс и единая административная настройка |
| [REQ-22](#req-22) | 4.2.1 | 4.2 Reliability | 226-229, стр. 13 | Резервное копирование по настраиваемому расписанию и восстановление за шесть часов |
| [REQ-23](#req-23) | 4.2.2 | 4.2 Reliability | 230-233, стр. 13 | Система доступна круглосуточно с доступностью не ниже 99 процентов |
| [REQ-24](#req-24) | 4.3.1 | 4.3 Performance | 235-237, стр. 13 | Система поддерживает не менее 1000 одновременных пользователей |
| [REQ-25](#req-25) | 4.4.1 | 4.4 Supportability | 239-241, стр. 13 | Система сопровождается без существенных изменений в коде |
| [REQ-26](#req-26) | 4.6.1 | 4.6 On-line User Documentation and Help System Requirements | 244-246, стр. 14 | Актуальная онлайн-документация доступна на каждой странице |
| [REQ-27](#req-27) | 4.6.2 | 4.6 On-line User Documentation and Help System Requirements | 247-250, стр. 14 | Администраторы получают полную доступную для поиска документацию |

</details>

Не вошли в требования (эти строки видит проверка набора в разделе 4):

- заголовки: строки 3-15, 41-102, 103-105, 108, 114-115, 117, 119, 121, 123-124, 126, 131-132, 137, 140-141, 143, 145, 147, 149, 157, 164, 179, 185, 197, 206, 213, 219-220, 225, 234, 238, 242-243, 251-258
- служебные сведения: строки 16-21
- история изменений: строки 22-40
- вводный и поясняющий текст: строки 106-107, 109-113, 116, 118, 120, 122, 125, 127-130, 133-136, 138-139, 142, 144, 146, 148, 150-155, 159-160, 166, 181, 187, 207, 214
- прочее: строки 161, 167, 182, 188, 199, 208, 215

## 3. Проверка каждого требования

Значки: ✅ выполнен, ❌ нарушен, ➖ не применим, ❔ нельзя оценить по тексту. Шесть основных критериев показаны всегда, уместность уровня, атомарность и корректность только при нарушении.

**Без замечаний, все критерии выполнены (1):** <a id="req-03"></a>REQ-03 (строки 162-163).

**Дефект описан в общем замечании, на которое ссылается строка (2):**

- <a id="req-01"></a>**REQ-01 · строка 156 · страница 8 · 3. Specific Requirements**: слито критиком: [D-01](#d-01) в [S-12](#s-12), [D-02](#d-02) в [S-12](#s-12); ❌ Однозначность: Набор Priority 3 не определён: фраза about timeframe и budget не задаёт перечень; ❔ Полнота: Сроки и бюджет в тексте не заданы, полноту набора оценить нельзя; ❔ Осуществимость: Сроки и бюджет не указаны, осуществимость Priority 3 оценить нельзя; ❌ Проверяемость: Для Priority 3 нет перечня и даты, по которым проверяется состав выпуска.
- <a id="req-14"></a>**REQ-14 · строка 198 · страница 11 · 3.5 Gradebook**: снято критиком: [D-32](#d-32), см. [приложение Б](#appendix-b); ❌ Проверяемость: Вторая фраза описывает желание («may want»), а не проверяемое обязательное поведение.

### <a id="req-02"></a>REQ-02 · строка 158 · страница 8 · 3.1 Multiple File Transfer
> The system must be able to capture and manage files where appropriate.

Оценки: ✅ Необх. ❌ Однозн. ❔ Полн. ✅ Осущ. ❌ Пров. ✅ Непрот.
- ❌ Однозначность: Условие where appropriate не определено, граница применения неясна
- ❔ Полнота: Не ясно, что значит manage и какие страницы; нужен ответ автора

<a id="d-03"></a>**D-03 [CRITICAL] Проверяемость.** Формулировка не задаёт результат, который можно наблюдать и проверить. Цитата: `manage files where appropriate` (строка 158). Последствие: Нельзя написать тест и принять решение о выполнении требования.
- Критик слил сюда: [D-04](#d-04), их текст в [приложении Б](#appendix-b).
- Вопрос тестировщику: Какой наблюдаемый результат подтверждает выполнение: файл загружен и показан в списке страницы (да или нет)? См. [Q-09](#q-09).

Слито критиком: [D-04](#d-04) в [D-03](#d-03).

**Готовая формулировка:** The system must allow <actor role> to upload and manage files on <page types>.

### <a id="req-04"></a>REQ-04 · строка 165 · страница 9 · 3.2 Audio Recording
> The system must be able to capture and organize voice clips that can be used where appropriate.

Оценки: ✅ Необх. ❌ Однозн. ❔ Полн. ✅ Осущ. ❌ Пров. ✅ Непрот.
- ❌ Однозначность: Условие where appropriate не определено, пригодность клипа неясна
- ❔ Полнота: Не ясно, для каких страниц и сценариев используются клипы; нужен ответ автора

<a id="d-05"></a>**D-05 [CRITICAL] Проверяемость.** Формулировка не задаёт наблюдаемый результат захвата и организации клипов. Цитата: `capture and organize voice clips that can be used where appropriate` (строка 165). Последствие: Нельзя написать тест, подтверждающий выполнение требования.
- Критик слил сюда: [D-06](#d-06), их текст в [приложении Б](#appendix-b).
- Вопрос тестировщику: Что подтверждает успешный захват: клип сохранён и виден в портфолио актора (да или нет)? См. [Q-10](#q-10).

Слито критиком: [D-06](#d-06) в [D-05](#d-05).

**Готовая формулировка:** The system must be able to capture and organize voice clips that can be used on <page types>.

### <a id="req-05"></a>REQ-05 · 3.2.1 · строки 168-172 · страница 9 · 3.2 Audio Recording
```text
3.2.1 The system must allow actors to organize their voice clips into a portfolio.
Equal and finite drive space needs to be allotted to each actor in the role of professor or administrator to allow for the storing of voice clips recorded and submitted by all actors in the roles of students. Actors in the role of professor or system administrator should be allowed to partition this space for actors in the roles of students. This can be done one of two ways: 1) the actor can be allowed to preview the voice clip before it is archived and determine whether or not he or she would like that clip to be archived, or 2) a newly created voice clip can be automatically archived. The first option would allow the actor to throw out an audio clip that is deemed to be unsuitable or inappropriate for an assignment without having to take it out of an archive of voice clips. The actor should have the option to have the voice clip be archived after a preview has taken place. The second option would automatically archive a voice clip once submitted but would require that the actor interact with the archived file. Thus, if the actor chooses to delete the file, it would need to be deleted from the archive of voice clips.
Maintaining an archive of voice clips makes it possible for comparisons to be made between clips to determine whether an actor is improving his or her language skills over multiple courses.
The actor should be able to optionally attach one of his or her archived items to any page where uploads are permitted.
The term archive used above may also be referred to as a portfolio.
```

Оценки: ✅ Необх. ❌ Однозн. ❌ Полн. ✅ Осущ. ✅ Пров. ❌ Непрот.

<a id="d-07"></a>**D-07 [CRITICAL] Непротиворечивость.** Вторая опция описана как автоматическая архивация и одновременно как требующая действия актора с архивным файлом. Цитата: `would automatically archive a voice clip once submitted but would require that the actor interact` (строка 169). Последствие: Нельзя определить, архивируется ли клип без участия актора, поэтому разработка и тесты невозможны.
- Вопрос заказчику (бизнес): Архивируется ли клип автоматически после отправки, или архивация требует действия актора с файлом? См. [Q-02](#q-02).

<a id="d-08"></a>**D-08 [MAJOR] Однозначность.** Фраза не определяет, какой из двух способов архивации применяется в системе. Цитата: `This can be done one of two ways` (строка 169). Последствие: Нельзя выбрать модель архивации для реализации и тестирования.
- Вопрос заказчику (бизнес): Кто выбирает способ архивации голосового клипа: администратор системы или актор при каждой загрузке? См. [Q-02](#q-02).

<a id="d-09"></a>**D-09 [MAJOR] Полнота.** Не указан объём выделяемого пространства и порядок действий при его исчерпании. Цитата: `Equal and finite drive space needs to be allotted` (строка 169). Последствие: Нельзя реализовать квоту и проверить её границу.
- Вопрос заказчику (бизнес): Какой объём дискового пространства выделяется каждому профессору для клипов студентов: задать значение в мегабайтах?

**Готовая формулировка:** The system must allow actors to organize their voice clips into a portfolio, archiving each clip <archiving mode: after actor preview or automatically after submission>. Each actor in the role of professor or system administrator is allotted <N MB> of drive space for student voice clips.

### <a id="req-06"></a>REQ-06 · 3.2.2 · строки 173-174 · страница 9 · 3.2 Audio Recording
```text
3.2.2 The system must allow actors to download their voice clips in a flexible format.
Voice clips should be optionally downloadable in a format such as MPEG Audio (mp3) format, since it is widely supported across different web browsers and operating systems. Voice clips should be downloadable for archival purposes or for the purpose of presenting them to other actors.
```

Оценки: ✅ Необх. ❌ Однозн. ❌ Полн. ✅ Осущ. ❌ Пров. ✅ Непрот.
- ❌ Однозначность: Слово flexible не задаёт набор форматов, поэтому допускает разные трактовки
- ❌ Полнота: Формат mp3 приведён как пример, полного списка форматов нет

<a id="d-10"></a>**D-10 [CRITICAL] Проверяемость.** Формулировка не задаёт проверяемый результат, так как формат flexible нельзя сравнить с ожидаемым. Цитата: `download their voice clips in a flexible format` (строка 173); `in a format such as MPEG Audio (mp3) format` (строка 174). Последствие: Нельзя написать тест, подтверждающий выполнение требования.
- Критик слил сюда: [D-11](#d-11), [D-12](#d-12), их текст в [приложении Б](#appendix-b).
- Вопрос тестировщику: Какой формат тестировщик должен получить при скачивании клипа: задать конкретный формат? См. [Q-08](#q-08).

Слито критиком: [D-11](#d-11) в [D-10](#d-10), [D-12](#d-12) в [D-10](#d-10).

**Готовая формулировка:** The system must allow actors to download their voice clips in <list of supported audio formats>.

### <a id="req-07"></a>REQ-07 · 3.2.3 · строки 175-176 · страница 9 · 3.2 Audio Recording
```text
3.2.3 The system must store audio clips in a format conducive to speech.
Voice clips should be stored in a format optimized for speech since this feature is meant to catalog voice recordings. Recordings should only be converted to MPEG Audio (mp3) format when they are being downloaded; a separate viewer should be provided in a cross-platform language for listening to clips in Moodle.
```

Оценки: ✅ Необх. ❌ Уровень ❌ Однозн. ❌ Полн. ✅ Осущ. ❌ Пров. ✅ Непрот.
- ❌ Однозначность: Фраза conducive to speech не задаёт конкретный формат
- ❌ Полнота: Не заданы кодек, битрейт и другие параметры хранения

<a id="d-13"></a>**D-13 [CRITICAL] Проверяемость.** Без конкретного формата нельзя проверить, что хранение соответствует требованию: критерия успеха нет. Цитата: `The system must store audio clips in a format` (строка 175); `a format conducive to speech` (строка 175); `a format optimized for speech` (строка 176). Последствие: Тестировщик не может написать проверку формата хранения.
- Критик слил сюда: [D-14](#d-14), [D-15](#d-15), их текст в [приложении Б](#appendix-b).
- Вопрос архитектору: Какой формат хранения аудиоклипов задать: название кодека и контейнера? См. [Q-06](#q-06).

<a id="d-16"></a>**D-16 [MINOR] Уместность уровня.** Требование хранения задаёт проектное решение: отдельный просмотрщик на кроссплатформенном языке. Это требование к просмотру, а не к хранению. Цитата: `a separate viewer should be provided in a cross-platform language` (строка 176).
- Вопрос архитектору: Какой формат хранения аудиоклипов задать: конкретные кодек и контейнер (строка 175) или выбор архитектором? См. [Q-06](#q-06).

Слито критиком: [D-14](#d-14) в [D-13](#d-13), [D-15](#d-15) в [D-13](#d-13).

**Готовая формулировка:** The system must store audio clips in <audio codec and container name> with <bitrate, kbit/s>.

### <a id="req-08"></a>REQ-08 · 3.2.4 · строки 177-178 · страница 10 · 3.2 Audio Recording
```text
3.2.4 The system must allow actors to delete recorded clips.
Since voice clips should be stored in a portfolio for each actor during his or her existence in the course management system, he or she should be able to examine his or her portfolio to select and delete clips if he or she chooses to. This allows him or her to manage archived voice clips and to create a cohesive portfolio that actors in the role of professor can use to judge improvement over time.
```

Оценки: ✅ Необх. ❌ Однозн. ❌ Полн. ✅ Осущ. ✅ Пров. ✅ Непрот.

<a id="d-17"></a>**D-17 [MAJOR] Однозначность.** Требование говорит про любых актёров, а пояснение описывает удаление только из своего портфеля. Цитата: `The system must allow actors to delete recorded clips.` (строка 177). Последствие: Нельзя определить права доступа и написать тест на удаление чужих клипов.
- Вопрос заказчику (бизнес): Может ли актор удалять клипы только из своего портфеля или также из чужих портфелей?

<a id="d-18"></a>**D-18 [MAJOR] Полнота.** Не описано, что происходит с клипом, прикреплённым к странице, при удалении из портфеля. Цитата: `delete clips if he or she chooses to` (строка 178). Последствие: Нельзя реализовать удаление без правила для уже прикреплённых клипов.
- Вопрос заказчику (бизнес): Что происходит с клипом, прикреплённым к странице, при его удалении из портфеля: вложение удаляется или удаление запрещено? См. [Q-14](#q-14).

**Готовая формулировка:** The system must allow <actor roles> to delete recorded clips from <own portfolio or any portfolio>, and must <behavior for clips attached to a page>.

### <a id="req-09"></a>REQ-09 · строка 180 · страница 10 · 3.3 Web Feeds
> The system must be able to display web feeds, such as RSS 2.0 feeds, for all pages of the course management system where elements such as forum posts, assignment postings, announcements, wiki alterations and other blocks of information that an actor may view are added. Actors in the role of course administrators should have the ability to determine which of these components have feeds and to whom these feeds should pertain.

Оценки: ✅ Необх. ❌ Однозн. ❌ Полн. ❌ Атом. ✅ Осущ. ❌ Пров. ✅ Непрот.
- ❌ Однозначность: Открытый список блоков и слово such as не дают полного перечня
- ❌ Полнота: Не указано, для каких актёров предназначена лента

<a id="d-19"></a>**D-19 [CRITICAL] Проверяемость.** Без полного списка компонентов нельзя проверить, что ленты выведены для всех нужных страниц. Цитата: `for all pages of the course management system` (строка 180); `and other blocks of information that an actor may view` (строка 180). Последствие: Тестировщик не может определить набор проверяемых страниц и компонентов.
- Критик слил сюда: [D-20](#d-20), их текст в [приложении Б](#appendix-b).
- Вопрос аналитику: Для каких страниц курса должны выводиться ленты: все страницы или только страницы с перечисленными компонентами? См. [Q-01](#q-01).

<a id="d-22"></a>**D-22 [MINOR] Атомарность.** В одном требовании описаны вывод лент и право администратора курса настраивать их. Цитата: `Actors in the role of course administrators should have the ability` (строка 180).
- Вопрос заказчику (бизнес): Кто переключает веб-ленты страницы: только администратор курса (строка 180) или любой актор? См. [Q-12](#q-12).

Слито критиком: [D-20](#d-20) в [D-19](#d-19); снято критиком: [D-21](#d-21), см. [приложение Б](#appendix-b).

**Готовая формулировка:** The system must display web feeds in <feed format> for <complete list of components and pages>, and the course administrator must be able to set the audience of each feed to <feed audience roles>.

### <a id="req-10"></a>REQ-10 · 3.3.1 · строки 183-184 · страница 10 · 3.3 Web Feeds
```text
3.3.1 The system must allow web feeds to be turned on or off on a per-page basis.
Actors in the course administrator role may not feel the need to provide web feeds for every page in their course. During the creation and editing of a page, that actor should be able to toggle web feed availability.
```

Оценки: ✅ Необх. ✅ Однозн. ❌ Полн. ✅ Осущ. ✅ Пров. ✅ Непрот.

<a id="d-23"></a>**D-23 [MAJOR] Полнота.** В требовании не указано, какой актор переключает ленты: роль администратора курса есть только в пояснении. Цитата: `The system must allow web feeds to be turned on or off` (строка 183). Последствие: Нельзя задать права доступа и написать тест на переключение лент.
- Вопрос заказчику (бизнес): Кто переключает ленты страницы: только администратор курса или любой актор? См. [Q-12](#q-12).

**Готовая формулировка:** The system must allow <actor role> to turn web feeds on or off on a per-page basis.

### <a id="req-11"></a>REQ-11 · строка 186 · страница 10 · 3.4 Search
> The system must be able to use search functionality as a way to navigate Moodle pages instead of using hierarchical links.

Оценки: ✅ Необх. ❌ Однозн. ✅ Полн. ✅ Осущ. ❌ Пров. ❌ Непрот.
- ❌ Непротиворечивость: Требование говорит о замене ссылок, пояснение о сохранении иерархии

<a id="d-25"></a>**D-25 [MAJOR] Однозначность.** Фраза as a way to navigate не задаёт, какие страницы должны быть достижимы поиском. Цитата: `use search functionality as a way to navigate` (строка 186). Последствие: Нельзя определить набор страниц, который должен находиться через поиск.
- Вопрос заказчику (бизнес): Какие страницы должны быть достижимы через поиск: все страницы Moodle или только страницы курса?

<a id="d-26"></a>**D-26 [MAJOR] Проверяемость.** Не задан критерий успеха: сколько переходов допустимо и до каких страниц. Цитата: `must be able to use search functionality` (строка 186). Последствие: Тестировщик не может определить, выполнено ли требование.
- Вопрос тестировщику: Сколько переходов от входа до страницы через поиск допустимо: задать число (например, 2)?

Слито критиком: [D-24](#d-24) в [S-01](#s-01).

**Готовая формулировка:** The system must provide search functionality to reach <set of pages> that <replaces or supplements> hierarchical links.

### <a id="req-12"></a>REQ-12 · 3.4.1 · строки 189-194 · страница 10 · 3.4 Search
```text
3.4.1 An actor must be able to search through pages in a course.
Actors should be able to search for pages at the course level, since most actors will be searching for material in a given course. The search feature should be present in two ways.
First, it should be present in the form of a search box and a “Search” button on the top or bottom of every page. More information on this topic is given in sub-section 3.4.2 below.
Second, a single page should be dedicated specifically to the task of searching the course management system. In addition to the basic search field, this page should allow an actor to filter out certain results (such as forum posts or grades, etc.) and search specific sections (or components) of the course management system. Results should appear in categories (e.g.,
Assignments, Wiki Pages, Forum Posts, etc.) based on relevance. In this case, relevance is determined by results that having the highest number terms matching the search terms. When the actor clicks a search result link, they should be taken to the page corresponding to the search result.
In addition, the search page described above might allow for the possibility of searching the world wide web using a standard search engine such as Google.
```

Оценки: ✅ Необх. ❌ Однозн. ✅ Полн. ❌ Атом. ✅ Осущ. ❌ Пров. ✅ Непрот.

<a id="d-27"></a>**D-27 [MAJOR] Однозначность.** Слово etc делает список фильтруемых результатов открытым, неясно, какие типы можно отфильтровать. Цитата: `(such as forum posts or grades, etc.)` (строка 192). Последствие: Нельзя составить полный перечень фильтров и тестовых сценариев.
- Вопрос заказчику (бизнес): Какие типы результатов, помимо форумов и оценок, должны фильтроваться на странице поиска?

<a id="d-28"></a>**D-28 [MAJOR] Проверяемость.** Слово might делает поиск в интернете необязательным, и неясно, входит ли он в выпуск. Цитата: `might allow for the possibility of searching the world wide web` (строка 194). Последствие: Нельзя ни реализовать, ни проверить эту возможность, так как её наличие не определено.
- Вопрос заказчику (бизнес): Поиск в интернете через внешний поисковик входит в требование: да или нет?

<a id="d-29"></a>**D-29 [MINOR] Атомарность.** Требование описывает поле поиска на каждой странице, отдельную страницу поиска и возможный поиск в интернете. Цитата: `The search feature should be present in two ways.` (строка 190).
- Вопрос заказчику (бизнес): Где показывается поле поиска: на каждой странице после входа (строка 195) или на каждой странице, включая страницы до входа (строка 191)? См. [Q-05](#q-05).

**Готовая формулировка:** An actor must be able to search pages in a course. The system must display a search box and a Search button at <search box position> of every page after login. The search page must allow filtering results by <list of result types>. Web search via <search engine name> must be <included or excluded>.

### <a id="req-13"></a>REQ-13 · 3.4.2 · строки 195-196 · страница 11 · 3.4 Search
```text
3.4.2 The system must display a search box on every page after an actor has logged in.
Actors should be able to search from any page. If the actor is hierarchically outside of a particular course, each of his or her courses should be searched and results should be grouped by course. If the actor is hierarchically inside of a course, that course should be searched with an option to search all courses.
```

Оценки: ✅ Необх. ❌ Однозн. ❌ Полн. ✅ Осущ. ✅ Пров. ✅ Непрот.

<a id="d-30"></a>**D-30 [MAJOR] Однозначность.** Понятие «hierarchically outside of a particular course» не определено, поэтому неясно, какие страницы считаются вне курса. От этого зависит, какие курсы и как попадают в поиск. Цитата: `If the actor is hierarchically outside of a particular course` (строка 196). Последствие: Нельзя реализовать правило выбора области поиска для страниц вне курса без решения, что считать вне курса.
- Вопрос аналитику: Что считается нахождением вне курса: страницы без привязки к курсу или любые страницы, кроме страниц данного курса?

<a id="d-31"></a>**D-31 [MAJOR] Полнота.** Не описано, как пользователь включает поиск по всем курсам и как выглядит результат при выборе этого варианта. Цитата: `with an option to search all courses` (строка 196). Последствие: Нельзя спроектировать интерфейс этого варианта и проверить результат поиска.
- Вопрос аналитику: Как реализуется вариант поиска по всем курсам: отдельная кнопка или переключатель области поиска?

**Готовая формулировка:** The system must display a search box on every page after an actor has logged in. Actors must be able to search from any page. If the actor is outside a particular course, as defined by <definition of pages outside a course>, the system must search each of the actor's courses and group results by course. If the actor is inside a particular course, the system must search that course and provide <control for searching all courses>.

### <a id="req-15"></a>REQ-15 · 3.5.1 · строки 200-201 · страница 11 · 3.5 Gradebook
```text
3.5.1 A course administrator must be able to grade an assignment.
Course administrators should be able to post grades for an assignment based on the ratio of points earned to points possible. The course administrator should also be able to attach feedback in the form of text or an attachment (as described above). Time stamps should be attached to the last time the grade was modified so that actors may examine when particular grades were submitted and how an actor in the role of student has improved or lessened his performance in the course.
```

Оценки: ✅ Необх. ❌ Однозн. ❌ Полн. ✅ Осущ. ✅ Пров. ❌ Непрот.

<a id="d-33"></a>**D-33 [MAJOR] Однозначность.** Ссылка «as described above» указывает на описание вложений, которого в разделах выше нет, поэтому правила вложения к отзыву не определены. Цитата: `attach feedback in the form of text or an attachment (as described above)` (строка 201). Последствие: Нельзя определить допустимые вложения к отзыву без отсылки к несуществующему описанию.
- Вопрос аналитику: Задать правила вложения к отзыву в этом требовании или сослаться на конкретный раздел документа, где они описаны?

<a id="d-34"></a>**D-34 [MAJOR] Полнота.** Для вложения не указаны допустимые форматы и максимальный размер файла. Цитата: `attach feedback in the form of text or an attachment` (строка 201). Последствие: Нельзя реализовать загрузку вложения и проверить, какие файлы принимаются.
- Вопрос архитектору: Какой максимальный размер вложения к отзыву: задать значение в мегабайтах?

<a id="d-35"></a>**D-35 [MAJOR] Непротиворечивость.** Метка времени только для последнего изменения не показывает, как менялась оценка, хотя текст требует видеть, как студент улучшил или ухудшил результаты. Цитата: `Time stamps should be attached to the last time the grade was modified` (строка 201). Последствие: Нельзя проверить, что система сохраняет данные, нужные для анализа динамики оценок.
- Вопрос заказчику (бизнес): Хранить метку времени только для последнего изменения оценки или для каждого изменения? См. [Q-15](#q-15).

**Готовая формулировка:** A course administrator must be able to grade an assignment. Course administrators must be able to post grades for an assignment based on the ratio of points earned to points possible. The course administrator must be able to attach feedback in the form of text or an attachment of up to <maximum attachment size, MB>. Time stamps must be attached to each change of the grade so that actors may examine when particular grades were set or changed and how an actor in the role of student has improved or lessened his performance in the course.

### <a id="req-16"></a>REQ-16 · 3.5.2 · строки 202-203 · страница 11 · 3.5 Gradebook
```text
3.5.2 The system should display grade information to the appropriate actor.
The system should display grade information such as the grade for each assignment, averages, and overall grade to the actor to whom the grades belong. No other actor should be able to view another’s grades except an actor in the role of course administrator for the course to which the grades belong.
```

Оценки: ✅ Необх. ❌ Однозн. ✅ Полн. ✅ Осущ. ✅ Пров. ✅ Непрот.

<a id="d-36"></a>**D-36 [MAJOR] Однозначность.** «Averages» не определены: непонятно, среднее по всем заданиям курса или по другим записям, и какой период учитывается. Цитата: `such as the grade for each assignment, averages, and overall grade` (строка 203). Последствие: Нельзя реализовать расчёт среднего и проверить отображаемое значение.
- Вопрос заказчику (бизнес): Какие средние показывать студенту: среднее по всем заданиям курса или только средние баллы по каждому заданию?

**Готовая формулировка:** The system should display grade information to the appropriate actor. The system should display grade information such as the grade for each assignment, <average definition>, and overall grade to the actor to whom the grades belong. No other actor should be able to view another’s grades except an actor in the role of course administrator for the course to which the grades belong.

### <a id="req-17"></a>REQ-17 · 3.5.3 · строки 204-205 · страница 11 · 3.5 Gradebook
```text
3.5.3 The system should maintain a grade history.
The system should maintain a history of grades for a particular assignment if the course administrator changes them. This way, another actor can review the grade information if their score on an assignment has changed and they wish to dispute it. Course administrators can also track how they have changed a score over time using the timestamps associated with each change to the gradebook.
```

Оценки: ✅ Необх. ❌ Однозн. ❌ Полн. ✅ Осущ. ✅ Пров. ✅ Непрот.

<a id="d-37"></a>**D-37 [MAJOR] Однозначность.** «Another actor» не задаёт круг участников, которые могут просматривать историю оценок. Цитата: `another actor can review the grade information` (строка 205). Последствие: Нельзя задать права доступа к истории оценок и проверить их.
- Вопрос заказчику (бизнес): Кто может просматривать историю изменений оценки: только студент, которого она касается, или также курс-администратор?

<a id="d-38"></a>**D-38 [MAJOR] Полнота.** Не сказано, какие сведения сохраняются при каждом изменении оценки, поэтому содержимое истории не определено. Цитата: `maintain a history of grades for a particular assignment` (строка 205). Последствие: Нельзя спроектировать структуру записи истории и проверить её содержимое.
- Вопрос аналитику: Какие сведения хранятся по каждому изменению оценки: только новое значение или старое и новое значение с временем изменения?

**Готовая формулировка:** The system should maintain a history of grades for a particular assignment if the course administrator changes them, storing <list of recorded fields> for each change. This way, <actor role allowed to review the history> can review the grade information if their score on an assignment has changed and they wish to dispute it. Course administrators can also track how they have changed a score over time using the timestamps associated with each change to the gradebook.

### <a id="req-18"></a>REQ-18 · 3.6.1 · строки 209-210 · страница 12 · 3.6 Social Networking Applications
```text
3.6.1 The system must provide a wiki where actors can collaboratively create networks of documents.
A freely available wiki should provide a simple markup language that actors can use to style their input, as well as link to other pages in the wiki. More importantly, having the wiki inside Moodle reduces confusion and allows for the integration of notifications and logins.
```

Оценки: ✅ Необх. ❌ Однозн. ✅ Полн. ✅ Осущ. ✅ Пров. ✅ Непрот.

<a id="d-39"></a>**D-39 [MAJOR] Однозначность.** Слово «simple» не задаёт проверяемого критерия, а конкретный язык разметки в требовании не назван. Цитата: `should provide a simple markup language` (строка 210). Последствие: Нельзя выбрать язык разметки и проверить, что он соответствует требованию.
- Вопрос архитектору: Какой язык разметки должна поддерживать wiki: задать название конкретного языка?

**Готовая формулировка:** The system must provide a wiki where actors can collaboratively create networks of documents. A freely available wiki should provide <markup language name> that actors can use to style their input, as well as link to other pages in the wiki. More importantly, having the wiki inside Moodle reduces confusion and allows for the integration of notifications and logins.

### <a id="req-19"></a>REQ-19 · 3.6.2 · строки 211-212 · страница 12 · 3.6 Social Networking Applications
```text
3.6.2 The system must provide a blog engine.
A freely available blog engine should provide all modern blog functionality, such as tagging, drafting, and comments. These blogs should share authentication and notification with Moodle.
```

Оценки: ✅ Необх. ❌ Однозн. ❌ Полн. ❌ Атом. ✅ Осущ. ❌ Пров. ✅ Непрот.
- ❌ Проверяемость: Нет перечня функций, по которому можно принять блог

<a id="d-40"></a>**D-40 [MAJOR] Однозначность.** Набор функций блога задан как «все современные» без перечня, поэтому объём работ неясен. Цитата: `should provide all modern blog functionality` (строка 212). Последствие: Нельзя определить, какие функции реализовать и с чем сверять блог.
- Критик слил сюда: [D-42](#d-42), их текст в [приложении Б](#appendix-b).
- Вопрос заказчику (бизнес): Какой обязательный набор функций блога: теги, черновики и комментарии или другой список?

<a id="d-41"></a>**D-41 [MAJOR] Полнота.** Не сказано, что значит общий вход и уведомления: общая учётная запись или отдельная синхронизация. Цитата: `share authentication and notification with Moodle` (строка 212). Последствие: Нельзя спроектировать и проверить интеграцию блога с Moodle.
- Вопрос аналитику: Как блоги используют вход Moodle: общая учётная запись без повторного входа или отдельная учётная запись с синхронизацией?

<a id="d-43"></a>**D-43 [MINOR] Атомарность.** В одном требовании смешаны блог и интеграция входа и уведомлений с Moodle. Цитата: `share authentication and notification with Moodle` (строка 212).

Слито критиком: [D-42](#d-42) в [D-40](#d-40).

**Готовая формулировка:** The system must provide a blog engine that supports <list of required blog functions> and shares <authentication and notification mechanism> with Moodle.

### <a id="req-20"></a>REQ-20 · 3.7.1 · строки 216-218 · страница 12 · 3.7 Notifications
```text
3.7.1 The system must provide both e-mail and SMS notifications for pages.
For this requirement, page refers to any distinct page (e.g., an assignment, a wiki page, a forum post, etc.). When a page is created, the actor in the role of course administrator should be able to toggle whether notifications are turned on. By default, they should be turned on for announcements. If notifications are turned off, actors in the capacity of student should be able to subscribe to notifications.
Students should be able to select in their preferences whether notifications are sent to their mobile telephone (via SMS) or e-mail account. They should also be able to manage their notification subscriptions (for example, remove themselves from notifications).
```

Оценки: ✅ Необх. ❌ Однозн. ❌ Полн. ❌ Атом. ✅ Осущ. ✅ Пров. ✅ Непрот.

<a id="d-44"></a>**D-44 [MAJOR] Однозначность.** Понятие «distinct page» и открытый список с etc не задают, для каких страниц действуют уведомления. Цитата: `any distinct page (e.g., an assignment, a wiki page, a forum post, etc.)` (строка 217). Последствие: Нельзя определить, для каких элементов реализовать переключатель и подписку.
- Вопрос заказчику (бизнес): Для каких страниц действуют уведомления: все страницы курса или только задания, вики и сообщения форума? См. [Q-01](#q-01).

<a id="d-45"></a>**D-45 [MAJOR] Полнота.** Не описано, могут ли студенты подписаться, когда уведомления включены, и как они тогда получают их. Цитата: `If notifications are turned off, actors in the capacity of student should be able to subscribe to notifications.` (строка 217). Последствие: Нельзя реализовать правило подписки для страниц с включёнными уведомлениями.
- Вопрос заказчику (бизнес): Когда уведомления страницы включены, студенты получают их без подписки: да или нет?

<a id="d-46"></a>**D-46 [MAJOR] Однозначность.** Формулировка с «or» допускает выбор одного канала или обоих, это не задано. Цитата: `whether notifications are sent to their mobile telephone (via SMS) or e-mail account` (строка 218). Последствие: Нельзя определить, сколько каналов доставки студент настраивает.
- Вопрос заказчику (бизнес): Студент выбирает один канал уведомлений (SMS или e-mail) или оба канала одновременно?

<a id="d-47"></a>**D-47 [MINOR] Атомарность.** Требование объединяет каналы, переключатель, подписку и управление подписками. Цитата: `The system must provide both e-mail and SMS notifications for pages.` (строка 216).

**Готовая формулировка:** The system must provide e-mail and SMS notifications for <list of page types>. A course administrator can turn notifications on or off when a page is created, and announcements have notifications on by default. When notifications are off, students can subscribe; <subscription rule when notifications are on>. A student selects <one channel or both channels> in preferences and can manage subscriptions.

### <a id="req-21"></a>REQ-21 · 4.1.1 · строки 221-224 · страница 12 · 4.1 Usability
```text
4.1.1 As far as possible, the system should provide a simple, responsive interface.
Although any courseware solution may be composed of diverse systems, applications, and processes, the underlying architecture should be transparent to the administrators. The system should be configurable from a single source at a central administrative position, and should provide a central, easy-to-use interface that will allow administrators to configure the user interface and features in a way that reduces page clutter.
A system will be considered to meet this requirement if it has a single administrative interface rather than individual links for editing each page. Furthermore, this interface must allow administrators to easily change themes and other setting that affect page layout across the entire courseware system.
Priority: 3
```

Оценки: ✅ Необх. ❌ Однозн. ✅ Полн. ❌ Атом. ✅ Осущ. ❌ Пров. ✅ Непрот.

<a id="d-48"></a>**D-48 [MAJOR] Однозначность.** Слова «simple» и «responsive» оценочные, без порога или метрики. Цитата: `a simple, responsive interface` (строка 221). Последствие: Нельзя определить, какой интерфейс считать соответствующим требованию.
- Вопрос аналитику: Какое предельное время отклика интерфейса задать: значение в секундах, например 2?

<a id="d-49"></a>**D-49 [MAJOR] Проверяемость.** Оговорка делает выполнение необязательным, и нет критерия, по которому его можно принять. Цитата: `As far as possible, the system should provide` (строка 221). Последствие: Нельзя доказать выполнение требования при приёмке.
- Вопрос заказчику (бизнес): Требование обязательно для всех случаев (без оговорки «as far as possible») или допускает исключения?

<a id="d-50"></a>**D-50 [MINOR] Атомарность.** В требовании смешаны простота интерфейса, единая настройка и смена тем. Цитата: `The system should be configurable from a single source` (строка 222).

**Готовая формулировка:** The system should provide an interface with <measurable simplicity criterion, e.g. number of clicks> and <maximum response time, in seconds>, configurable from a single administrative interface.

### <a id="req-22"></a>REQ-22 · 4.2.1 · строки 226-229 · страница 13 · 4.2 Reliability
```text
4.2.1 The system must be backed up on a configurable schedule.
Back-up requirements will need to be determined, based on individual components of the system. The system should be backed up with a frequency that ensures system and course data is protected. Since assignments will be submitted via the system, it should be backed up on a nightly basis, with options for weekly, off-site backup when necessary.
The system must have the ability and capacity to restore back-up data within six hours so that the system is never offline for an inordinate period of time.
Priority: 2
```

Оценки: ✅ Необх. ❌ Однозн. ❌ Полн. ❌ Атом. ✅ Осущ. ❌ Пров. ✅ Непрот.
- ❌ Полнота: Периодичность и состав копирования не заданы, текст откладывает решение

<a id="d-51"></a>**D-51 [MAJOR] Однозначность.** Понятие «inordinate» не задано, поэтому допустимый простой не измерен. Цитата: `for an inordinate period of time` (строка 228). Последствие: Нельзя установить, при каком простое требование считается нарушенным.
- Вопрос заказчику (бизнес): Какое максимальное допустимое время простоя системы: задать значение в часах?

<a id="d-53"></a>**D-53 [MAJOR] Проверяемость.** Условие «when necessary» не задано, поэтому нельзя проверить, когда нужна внешняя копия. Цитата: `with options for weekly, off-site backup when necessary` (строка 227). Последствие: Нельзя проверить выполнение внешнего копирования в нужных случаях.
- Вопрос заказчику (бизнес): Какое условие запускает еженедельное внешнее копирование: задать правило, например объём данных в ГБ?

<a id="d-54"></a>**D-54 [MINOR] Атомарность.** В одном требовании смешаны расписание, внешняя копия и время восстановления. Цитата: `The system must be backed up on a configurable schedule.` (строка 226).

Слито критиком: [D-52](#d-52) в [S-05](#s-05).

**Готовая формулировка:** The system must be backed up on a configurable schedule with a frequency of <backup frequency, e.g. hours>, and weekly off-site backup when <condition for off-site backup>. The system must restore back-up data within six hours, and downtime must not exceed <maximum downtime, hours>.

### <a id="req-23"></a>REQ-23 · 4.2.2 · строки 230-233 · страница 13 · 4.2 Reliability
```text
4.2.2 The system should be available 24 hours a day, 7 days a week.
This statement provides a general sense of system availability. It is not intended to demand the system maintain reliability, or to require the system to be highly available. It should not exclude maintenance windows, or scheduled downtime. It is only intended to convey the expectation that our customers should have access to the system during off-hours as well as business hours.
99% up-time should be considered sufficient to meet this requirement.
Priority: 1
```

Оценки: ✅ Необх. ✅ Однозн. ✅ Полн. ✅ Осущ. ❌ Пров. ❌ Непрот.

<a id="d-55"></a>**D-55 [MAJOR] Непротиворечивость.** Требование 24x7 не допускает простоя, а 99% допускает около 87 часов простоя в год. Цитата: `99% up-time should be considered sufficient to meet this requirement.` (строка 232). Последствие: Нельзя понять, какой уровень доступности реализовывать и проверять.
- Критик понизил уровень с CRITICAL: Строка 232 признаёт 99 процентов достаточными, но 24x7 в строке 230 не согласовано с допустимым простоем, это не прямой конфликт.
- Вопрос заказчику (бизнес): Какой уровень доступности считать выполнением требования: 99% или полная доступность 24x7? См. [Q-11](#q-11).

<a id="d-56"></a>**D-56 [MAJOR] Проверяемость.** Не указано, за какой период измеряется 99% и входят ли плановые окна обслуживания в простой. Цитата: `99% up-time should be considered sufficient` (строка 232). Последствие: Нельзя измерить и принять выполнение требования доступности.
- Вопрос тестировщику: За какой период измеряется доступность: задать значение, например календарный месяц? См. [Q-11](#q-11).

**Готовая формулировка:** The system should be available 24 hours a day, 7 days a week, with availability of <target availability, %> measured over <measurement period>, and <handling of scheduled maintenance windows>.

### <a id="req-24"></a>REQ-24 · 4.3.1 · строки 235-237 · страница 13 · 4.3 Performance
```text
4.3.1 The system should support at least 1000 concurrent users.
This statement provides a general sense of reliability when the system is under load. It is important that a substantial number of actors be able to access the system at the same time, since a courseware system is important to the courses that employ it. The times when the system will be under the most stress are likely during midterm and finals weeks. Therefore, it must be able to handle at least 1,000 concurrent users.
Priority: 1
```

Оценки: ✅ Необх. ❌ Однозн. ✅ Полн. ❔ Осущ. ❌ Пров. ✅ Непрот.
- ❔ Осуществимость: Осуществимость зависит от архитектуры и ресурсов, в тексте не описаны

<a id="d-57"></a>**D-57 [MAJOR] Однозначность.** Не определено, что считается одновременным пользователем: активная сессия или одновременный запрос. Цитата: `at least 1000 concurrent users` (строка 235). Последствие: Нельзя задать сценарий нагрузки, который нужно выдержать.
- Вопрос аналитику: Что считается одновременным пользователем: активная сессия входа или одновременный запрос к системе?

<a id="d-58"></a>**D-58 [MAJOR] Проверяемость.** Нет критерия успешной работы при нагрузке, например времени ответа или доли ошибок. Цитата: `should support at least 1000 concurrent users` (строка 235). Последствие: Нельзя проверить, что система выдерживает заданную нагрузку.
- Вопрос тестировщику: Какое предельное время ответа задать при 1000 одновременных пользователях: значение в секундах?

**Готовая формулировка:** The system should support at least 1000 concurrent users, where a concurrent user is <definition of concurrent user>, with response time not exceeding <maximum response time, in seconds> under that load.

### <a id="req-25"></a>REQ-25 · 4.4.1 · строки 239-241 · страница 13 · 4.4 Supportability
```text
4.4.1 The system must be maintainable without substantial modification.
Due to limited staff in the Office of Information Services, it is important that the system be mostly self-sustaining. This will reduce the number of FTE hours spent maintaining the system and simplify maintenance tasks.
Priority: 3
```

Оценки: ✅ Необх. ❌ Однозн. ✅ Полн. ✅ Осущ. ❌ Пров. ✅ Непрот.

<a id="d-59"></a>**D-59 [CRITICAL] Проверяемость.** Формулировка mostly self-sustaining не задаёт измеримого критерия, а требование сопровождаемости без измерения не проверить. Цитата: `the system be mostly self-sustaining` (строка 240). Последствие: Нельзя провести тест или измерение, которое подтвердит выполнение требования.
- Вопрос заказчику (бизнес): Какой предельный объём трудозатрат на сопровождение допустим: задать число FTE-часов в месяц? См. [Q-03](#q-03).

<a id="d-60"></a>**D-60 [MAJOR] Однозначность.** Слово substantial допускает разные толкования объёма допустимой доработки. Оценка по тексту невозможна. Цитата: `without substantial modification` (строка 239). Последствие: Нельзя определить, какие изменения считаются допустимыми при сопровождении.
- Вопрос заказчику (бизнес): Какой предельный объём доработки системы допустим для сопровождения: задать долю изменённого кода, в процентах? См. [Q-03](#q-03).

**Готовая формулировка:** The system must be maintainable with no more than <N percent> of its code modified, and maintenance effort must not exceed <N FTE hours per month>.

### <a id="req-26"></a>REQ-26 · 4.6.1 · строки 244-246 · страница 14 · 4.6 On-line User Documentation and Help System Requirements
```text
4.6.1 Relevant, online documentation for users should be available on each page.
Users must have easy access to help while interacting with the system. Adequate user documentation should be provided to minimize the number of calls to the Help Desk about problems with the system. Modifications should be reported via the main page to inform actors of unexpected changes. This electronic documentation should be supplemented with phone and on-site support provided by the Office of Information Services.
Priority: 3
```

Оценки: ✅ Необх. ❌ Однозн. ✅ Полн. ✅ Осущ. ❌ Пров. ✅ Непрот.

<a id="d-61"></a>**D-61 [MAJOR] Однозначность.** Слово easy и прилагательное Relevant в строке 244 не определены, что оставляет их на усмотрение исполнителя. Цитата: `Users must have easy access to help` (строка 245). Последствие: Нельзя однозначно реализовать и принять доступ к справке и релевантность документации.
- Вопрос заказчику (бизнес): Что считать релевантной справкой на странице: задать перечень функций страницы, которые справка обязана описывать?

<a id="d-62"></a>**D-62 [MAJOR] Проверяемость.** Adequate не задано измеримо, поэтому выполнение нельзя подтвердить тестом или осмотром. Цитата: `Adequate user documentation should be provided` (строка 245). Последствие: Нельзя определить, достаточна ли документация, и принять эту часть требования.
- Вопрос заказчику (бизнес): Какое число обращений в Help Desk в месяц считать признаком достаточной документации: задать значение, например 20?

**Готовая формулировка:** Online user documentation must be available on each page and must describe <list of functions of that page>, reachable in <N clicks> from that page.

### <a id="req-27"></a>REQ-27 · 4.6.2 · строки 247-250 · страница 14 · 4.6 On-line User Documentation and Help System Requirements
```text
4.6.2 System administrators must have access to comprehensive, searchable documentation.
A comprehensive database of maintenance tasks and help files should be compiled to make the courseware system easier to maintain from an IT staff point-of-view. Search results should be displayed based on relevance.
This documentation must cover all procedures necessary for regular maintenance with links to additional information, all common errors, and links or documentation for advanced troubleshooting.
Priority: 3
```

Оценки: ✅ Необх. ❌ Уровень ❌ Однозн. ✅ Полн. ❌ Атом. ✅ Осущ. ❌ Пров. ✅ Непрот.

<a id="d-63"></a>**D-63 [CRITICAL] Проверяемость.** Фраза all procedures necessary и all common errors не перечисляет процедуры и ошибки, полноту покрытия проверить нельзя. Цитата: `This documentation must cover all procedures necessary` (строка 249). Последствие: Нельзя составить тест или осмотр, который подтвердит полноту документации.
- Вопрос аналитику: Какой перечень процедур регламентного обслуживания документация обязана покрывать: задать список процедур? См. [Q-04](#q-04).

<a id="d-64"></a>**D-64 [MAJOR] Однозначность.** Слово comprehensive не определяет объём документации, поэтому граница полноты неясна. Цитата: `comprehensive, searchable documentation` (строка 247). Последствие: Нельзя установить, какие разделы документация обязана содержать.
- Вопрос заказчику (бизнес): Какие разделы должна содержать документация администратора: задать перечень разделов? См. [Q-04](#q-04).

<a id="d-65"></a>**D-65 [MAJOR] Атомарность.** В требование о доступности документации добавлено отдельное правило ранжирования результатов поиска. Цитата: `Search results should be displayed based on relevance.` (строка 248). Последствие: Одно требование нельзя принять или проверить отдельно от ранжирования поиска.
- Вопрос аналитику: Нужно ли ранжирование результатов поиска по релевантности оформлять отдельным требованием: ответ да или нет?

<a id="d-66"></a>**D-66 [MINOR] Уместность уровня.** Требование задаёт способ реализации, компиляцию базы данных, вместо результата, нужного администратору. Цитата: `A comprehensive database of maintenance tasks` (строка 248).

**Готовая формулировка:** System administrators must have access to searchable documentation that covers <list of maintenance procedures>, <list of common errors>, and links to advanced troubleshooting for each of them.

## 4. Проверка набора требований целиком

### 4.1. Системная полнота

**Анализ.**

- Полнота набора (ISO 29148 п. 5.2.6; IEEE 830 п. 4.3.3): **нарушен**. Проверил маркеры незаполненности, пустые разделы и негативные сценарии. Найдены пометки TODO (строка 109) и to be determined (строка 227), пустые разделы 4.9 и 5, а также не описаны отказ уведомлений, одновременное изменение оценок и требования к безопасности и аудиту.
- Валидируемость (ISO 29148 п. 5.2.6): **нарушен**. Цель документа (строки 106 и 135) сформулирована без измеримых показателей и целевых значений. Критериев приёмки в наборе нет, поэтому покрытие требований критериями нельзя подтвердить.
- Прослеживаемость (IEEE 830 п. 4.3.8): **нарушен**. Пять утверждений в строках 158, 165, 180, 186 и 198 не имеют идентификатора, поэтому на них нельзя сослаться. Версия 1.0 на титуле расходится с историей изменений, это уже отмечено, а источник требований указан только общей ссылкой на брейнсторминг (строки 124 и 148).

#### <a id="s-04"></a>S-04 [MAJOR] Версия базовой системы Moodle не указана, в тексте стоит пометка TODO
- Пробел · Полнота набора · раздел «1.2 Scope».
- Цитата: `the existing courseware system candidate (version TODO: Version of` (строка 109).
- Что не так: В области действия вместо версии Moodle стоит незаполненная пометка TODO, поэтому базовая платформа доработок не определена. Последствие: Нельзя проверить, какие API и функции Moodle доступны и применимы к требованиям, и нельзя сверить набор с конкретной версией платформы.
- Вопрос заказчику (бизнес): Какая версия Moodle является базовой для доработки?
- Как исправить: Указать точную версию Moodle, на которую ведётся доработка, и убрать пометку TODO.

#### <a id="s-05"></a>S-05 [MAJOR] Состав резервного копирования по компонентам системы не определён
- Пробел · Полнота набора · [REQ-22](#req-22) · раздел «4.2 Reliability».
- Цитата: `Back-up requirements will need to be determined` (строка 227).
- Что не так: Требования к резервному копированию отложены: сказано, что они будут определены по отдельным компонентам, но перечня компонентов нет. Последствие: Нельзя проверить, что требование 4.2.1 покрывает все данные системы, и нельзя спланировать расписание и объём копий.
- Критик слил сюда: [D-52](#d-52), их текст в [приложении Б](#appendix-b).
- Вопрос архитектору: Какие компоненты системы входят в резервное копирование: все данные системы или только курсы и задания?
- Как исправить: Перечислить компоненты системы, которые входят в резервное копирование, и для каждого указать требуемую частоту.

#### <a id="s-06"></a>S-06 [MAJOR] Раздел стандартов пуст, перечень стандартов и протоколов не задан
- Пробел · Полнота набора · раздел «4.9 Applicable Standards».
- Цитата: `4.9 Applicable Standards` (строка 101).
- Что не так: В разделе 4.9 нет ни одного стандарта, протокола или формата, которым должна соответствовать система. Последствие: Нельзя проверить соответствие требований обязательным стандартам, например формату записи и каналам уведомлений.
- Вопрос архитектору: Какие стандарты и протоколы обязательны для системы, с указанием версий?
- Как исправить: Перечислить обязательные стандарты и протоколы с версиями или явно указать, что обязательных стандартов нет.

#### <a id="s-07"></a>S-07 [MAJOR] Не описано, что происходит при сбое отправки уведомлений
- Пробел · Полнота набора · [REQ-20](#req-20) · раздел «3.7 Notifications».
- Цитата: `The system must provide both e-mail and SMS notifications for pages.` (строка 216).
- Что не так: Для отправки e-mail и SMS не описано поведение при недоступности почтового сервера или SMS-шлюза: повтор, журналирование или отказ. Последствие: Нельзя проверить поведение системы при отказе внешнего сервиса, и разработчик не знает, терять ли уведомление.
- Вопрос аналитику: Сколько раз повторять отправку уведомления, если SMS-шлюз или почтовый сервер недоступен: задать число попыток, например 3?
- Как исправить: Добавить сценарий отказа канала уведомлений с числом повторов и поведением после исчерпания попыток.

#### <a id="s-08"></a>S-08 [MAJOR] Не описано одновременное изменение одной оценки двумя администраторами
- Пробел · Полнота набора · [REQ-15](#req-15), [REQ-17](#req-17) · раздел «3.5 Gradebook».
- Цитата: `A course administrator must be able to grade an assignment.` (строка 200).
- Что не так: Для параллельных запросов на изменение одной и той же оценки не задано правило, какое значение сохраняется и что видит второй администратор. Последствие: Нельзя проверить целостность истории оценок (3.5.3) при одновременных изменениях и нельзя написать тест на конкурентный доступ.
- Вопрос заказчику (бизнес): Что происходит, если два администратора курса сохраняют оценку за одно задание одновременно: сохраняется последнее значение или второе сохранение отклоняется?
- Как исправить: Описать правило конкурентного изменения оценки и отображение конфликта для второго администратора.

#### <a id="s-09"></a>S-09 [MAJOR] Нет нефункциональных требований к безопасности, защите данных и аудиту
- Пробел · Полнота набора · раздел «4. General System Functional Requirements».
- Цитата: `4. General System Functional Requirements` (строка 84).
- Что не так: В разделах 4.x нет требований к аутентификации, разграничению доступа на уровне системы, журналу действий и защите хранимых данных, кроме отдельной фразы о видимости оценок. Последствие: Нельзя проверить соответствие системы требованиям безопасности и аудита, и нельзя определить, что фиксируется в журнале при изменении данных.
- Вопрос специалисту по безопасности: Должна ли система вести журнал входов в систему и изменений данных с указанием пользователя: да или нет?
- Как исправить: Добавить раздел нефункциональных требований по безопасности, правам доступа и журналированию с перечнем фиксируемых действий.

#### <a id="s-13"></a>S-13 [MAJOR] Утверждения раздела 3 без идентификаторов нельзя адресовать
- Пробел · Прослеживаемость · [REQ-02](#req-02), [REQ-04](#req-04), [REQ-09](#req-09), [REQ-11](#req-11), [REQ-14](#req-14) · раздел «3. Specific Requirements».
- Цитата: `The system must be able to capture and manage files where appropriate.` (строка 158).
- Что не так: Пять утверждений, записанных как «The system must» или «Администратор курса публикует», не имеют номера, при этом часть из них оформлена как самостоятельное требование. Последствие: На эти утверждения нельзя сослаться из проекта, кода и тестов, и их нельзя связать с критериями приёмки.
- Вопрос аналитику: Строка 158 является самостоятельным требованием или вводным описанием раздела 3.1?
- Как исправить: Присвоить каждому самостоятельному требованию уникальный идентификатор или явно отнести утверждение к вводному описанию раздела.

#### <a id="s-14"></a>S-14 [MAJOR] Цель набора не измерима, критерии приёмки не заданы
- Пробел · Валидируемость · раздел «1.1 Purpose».
- Цитата: `The purpose of this document is to capture, in natural language and at a functional level` (строка 106).
- Что не так: Цель описана как фиксация требований, а не как результат, который можно измерить. Критериев приёмки, по которым проверяется достижение цели, в наборе нет. Последствие: Нельзя показать, что выполнение набора приведёт к заявленной цели, и нельзя решить, что набор принят.
- Вопрос заказчику (бизнес): Какой измеримый показатель и какое целевое значение подтверждают достижение цели набора?
- Как исправить: Задать измеримую цель набора с показателями и целевыми значениями и связать с ней критерии приёмки требований.

### 4.2. Взаимная непротиворечивость

**Анализ.**

- Согласованность (ISO 29148 п. 5.2.6; IEEE 830 п. 4.3.4): **нарушен**. Сверены термины и правила, которые повторяются в разделах 3 и 4. Найдено прямое противоречие в разделе поиска (поиск вместо иерархических ссылок и поиск в дополнение к ним), расхождение в определении термина «страница» между разделами 3.3 и 3.4 и разнобой в названиях ролей при назначении квоты. Версия документа на титульном листе не совпадает с последней записью истории изменений.
- Понятность (ISO 29148 п. 5.2.6): **частично**. Функциональные требования описаны достаточно подробно, но разделы 4.5, 4.7 (кроме заголовков подразделов), 4.8 и 4.9 не содержат текста. Из набора не видно, с какими внешними и смежными системами связана курсовая система и какими интерфейсами обмениваться.

#### <a id="s-01"></a>S-01 [CRITICAL] Поиск одновременно заменяет и дополняет иерархические ссылки навигации
- Противоречие · Согласованность · [REQ-11](#req-11), [REQ-12](#req-12) · раздел «3.4 Search».
- Цитаты: `The system must be able to use search functionality as a way to navigate Moodle pages instead of using hierarchical links.` (строка 186); `A search utility enables actors to find what they are looking for quickly in addition to having a hierarchical approach to finding functions of the course management system.` (строка 187).
- Что не так: В строке 186 поиск назван способом навигации вместо иерархических ссылок. В строке 187 поиск назван дополнением к иерархическому подходу, который сохраняется. Последствие: Нельзя определить, нужно ли сохранять иерархическое меню навигации по страницам курса и каким должен быть основной путь поиска по страницам.
- Критик слил сюда: [D-24](#d-24), их текст в [приложении Б](#appendix-b).
- Вопрос заказчику (бизнес): Поиск заменяет иерархические ссылки навигации или только дополняет их: что верно? См. [Q-07](#q-07).
- Как исправить: Привести строки 186 и 187 к одному утверждению о роли поиска и иерархических ссылок и убрать второе.

#### <a id="s-02"></a>S-02 [CRITICAL] Термин «страница» определён в разных разделах как блок и как отдельная страница
- Противоречие · Согласованность · [REQ-10](#req-10), [REQ-20](#req-20) · раздел «3.3 Web Feeds».
- Цитаты: `For this requirement, page refers to any distinct block (e.g., assignments, wikis, forum threads, etc.).` (строка 181); `For this requirement, page refers to any distinct page, such as an assignment, a wiki page, or a forum post.` (строка 187).
- Что не так: В разделе 3.3 под страницей понимается отдельный блок (например, задания или форумные темы). В разделе 3.4 и в разделе 3.7 под страницей понимается отдельная страница (например, задание, вики-страница, сообщение форума). Последствие: Нельзя определить, к чему относится включение и выключение веб-лент по страницам и к чему относятся уведомления по страницам, то есть какие объекты получают эти настройки.
- Вопрос заказчику (бизнес): Что считается страницей для включения веб-лент и уведомлений: отдельный блок информации или отдельная страница целиком? См. [Q-01](#q-01).
- Как исправить: Задать одно определение термина «страница» в разделе 1.3 и использовать его во всех требованиях, где он встречается.

#### <a id="s-10"></a>S-10 [MAJOR] Не описаны внешние системы и интерфейсы, с которыми связана курсовая система
- Пробел · Понятность · раздел «4.7 Interfaces».
- Цитаты: `4.7.4 Communications Interfaces` (строка 99); `4.8 Licensing Requirements` (строка 100).
- Что не так: Раздел 4.7 содержит только заголовки подразделов (пользовательские, аппаратные, программные и коммуникационные интерфейсы), без текста. Разделы 4.5, 4.8 и 4.9 тоже пусты. Требование 3.7.1 и раздел 3.6 упоминают внешние сервисы, но их границы и способ связи не описаны. Последствие: Нельзя определить, какие внешние системы должны получать данные от курсовой системы или передавать их ей и в каком виде, поэтому нельзя проверить, что интеграции покрыты требованиями.
- Вопрос архитектору: Должен ли раздел 4.7 Interfaces описывать обмен данными с внешними системами (например, с системой учёта студентов): да или нет?
- Как исправить: Заполнить раздел 4.7 перечнем внешних и смежных систем с описанием обмена данными или явно отметить, что внешних интеграций нет.

#### <a id="s-11"></a>S-11 [MAJOR] Роль, которой назначается квота дискового пространства, названа по-разному
- Прочее · Согласованность · [REQ-03](#req-03), [REQ-05](#req-05), [REQ-08](#req-08) · раздел «3.2 Audio Recording».
- Цитаты: `Actors in the capacity of course administrator or professor should be able to enable multiple file uploads on a page of his or her choosing.` (строка 163); `Equal and finite drive space needs to be allotted to each actor in the role of professor or administrator to allow for the storing of voice clips recorded and submitted by all actors in the roles of students.` (строка 169).
- Что не так: В разделе 3.1.1 роли названы как «course administrator or professor». В строке 169 та же группа названа «professor or administrator», а в следующей фразе той же строки «professor or system administrator». Из раздела 1.3.2 следует, что курсовой администратор это профессор или системный администратор, но «administrator» без уточнения может означать любую из двух ролей. Последствие: Нельзя определить, кто получает квоту дискового пространства для голосовых клипов и кто может выставлять её студентам.
- Вопрос заказчику (бизнес): Кому выделяется квота дискового пространства для голосовых клипов: профессору, курсовому администратору или системному администратору? См. [Q-13](#q-13).
- Как исправить: Использовать один термин роли из раздела 1.3 во всех требованиях раздела 3.2 и указать, кому выделяется квота.

#### <a id="s-15"></a>S-15 [MINOR] Версия документа на титульном листе не совпадает с историей изменений
- Прочее · Согласованность.
- Цитаты: `Version 1.0` (строка 18); `| | | 11/2/2007 | | | 1.4 | | | | | | | |` (строка 38).
- Что не так: На титульном листе указана версия 1.0, а в истории изменений последняя запись имеет версию 1.4.
- Как исправить: Указать на титульном листе версию, соответствующую последней записи истории изменений.

### 4.3. Осуществимость и стандарты

**Анализ.**

- Осуществимость набора (ISO 29148 п. 5.2.6): **частично**. Документ ссылается на RSS 2.0 (строка 180), формат MPEG Audio mp3 (строки 174 и 176) и существующие API Moodle (строка 112). Эти ссылки между собой не расходятся, но раздел 4.9 Applicable Standards пуст, а срок и бюджет релиза названы без значений, поэтому осуществимость в заданных ограничениях проверить нельзя.
- Ранжированность (IEEE 830 п. 4.3.5): **частично**. Приоритеты заданы для групп разделов (строки 161, 167, 182, 199, 215, 224, 229, 233, 237, 241, 246, 250), а не для каждого требования отдельно. Стабильность не указана ни для одного требования, при этом документ сам называет себя рабочим и подлежащим изменению (строка 127).
- Модифицируемость (IEEE 830 п. 4.3.7): **частично**. Перекрёстная ссылка на 3.4.2 в строке 191 есть, но поиск с полем описан в 3.4.1 и 3.4.2 с разным условием показа. Ссылка «as described above» в строке 201 не указывает на конкретный пункт, а часть требований записана общими фразами без отдельного пункта.

#### <a id="s-03"></a>S-03 [CRITICAL] Поле поиска описано в 3.4.1 и 3.4.2 с разным условием показа
- Противоречие · Модифицируемость · [REQ-12](#req-12), [REQ-13](#req-13) · раздел «3.4 Search».
- Цитаты: `First, it should be present in the form of a search box and a “Search” button on the top or bottom of every page.` (строка 191); `The system must display a search box on every page after an actor has logged in.` (строка 195).
- Что не так: В 3.4.1 поле поиска показывается на каждой странице без условия входа, а в 3.4.2 только после входа. Одно и то же поле описано дважды. Последствие: Нельзя определить, видит ли неавторизованный пользователь поле поиска, и нельзя написать тест на показ поля до входа.
- Вопрос заказчику (бизнес): Какое из двух мест верно: поле поиска на каждой странице (3.4.1) или только после входа (3.4.2)? См. [Q-05](#q-05).
- Как исправить: Оставить одно описание поля поиска с указанием условия показа и на него ссылаться из другого пункта.

#### <a id="s-12"></a>S-12 [MAJOR] Срок и бюджет первого релиза названы без значений
- Пробел · Осуществимость набора · [REQ-01](#req-01) · раздел «4.5 Design Constraints».
- Цитата: `along with such Priority 3 requirements as can be developed within the project timeframe and budget constraints.` (строка 156).
- Что не так: Ограничения по сроку и бюджету упомянуты, но их значения не заданы, поэтому нельзя понять, какие требования приоритета 3 реально войдут в релиз. Последствие: Нельзя оценить осуществимость набора в заданных ограничениях и отобрать требования для первого релиза.
- Критик слил сюда: [D-01](#d-01), [D-02](#d-02), их текст в [приложении Б](#appendix-b).
- Вопрос заказчику (бизнес): Какой срок первого релиза задать, в месяцах?
- Как исправить: Указать срок первого релиза и бюджет в единицах измерения и связать их с перечнем требований приоритета 3.

<a id="summary"></a>
## 5. Сводка

| Показатель | Значение |
| :--- | :---: |
| Требований всего | 27 |
| без дефектов | 3 |
| с дефектами | 24 |
| Замечаний всего | 67 |
| в отдельных требованиях | 52 |
| по набору | 15 |
| CRITICAL (критичный) | 11 |
| MAJOR (существенный) | 47 |
| MINOR (незначительный) | 9 |
| Вопросов автору | 15 |

### Блокеры

**Противоречия**

1. [S-01](#s-01) · [REQ-11](#req-11), [REQ-12](#req-12) · Поиск одновременно заменяет и дополняет иерархические ссылки навигации
2. [S-02](#s-02) · [REQ-10](#req-10), [REQ-20](#req-20) · Термин «страница» определён в разных разделах как блок и как отдельная страница
3. [S-03](#s-03) · [REQ-12](#req-12), [REQ-13](#req-13) · Поле поиска описано в 3.4.1 и 3.4.2 с разным условием показа
4. [D-07](#d-07) · [REQ-05](#req-05) · Вторая опция описана как автоматическая архивация и одновременно как требующая действия актора с архивным файлом.

**Непроверяемые и неоднозначные формулировки**

5. [D-03](#d-03) · [REQ-02](#req-02) · Формулировка не задаёт результат, который можно наблюдать и проверить.
6. [D-05](#d-05) · [REQ-04](#req-04) · Формулировка не задаёт наблюдаемый результат захвата и организации клипов.
7. [D-10](#d-10) · [REQ-06](#req-06) · Формулировка не задаёт проверяемый результат, так как формат flexible нельзя сравнить с ожидаемым.
8. [D-13](#d-13) · [REQ-07](#req-07) · Без конкретного формата нельзя проверить, что хранение соответствует требованию: критерия успеха нет.
9. [D-19](#d-19) · [REQ-09](#req-09) · Без полного списка компонентов нельзя проверить, что ленты выведены для всех нужных страниц.
10. [D-59](#d-59) · [REQ-25](#req-25) · Формулировка mostly self-sustaining не задаёт измеримого критерия, а требование сопровождаемости без измерения не проверить.
11. [D-63](#d-63) · [REQ-27](#req-27) · Фраза all procedures necessary и all common errors не перечисляет процедуры и ошибки, полноту покрытия проверить нельзя.

## 6. Вердикт

**Не рекомендуется начинать.**

Правило. «Не рекомендуется начинать», если есть хотя бы одно замечание CRITICAL, которое не снято критиком и не ушло в карантин из-за ненайденной цитаты. «Условно допускается», если CRITICAL нет, но есть MAJOR. «Допускается», если есть только MINOR или замечаний нет. Готовность к тестированию считается отдельно: «Нет», если есть CRITICAL по проверяемости, однозначности, полноте, согласованности или валидируемости; «Да, с оговорками», если есть другие CRITICAL или MAJOR; иначе «Да». Если отчёт неполный, а CRITICAL не найден, решение «Не вынесен», готовность «Не определена».

Решение по документу: не рекомендуется начинать. Одиннадцать CRITICAL-замечаний делятся на три группы. Первая группа, D-03, D-05, D-10, D-13, D-19, D-59 и D-63, это формулировки без наблюдаемого результата, формата или перечня, по которым нельзя написать тест. Вторая группа, S-01, S-02 и S-03, это противоречия в навигации, определении страницы и месте поля поиска, так что одно и то же требование читается двумя способами. Третья группа, D-07 и D-55, касается архивации клипов и доступности, где документ описывает два варианта поведения. Пока эти места не решены, разработка и приёмочные тесты опираются на догадки.

Что исправить в первую очередь:

1. Выбрать один вариант по каждому противоречию с автором ТЗ и переписать пункты 3.4, 3.2.1 и 4.2.2 без альтернатив. ([S-01](#s-01), [S-03](#s-03), [D-07](#d-07), [D-55](#d-55))
2. Определить термин «страница» один раз в разделе 1.3 и использовать его во всех требованиях лент и уведомлений. ([S-02](#s-02), [D-19](#d-19), [D-44](#d-44), [D-22](#d-22))
3. Переписать требования 3.1 3.2 и 4.6 с наблюдаемым результатом, конкретным форматом и без слов where appropriate, flexible, adequate. ([D-03](#d-03), [D-05](#d-05), [D-10](#d-10), [D-13](#d-13), [D-16](#d-16), [D-62](#d-62))
4. Заменить оценочные слова в 4.4.1 и 4.6.2 числовыми порогами и явным перечнем процедур и разделов документации. ([D-59](#d-59), [D-60](#d-60), [D-63](#d-63), [D-64](#d-64), [D-66](#d-66))
5. Присвоить идентификаторы каждому требованию раздела 3, заполнить версию Moodle вместо TODO и сверить версию документа с историей. ([S-13](#s-13), [S-15](#s-15), [S-04](#s-04))
6. Заполнить пустые разделы 4.7, 4.9 и состав резервного копирования, добавить требования к безопасности и журналированию. ([S-06](#s-06), [S-10](#s-10), [S-05](#s-05), [S-09](#s-09))
7. Описать поведение при сбое уведомлений, одновременном сохранении оценки и удалении клипа с вложением. ([S-07](#s-07), [S-08](#s-08), [D-18](#d-18), [D-45](#d-45))

<a id="questions"></a>
## 7. Вопросы к автору ТЗ

### Вопросы заказчику (бизнес)

#### <a id="q-01"></a>Q-01 · заказчику (бизнес) · блокирует разработку
**Что считается страницей для лент и уведомлений: отдельный блок информации (строка 181) или страница целиком (строка 217)?**
- Сейчас в документе: `For this requirement, page refers to any distinct block (e.g., assignments, wikis, forum threads, etc.).` (строка 181); `For this requirement, page refers to any distinct page, such as an assignment, a wiki page, or a forum post.` (строка 187); `for all pages of the course management system` (строка 180).
- Суть: Термин определён как блок в 3.3 и как страница в 3.7
- Варианты:
  1. Отдельный блок, например задание или сообщение форума. Последствие: Определения в 3.3, 3.7 и 3.4 приводятся к блоку
  2. Страница целиком, например страница задания или курса. Последствие: Определения в 3.3, 3.7 и 3.4 переписываются под страницу целиком
- Без ответа нельзя: Нельзя реализовать включение лент и уведомлений по страницам
- Закрывает замечания: [S-02](#s-02), [D-19](#d-19), [D-44](#d-44).

#### <a id="q-02"></a>Q-02 · заказчику (бизнес) · блокирует разработку
**Как архивируется голосовой клип: после предпросмотра по решению актора или автоматически сразу после отправки?**
- Сейчас в документе: `would automatically archive a voice clip once submitted but would require that the actor interact` (строка 169); `This can be done one of two ways` (строка 169).
- Суть: 3.2.1 описывает оба способа, второй требует действия актора с архивом
- Варианты:
  1. После предпросмотра, актор решает об архивации. Последствие: Вариант автоархивации удаляется из 3.2.1
  2. Автоматически после отправки, удаление через архив. Последствие: Вариант предпросмотра удаляется из 3.2.1
- Без ответа нельзя: Нельзя реализовать архивацию клипа и тесты её состояний
- Закрывает замечания: [D-07](#d-07), [D-08](#d-08).

#### <a id="q-03"></a>Q-03 · заказчику (бизнес) · блокирует разработку
**Каким показателем измеряется сопровождаемость по 4.4.1: часами FTE в месяц или долей изменённого кода в процентах?**
- Сейчас в документе: `the system be mostly self-sustaining` (строка 240); `without substantial modification` (строка 239).
- Суть: Строки 239 и 240 говорят о substantial и mostly self-sustaining без числа
- Варианты:
  1. Задать FTE-часов в месяц, например 40. Последствие: 4.4.1 получает числовой лимит трудозатрат на сопровождение
  2. Задать долю изменённого кода, в процентах. Последствие: 4.4.1 получает лимит доли доработки, например 10
- Без ответа нельзя: Нельзя оценить и проверить сопровождаемость системы
- Закрывает замечания: [D-59](#d-59), [D-60](#d-60).

#### <a id="q-05"></a>Q-05 · заказчику (бизнес) · блокирует разработку
**Где показывается поле поиска: на каждой странице после входа (строка 195) или на каждой странице, включая страницы до входа (строка 191)?**
- Сейчас в документе: `First, it should be present in the form of a search box and a “Search” button on the top or bottom of every page.` (строка 191); `The system must display a search box on every page after an actor has logged in.` (строка 195); `The search feature should be present in two ways.` (строка 190).
- Суть: 3.4.1 задаёт поле на каждой странице, 3.4.2 только после входа
- Варианты:
  1. На каждой странице только после входа. Последствие: Строка 191 переписывается под условие входа в систему
  2. На каждой странице, в том числе до входа. Последствие: Требование 3.4.2 и строка 195 переписываются под все страницы
- Рекомендуем: вариант 1, потому что заголовок 3.4.2 и строка 195 задают показ только после входа.
- Без ответа нельзя: Нельзя реализовать вывод поля поиска на страницах до входа
- Закрывает замечания: [S-03](#s-03), [D-29](#d-29).

#### <a id="q-07"></a>Q-07 · заказчику (бизнес) · блокирует разработку
**Поиск заменяет иерархические ссылки навигации или только дополняет их: что верно?**
- Сейчас в документе: `The system must be able to use search functionality as a way to navigate Moodle pages instead of using hierarchical links.` (строка 186); `A search utility enables actors to find what they are looking for quickly in addition to having a hierarchical approach to finding functions of the course management system.` (строка 187).
- Без ответа нельзя: Нельзя определить, нужно ли сохранять иерархическое меню навигации по страницам курса и каким должен быть основной путь поиска по страницам.
- Закрывает замечания: [S-01](#s-01).

#### <a id="q-11"></a>Q-11 · заказчику (бизнес) · нужен до начала спринта
**Какой уровень доступности считать выполнением 4.2.2: 99% аптайма (строка 232) или полная доступность 24x7 без простоя (строка 230)?**
- Сейчас в документе: `99% up-time should be considered sufficient to meet this requirement.` (строка 232).
- Суть: 24x7 не допускает простоя, а 99% допускает около 87 часов в год
- Варианты:
  1. 99% аптайма, плановые работы не входят в простой. Последствие: 4.2.2 получает процент и правило окон обслуживания
  2. Полная доступность 24x7 без простоя. Последствие: 4.2.2 переписывается, окна обслуживания не допускаются
- Без ответа нельзя: Нельзя оценить и протестировать доступность системы
- Закрывает замечания: [D-55](#d-55), [D-56](#d-56).

#### <a id="q-12"></a>Q-12 · заказчику (бизнес) · нужен до начала спринта
**Кто переключает веб-ленты страницы: только администратор курса (строка 180) или любой актор?**
- Сейчас в документе: `The system must allow web feeds to be turned on or off` (строка 183); `Actors in the role of course administrators should have the ability` (строка 180).
- Суть: Роль администратора курса упомянута только в пояснении
- Варианты:
  1. Только администратор курса. Последствие: 3.3 и 3.3.1 согласуются с пояснением строки 180
  2. Любой актор, создавший страницу. Последствие: Меняется право переключения лент в 3.3 и 3.3.1
- Рекомендуем: вариант 1, потому что строки 180 и 184 называют администратора курса.
- Без ответа нельзя: Нельзя задать права на переключение лент
- Закрывает замечания: [D-23](#d-23), [D-22](#d-22).

#### <a id="q-13"></a>Q-13 · заказчику (бизнес) · нужен до начала спринта
**Кому выделяется квота дискового пространства для клипов: профессору, курсовому администратору или системному администратору?**
- Сейчас в документе: `Actors in the capacity of course administrator or professor should be able to enable multiple file uploads on a page of his or her choosing.` (строка 163); `Equal and finite drive space needs to be allotted to each actor in the role of professor or administrator to allow for the storing of voice clips recorded and submitted by all actors in the roles of students.` (строка 169).
- Суть: Строка 169 называет professor и administrator, строка 163 course administrator
- Варианты:
  1. Профессору. Последствие: Квота назначается роли профессора в 3.2.1
  2. Курсовому администратору. Последствие: Квота назначается роли курсового администратора в 3.2.1
  3. Системному администратору. Последствие: Квота назначается системной роли, профессор её не настраивает
- Без ответа нельзя: Нельзя реализовать распределение квоты между ролями
- Закрывает замечания: [S-11](#s-11).

#### <a id="q-14"></a>Q-14 · заказчику (бизнес) · нужен до начала спринта
**Что происходит с клипом, прикреплённым к странице, при его удалении из портфеля (строка 178)?**
- Сейчас в документе: `delete clips if he or she chooses to` (строка 178).
- Суть: 3.2.4 разрешает удаление, про прикреплённые клипы не сказано
- Варианты:
  1. Клип удаляется и со страницы, вложение пропадает. Последствие: Страница теряет вложение, нужно уведомление актора
  2. Удаление запрещено, пока клип прикреплён. Последствие: Нужна проверка вложений перед удалением клипа
  3. Клип остаётся на странице как копия. Последствие: Нужно хранить копию, квота портфеля растёт
- Без ответа нельзя: Нельзя реализовать удаление клипа, если он прикреплён к странице
- Закрывает замечания: [D-18](#d-18).

#### <a id="q-15"></a>Q-15 · заказчику (бизнес) · нужен до начала спринта
**Хранить метку времени только для последнего изменения оценки (строка 201) или для каждого изменения, чтобы видеть историю?**
- Сейчас в документе: `Time stamps should be attached to the last time the grade was modified` (строка 201).
- Суть: Метка времени привязана только к последнему изменению
- Варианты:
  1. Для каждого изменения, с историей. Последствие: 3.5.3 получает хранение всех изменений с временем
  2. Только для последнего изменения. Последствие: 3.5.3 переписывается, история изменений не ведётся
- Рекомендуем: вариант 1, потому что строка 205 требует видеть, как менялась оценка студента.
- Без ответа нельзя: Нельзя реализовать историю изменений оценок
- Закрывает замечания: [D-35](#d-35).

### Вопросы аналитику

#### <a id="q-04"></a>Q-04 · аналитику · блокирует разработку
**Какие процедуры регламентного обслуживания и ошибки обязана покрывать документация администратора: задать явный список?**
- Сейчас в документе: `This documentation must cover all procedures necessary` (строка 249); `comprehensive, searchable documentation` (строка 247).
- Суть: Строка 249 «all procedures necessary» и «all common errors» без перечня
- Варианты:
  1. Задать явный список процедур и ошибок. Последствие: 4.6.2 получает перечень для проверки полноты документации
  2. Полнота задаётся регламентом Office of Information Services. Последствие: 4.6.2 ссылается на внешний регламент, его нужно добавить в References
- Рекомендуем: вариант 1, потому что перечень в тексте позволяет проверить полноту документации.
- Без ответа нельзя: Нельзя проверить полноту документации для администраторов
- Закрывает замечания: [D-63](#d-63), [D-64](#d-64).

### Вопросы архитектору

#### <a id="q-06"></a>Q-06 · архитектору · блокирует разработку
**Какой формат хранения аудиоклипов задать: конкретные кодек и контейнер (строка 175) или выбор архитектором?**
- Сейчас в документе: `The system must store audio clips in a format` (строка 175); `a format conducive to speech` (строка 175); `a format optimized for speech` (строка 176).
- Суть: Строка 176 говорит «optimized for speech» без кодека и контейнера
- Варианты:
  1. Задать конкретные кодек и контейнер. Последствие: Строка 175 получает конкретные значения для проверки хранения
  2. Выбор формата остаётся архитектору. Последствие: Требование хранения остаётся без проверяемого критерия
- Рекомендуем: вариант 1, потому что без конкретного формата соответствие хранения требованию нельзя проверить.
- Без ответа нельзя: Нельзя проверить хранение клипов и выбрать библиотеку воспроизведения
- Закрывает замечания: [D-13](#d-13), [D-16](#d-16).

### Вопросы тестировщику

#### <a id="q-08"></a>Q-08 · тестировщику · блокирует разработку
**Какой формат должен получить актор при скачивании клипа: mp3 (строка 174) или другой формат, название которого нужно задать?**
- Сейчас в документе: `download their voice clips in a flexible format` (строка 173); `in a format such as MPEG Audio (mp3) format` (строка 174).
- Суть: Строка 174 называет mp3 как пример, с оговоркой such as
- Варианты:
  1. mp3 (MPEG Audio). Последствие: Формат фиксируется в 3.2.2, при скачивании клип конвертируется в mp3
  2. Другой формат, название задать. Последствие: Пункт 3.2.2 переписывается, тесты берут новый формат
- Рекомендуем: вариант 1, потому что строка 174 называет mp3 как пример формата для скачивания.
- Без ответа нельзя: Нельзя написать проверку скачивания клипа
- Закрывает замечания: [D-10](#d-10).

#### <a id="q-09"></a>Q-09 · тестировщику · блокирует разработку
**Какой результат подтверждает загрузку файла на страницу: файл сохранён и виден в списке файлов страницы?**
- Сейчас в документе: `manage files where appropriate` (строка 158).
- Суть: Строка 158 «manage files where appropriate» без наблюдаемого результата
- Варианты:
  1. Да: файл сохранён и виден в списке страницы. Последствие: Тест проверяет появление файла в списке страницы
  2. Файл сохранён, показ в списке не требуется. Последствие: Критерий сводится к факту сохранения без вывода
- Рекомендуем: вариант 1, потому что управление файлами по строке 159 подразумевает видимость в списке.
- Без ответа нельзя: Нельзя написать приёмочный тест загрузки файла
- Закрывает замечания: [D-03](#d-03).

#### <a id="q-10"></a>Q-10 · тестировщику · блокирует разработку
**Что подтверждает захват голосового клипа: клип сохранён и виден в портфолио актора (строка 168)?**
- Сейчас в документе: `capture and organize voice clips that can be used where appropriate` (строка 165).
- Суть: Строка 165 «used where appropriate» без наблюдаемого результата
- Варианты:
  1. Да: клип сохранён и виден в портфолио. Последствие: Тест проверяет появление клипа в портфолио после записи
  2. Клип сохранён, показ в портфолио не проверяется. Последствие: Портфолио проверяется отдельно или не проверяется вовсе
- Рекомендуем: вариант 1, потому что строка 168 относит организацию клипов к портфолио.
- Без ответа нельзя: Нельзя написать тест захвата голосового клипа
- Закрывает замечания: [D-05](#d-05).

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

- <a id="d-01"></a>**D-01 [MAJOR] Однозначность** · [REQ-01](#req-01) · Фраза не задаёт, какие Priority 3 требования входят в выпуск. Причина: слито с другим замечанием [S-12](#s-12): Тот же дефект: состав приоритета 3 в строке 156 не определён. Исправление общее со сроками и бюджетом, его закрывает замечание по набору.
- <a id="d-02"></a>**D-02 [MAJOR] Проверяемость** · [REQ-01](#req-01) · Критерий приёмки выпуска для Priority 3 не задан, поэтому состав выпуска нельзя сверить с требованием. Причина: слито с другим замечанием [S-12](#s-12): Строка 156 не даёт перечня выпуска для приоритета 3, поэтому критерий приёмки закрывается тем же исправлением, что и S-12.
- <a id="d-04"></a>**D-04 [MAJOR] Однозначность** · [REQ-02](#req-02) · Фраза where appropriate оставляет открытым, на каких страницах допустима загрузка и управление файлами. Причина: слито с другим замечанием [D-03](#d-03): Та же фраза «where appropriate» в строке 158, исправление одно: перечислить страницы для загрузки файлов.
- <a id="d-06"></a>**D-06 [MAJOR] Однозначность** · [REQ-04](#req-04) · Условие where appropriate не задаёт, для каких заданий или страниц клипы используются. Причина: слито с другим замечанием [D-05](#d-05): Условие «where appropriate» в строке 165 устраняется тем же уточнением, что и критерий результата.
- <a id="d-11"></a>**D-11 [MAJOR] Однозначность** · [REQ-06](#req-06) · Слово flexible оценочное и не определяет набор поддерживаемых форматов. Причина: слито с другим замечанием [D-10](#d-10): Слово «flexible» в строке 173 устраняется тем же исправлением: перечислить поддерживаемые форматы.
- <a id="d-12"></a>**D-12 [MAJOR] Полнота** · [REQ-06](#req-06) · Формат mp3 назван примером, поэтому полный набор форматов не определён. Причина: слито с другим замечанием [D-10](#d-10): Пример «such as» в строке 174 закрывается тем же списком форматов, что и D-10.
- <a id="d-14"></a>**D-14 [MAJOR] Однозначность** · [REQ-07](#req-07) · Фраза «conducive to speech» не задаёт формат: нет ни кодека, ни контейнера, ни параметров. Причина: слито с другим замечанием [D-13](#d-13): Фраза «conducive to speech» в строке 175 закрывается указанием конкретного формата, как и D-13.
- <a id="d-15"></a>**D-15 [MAJOR] Полнота** · [REQ-07](#req-07) · Формула «optimized for speech» не задаёт значений: не указаны битрейт и другие параметры кодирования. Причина: слито с другим замечанием [D-13](#d-13): Строка 176 не задаёт параметры кодирования, исправление то же: описать формат хранения с параметрами.
- <a id="d-20"></a>**D-20 [MAJOR] Однозначность** · [REQ-09](#req-09) · Фраза and other blocks не перечисляет блоки, список остаётся открытым. Причина: слито с другим замечанием [D-19](#d-19): Открытый список «and other blocks» в строке 180 закрывается тем же полным перечнем компонентов.
- <a id="d-21"></a>**D-21 [MAJOR] Полнота** · [REQ-09](#req-09) · Не указано, для каких актёров предназначена лента: значение получателя не задано. Причина: снято критиком: Строка 180 прямо говорит, что курсовые администраторы определяют, для кого предназначены ленты.
  - Цитата модели: `to whom these feeds should pertain` (строка 180)
- <a id="d-24"></a>**D-24 [CRITICAL] Непротиворечивость** · [REQ-11](#req-11) · Требование заменяет иерархические ссылки поиском, а пояснение в строке 187 сохраняет иерархический доступ. Причина: слито с другим замечанием [S-01](#s-01): Противоречие строк 186 и 187 о замене или дополнении иерархических ссылок то же самое, что и S-01.
- <a id="d-32"></a>**D-32 [MAJOR] Проверяемость** · [REQ-14](#req-14) · Фраза «may want to optionally grade» выражает желание, а не обязательное поведение системы, и не даёт условия, по которому можно принять результат. Причина: снято критиком: Фраза строки 198 описывает желание преподавателя, а проверяемое требование «must allow» в той же строке задано.
  - Цитата модели: `Actors in the role of professor may want to optionally grade assignments online` (строка 198)
- <a id="d-42"></a>**D-42 [MAJOR] Проверяемость** · [REQ-19](#req-19) · Без перечня функций приёмка не имеет критерия успеха, так как «все современные» нельзя сверить. Причина: слито с другим замечанием [D-40](#d-40): Тот же перечень функций блога из строки 212 закрывает и неясность объёма, и проверяемость приёмки.
- <a id="d-52"></a>**D-52 [MAJOR] Полнота** · [REQ-22](#req-22) · Периодичность, объём и состав копий не заданы, текст откладывает решение. Причина: слито с другим замечанием [S-05](#s-05): Отложенное определение резервного копирования в строке 227 закрывает то же исправление, что и S-05.
