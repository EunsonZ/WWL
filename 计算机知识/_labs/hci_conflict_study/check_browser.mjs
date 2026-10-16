/** Native CDP checks of the two finite fixtures. No participant or screen-reader claims. */
import {spawn} from 'node:child_process';
import {mkdtemp,readFile,writeFile,mkdir,rm} from 'node:fs/promises';
import {tmpdir} from 'node:os';
import path from 'node:path';
import {fileURLToPath,pathToFileURL} from 'node:url';
import assert from 'node:assert/strict';
const root=path.dirname(fileURLToPath(import.meta.url));
const output=process.argv[2];
if(!output)throw new Error('usage: node check_browser.mjs NEW_OUTPUT_DIRECTORY');
await mkdir(output,{recursive:false});
const profile=await mkdtemp(path.join(tmpdir(),'wwl-hci-cdp-'));
const chrome=process.env.CHROME_BINARY || '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome';
const child=spawn(chrome,['--headless=new','--disable-gpu','--no-first-run','--no-default-browser-check',
  '--use-mock-keychain','--password-store=basic','--disable-background-networking','--disable-component-update','--disable-sync','--renderer-process-limit=1',
  '--remote-debugging-address=127.0.0.1','--remote-debugging-port=0',`--user-data-dir=${profile}`,'about:blank'],
  {stdio:['ignore','ignore','pipe']});
let stderr='';child.stderr.on('data',d=>{stderr+=d.toString();});
const pause=ms=>new Promise(r=>setTimeout(r,ms));
async function until(fn){let last;for(let i=0;i<500;i++){try{last=await fn();if(last)return last;}catch{}await pause(30);}throw new Error('bounded readiness check failed');}
class CDP{
 constructor(url){this.ws=new WebSocket(url);this.id=0;this.pending=new Map();this.ws.addEventListener('message',event=>{const m=JSON.parse(event.data);if(m.id){const p=this.pending.get(m.id);if(p){this.pending.delete(m.id);m.error?p.reject(new Error(JSON.stringify(m.error))):p.resolve(m.result);}}});}
 async open(){await new Promise((resolve,reject)=>{this.ws.addEventListener('open',resolve,{once:true});this.ws.addEventListener('error',reject,{once:true});});}
 send(method,params={}){const id=++this.id;return new Promise((resolve,reject)=>{this.pending.set(id,{resolve,reject});this.ws.send(JSON.stringify({id,method,params}));});}
 async evaluate(expression){const r=await this.send('Runtime.evaluate',{expression,returnByValue:true,awaitPromise:true});if(r.exceptionDetails)throw new Error(JSON.stringify(r.exceptionDetails));return r.result.value;}
 close(){this.ws.close();}
}
let browser;
const pages=[];
const report={identity:'Actual headless-browser automation on synthetic local task; no human participants or AT audio',checks:[],variants:{}};
function check(name,actual,expected){assert.deepEqual(actual,expected,name);report.checks.push({name,actual,expected});}
async function key(page,key,modifiers=0){await page.send('Input.dispatchKeyEvent',{type:'keyDown',key,code:key==='Tab'?'Tab':key,windowsVirtualKeyCode:key==='Tab'?9:13,nativeVirtualKeyCode:key==='Tab'?9:13,modifiers,text:key==='Enter'?'\r':undefined,unmodifiedText:key==='Enter'?'\r':undefined});await page.send('Input.dispatchKeyEvent',{type:'keyUp',key,code:key==='Tab'?'Tab':key,windowsVirtualKeyCode:key==='Tab'?9:13,nativeVirtualKeyCode:key==='Tab'?9:13,modifiers});}
async function fill(page,id,text){await page.evaluate(`document.getElementById(${JSON.stringify(id)}).focus();document.getElementById(${JSON.stringify(id)}).select();`);await page.send('Input.insertText',{text});}
async function state(page){return page.evaluate(`({...hciLab.snapshot(),focus:document.activeElement.id||document.activeElement.textContent,result:document.getElementById('result').textContent,invalid:[document.getElementById('start').getAttribute('aria-invalid'),document.getElementById('end').getAttribute('aria-invalid')],statusRole:document.getElementById('result').getAttribute('role'),positiveTabindex:document.querySelectorAll('[tabindex]:not([tabindex="0"]):not([tabindex="-1"])').length})`);}
try{
 const portText=await until(async()=>{const s=await readFile(path.join(profile,'DevToolsActivePort'),'utf8');return s;});
 const [port,browserPath]=portText.trim().split('\n');
 browser=new CDP(`ws://127.0.0.1:${port}${browserPath}`);await browser.open();
 report.version=await browser.send('Browser.getVersion');
 for(const variant of ['A','B']){
  const url=pathToFileURL(path.join(root,'prototype.html'));url.searchParams.set('variant',variant);url.searchParams.set('stage','conflict');
  const target=await (await fetch(`http://127.0.0.1:${port}/json/new?${encodeURIComponent(url.href)}`,{method:'PUT'})).json();
  const page=new CDP(target.webSocketDebuggerUrl);pages.push(page);await page.open();
  await page.send('Page.enable');await page.send('Runtime.enable');await page.send('Accessibility.enable');
  await page.send('Emulation.setDeviceMetricsOverride',{width:1024,height:900,deviceScaleFactor:1,mobile:false});
  await until(async()=>page.evaluate('document.readyState==="complete" && typeof hciLab!=="undefined"'));
  await page.evaluate('document.fonts.ready.then(()=>true)');
  const initial=await state(page);
  check(`${variant} initial conflict active count`,initial.active.length,1);
  check(`${variant} initial values`,initial.fields,variant==='A'?['','']:['570','600']);
  check(`${variant} initial focus`,initial.focus,'start');
  check(`${variant} identical conflict message`,initial.result,'未创建：该时间与活动预约重叠，请修改开始或结束。');
  check(`${variant} no positive tabindex`,initial.positiveTabindex,0);
  const ax=await page.send('Accessibility.getFullAXTree');
  const selected=ax.nodes.filter(n=>!n.ignored && ['spinbutton','button','status'].includes(n.role?.value)).map(n=>({role:n.role.value,name:n.name?.value,properties:n.properties}));
  check(`${variant} AX start name`,selected.some(n=>n.role==='spinbutton'&&n.name==='开始分钟'),true);
  check(`${variant} AX end name`,selected.some(n=>n.role==='spinbutton'&&n.name==='结束分钟'),true);
  check(`${variant} AX status exists`,selected.some(n=>n.role==='status'),true);
  report.variants[variant]={initial,ax:selected};
  await writeFile(path.join(output,`conflict-${variant}.png`),Buffer.from((await page.send('Page.captureScreenshot',{format:'png'})).data,'base64'));
  await key(page,'Tab');check(`${variant} Tab start to end`,(await state(page)).focus,'end');
  await key(page,'Tab',8);check(`${variant} ShiftTab end to start`,(await state(page)).focus,'start');
  const outline=await page.evaluate('getComputedStyle(document.activeElement).outlineWidth');
  check(`${variant} keyboard visible outline`,outline,'3px');
  await fill(page,'start','600');await key(page,'Tab');await fill(page,'end','630');
  await key(page,'Tab');check(`${variant} Tab end to create`,(await state(page)).focus,'create');
  await key(page,'Enter');const success=await state(page);check(`${variant} Enter creates adjacent slot`,success.active.map(x=>[x.start,x.end]),[[540,600],[600,630]]);
  check(`${variant} success result`,success.result,'已创建预约2：600–630分钟。');
  await key(page,'Tab');await key(page,'Tab');check(`${variant} cancel reachable`,(await state(page)).focus,'取消预约2');
  await key(page,'Enter');check(`${variant} cancel releases and returns focus`,[(await state(page)).active.length,(await state(page)).focus],[1,'start']);
  await fill(page,'start','600');await fill(page,'end','629');await page.evaluate('document.getElementById("create").focus()');await key(page,'Enter');
  const invalid=await state(page);check(`${variant} invalid duration retains input`,invalid.fields,['600','629']);check(`${variant} invalid duration focus`,invalid.focus,'end');check(`${variant} invalid field flag`,invalid.invalid,[null,'true']);
  await fill(page,'start','570');await fill(page,'end','600');await page.evaluate('document.getElementById("create").focus()');await key(page,'Enter');
  const conflict=await state(page);check(`${variant} repeated conflict never creates`,conflict.active.length,1);check(`${variant} repeated conflict manipulation`,conflict.fields,variant==='A'?['','']:['570','600']);
  report.variants[variant].repeatedConflict=conflict;
  if(variant==='B'){
   await page.send('Emulation.setDeviceMetricsOverride',{width:375,height:812,deviceScaleFactor:1,mobile:false});
   check('B 375px no horizontal document overflow',await page.evaluate('document.documentElement.scrollWidth<=innerWidth'),true);
   await writeFile(path.join(output,'conflict-B-375.png'),Buffer.from((await page.send('Page.captureScreenshot',{format:'png',captureBeyondViewport:true})).data,'base64'));
  }
 }
 report.check_count=report.checks.length;
 await writeFile(path.join(output,'browser-results.json'),JSON.stringify(report,null,2)+'\n');
 console.log(JSON.stringify({check_count:report.check_count,version:report.version.product,output}));
}finally{
 for(const p of pages)p.close();
 if(browser){try{await browser.send('Browser.close');}catch{}browser.close();}
 if(child.exitCode===null){child.kill('SIGTERM');await Promise.race([new Promise(r=>child.once('exit',r)),pause(2000)]);}
 if(child.exitCode===null)child.kill('SIGKILL');
 await writeFile(path.join(output,'chrome-stderr.txt'),stderr);
 await rm(profile,{recursive:true,force:true});
}
