use classic_shared_core::get_runtime;
use classic_update_core::{Classification, NotificationStatus, check_app_notification};

use super::{App, AsyncMessage};

impl App {
    pub fn check_updates(&mut self) {
        if self.update_checking {
            return;
        }
        self.update_checking = true;
        self.scan_status = "Checking for updates...".to_string();
        self.scan_progress = -1.0;

        let tx = self.async_tx.clone();

        // `CLASSIC_APP_VERSION` is baked at build time by `build.rs`,
        // which reads `CLASSIC_Info.version` directly from
        // `CLASSIC Main.yaml` (the install-immutable source of truth) and
        // verifies it matches `Cargo.toml`'s `version` field. Mirrors the
        // CLI's CMake-based `CLASSIC_CLI_VERSION` and the GUI's CMake-based
        // `CLASSIC_GUI_VERSION`, so all three native frontends derive
        // their installed-binary version from the same install-immutable
        // bytes. Sourcing the runtime cache-preferring `load_main_yaml_version`
        // here would let a per-user YAML data update move the broadcast
        // version ahead of the actual installed binary and make the TUI
        // alone misclassify updates relative to the other frontends —
        // the codex adversarial-review fix for the binary-identity bug.
        let installed_version = env!("CLASSIC_APP_VERSION");
        get_runtime().spawn(async move {
            let payload =
                check_app_notification("evildarkarchon", "CLASSIC-Fallout4", installed_version)
                    .await
                    .map_err(|error| error.to_string());
            let _ = tx.send(AsyncMessage::UpdateResult(payload));
        });
    }
}

pub(super) fn format_update_status(status: &NotificationStatus) -> String {
    match status.classification {
        Classification::UpToDate => "You are up to date".to_string(),
        Classification::UpdateAvailable => {
            let base = format!("Update available: v{}", status.latest_version);
            match status.display.as_ref() {
                Some(display) if !display.title.trim().is_empty() => {
                    format!("{base} — {}", display.title.trim())
                }
                _ => base,
            }
        }
        Classification::DeprecatedClient => {
            let min = status.min_supported_version.as_deref().unwrap_or("unknown");
            format!(
                "Client deprecated (min v{min}); upgrade to v{}",
                status.latest_version
            )
        }
        Classification::Unknown => match status.parse_error.as_deref() {
            Some(detail) => format!("Update check returned unknown status: {detail}"),
            None => "Update check returned unknown status".to_string(),
        },
        Classification::NotPublished => "No update information available".to_string(),
    }
}
