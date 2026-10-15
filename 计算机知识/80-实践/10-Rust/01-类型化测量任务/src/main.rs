use std::env;
use std::fs::File;
use std::io::{self, BufReader, BufWriter};
use std::path::{Path, PathBuf};
use std::process::ExitCode;
use wwl_measurement::{parse_codes, read_codes, read_config, InputError, TaskConfig};
fn open(path: &Path) -> io::Result<File> {
    File::open(path)
        .map_err(|error| io::Error::new(error.kind(), format!("open {}: {error}", path.display())))
}
fn run() -> Result<(), Box<dyn std::error::Error>> {
    let mut args = env::args_os().skip(1);
    let mut config_path = None;
    let mut file_path = None;
    let mut codes = None;
    let mut threaded = false;
    while let Some(flag) = args.next() {
        if flag == "--config" {
            if config_path.is_some() {
                return Err("duplicate --config".into());
            }
            config_path = Some(PathBuf::from(
                args.next().ok_or("--config requires a path")?,
            ));
        } else if flag == "--threaded" {
            if threaded {
                return Err("duplicate --threaded".into());
            }
            threaded = true;
        } else if flag == "--file" {
            if file_path.is_some() || codes.is_some() {
                return Err("duplicate input selection".into());
            }
            file_path = Some(PathBuf::from(args.next().ok_or("--file requires a path")?));
        } else if flag == "--codes" {
            if file_path.is_some() || codes.is_some() {
                return Err("duplicate input selection".into());
            }
            let mut tokens = Vec::new();
            for arg in args.by_ref() {
                if tokens.len() == wwl_measurement::MAX_SAMPLES {
                    return Err(InputError::TooMany {
                        limit: wwl_measurement::MAX_SAMPLES,
                    }
                    .into());
                }
                tokens.push(arg.into_string().map_err(|_| "code is not Unicode")?);
            }
            codes = Some(tokens); // --codes consumes the rest; flags must precede it
        } else {
            return Err("usage: wwl-measurement [--config PATH] [--threaded] [--file PATH | --codes CODE ...]".into());
        }
    }
    #[cfg(not(feature = "threaded"))]
    if threaded {
        return Err(
            "--threaded requires build feature: cargo run --features threaded -- ...".into(),
        );
    }
    let config = match config_path {
        Some(path) => read_config(open(&path)?)?,
        None => TaskConfig::default(),
    };
    let batch = match (file_path, codes) {
        (Some(path), None) => read_codes(BufReader::new(open(&path)?))?,
        (None, Some(tokens)) => parse_codes(tokens)?,
        (None, None) => parse_codes(["2", "4", "6", "8"])?,
        _ => unreachable!("input choices were validated"),
    };
    if batch.records().len() > config.max_samples() {
        return Err(InputError::TooMany {
            limit: config.max_samples(),
        }
        .into());
    }
    #[cfg(feature = "threaded")]
    if threaded {
        use wwl_measurement::threaded::{process_threaded, split_batch};
        use wwl_measurement::{summarize, write_summary_report};
        let summary = summarize(batch.records())?;
        let output = process_threaded(split_batch(batch, config), config)?;
        write_summary_report(BufWriter::new(io::stdout().lock()), &summary, &output)?;
        return Ok(());
    }
    wwl_measurement::write_report(BufWriter::new(io::stdout().lock()), &batch)?;
    Ok(())
}
fn main() -> ExitCode {
    match run() {
        Ok(()) => ExitCode::SUCCESS,
        Err(error) => {
            eprintln!("error: {error}");
            ExitCode::from(2)
        }
    }
}
