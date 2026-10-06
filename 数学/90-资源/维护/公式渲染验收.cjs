#!/usr/bin/env node
/** 全部 Markdown 数学片段由同目录 Python 审计器提取，再逐个交给 MathJax。
 * 用法：node 公式渲染验收.cjs [数学根目录]
 * 依赖：mathjax-full；使用 NODE_PATH 或与脚本相邻的 node_modules 解析依赖。
 * 环境变量 PYTHON 可覆盖默认 python。报告是解析检查，不是数学证明检查。
 */
'use strict';
const fs=require('fs');
const path=require('path');
const cp=require('child_process');
const {mathjax}=require('mathjax-full/js/mathjax.js');
const {TeX}=require('mathjax-full/js/input/tex.js');
const {SVG}=require('mathjax-full/js/output/svg.js');
const {liteAdaptor}=require('mathjax-full/js/adaptors/liteAdaptor.js');
const {RegisterHTMLHandler}=require('mathjax-full/js/handlers/html.js');
const {AllPackages}=require('mathjax-full/js/input/tex/AllPackages.js');
const root=path.resolve(process.argv[2]||path.join(__dirname,'../..'));
const audit=path.join(root,'90-资源','维护','审计知识库.py');
let extracted;
try {
  extracted=JSON.parse(cp.execFileSync(process.env.PYTHON||'python',[audit,'--root',root,'--extract-formulas'],{encoding:'utf8',maxBuffer:32*1024*1024}));
} catch(e) {
  console.error('无法完整提取公式；先运行静态审计。',e.message);process.exit(1);
}
const adaptor=liteAdaptor();RegisterHTMLHandler(adaptor);
const tex=new TeX({packages:AllPackages,maxBuffer:100000,formatError:(jax,error)=>{throw error;}});
const svg=new SVG({fontCache:'none'});
const doc=mathjax.document('',{InputJax:tex,OutputJax:svg});
let passed=0;const errors=[];
for (const item of extracted.formulas) {
  try {
    tex.reset();
    const node=doc.convert(item.tex,{display:item.display});
    const xml=adaptor.outerHTML(node);
    if (/data-mjx-error|data-mml-node="merror"/.test(xml))throw new Error('MathJax生成错误节点');
    passed++;
  } catch(e) {
    errors.push({...item,error:e.message||String(e)});
  }
}
const report={environment:{node:process.version,mathjax:require('mathjax-full/package.json').version},total:extracted.formulas.length,passed,failed:errors.length,delimiter_errors:extracted.delimiter_errors,errors,limits:'仅验证提取后的TeX能否被本机MathJax解析；不证明公式正确，不等同于用户的Obsidian界面验收。'};
const dest=path.join(root,'90-资源','维护','公式渲染验收.json');fs.writeFileSync(dest,JSON.stringify(report,null,2)+'\n','utf8');
console.log(JSON.stringify({total:report.total,passed,failed:errors.length}));
if (errors.length) console.log(JSON.stringify(errors.slice(0,20),null,2));
process.exitCode=errors.length?1:0;
