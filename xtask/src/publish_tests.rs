use super::*;
use std::time::Duration;

fn at(seconds: u64) -> String {
    utc_timestamp(UNIX_EPOCH + Duration::from_secs(seconds))
}

#[test]
fn utc_timestamp_formats_known_instants() {
    assert_eq!(at(0), "1970-01-01T00:00:00Z");
    // 2000-02-29 (leap day in a century leap year) 12:34:56.
    assert_eq!(at(951_827_696), "2000-02-29T12:34:56Z");
    // 2026-10-11T23:59:59Z
    assert_eq!(at(1_791_763_199), "2026-10-11T23:59:59Z");
    // 2100-03-01, the day after a skipped (non-leap) century Feb 28.
    assert_eq!(at(4_107_542_400), "2100-03-01T00:00:00Z");
}

#[test]
fn utc_timestamp_clamps_times_before_the_epoch() {
    assert_eq!(
        utc_timestamp(UNIX_EPOCH - Duration::from_secs(10)),
        "1970-01-01T00:00:00Z"
    );
}
