// Intentionally rejected: mutation while an immutable borrow is used later.
fn main() {
    let mut v=vec![1,2];
    let first=&v[0];
    v.push(3);
    println!("{}", first);
}
