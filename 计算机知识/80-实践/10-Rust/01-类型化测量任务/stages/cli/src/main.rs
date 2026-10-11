use measurement_step::{read_codes, write_report};
fn main() {
    let result = read_codes(std::io::stdin().lock())
        .and_then(|records| write_report(std::io::stdout().lock(), &records));
    if let Err(error) = result {
        eprintln!("measurement: {error}");
        std::process::exit(2);
    }
}
