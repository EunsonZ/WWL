/* 用 MathJax 3 检查提取公式的 TeX 渲染语法。依赖 mathjax-full；不请求网络。 */
const fs = require('fs');
const {mathjax} = require('mathjax-full/js/mathjax.js');
const {TeX} = require('mathjax-full/js/input/tex.js');
const {SVG} = require('mathjax-full/js/output/svg.js');
const {liteAdaptor} = require('mathjax-full/js/adaptors/liteAdaptor.js');
const {RegisterHTMLHandler} = require('mathjax-full/js/handlers/html.js');
const {AllPackages} = require('mathjax-full/js/input/tex/AllPackages.js');
const adaptor = liteAdaptor(); RegisterHTMLHandler(adaptor);
const tex = new TeX({packages: AllPackages});
const doc = mathjax.document('', {InputJax: tex, OutputJax: new SVG({fontCache: 'none'})});
const [input, output] = process.argv.slice(2);
if (!input || !output) {console.error('用法: node check_math.cjs formulas.json report.json'); process.exit(2);}
const formulas = JSON.parse(fs.readFileSync(input, 'utf8')); const errors = [];
for (const item of formulas) {
  try {
    tex.reset();
    const node = doc.convert(item.tex, {display: item.display});
    const rendered = adaptor.outerHTML(node);
    if (/data-mjx-error|data-mml-node="merror"/.test(rendered))
      errors.push({...item, error: (rendered.match(/data-mjx-error="([^"]+)"/) || [,'merror'])[1]});
  } catch (error) {errors.push({...item, error: String(error)});}
}
const result = {engine: 'MathJax', version: require('mathjax-full/package.json').version,
                total: formulas.length, passed: formulas.length-errors.length, errors};
fs.writeFileSync(output, JSON.stringify(result, null, 2));
console.log(JSON.stringify({total: result.total, passed: result.passed, errors: errors.length}));
process.exitCode = errors.length ? 1 : 0;
