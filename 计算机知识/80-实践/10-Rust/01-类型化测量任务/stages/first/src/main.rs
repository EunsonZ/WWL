#[derive(Debug, PartialEq)]
enum Level {
    Low,
    Normal,
    High,
}
fn classify(code: i32) -> Result<Level, &'static str> {
    if !(0..=4095).contains(&code) {
        return Err("code outside 0..4095");
    }
    Ok(match code {
        0..=3 => Level::Low,
        4..=6 => Level::Normal,
        _ => Level::High,
    })
}
fn main() {
    let codes = [2, 4, 6, 8];
    let mut sum = 0;
    for code in codes {
        match classify(code) {
            Ok(level) => {
                println!("{code}: {level:?}");
                sum += code;
            }
            Err(error) => println!("{code}: {error}"),
        }
    }
    let result = (sum, f64::from(sum) / codes.len() as f64);
    println!("sum={} mean={}", result.0, result.1);
}
#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn boundaries() {
        assert_eq!(classify(3), Ok(Level::Low));
        assert_eq!(classify(4), Ok(Level::Normal));
        assert_eq!(classify(6), Ok(Level::Normal));
        assert_eq!(classify(7), Ok(Level::High));
        assert!(classify(-1).is_err());
        assert!(classify(4096).is_err());
    }
}
