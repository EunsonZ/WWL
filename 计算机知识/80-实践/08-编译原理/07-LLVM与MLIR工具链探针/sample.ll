; A deliberately small target-neutral LLVM IR input: it intentionally omits
; target triple/data layout; the probe supplies and records its codegen target.
define i32 @add(i32 %lhs, i32 %rhs) {
entry:
  %sum = add i32 %lhs, %rhs
  ret i32 %sum
}

define i32 @main() {
entry:
  %answer = call i32 @add(i32 20, i32 22)
  %ok = icmp eq i32 %answer, 42
  %status = select i1 %ok, i32 0, i32 1
  ret i32 %status
}
