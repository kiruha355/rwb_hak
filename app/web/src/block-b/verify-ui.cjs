/* Small offline check. Uses existing dependencies, installs nothing, starts no server.
   node app/web/src/block-b/verify-ui.cjs --tools /path/with/node_modules --out /absolute/evidence
   The evidence is synthetic UI QA, never Olist DB or endpoint E2E. */
const fs = require("node:fs"), path = require("node:path"), vm = require("node:vm");
const assert = require("node:assert/strict"), cp = require("node:child_process");
const args = process.argv.slice(2), arg = key => args[args.indexOf(key) + 1];
const toolsPath = arg("--tools"), out = path.resolve(arg("--out"));
if (!args.includes("--tools") || !args.includes("--out")) throw new Error("Use --tools EXISTING_PROJECT --out EVIDENCE_DIR");
const resolve = name => require.resolve(name, { paths: [toolsPath] });
const ts = require(resolve("typescript")), React = require(resolve("react"));
const { renderToStaticMarkup } = require(resolve("react-dom/server"));
const esbuild = require(resolve("esbuild"));
const root = path.resolve(__dirname, "../../../.."), src = path.resolve(__dirname, "..");
const cache = new Map();
function load(file) {
  if (cache.has(file)) return cache.get(file).exports;
  const m = { exports: {} }; cache.set(file, m);
  const result = ts.transpileModule(fs.readFileSync(file, "utf8"), {
    fileName: file, compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2020, jsx: ts.JsxEmit.ReactJSX },
    reportDiagnostics: true,
  });
  assert.equal((result.diagnostics || []).filter(d => d.category === ts.DiagnosticCategory.Error).length, 0);
  const localRequire = name => {
    if (name.endsWith(".css")) return {};
    if (name.startsWith(".")) {
      const base = path.resolve(path.dirname(file), name), found = [base, base + ".ts", base + ".tsx"].find(p => fs.existsSync(p));
      return load(found);
    }
    return require(resolve(name));
  };
  vm.runInThisContext(`(function(require,module,exports){${result.outputText}\n})`, { filename: file })(localRequire, m, m.exports);
  return m.exports;
}
const results = [];
function check(name, fn) { fn(); results.push({ name, status: "PASS" }); }
const contract = load(path.join(__dirname, "contract.ts"));
const { BlockBView } = load(path.join(src, "BlockBAnswers.tsx"));
const fixture = require("./qa-fixture.cjs"), raw = fixture(), data = contract.adaptBlockB(raw);
const render = state => {
  const originalError = console.error, errors = [];
  console.error = (...args) => errors.push(args.join(" "));
  try {
    const html = renderToStaticMarkup(React.createElement(BlockBView, { state, retry() {} }));
    assert.deepEqual(errors, [], "React SSR console warnings");
    return html;
  } finally { console.error = originalError; }
};
check("PostgreSQL strings and NULL stay distinct from zero", () => {
  assert.equal(data.q6.rows[0].price, 0); assert.equal(data.q6.rows[3].price, null);
  assert.equal(data.q9.states[0].payment_amount, null); assert.equal(data.q9.states[1].payment_amount, 0);
  assert.equal(data.q9.states[0].known_payment_amount_sum, 12500.5);
});
check("All named variants survive adaptation", () => {
  assert.equal(data.q10.rows.length, 40);
  assert.deepEqual(data.q10.rows.map(r => [r.population, r.score_policy, r.late_basis, r.review_score]), raw.q10.rows.map(r => [r.population, r.score_policy, r.late_basis, r.review_score]));
  assert.deepEqual([...new Set(data.q9.methods.map(r => r.period))], ["all_snapshot", "purchase_2018"]);
});
check("CSV keeps dimensions, coverage, zero and NULL distinct", () => {
  const csv = contract.csvRows(data.q10.rows);
  assert.ok(csv.includes('"population";"late_basis";"orders_count";"duration_denominator"'));
  assert.ok(csv.includes('"within_score"')); assert.ok(csv.includes('"single_score_only"'));
  const amounts = contract.csvRows(data.q9.states);
  assert.ok(amounts.includes('"500";"499";;"12500.5"'));
  assert.ok(amounts.includes('"2";"2";"0";"0"'));
});
check("Malformed/missing/unknown/duplicate data fails instead of appearing empty", () => {
  for (const mutate of [
    d => delete d.q9.states, d => d.q7.rows[0].population = "UNKNOWN_VARIANT",
    d => d.q6.rows[0].price = "", d => delete d.q8.rows[0].orders_count,
    d => d.q10.rows.pop(), d => d.q10.rows.push(d.q10.rows[0]), d => d.q10.coverage.pop(),
    d => d.q7.rows[0].orders_count = "9007199254740993",
    d => d.q6.rows[0].purchase_date = "2018-02-31",
    d => d.q6.rows[1].units_with_unknown_price = 100,
  ]) { const d = fixture(); mutate(d); assert.throws(() => contract.adaptBlockB(d)); }
});
const html = render({ status: "ready", data });
check("Every tied Q6 leader survives; unknowns remain explicit", () => {
  assert.ok(html.includes("leader-aaaaaaaaaaaaaaaaaaaaaaaaa"));
  assert.ok(html.includes("tied-bbbbbbbbbbbbbbbbbbbbbbbbbbb"));
  assert.ok(html.includes("Дата неизвестна")); assert.ok(html.includes("Штат неизвестен"));
  assert.ok(html.includes("Способ неизвестен")); assert.ok(html.includes("Нет данных"));
});
check("Q7 threshold includes 500 and excludes 499 without reweighting", () => {
  assert.ok(!html.includes("BELOW_THRESHOLD")); assert.ok(html.includes("500"));
  assert.equal(data.q7.rows.length, raw.q7.rows.length);
});
check("Q9 has states and two separate method windows", () => {
  assert.ok(html.includes("Платежи по штатам за покупки 2018 года"));
  assert.ok(html.includes("Способы оплаты: Весь снимок")); assert.ok(html.includes("Способы оплаты: Покупки 2018 года"));
  assert.ok(html.includes("12 500,50")); assert.ok(html.includes("не задаёт срок в месяцах"));
});
check("Q10 shows five scores per variant, zero groups, separate denominators and overlaps", () => {
  assert.equal((html.match(/<td>[1-5]<span class="bb-denom">/g) || []).length, 40);
  assert.ok(html.includes("измерено 0 из 0")); assert.ok(html.includes("0 из 0 измеренных"));
  assert.ok(html.includes("Причины пересекаются")); assert.ok(!html.includes("Итого"));
});
const empty = { q6: { rows: [] }, q7: { rows: [] }, q8: { rows: [] }, q9: { states: [], methods: [] }, q10: { rows: [], coverage: [] }, meta: { scope: "empty fixture" } };
check("Successful empty, loading and error are different states", () => {
  const e = render({ status: "ready", data: contract.adaptBlockB(empty) });
  const loading = render({ status: "loading" }), failure = render({ status: "error", message: "Витрина недоступна (HTTP 503)." });
  assert.ok(e.includes("не вернула строк")); assert.ok(!e.includes("role=\"alert\""));
  assert.ok(loading.includes("role=\"status\"")); assert.ok(!loading.includes("<table"));
  assert.ok(failure.includes("role=\"alert\"")); assert.ok(failure.includes("Повторить загрузку")); assert.ok(!failure.includes("<table"));
});
check("Q1–Q5 baseline differs by the owned insertion only", () => {
  const baseline = cp.execFileSync("git", ["show", "6452806eae21d13126da9de8ebaba01a2152eaea:app/web/src/pages/Answers.tsx"], { cwd: root, encoding: "utf8" });
  const current = fs.readFileSync(path.join(src, "pages/Answers.tsx"), "utf8");
  assert.equal(current.replace('import BlockBAnswers from "../BlockBAnswers";\n', "").replace('<BlockBAnswers fallback={<AnswersB />} />', '<AnswersB />'), baseline);
});
check("Strict typecheck of owned production modules with available React types", () => {
  const options = { target: ts.ScriptTarget.ES2020, lib: ["lib.es2020.d.ts", "lib.dom.d.ts", "lib.dom.iterable.d.ts"],
    module: ts.ModuleKind.ESNext, moduleResolution: ts.ModuleResolutionKind.Bundler, jsx: ts.JsxEmit.ReactJSX,
    strict: true, noEmit: true, skipLibCheck: true, isolatedModules: true, types: [], baseUrl: root,
    paths: { "react": [path.dirname(resolve("@types/react/package.json"))], "react/*": [path.join(path.dirname(resolve("@types/react/package.json")), "*")] },
  };
  const program = ts.createProgram([path.join(src, "BlockBAnswers.tsx"), path.join(__dirname, "components.tsx"), path.join(__dirname, "contract.ts")], options);
  const diagnostics = ts.getPreEmitDiagnostics(program);
  if (diagnostics.length) throw new Error(ts.formatDiagnosticsWithColorAndContext(diagnostics, { getCanonicalFileName: f => f, getCurrentDirectory: () => root, getNewLine: () => "\n" }));
});
fs.mkdirSync(out, { recursive: true });
// Baseline panel/table/button rules, with T3 theme aliases only in the QA artifact.
const baselineCSS = cp.execFileSync("git", ["show", "6452806eae21d13126da9de8ebaba01a2152eaea:app/web/src/styles.css"], { cwd: root, encoding: "utf8" });
const common = [...baselineCSS.matchAll(/([^{}]+)\{([^{}]+)\}/g)]
  .map(m => [m[1].replace(/\/\*[\s\S]*?\*\//g, "").trim(), m[2]])
  .filter(([selector]) => /^(\.btn([ .:]|$)|\.card, \.panel|table\s|th, td|th\s|td.n, th.n|tbody tr:hover)/.test(selector)).map(([selector, body]) => `${selector}{${body}}`).join("\n");
const styles = `:root{--ink:var(--foreground);--muted:var(--muted-foreground);--surface:var(--card);--sunken:var(--secondary);--line:var(--border);--line-strong:var(--border);--accent:var(--chart-1);--sand:var(--chart-2);--font:var(--font-sans);--mono:var(--font-mono);--r:var(--radius);--r-s:var(--radius)}*{box-sizing:border-box}html,body{margin:0}h2,h3{margin:0}button{font:inherit} ${common}\n${fs.readFileSync(path.join(__dirname, "styles.css"), "utf8")}`;
const document = content => `<!doctype html><html lang="ru"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"><style>${styles}</style></head><body><p style="font-size:12px;color:var(--muted-foreground)">Синтетические данные для проверки UI · не ответы Olist</p>${content}</body></html>`;
for (const [name, state] of Object.entries({ ready: { status: "ready", data }, empty: { status: "ready", data: contract.adaptBlockB(empty) }, loading: { status: "loading" }, error: { status: "error", message: "Витрина недоступна (HTTP 503). Проверьте доступность новых витрин." } })) {
  fs.writeFileSync(path.join(out, `${name}.html`), document(render(state)));
}
// Bundle only this small feature using existing tools; no app build or server.
const clientScript = `import React from "react";import {createRoot} from "react-dom/client";import BlockBAnswers from ${JSON.stringify(path.join(src, "BlockBAnswers.tsx"))};
const fixture=${JSON.stringify(raw)};const calls=[];let replies=[503,200],deferred=null,wasAborted=false;
window.fetch=async (url,options)=>{const reply=replies.shift()??200;calls.push({url,aborted:options?.signal?.aborted});if(reply==="defer")return new Promise(resolve=>{deferred=()=>resolve({ok:true,status:200,json:async()=>structuredClone(fixture)});options.signal.addEventListener("abort",()=>{wasAborted=true})});const status=typeof reply==="number"?reply:reply.status;return {ok:status===200,status,json:async()=>structuredClone(typeof reply==="number"?fixture:reply.payload)}};
const root=createRoot(document.getElementById("root"));root.render(React.createElement(BlockBAnswers,{key:"initial"}));
const wait=()=>new Promise(r=>setTimeout(r,0));
const until=async(fn)=>{for(let i=0;i<120;i++){if(fn())return;await wait()}throw Error("UI check timed out")};
(async()=>{try{
await until(()=>document.querySelector('[role="alert"]'));
if(document.querySelector("table"))throw Error("Error masked by data");
const retry=document.querySelector(".bb-error button");retry.focus();if(document.activeElement!==retry)throw Error("Retry cannot receive focus");retry.click();
await until(()=>document.querySelector("#bb-q10"));
if(calls.length!==2||calls.some(c=>c.url!=="/api/answers-block-b"))throw Error("Unexpected request scope");
for(const details of document.querySelectorAll("details")){details.open=true;details.open=false}
if(document.querySelectorAll('td').length===0)throw Error("No result");
replies=[404];root.render(React.createElement(BlockBAnswers,{key:"legacy",fallback:React.createElement("div",{id:"legacy-slot"},"Existing colleague component")}));
await until(()=>document.getElementById("legacy-slot"));if(document.querySelector("#bb-q6"))throw Error("Duplicate block B");
replies=[{status:200,payload:{...fixture,q10:{...fixture.q10,rows:fixture.q10.rows.slice(1)}}}];root.render(React.createElement(BlockBAnswers,{key:"bad-contract"}));
await until(()=>document.querySelector('[role="alert"]'));
if(!document.querySelector('[role="alert"]').textContent.includes("q10.rows")||document.querySelector("table"))throw Error("Bad contract masked");
replies=["defer"];root.render(React.createElement(BlockBAnswers,{key:"cancel"}));await until(()=>deferred);
root.render(React.createElement("div",{id:"cancelled-slot"}));await until(()=>wasAborted);deferred();await wait();
if(!document.getElementById("cancelled-slot"))throw Error("Stale response updated an unmounted view");
replies=[200];root.render(React.createElement(BlockBAnswers,{key:"final"}));await until(()=>document.querySelector("#bb-q10"));
const outside=[...document.querySelectorAll(".block-b *")].filter(e=>{const r=e.getBoundingClientRect();return r.width>0&&r.right>innerWidth+1&&!e.closest(".bb-table")});
if(outside.length)throw Error("Page overflow: "+outside.map(e=>e.tagName+"."+e.className).join(","));
window.__blockBQa={status:"PASS",calls,checks:["503 error distinct from empty","focusable retry","retry to ready","fixed snapshot endpoint without query filters","details open/close","404 uses existing component slot without duplicate block","missing score grid raises contract error","unmount aborts request and ignores stale response"],layoutChecked:!navigator.userAgent.includes("jsdom"),width:innerWidth};
console.log("BLOCK_B_CLIENT_QA PASS layout="+window.__blockBQa.layoutChecked+" width="+innerWidth+" checks="+window.__blockBQa.checks.length+" calls="+calls.length);
document.getElementById("qa-status").textContent="React UI: проверки пройдены · синтетические данные";
}catch(e){window.__blockBQa={status:"FAIL",error:String(e)};console.error("BLOCK_B_CLIENT_QA "+JSON.stringify(window.__blockBQa));document.getElementById("qa-status").textContent=String(e)}})();`;
const bundle = esbuild.buildSync({ stdin: { contents: clientScript, resolveDir: toolsPath, loader: "tsx" }, bundle: true, write: false, minify: true,
  nodePaths: [path.join(toolsPath, "node_modules")], platform: "browser", format: "iife", jsx: "automatic", define: { "process.env.NODE_ENV": '"production"' },
  loader: { ".css": "empty" }, logLevel: "silent" }).outputFiles[0].text;
fs.writeFileSync(path.join(out, "interactive.html"), document(`<p id="qa-status" role="status">Проверка React UI…</p><div id="root"></div><script>${bundle.replace(/<\/script/gi, "<\\/script")}</script>`));
fs.writeFileSync(path.join(out, "reviews.html"), document(`<style>.bb-section:not([aria-labelledby="bb-q10"]){display:none}</style>${html}`));
fs.writeFileSync(path.join(out, "states.html"), document(`<h2>Ожидание</h2>${render({ status: "loading" })}<h2>Ошибка</h2>${render({ status: "error", message: "Витрина недоступна (HTTP 503). Проверьте доступность новых витрин." })}<h2>Успешный пустой ответ</h2>${render({ status: "ready", data: contract.adaptBlockB(empty) })}`));
const summary = { status: "PASS", timestamp: new Date().toISOString(), tests: results,
  tools: { node: process.version, typescript: ts.version, react: React.version, esbuild: esbuild.version },
  scope: "Synthetic adapter, strict types and React SSR only; interactive.html requires html_preview. Not an API/DB E2E or pinned React 18 check.",
};
fs.writeFileSync(path.join(out, "checks.json"), JSON.stringify(summary, null, 2) + "\n");
console.log(JSON.stringify(summary, null, 2));

// Real React effects in an existing DOM implementation; no network/browser/server.
// Layout remains a separate html_preview check because jsdom does not lay out CSS.
(async () => {
  const { JSDOM, VirtualConsole } = require(resolve("jsdom"));
  const virtualConsole = new VirtualConsole(), errors = [];
  virtualConsole.on("jsdomError", e => errors.push(String(e)));
  const dom = new JSDOM(fs.readFileSync(path.join(out, "interactive.html"), "utf8"), {
    runScripts: "dangerously", pretendToBeVisual: true, url: "https://ui-fixture.invalid/",
    virtualConsole, beforeParse(window) { window.structuredClone = structuredClone; },
  });
  try {
    const deadline = Date.now() + 5000;
    while (!dom.window.__blockBQa && Date.now() < deadline) await new Promise(r => setTimeout(r, 10));
    const result = dom.window.__blockBQa;
    assert.ok(result, "Client QA timed out"); assert.equal(result.status, "PASS", JSON.stringify(result));
    assert.deepEqual(errors, []);
    fs.writeFileSync(path.join(out, "client-checks.json"), JSON.stringify({ ...result, environment: "jsdom; layout is not verified here", react: React.version, timestamp: new Date().toISOString() }, null, 2) + "\n");
    console.log(JSON.stringify({ client: result.status, checks: result.checks.length, layoutChecked: false }));
  } finally { dom.window.close(); }
})().catch(error => { console.error(error); process.exitCode = 1; });
