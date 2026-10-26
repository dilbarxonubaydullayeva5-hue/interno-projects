"""Шаг 5 REELS-PROCESS.md: раскадровка по реальным таймкодам голоса.

Использование: python3 tools/storyboard.py <NN-имя>
Берёт scripts/<NN>/shots.json и public/video/<NN>/words.json,
пишет scripts/<NN>/storyboard.md и scripts/<NN>/clips.md (таблица «клип → секунд на экране»).
Граница плана — начало первого слова плана; план держится до начала следующего.
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FPS = 30
MAX_SHOT = 3.0  # дольше без смены нельзя
LABEL = {'G': 'генерация (Flow)', 'R': 'настоящий снимок', 'RG': 'клип из настоящего снимка', 'M': 'графика кодом'}

name = sys.argv[1]
W = json.loads((ROOT / 'public/video' / name / 'words.json').read_text())
words = {w['i']: w for w in W['words']}
shots = json.loads((ROOT / 'scripts' / name / 'shots.json').read_text())

def start_frame(i):
    while i not in words:  # слово, которого нет в записи (например, проглоченное «И»)
        i += 1
    return words[i]['frameStart']

rows, clips, warn = [], {}, []
for k, s in enumerate(shots):
    f0 = 0 if k == 0 else start_frame(s['from'])
    f1 = W['durationInFrames'] if k == len(shots) - 1 else start_frame(shots[k + 1]['from'])
    dur = (f1 - f0) / FPS
    last = (shots[k + 1]['from'] - 1) if k < len(shots) - 1 else max(words)
    text = ' '.join(words[i]['text'] for i in range(s['from'], last + 1) if i in words)
    if dur > MAX_SHOT:
        warn.append(f"план {s['id']}: {dur:.2f} с > {MAX_SHOT} с")
    rows.append((s, f0, f1, dur, text))
    if s['type'] in ('G', 'RG'):
        clips.setdefault(s['clip'], []).append((s['id'], dur))

out = [f'# Раскадровка — {name}', '',
       f"Голос: {W['duration']} с, {W['durationInFrames']} кадров при {FPS} fps. Границы — по началу слов из words.json.", '',
       '| План | Кадры | Сек | Слова | Тип | Фон (нижний слой) | Поверх | Переход на входе | Звук |',
       '|---|---|---|---|---|---|---|---|---|']
for s, f0, f1, dur, text in rows:
    out.append(f"| {s['id']} | {f0}–{f1} | {dur:.2f} | {text} | {LABEL[s['type']]}{' · ' + s['clip'] if s.get('clip') else ''} | {s['bg']} | {s['over']} | {s['tr']} | {s['sfx']} |")
out += ['', f"Планов: {len(rows)}. Видеоклипов (генерация и из снимков): {len(clips)}. Настоящих снимков: {sum(1 for r in rows if r[0]['type'] == 'R')}.",
        f"Самый длинный план: {max(r[3] for r in rows):.2f} с. " + ('Предупреждения: ' + '; '.join(warn) if warn else 'Планов дольше 3 с нет.')]
(ROOT / 'scripts' / name / 'storyboard.md').write_text('\n'.join(out) + '\n')

c = ['# Клипы → секунд на экране', '', 'Длина заказа = сумма планов клипа + 0,5 с запаса, округлённая вверх до доступной длины.', '',
     '| Клип | Планы | На экране, с | Нужно с запасом, с |', '|---|---|---|---|']
for cid, ps in clips.items():
    t = sum(d for _, d in ps)
    c.append(f"| {cid} | {', '.join(p for p, _ in ps)} | {t:.2f} | {t + 0.5:.2f} |")
(ROOT / 'scripts' / name / 'clips.md').write_text('\n'.join(c) + '\n')
print('\n'.join(out[-2:]))
