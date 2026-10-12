//! Helpers shared by the publish subcommands (`yaml-data` and
//! `app-notification`).

pub(crate) mod pages;
pub(crate) mod probe;

use std::time::{SystemTime, UNIX_EPOCH};

/// Formats `time` as a UTC timestamp to the second, `YYYY-MM-DDTHH:MM:SSZ`
/// (what Python's `datetime.now(timezone.utc).isoformat(timespec="seconds")`
/// gives once `+00:00` is replaced by `Z`). Times before 1970 clamp to the
/// epoch.
pub(crate) fn utc_timestamp(time: SystemTime) -> String {
    let seconds = time
        .duration_since(UNIX_EPOCH)
        .map(|elapsed| elapsed.as_secs())
        .unwrap_or_default();
    let days = seconds / 86_400;
    let of_day = seconds % 86_400;
    let (year, month, day) = civil_from_days(days);
    format!(
        "{year:04}-{month:02}-{day:02}T{:02}:{:02}:{:02}Z",
        of_day / 3600,
        of_day % 3600 / 60,
        of_day % 60
    )
}

/// Converts days since 1970-01-01 to a proleptic Gregorian `(year, month,
/// day)`, using Howard Hinnant's `civil_from_days` algorithm.
fn civil_from_days(days: u64) -> (u64, u64, u64) {
    let z = days + 719_468;
    let era = z / 146_097;
    let day_of_era = z % 146_097;
    let year_of_era =
        (day_of_era - day_of_era / 1460 + day_of_era / 36_524 - day_of_era / 146_096) / 365;
    let day_of_year = day_of_era - (365 * year_of_era + year_of_era / 4 - year_of_era / 100);
    let shifted_month = (5 * day_of_year + 2) / 153;
    let day = day_of_year - (153 * shifted_month + 2) / 5 + 1;
    let month = if shifted_month < 10 {
        shifted_month + 3
    } else {
        shifted_month - 9
    };
    let year = year_of_era + era * 400 + u64::from(month <= 2);
    (year, month, day)
}

#[cfg(test)]
#[path = "publish_tests.rs"]
mod tests;
