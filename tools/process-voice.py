"""Шаг 4 REELS-PROCESS.md: вырезать паузы, ускорить голос, разложить слова по кадрам.

Использование:
  python3 tools/process-voice.py <NN-имя> [--rate 7.3]

Берёт:
  public/video/<NN>/voice-raw.mp3          — дубль
  scripts/<NN>/scribe-asr-words.json       — распознавание (только время слов)
  scripts/<NN>/voice.txt                   — текст для озвучки (написание слов)
Пишет:
  public/video/<NN>/voice.wav              — обработанный голос
  public/video/<NN>/words.json             — слова сценария с таймкодами и кадрами (30 fps)
  scripts/<NN>/voice-report.md             — темп, ускорение, проверка склеек
"""
import argparse
import difflib
import json
import re
import subprocess
import sys
from pathlib import Path

import numpy as np

SR = 48000
FPS = 30
VOWELS = set('аеёиоуыэюяaeiou')

# Паузы, которые оставляем после слова (в секундах записи ДО ускорения).
GAP_DEFAULT = 0.03     # между словами
GAP_COMMA = 0.07       # после запятой и тире
GAP_SENTENCE = 0.14    # после точки и восклицания
GAP_QUESTION = 0.32    # после вопроса
GAP_KEY = 0.30         # после ключевых фраз (по последнему слову фразы, см. KEY_AFTER)
FADE = 0.005           # микрофейд на каждой склейке, чтобы не было щелчков
SILENCE_DB = -45       # ниже этого уровня окно 10 мс считается тишиной
MIN_SILENCE = 0.06     # тихий участок короче этого не трогаем

ROOT = Path(__file__).resolve().parent.parent


def norm(w):
    return re.sub(r'[^\w-]', '', w.lower().replace('ё', 'е')).strip('-')


def syllables(text):
    return sum(1 for c in text.lower() if c in VOWELS)


def load_audio(path):
    raw = subprocess.run(
        ['ffmpeg', '-v', 'error', '-i', str(path), '-ac', '1', '-ar', str(SR), '-f', 'f32le', '-'],
        check=True, capture_output=True).stdout
    return np.frombuffer(raw, dtype=np.float32).copy()


def save_wav(path, audio):
    subprocess.run(
        ['ffmpeg', '-v', 'error', '-y', '-f', 'f32le', '-ar', str(SR), '-ac', '1', '-i', '-',
         '-c:a', 'pcm_s16le', str(path)],
        input=audio.astype(np.float32).tobytes(), check=True)


def rms_db(audio, t, win=0.01):
    a = audio[max(0, int((t - win / 2) * SR)):int((t + win / 2) * SR)]
    if len(a) == 0:
        return -120.0
    return 20 * np.log10(np.sqrt(np.mean(a ** 2)) + 1e-9)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('name')
    ap.add_argument('--rate', type=float, default=7.3, help='целевой темп, слогов в секунду')
    ap.add_argument('--key', default='', help='номера слов сценария (с 1), после которых держать паузу, через запятую')
    args = ap.parse_args()

    vdir = ROOT / 'public/video' / args.name
    sdir = ROOT / 'scripts' / args.name

    # Слова сценария (написание) с пунктуацией.
    text = re.sub(r'\[[^\]]+\]', ' ', (sdir / 'voice.txt').read_text())
    ref = [w for w in text.split() if norm(w)]
    ref_n = [norm(w) for w in ref]

    asr = [w for w in json.loads((sdir / 'scribe-asr-words.json').read_text())['words']
           if w['type'] == 'word' and norm(w['text'])]
    asr_n = [norm(w['text']) for w in asr]

    # Сопоставляем: время берём от распознавания, написание — из сценария.
    timed = []  # (index in ref, start, end)
    missing = []
    for op, a1, a2, b1, b2 in difflib.SequenceMatcher(None, ref_n, asr_n, autojunk=False).get_opcodes():
        if op == 'equal' or (op == 'replace' and a2 - a1 == b2 - b1):
            for k in range(a2 - a1):
                timed.append((a1 + k, asr[b1 + k]['start'], asr[b1 + k]['end']))
        else:
            missing += list(range(a1, a2))

    key = {int(x) - 1 for x in args.key.split(',') if x.strip()}

    audio = load_audio(vdir / 'voice-raw.mp3')
    total = len(audio) / SR

    def target_after(i):
        word = ref[i]
        if i in key:
            return GAP_KEY
        if word.endswith('?'):
            return GAP_QUESTION
        if word.endswith(('.', '!')):
            return GAP_SENTENCE
        if word.endswith((',', '—', ':')) or (i + 1 < len(ref) and ref[i + 1] == '—'):
            return GAP_COMMA
        return GAP_DEFAULT

    # Тихие участки по огибающей громкости (окна 10 мс). Режем только внутри них,
    # чтобы склейка всегда попадала между словами, а не в слитную речь.
    win = int(0.01 * SR)
    env = 20 * np.log10(np.sqrt(np.mean(audio[:len(audio) // win * win].reshape(-1, win) ** 2, axis=1)) + 1e-9)
    quiet = env < SILENCE_DB
    silences = []
    k = 0
    while k < len(quiet):
        if quiet[k]:
            k2 = k
            while k2 < len(quiet) and quiet[k2]:
                k2 += 1
            if (k2 - k) * 0.01 >= MIN_SILENCE:
                silences.append((k * 0.01, k2 * 0.01))
            k = k2
        else:
            k += 1

    first, last = timed[0][1], timed[-1][2]
    keep = []  # (start, end) в исходной записи
    cuts = []  # (рез с, рез по) в исходной записи
    seg_start = max(0.0, first - 0.05)
    for a0, b0 in silences:
        if b0 <= first or a0 >= last:
            continue
        mid = (a0 + b0) / 2
        prev = [t for t in timed if t[2] <= mid + 0.05]
        target = target_after(prev[-1][0]) if prev else GAP_DEFAULT
        # Оставляем target тишины плюс по 20 мс у краёв, чтобы не задеть хвосты слов.
        # Тишина внутри слова (смычка перед «п», «т», «к») — не пауза, её не трогаем.
        # Тихий участок обрезаем по границам слов от распознавания.
        for _, s, e in timed:
            if s < b0 and e > a0:
                if s <= a0 + 0.01 and e >= b0 - 0.01:
                    a0 = b0  # целиком внутри слова
                elif s <= a0 + 0.01:
                    a0 = e
                else:
                    b0 = min(b0, s)
        if (b0 - a0) > target + 0.06:
            a = a0 + 0.02 + target / 2
            b = b0 - 0.02 - target / 2
            keep.append((seg_start, a))
            cuts.append((a, b))
            seg_start = b
    keep.append((seg_start, min(total, last + 0.25)))

    # Склейка с микрофейдами.
    fade_n = int(FADE * SR)
    ramp = np.linspace(0, 1, fade_n, dtype=np.float32)
    pieces = []
    for a, b in keep:
        p = audio[int(a * SR):int(b * SR)].copy()
        if len(p) > 2 * fade_n:
            p[:fade_n] *= ramp
            p[-fade_n:] *= ramp[::-1]
        pieces.append(p)
    cut_audio = np.concatenate(pieces)
    cut_dur = len(cut_audio) / SR

    # Отображение времени: исходная запись → после вырезания пауз.
    def map_cut(t):
        acc = 0.0
        for a, b in keep:
            if t < a:
                return acc
            if t <= b:
                return acc + (t - a)
            acc += b - a
        return acc

    # Темп и ускорение.
    syl = syllables(' '.join(ref))
    speech_after_cut = cut_dur
    factor = max(1.0, speech_after_cut / (syl / args.rate))

    tmp = vdir / '_cut.wav'
    save_wav(tmp, cut_audio)
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', str(tmp), '-filter:a', f'atempo={factor:.4f}',
                    '-ar', str(SR), '-ac', '1', '-c:a', 'pcm_s16le', str(vdir / 'voice.wav')], check=True)
    tmp.unlink()
    out = load_audio(vdir / 'voice.wav')
    out_dur = len(out) / SR

    words = []
    for i, s, e in timed:
        ns, ne = map_cut(s) / factor, map_cut(e) / factor
        words.append({'i': i + 1, 'word': re.sub(r'[^\w-]', '', ref[i]) or ref[i], 'text': ref[i],
                      'start': round(ns, 3), 'end': round(ne, 3),
                      'frameStart': int(round(ns * FPS)), 'frameEnd': int(round(ne * FPS))})
    (vdir / 'words.json').write_text(json.dumps(
        {'fps': FPS, 'duration': round(out_dur, 3), 'durationInFrames': int(np.ceil(out_dur * FPS)),
         'words': words}, ensure_ascii=False, indent=1))

    # Проверка склеек: на каждой точке реза в исходнике должна быть тишина.
    cut_levels = [(round(a, 3), round(b, 3), round(rms_db(audio, a), 1), round(rms_db(audio, b), 1))
                  for a, b in cuts]
    loud = [c for c in cut_levels if max(c[2], c[3]) > -40]
    rate = syl / out_dur

    rep = [
        f'# Обработка голоса — {args.name}', '',
        f'- Исходник: {total:.2f} с; после вырезания пауз: {cut_dur:.2f} с; склеек: {len(cuts)}',
        f'- Слогов (по тексту озвучки): {syl}',
        f'- Ускорение: ×{factor:.3f} (atempo, высота голоса не меняется){"  ⚠ больше 1,40 — перепроверить" if factor > 1.40 else ""}',
        f'- Итог: {out_dur:.2f} с, темп {rate:.2f} слога/с (норма 7,0–7,6)',
        f'- Ключевые паузы после слов: {", ".join(f"{i + 1} «{ref[i]}»" for i in sorted(key)) or "—"}',
        f'- Не найдены в записи (нет в words.json): {", ".join(ref[i] for i in missing) or "—"}',
        f'- Склейки с уровнем выше −40 dBFS в точке реза: {len(loud)} из {len(cuts)}',
        '', '| # | рез с, с | рез по, с | уровень в начале, dBFS | уровень в конце, dBFS |', '|---|---|---|---|---|',
    ] + [f'| {k + 1} | {a} | {b} | {la} | {lb} |' for k, (a, b, la, lb) in enumerate(cut_levels)]
    (sdir / 'voice-report.md').write_text('\n'.join(rep) + '\n')
    print('\n'.join(rep[:9]))
    return 1 if loud else 0


if __name__ == '__main__':
    sys.exit(main())
