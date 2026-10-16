/** Native CDP checks: new finite target/choice materials, no human timing claims. */
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
async function state(page){return page.evaluate(`({...hciTarget.snapshot(),focus:document.activeElement.id,status:document.getElementById('status').textContent,task:document.getElementById('task').textContent,bookings:document.querySelectorAll('#bookings li').length,confirmDisabled:document.getElementById('confirm').disabled})`);}
async function clickCenter(page,id){await page.evaluate(`document.getElementById(${JSON.stringify(id)}).scrollIntoView({block:'nearest',inline:'nearest'});`);const p=await page.evaluate(`(()=>{const r=document.getElementById(${JSON.stringify(id)}).getBoundingClientRect();return {x:r.x+r.width/2,y:r.y+r.height/2};})()`);await page.send('Input.dispatchMouseEvent',{type:'mouseMoved',...p});await page.send('Input.dispatchMouseEvent',{type:'mousePressed',button:'left',clickCount:1,...p});await page.send('Input.dispatchMouseEvent',{type:'mouseReleased',button:'left',clickCount:1,...p});}
try{
 const portText=await until(async()=>readFile(path.join(profile,'DevToolsActivePort'),'utf8'));
 const [port,browserPath]=portText.trim().split('\n');
 browser=new CDP(`ws://127.0.0.1:${port}${browserPath}`);await browser.open();report.version=await browser.send('Browser.getVersion');
 async function open(params){
  const url=pathToFileURL(path.join(root,'prototype.html'));for(const [k,v] of Object.entries(params))url.searchParams.set(k,String(v));
  const target=await (await fetch(`http://127.0.0.1:${port}/json/new?${encodeURIComponent(url.href)}`,{method:'PUT'})).json();
  const page=new CDP(target.webSocketDebuggerUrl);pages.push(page);await page.open();await page.send('Page.enable');await page.send('Runtime.enable');await page.send('Accessibility.enable');
  await page.send('Emulation.setDeviceMetricsOverride',{width:1024,height:1000,deviceScaleFactor:1,mobile:false});
  await until(async()=>page.evaluate('document.readyState==="complete"&&typeof hciTarget!=="undefined"'));await page.evaluate('document.fonts.ready.then(()=>true)');return page;
 }
 report.conditions=[];
 for(const width of [64,128])for(const n of [2,4,8])for(const cue of ['brief','explicit']){
  const id=`w${width}-n${n}-${cue}`;const page=await open({width,n,cue,target:0});let s=await state(page);
  check(`${id} valid idle`,[s.configOK,s.phase,s.selected,s.created,s.bookings],[true,'idle',null,null,1]);
  check(`${id} count`,s.targets.length,n);check(`${id} exact width`,s.targets.map(t=>t.width),Array(n).fill(width));
  check(`${id} same height`,s.targets.map(t=>t.height),Array(n).fill(44));check(`${id} before start disabled`,s.targets.every(t=>t.disabled),true);
  const initialGeometry=await page.evaluate(`(()=>{const a=document.getElementById('startTrial').getBoundingClientRect(),b=document.getElementById('slot0').getBoundingClientRect();return {origin:[a.x+a.width/2,a.y+a.height/2],target:[b.x+b.width/2,b.y+b.height/2]};})()`);
  check(`${id} first target horizontal centers`,initialGeometry.origin[1],initialGeometry.target[1]);
  await clickCenter(page,'startTrial');s=await state(page);check(`${id} starts without creating`,[s.phase,s.created,s.bookings],['choosing',null,1]);check(`${id} pointer origin within event quantization`,Math.max(...s.trial.origin.map((v,i)=>Math.abs(v-initialGeometry.origin[i])))<=1,true);
  await clickCenter(page,'slot1');s=await state(page);check(`${id} selection is not creation`,[s.phase,s.selected,s.created,s.bookings],['selected',1,null,1]);
  check(`${id} cue text only`,s.status,cue==='brief'?'已选择。':'已选择630–660分钟，尚未创建；请确认创建。');
  check(`${id} only selected pressed`,s.targets.filter(t=>t.pressed==='true').map(t=>t.index),[1]);
  await clickCenter(page,'confirm');s=await state(page);check(`${id} wrong confirmation rejects`,[s.phase,s.created,s.bookings,s.focus],['selected',null,1,'slot1']);
  check(`${id} wrong feedback`,s.status,'未创建：所选时段不符任务，请重新选择。');
  await clickCenter(page,'slot0');await clickCenter(page,'confirm');s=await state(page);check(`${id} correct creates once`,[s.phase,s.created,s.bookings,s.focus],['confirmed',0,2,'restart']);
  check(`${id} confirmed disabled`,s.targets.every(t=>t.disabled)&&s.confirmDisabled,true);
  await clickCenter(page,'cancel');s=await state(page);check(`${id} cancel preserves existing`,[s.phase,s.created,s.bookings,s.focus],['idle',null,1,'startTrial']);
  report.conditions.push({id,params:{width,n,cue,target:0},geometry:initialGeometry,events:s.events});
  await browser.send('Target.closeTarget',{targetId:(await page.send('Target.getTargetInfo')).targetInfo.targetId});page.close();
 }
 for(const cue of ['brief','explicit']){
  const page=await open({width:128,n:4,cue,target:0});check(`${cue} initial keyboard focus`,(await state(page)).focus,'startTrial');
  await key(page,'Enter');check(`${cue} keyboard starts without pointer origin`,[(await state(page)).phase,(await state(page)).trial.origin],['choosing',null]);
  await key(page,'Tab');check(`${cue} Tab to first slot`,(await state(page)).focus,'slot0');
  await key(page,'Tab');check(`${cue} Tab to second slot`,(await state(page)).focus,'slot1');await key(page,'Tab',8);check(`${cue} ShiftTab back`,(await state(page)).focus,'slot0');
  check(`${cue} visible focus`,await page.evaluate('getComputedStyle(document.activeElement).outlineWidth'),'3px');
  await key(page,'Enter');check(`${cue} Enter select only`,[(await state(page)).phase,(await state(page)).created],['selected',null]);
  for(let i=0;i<4;i++)await key(page,'Tab');check(`${cue} confirm reachable`,(await state(page)).focus,'confirm');
  await key(page,'Enter');check(`${cue} Enter confirmation`,[(await state(page)).phase,(await state(page)).bookings],['confirmed',2]);
  await key(page,'Enter');check(`${cue} Enter restart`,[(await state(page)).phase,(await state(page)).bookings],['idle',1]);
  await key(page,'Enter');await key(page,'Tab');await key(page,'Enter');
  const ax=await page.send('Accessibility.getFullAXTree');const named=ax.nodes.filter(a=>!a.ignored&&['button','status','group'].includes(a.role?.value)).map(a=>({role:a.role.value,name:a.name?.value,properties:a.properties}));
  check(`${cue} AX target full name`,named.some(a=>a.role==='button'&&a.name==='选择600–630分钟'),true);check(`${cue} AX status`,named.some(a=>a.role==='status'),true);
  report.variants[cue]={ax:named,selected:await state(page)};
  await writeFile(path.join(output,`selected-${cue}.png`),Buffer.from((await page.send('Page.captureScreenshot',{format:'png'})).data,'base64'));
  await page.send('Emulation.setDeviceMetricsOverride',{width:375,height:1000,deviceScaleFactor:1,mobile:false});
  check(`${cue} 375 no horizontal overflow`,await page.evaluate('document.documentElement.scrollWidth<=innerWidth'),true);
  check(`${cue} 375 hitbox width`,(await state(page)).targets[0].width,128);
  await writeFile(path.join(output,`selected-${cue}-375.png`),Buffer.from((await page.send('Page.captureScreenshot',{format:'png',captureBeyondViewport:true})).data,'base64'));
 }
 for(const params of [{width:63,n:4,cue:'explicit',target:0},{width:64,n:3,cue:'explicit',target:0},{width:64,n:2,cue:'explicit',target:2},{width:64,n:2,cue:'other',target:0},{width:64,n:2,cue:'explicit',target:'NaN'},{}]){
  const page=await open(params);const s=await state(page);check(`invalid ${JSON.stringify(params)} fails closed`,[s.configOK,s.phase,s.created,s.bookings,s.targets.length,s.confirmDisabled],[false,'idle',null,1,0,true]);
 }
 report.check_count=report.checks.length;
 await writeFile(path.join(output,'browser-results.json'),JSON.stringify(report,null,2)+'\n');console.log(JSON.stringify({check_count:report.check_count,version:report.version.product,output}));
}finally{
 for(const p of pages)p.close();
 if(browser){try{await Promise.race([browser.send('Browser.close'),pause(2000)]);}catch{}browser.close();}
 if(child.exitCode===null){child.kill('SIGTERM');await Promise.race([new Promise(r=>child.once('exit',r)),pause(2000)]);}
 if(child.exitCode===null)child.kill('SIGKILL');
 await writeFile(path.join(output,'chrome-stderr.txt'),stderr);await rm(profile,{recursive:true,force:true});
}
