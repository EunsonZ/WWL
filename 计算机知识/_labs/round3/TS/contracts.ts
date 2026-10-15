type Reading = Readonly<{value:number}>;
type Result<T> = {ok:true;value:T}|{ok:false;error:string};
function parseReading(x:unknown):Result<Reading>{
    if(typeof x!=="object" || x===null || !("value" in x))return {ok:false,error:"shape"};
    const n=x.value;
    if(typeof n!=="number" || !Number.isInteger(n) || n<0 || n>1000)
        return {ok:false,error:"range"};
    return {ok:true,value:{value:n}};
}
function check(b:boolean,label:string):void{if(!b)throw new Error(label);}
for(const x of [null,true,{}, {value:true},{value:NaN},{value:Infinity},{value:-1},{value:1001}])
    check(!parseReading(x).ok,"must reject invalid data");
for(const x of [{value:0},{value:1000}])check(parseReading(x).ok,"valid boundary");
const trace:string[]=[];
trace.push("sync");
Promise.resolve().then(()=>trace.push("micro"));
setTimeout(()=>{
    check(trace.join(',')==='sync,end,micro','task/microtask ordering');
    console.log("PASS: strict runtime boundary + current task before Promise job");
},0);
trace.push("end");
