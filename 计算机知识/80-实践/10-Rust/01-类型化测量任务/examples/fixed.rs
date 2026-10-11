use wwl_measurement::fixed_core::FixedFir;
use wwl_measurement::{parse_codes, Fir2};
fn main() -> Result<(), Box<dyn std::error::Error>> {
    let mut state = FixedFir::default();
    let mut output = [0; 4];
    state.process_into(&[2, 4], &mut output[..2])?;
    state.process_into(&[6, 8], &mut output[2..])?;
    let owned = Fir2::default().process(parse_codes(["2", "4", "6", "8"])?);
    assert_eq!(
        output,
        owned
            .iter()
            .map(|x| x.twice_mv())
            .collect::<Vec<_>>()
            .as_slice()
    );
    println!(
        "fixed kernel: twice-mV {output:?}, previous={}",
        state.previous()
    );
    Ok(())
}
