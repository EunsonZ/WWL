// Rust 2021 edition, std only. Run: rustc --edition=2021 --test ownership.rs -o test_rs
#[derive(Debug, PartialEq)]
enum ReadError { Empty, OutOfRange }
fn parse_reading(s: &str) -> Result<u32, ReadError> {
    if s.is_empty() { return Err(ReadError::Empty); }
    let n: u32 = s.parse().map_err(|_| ReadError::OutOfRange)?;
    if n > 1000 { return Err(ReadError::OutOfRange); }
    Ok(n)
}
fn checked_total(xs: &[u32]) -> Option<u32> {
    xs.iter().try_fold(0u32, |acc, &x| acc.checked_add(x))
}
#[test]
fn parsing_contract() {
    assert_eq!(parse_reading("0"), Ok(0));
    assert_eq!(parse_reading("1000"), Ok(1000));
    assert_eq!(parse_reading("1001"), Err(ReadError::OutOfRange));
    assert_eq!(parse_reading(""), Err(ReadError::Empty));
}
#[test]
fn overflow_is_explicit() {
    assert_eq!(checked_total(&[1,2,3]), Some(6));
    assert_eq!(checked_total(&[u32::MAX,1]), None);
}
#[test]
fn borrow_then_mutate() {
    let mut v = vec![1,2,3];
    let first = &v[0];
    assert_eq!(*first,1); // last use ends this borrow
    v.push(4);
    assert_eq!(v,vec![1,2,3,4]);
}
#[test]
fn scoped_threads() {
    let values = [1,2,3,4];
    let sum = std::thread::scope(|scope| {
        let left = scope.spawn(|| values[..2].iter().sum::<i32>());
        let right = scope.spawn(|| values[2..].iter().sum::<i32>());
        left.join().unwrap() + right.join().unwrap()
    });
    assert_eq!(sum,10);
}
