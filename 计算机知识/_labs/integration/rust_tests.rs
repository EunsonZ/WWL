// Rust standard library only; run with rustc --edition=2021 --test.
fn first<T>(xs: &[T]) -> Option<&T> { xs.first() }
fn sum_checked(xs: &[u32]) -> Option<u32> {
    xs.iter().try_fold(0_u32, |acc, x| acc.checked_add(*x))
}
#[test]
fn borrowing_views() { let v = vec![3,4]; assert_eq!(first(&v), Some(&3)); assert_eq!(first::<i32>(&[]), None); }
#[test]
fn checked_arithmetic() { assert_eq!(sum_checked(&[2,3]), Some(5)); assert_eq!(sum_checked(&[u32::MAX,1]), None); }
#[test]
fn unicode_boundaries() { let s = "你a"; assert_eq!(s.chars().count(), 2); assert_eq!(s.len(), 4); assert!(s.get(..1).is_none()); assert_eq!(s.get(..3), Some("你")); }
#[test]
fn weak_reference_does_not_own() {
    use std::rc::Rc;
    let owner = Rc::new(7); let weak = Rc::downgrade(&owner);
    assert_eq!(*weak.upgrade().unwrap(), 7); drop(owner); assert!(weak.upgrade().is_none());
}
#[test]
fn mutex_protects_whole_update() {
    use std::sync::{Arc,Mutex};
    let count = Arc::new(Mutex::new(0));
    let workers: Vec<_> = (0..4).map(|_| { let c=Arc::clone(&count); std::thread::spawn(move || { for _ in 0..100 { *c.lock().unwrap() += 1; } }) }).collect();
    for w in workers { w.join().unwrap(); }
    assert_eq!(*count.lock().unwrap(), 400);
}
#[test]
fn result_propagation() {
    fn parse(s: &str) -> Result<u32, std::num::ParseIntError> { let n=s.parse::<u32>()?; Ok(n) }
    assert_eq!(parse("12").unwrap(), 12); assert!(parse("-1").is_err());
}
