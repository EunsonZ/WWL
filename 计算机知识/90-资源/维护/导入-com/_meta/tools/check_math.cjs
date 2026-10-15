// Requires mathjax-full. Does not download assets or execute notebook examples.
const fs = require('fs');
const {mathjax}=require('mathjax-full/js/mathjax.js');
const {TeX}=require('mathjax-full/js/input/tex.js');
const {SVG}=require('mathjax-full/js/output/svg.js');
const {liteAdaptor}=require('mathjax-full/js/adaptors/liteAdaptor.js');
const {RegisterHTMLHandler}=require('mathjax-full/js/handlers/html.js');
const {AllPackages}=require('mathjax-full/js/input/tex/AllPackages.js');
if(process.argv.length<4){console.error('Usage: node check_math.cjs expressions.json output.json');process.exit(2);}
const input=JSON.parse(fs.readFileSync(process.argv[2],'utf8'));
const adaptor=liteAdaptor();RegisterHTMLHandler(adaptor);
const tex=new TeX({packages:AllPackages.filter(x=>!['noerrors','noundefined'].includes(x)),formatError:(jax,error)=>{throw error;}});
const document=mathjax.document('',{InputJax:tex,OutputJax:new SVG({fontCache:'none'})});
const errors=[];let passed=0;
for(const item of input.expressions){
 try {
  const node=document.convert(item.tex,{display:item.display});
  const xml=adaptor.outerHTML(node);
  if(xml.includes('data-mjx-error')||xml.includes('data-mml-node="merror"')) errors.push({...item,error:'MathJax merror output'});
  else passed++;
 } catch(e){errors.push({...item,error:String(e.message||e)});}
}
const result={engine:'mathjax-full',version:require('mathjax-full/package.json').version,total:input.expressions.length,passed,errors,delimiter_review:input.delimiter_review,scope:'LaTeX syntax conversion only; no proof or semantic verification.'};
fs.writeFileSync(process.argv[3],JSON.stringify(result,null,2));
console.log(JSON.stringify({total:result.total,passed,errors:errors.length,delimiter_review:input.delimiter_review.length}));
