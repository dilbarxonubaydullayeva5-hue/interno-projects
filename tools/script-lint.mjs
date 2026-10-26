#!/usr/bin/env node
// script-lint: checks a video script (videos/NN-slug/script.md) against the
// rules in VIDEO-SYSTEM.md and script-method.md. Exit code 1 on any error.
//
// Usage: node tools/script-lint.mjs videos/NN-slug/script.md

import { readFileSync } from "node:fs";

const RATE_MIN = 7.0;
const RATE_MAX = 7.6;
const HOOK_MAX_WORDS = 12;
const SENTENCE_MAX_WORDS = 20;

const file = process.argv[2];
if (!file) {
  console.error("Usage: node tools/script-lint.mjs <script.md>");
  process.exit(2);
}
const src = readFileSync(file, "utf8");

// --- parsing ---------------------------------------------------------------

const front = {};
const fm = src.match(/^---\n([\s\S]*?)\n---/);
if (fm) {
  for (const line of fm[1].split("\n")) {
    const m = line.match(/^(\w+):\s*([^#]*?)\s*(#.*)?$/);
    if (m) front[m[1]] = m[2];
  }
}

const section = (name) => {
  const m = src.match(new RegExp(`^## ${name}\\s*\\n([\\s\\S]*?)(?=^## |(?![\\s\\S]))`, "m"));
  return m ? m[1].replace(/<!--[\s\S]*?-->/g, "") : null;
};

const matn = section("Matn");
const faktlar = section("Faktlar");

const errors = [];
const warnings = [];
const err = (line, msg) => errors.push({ line, msg });
const warn = (line, msg) => warnings.push({ line, msg });

if (matn === null) {
  console.error(`${file}: нет раздела "## Matn"`);
  process.exit(1);
}

const lines = matn
  .split("\n")
  .map((l) => l.trim())
  .filter((l) => l && l !== "…");

// Fact tags are not voiced, strip them before checking speech.
const spoken = lines.map((l) => l.replace(/\[F\d+\]/g, "").trim());

// --- helpers ---------------------------------------------------------------

const words = (s) => s.split(/\s+/).filter((w) => /[\p{L}\d]/u.test(w));

// Uzbek Latin: one syllable per vowel. o‘ / oʻ / o' count as one vowel.
const syllables = (s) =>
  (s.toLowerCase().replace(/o[‘ʻ'`’]/g, "o").match(/[aeiouаеёиоуўэюя]/g) || []).length;

const hasWord = (s, list) => {
  const lower = ` ${s.toLowerCase().replace(/[.,!?;:«»"()—–-]/g, " ")} `;
  return list.find((w) => lower.includes(` ${w} `));
};

// --- rules -----------------------------------------------------------------

const SEN_FORMS = ["sen", "seni", "senga", "sening", "sendan", "senda", "senlar"];
const DATING = [
  "bahor", "bahorda", "yozda", "kuzda", "qishda", "yozgi", "qishki", "kuzgi", "bahorgi",
  "bu yil", "bu yili", "joriy yil", "joriy yilda", "o‘tgan yil", "o‘tgan yili", "o'tgan yil",
  "o'tgan yili", "kecha", "bugun", "hozir", "hozirgi kunda", "shu kunlarda", "yaqinda",
];
const OPENERS = ["salom", "assalomu alaykum", "bugun sizga", "aytib beraman", "keling"];

spoken.forEach((s, i) => {
  const n = i + 1;

  if (/\b(1\d{3}|20\d{2})\b/.test(s)) err(n, "год цифрами — пишите словами");
  else if (/\d/.test(s)) warn(n, "цифры в тексте для голоса — лучше словами");

  const sen = hasWord(s, SEN_FORMS);
  if (sen) err(n, `обращение на «sen» («${sen}») — только «siz»`);

  const dated = hasWord(s, DATING);
  if (dated) err(n, `привязка ко времени («${dated}») — ролик устареет`);

  if (/[а-яё]/i.test(s)) warn(n, "кириллица в узбекском тексте");

  const wc = words(s).length;
  if (wc > SENTENCE_MAX_WORDS) warn(n, `длинная фраза: ${wc} слов (до ${SENTENCE_MAX_WORDS})`);
});

// Hook
if (spoken.length === 0) {
  err(0, "раздел Matn пустой");
} else {
  const hook = spoken[0];
  const opener = hasWord(hook, OPENERS);
  if (opener) err(1, `хук начинается с разгона («${opener}») — тема и главное в первой фразе`);
  const hw = words(hook).length;
  if (hw > HOOK_MAX_WORDS) warn(1, `хук ${hw} слов (до ${HOOK_MAX_WORDS})`);
}

// CTA
const cta = (front.cta || "montaj").toLowerCase();
const last = spoken[spoken.length - 1] || "";
if (cta === "montaj") {
  if (!/montaj/i.test(last)) err(spoken.length, "последняя фраза без призыва MONTAJ");
} else if (/montaj/i.test(matn)) {
  warn(0, "cta: none, но в тексте есть MONTAJ");
}

// Apostrophe consistency for o‘ / g‘
const marks = new Set((matn.match(/[og]([‘ʻ'`’])/gi) || []).map((m) => m[1]));
if (marks.size > 1) warn(0, `разные апострофы в o‘/g‘: ${[...marks].join(" ")} — выберите один`);

// Facts: every [Fn] in Matn must have a row with a source in Faktlar
const tags = [...new Set((matn.match(/\[F\d+\]/g) || []).map((t) => t.slice(1, -1)))];
const rows = {};
for (const row of (faktlar || "").split("\n")) {
  const cells = row.split("|").map((c) => c.trim());
  if (/^F\d+$/.test(cells[1] || "")) rows[cells[1]] = cells;
}
if (tags.length === 0) warn(0, "в тексте нет ни одной метки факта [F1]");
for (const t of tags) {
  const r = rows[t];
  if (!r) err(0, `${t} есть в тексте, но нет в таблице Faktlar`);
  else if (!r[3] || r[3] === "…") err(0, `${t}: не указан источник`);
  else if (!r[4] || r[4] === "…") warn(0, `${t}: один источник — подавать осторожно или убрать`);
}
for (const t of Object.keys(rows)) {
  if (!tags.includes(t)) warn(0, `${t} в таблице, но не используется в тексте`);
}

// Duration estimate
const syl = spoken.reduce((a, s) => a + syllables(s), 0);
const durMin = syl / RATE_MAX;
const durMax = syl / RATE_MIN;
const target = Number(front.target);
if (target && durMin > target) {
  err(0, `текст длиннее цели: ${durMin.toFixed(1)}–${durMax.toFixed(1)} с при цели ${target} с — режьте текст, голос не ускоряем`);
}

// --- report ----------------------------------------------------------------

const fmt = ({ line, msg }) => `  ${line ? `строка ${line}` : "весь текст"}: ${msg}`;
console.log(`${file}`);
console.log(`  фраз: ${spoken.length}, слогов: ${syl}, длина при ${RATE_MIN}–${RATE_MAX} слог/с: ${durMin.toFixed(1)}–${durMax.toFixed(1)} с${target ? ` (цель ${target} с)` : ""}`);
if (errors.length) console.log(`\nОшибки (${errors.length}):\n${errors.map(fmt).join("\n")}`);
if (warnings.length) console.log(`\nПредупреждения (${warnings.length}):\n${warnings.map(fmt).join("\n")}`);
console.log(`\n${errors.length} ошибок, ${warnings.length} предупреждений`);
process.exit(errors.length ? 1 : 0);
