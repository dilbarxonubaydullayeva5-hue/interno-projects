// Механическая проверка сценария (шаг 2 REELS-PROCESS.md).
// Использование: node tools/lint-script.mjs scripts/<NN-имя>/lines.txt "тема1,тема2"
import fs from 'node:fs';

const [file, themeArg = ''] = process.argv.slice(2);
const lines = fs.readFileSync(file, 'utf8').split('\n').map((l) => l.trim()).filter(Boolean);
const themes = themeArg.split(',').map((t) => t.trim().toLowerCase()).filter(Boolean);

const MAX_WORDS = 12;
const STOP = new Set([
  'va', 'esa', 'bu', 'u', 'bir', 'bilan', 'ham', 'hali', 'uning', 'uni', 'o\'sha', 'yil', 'edi',
  'это', 'этот', 'эту', 'того', 'тоже', 'было', 'была', 'были', 'него', 'неё', 'нее', 'году', 'когда', 'потому',
]);
// Канцелярит: узбекский и русский.
const KANS = [
  'amalga osh', 'mavjud', 'hisoblanadi', 'tomonidan', "bo'yicha", 'yuzasidan', 'maqsadida', 'ta\'minla',
  'осуществ', 'является', 'являлся', 'данный', 'данная', 'в рамках', 'в целях', 'производится', 'имеет место',
  'в связи с', 'на сегодняшний день', 'вышеуказ', 'с целью',
];

const errors = [];
const warnings = [];
const words = (l) => l.toLowerCase().replace(/[—.,!?:;«»"]/g, ' ').split(/\s+/).filter(Boolean);

if (themes.length && !themes.some((t) => lines[0].toLowerCase().includes(t))) {
  errors.push(`строка 1: тема (${themes.join('/')}) не названа в первой фразе`);
}

const freq = new Map();
lines.forEach((l, i) => {
  const n = i + 1;
  const w = words(l);
  if (w.length > MAX_WORDS) errors.push(`строка ${n}: ${w.length} слов (макс. ${MAX_WORDS})`);
  for (const k of KANS) if ((' ' + l.toLowerCase()).includes(' ' + k)) errors.push(`строка ${n}: канцелярит «${k}»`);
  for (const m of l.match(/\d+/g) || []) warnings.push(`строка ${n}: число ${m} — сверить с таблицей фактов`);
  w.forEach((x) => {
    if (x.length < 4 || STOP.has(x)) return;
    const root = x.slice(0, 6);
    freq.set(root, [...(freq.get(root) || []), n]);
  });
});
for (const [root, at] of freq) {
  if (at.length > 3) errors.push(`повтор «${root}…» ${at.length} раз (строки ${at.join(', ')})`);
  else if (at.length === 3) warnings.push(`повтор «${root}…» 3 раза (строки ${at.join(', ')}) — проверить, намеренно ли`);
}

const syll = lines.join(' ').toLowerCase().match(/[aeiouаеёиоуыэюя]/g)?.length ?? 0;
console.log(`строк: ${lines.length}, слогов ≈ ${syll}, при 7,0–7,6 слога/с ≈ ${(syll / 7.6).toFixed(1)}–${(syll / 7.0).toFixed(1)} с`);
warnings.forEach((w) => console.log('  ⚠ ' + w));
errors.forEach((e) => console.log('  ✗ ' + e));
console.log(errors.length ? `ОШИБОК: ${errors.length}` : 'ОШИБОК: 0');
process.exit(errors.length ? 1 : 0);
