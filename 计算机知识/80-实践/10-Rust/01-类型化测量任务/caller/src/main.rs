#[cfg(not(feature = "threaded"))]
use wwl_measurement::Fir2;
use wwl_measurement::{parse_codes, parse_config, summarize};
fn main() -> Result<(), Box<dyn std::error::Error>> {
    let batch = parse_codes(["2", "4", "6", "8"])?;
    let summary = summarize(batch.records()).unwrap();
    assert_eq!((summary.sum_mv, summary.mean_mv), (20, Some(5.0)));
    let config = parse_config("capacity=1\nbatch_size=2\nmax_samples=4\n")?;
    #[cfg(not(feature = "threaded"))]
    let output = {
        assert_eq!(config.max_samples(), 4);
        Fir2::default().process(batch)
    };
    #[cfg(feature = "threaded")]
    let output = wwl_measurement::threaded::process_threaded(
        wwl_measurement::threaded::split_batch(batch, config),
        config,
    )?;
    assert_eq!(
        output.iter().map(|v| v.twice_mv()).collect::<Vec<_>>(),
        [2, 6, 10, 14]
    );
    println!("public API: sum=20 mV mean=5 mV filtered=[1,3,5,7] mV");
    Ok(())
}
