// Expected rejection: overlapping mutable borrows, not a runtime test.
fn main() {
    let mut a=[1,2];
    let first=&mut a[0];
    let second=&mut a[1];
    *first+=1;
    *second+=1;
}
