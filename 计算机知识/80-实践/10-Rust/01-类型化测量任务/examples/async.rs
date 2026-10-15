use wwl_measurement::{asynchronous::AsyncTask, parse_codes, threaded::split_batch, TaskConfig};
fn main() -> Result<(), Box<dyn std::error::Error>> {
    let runtime = tokio::runtime::Builder::new_current_thread().build()?;
    runtime.block_on(async {
        let config = TaskConfig::try_new(1, 2, 4)?;
        let mut task = AsyncTask::start(config)?;
        for batch in split_batch(parse_codes(["2", "4", "6", "8"])?, config) {
            task.send(batch).await?;
        }
        let output = task.finish().await?;
        let values: Vec<_> = output.iter().map(|x| x.twice_mv()).collect();
        assert_eq!(values, [2, 6, 10, 14]);
        println!("async twice_mV={values:?}; worker completion observed");
        Ok::<(), Box<dyn std::error::Error>>(())
    })
}
