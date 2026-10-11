use measurement_step::{make_records, process_queue, summary};
fn main() {
    let records = make_records(&[2, 4, 6, 8]).unwrap();
    println!("{:?}", summary(&records));
    println!("twice_mV={:?}", process_queue([records].into()));
}
