// A small generic MLIR module using only common upstream dialects.
module {
  func.func @add(%lhs: i32, %rhs: i32) -> i32 {
    %sum = arith.addi %lhs, %rhs : i32
    return %sum : i32
  }
}
