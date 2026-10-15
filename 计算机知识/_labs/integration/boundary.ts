type User = { id: number; name: string };
function isRecord(x: unknown): x is Record<string, unknown> {
  return typeof x === "object" && x !== null && !Array.isArray(x);
}
function parseUser(x: unknown): User {
  if (!isRecord(x) || typeof x.id !== "number" || !Number.isSafeInteger(x.id) ||
      x.id < 0 || typeof x.name !== "string") throw new Error("invalid user");
  return {id: x.id, name: x.name};
}
type State<T> = {kind: "idle"} | {kind: "ready"; data: T} | {kind: "failed"; message: string};
function unreachable(x: never): never { throw new Error(`unreachable: ${String(x)}`); }
function describe(s: State<User>): string {
  switch (s.kind) {
    case "idle": return "idle";
    case "ready": return s.data.name;
    case "failed": return s.message;
    default: return unreachable(s);
  }
}
function assert(c: unknown, message: string): asserts c { if (!c) throw new Error(message); }
assert(parseUser({id: 3, name: "Ada"}).id === 3, "valid input");
for (const bad of [null, [], {id: true, name: "x"}, {id: NaN, name:"x"},
                   {id: Infinity, name:"x"}, {id: 1.5, name:"x"}, {id: -1, name:"x"},
                   {id: 2}, {id: 2, name: 7}]) {
  let rejected = false;
  try { parseUser(bad); } catch { rejected = true; }
  assert(rejected, "invalid input accepted");
}
assert(describe({kind:"ready", data:{id:1,name:"Ada"}}) === "Ada", "state narrowing");
if (false) {
  // This is a compile-time regression test, not an executable failure.
  // @ts-expect-error A ready state must carry its data.
  const badState: State<User> = {kind:"ready"};
  void badState;
}
console.log("TypeScript boundary and state tests passed");
