fn select<'a>(x: &'a str, y: &'a str, first: bool) -> &'a str {
    if first { x } else { y }
}

fn add_pair(xs: &mut [i32], i: usize, j: usize) -> Result<(), &'static str> {
    if i >= xs.len() || j >= xs.len() || i == j { return Err("bad indices"); }
    let (lo, hi) = if i < j { (i, j) } else { (j, i) };
    let (left, right) = xs.split_at_mut(hi);
    left[lo] += 1;
    right[0] += 1;
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::{cell::Cell, future::Future, marker::PhantomPinned, pin::Pin,
        rc::Rc, task::{Context,Poll}};
    #[test]
    fn reborrow_and_split() {
        let mut number=10;
        let outer=&mut number;
        { let inner=&mut *outer; *inner+=5; }
        *outer+=1;
        assert_eq!(number,16);
        let mut values=[1,2,3];
        assert_eq!(add_pair(&mut values,0,2),Ok(()));
        assert_eq!(values,[2,2,4]);
        assert!(add_pair(&mut values,1,1).is_err());
        assert!(add_pair(&mut values,0,9).is_err());
        assert_eq!(select("left","right",true),"left");
    }
    struct Pinned { value:i32, _pin:PhantomPinned }
    #[test]
    fn moving_pin_handle_keeps_box_pointee() {
        let owner=Box::pin(Pinned{value:7,_pin:PhantomPinned});
        let before=owner.as_ref().get_ref() as *const Pinned;
        let moved_owner=owner;
        assert_eq!(before,moved_owner.as_ref().get_ref() as *const Pinned);
        assert_eq!(moved_owner.as_ref().get_ref().value,7);
    }
    struct PendingWork(Rc<Cell<bool>>);
    impl Future for PendingWork {
        type Output=();
        fn poll(self:Pin<&mut Self>,_:&mut Context<'_>)->Poll<()> { Poll::Pending }
    }
    impl Drop for PendingWork { fn drop(&mut self){self.0.set(true);} }
    #[test]
    fn dropping_owned_future_runs_synchronous_drop() {
        let flag=Rc::new(Cell::new(false));
        let work=PendingWork(flag.clone());
        assert!(!flag.get());drop(work);assert!(flag.get());
        // This does not exercise Tokio JoinHandle or asynchronous cleanup.
    }
}
