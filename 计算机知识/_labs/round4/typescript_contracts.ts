type Wrap<T> = T extends string ? { text: T } : { value: T };
type A = Wrap<"a" | 7>;
// { text: "a" } | { value: 7 }

type Whole<T> = [T] extends [string] ? true : false;
type B = Whole<"a" | 7>; // false

type IsNever<T> = [T] extends [never] ? true : false;
type N1 = IsNever<never>;  // true
type N2 = IsNever<string>; // false

type Item<T> = T extends readonly (infer E)[] ? E : never;
type Return<T> = T extends (...args: never[]) => infer R ? R : never;
type I = Item<readonly [1, "x"]>; // 1 | "x"

type Settings = { theme?: "light" | "dark" };
const a: Settings = {};
const b: Settings = { theme: "dark" };
// exactOptionalPropertyTypes 开启时，下面应被拒绝：
// const c: Settings = { theme: undefined };

const counts: Record<string, number> = {};
const x = counts["missing"];
// 开启 noUncheckedIndexedAccess 后，x 为 number | undefined。

type Order = { id: string; cents: number };
type Result<T> = { ok: true; value: T } | { ok: false; error: string };

function parseOrder(value: unknown): Result<Order> {
  if (typeof value !== "object" || value === null || Array.isArray(value)) {
    return { ok: false, error: "expected object" };
  }
  if (!("id" in value) || !("cents" in value)) {
    return { ok: false, error: "missing field" };
  }
  const id = value.id;
  const cents = value.cents;
  if (typeof id !== "string" || !/^[A-Za-z0-9_-]{1,40}$/.test(id)) {
    return { ok: false, error: "invalid id" };
  }
  if (typeof cents !== "number" || !Number.isSafeInteger(cents) || cents < 0) {
    return { ok: false, error: "invalid cents" };
  }
  return { ok: true, value: { id, cents } };
}

type LoadState =
  | { kind: "idle" }
  | { kind: "loading"; requestId: number }
  | { kind: "ready"; requestId: number; order: Order }
  | { kind: "failed"; requestId: number; message: string };

function unreachable(value: never): never {
  throw new Error(`unexpected state: ${String(value)}`);
}

let current = 0;
let state: LoadState = { kind: "idle" };

async function load(get: () => Promise<unknown>): Promise<void> {
  const id = ++current;
  state = { kind: "loading", requestId: id };
  try {
    const parsed = parseOrder(await get());
    if (id !== current) return;
    state = parsed.ok
      ? { kind: "ready", requestId: id, order: parsed.value }
      : { kind: "failed", requestId: id, message: parsed.error };
  } catch (error: unknown) {
    if (id !== current) return;
    state = { kind: "failed", requestId: id, message: "request failed" };
  }
}

type Equal<X,Y> = (<T>() => T extends X ? 1 : 2) extends (<T>() => T extends Y ? 1 : 2) ? true : false;
type Assert<T extends true> = T;
type CheckA = Assert<Equal<A,{text:"a"}|{value:7}>>;
type CheckB = Assert<Equal<B,false>>;
type CheckNever = Assert<Equal<Wrap<never>,never>>;
type CheckIsNever = Assert<Equal<IsNever<never>,true>>;
type CheckItem = Assert<Equal<I,1|"x">>;
type CheckIndex = Assert<Equal<typeof x,number|undefined>>;
// @ts-expect-error exactOptionalPropertyTypes rejects a present undefined value.
const invalidSettings: Settings = {theme:undefined};
// @ts-expect-error unchecked indexed access may produce undefined.
const unsafeCount: number = counts["missing"];
// @ts-expect-error never has no ordinary inhabitant.
const impossible: Wrap<never> = {text:"x"};
// @ts-expect-error discriminated state requires all fields of the selected variant.
const missingOrder: LoadState = {kind:"ready",requestId:1};

function check(condition: boolean, message: string): void {
  if (!condition) throw new Error(message);
}
function deferred<T>(): {promise:Promise<T>; resolve:(value:T)=>void} {
  let resolve!: (value:T)=>void;
  const promise = new Promise<T>(r => {resolve=r;});
  return {promise,resolve};
}
function readState(): LoadState {return state;}
async function run(): Promise<void> {
  for (const bad of [null, [], {}, {id:"",cents:0}, {id:"x",cents:NaN},
      {id:"x",cents:Infinity}, {id:"x",cents:-1}, {id:"x",cents:0.5},
      {id:"x",cents:9007199254740992}, {id:"x",cents:true}]) {
    check(!parseOrder(bad).ok,"invalid input accepted");
  }
  const input={id:"order_1",cents:123};
  const parsed=parseOrder(input);check(parsed.ok,"valid input rejected");
  input.cents=999;
  if(parsed.ok) check(parsed.value.cents===123,"validation result must not alias source object");
  const older=deferred<unknown>(),newer=deferred<unknown>();
  const one=load(()=>older.promise),two=load(()=>newer.promise);
  newer.resolve({id:"new",cents:2});await two;
  older.resolve({id:"old",cents:1});await one;
  const final=readState();check(final.kind==="ready" && final.order.id==="new","stale response overwrote new state");
  await load(async()=>{throw new Error("transport failure");});
  check(readState().kind==="failed","failure state not recorded");
  const pending=deferred<void>();let completed=false;
  const survivor=pending.promise.then(()=>{completed=true;});
  try {await Promise.all([Promise.reject(new Error("first failure")),survivor]);}
  catch { /* Observe the rejection without claiming it cancels the other promise. */ }
  pending.resolve(undefined);await survivor;
  check(completed,"the other promise should remain independent");
  console.log("TypeScript runtime contracts and four expected type rejections passed");
}
void run().catch(error=>{console.error(error);throw error;});
