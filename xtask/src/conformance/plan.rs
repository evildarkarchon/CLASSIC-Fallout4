//! Input-only run plans: what one participant invocation is handed.
//!
//! A plan is built centrally from a validated pack ([`PreparedPack`]), so a
//! participant can neither choose its scenarios nor see an expectation:
//!
//! - **Pack-owned fields** (`schemaVersion`, `familyId`, `familyVersion`,
//!   `expectationDigest`, `fixtureRoot`, `fixtures`, and the `scenarios` or
//!   `obligations` payload) come from the pack and the catalogs.
//! - **`sourcePaths`** are the repo-relative files and directories whose bytes,
//!   together with the pack, its oracles and its fixtures, form the
//!   invocation's `sourceIdentity` (`git:<HEAD>:sha256:<framed digest>`).
//! - **`invocation`** carries a fresh UUID v4, the source identity and the
//!   `runPlanDigest`, a framed digest of the plan without that member.
//!
//! The plan is written as canonical bytes (no trailing newline) to
//! `<artifact root>/<participant>/<instance>/<invocation id>/run_plan.json`;
//! `receipt.json` beside it is reserved and never pre-created. [`reload`]
//! authenticates a plan read back from disk against the current tree before a
//! verdict counts its receipt.
//!
//! The digests keep the retired Python engine's frame layout and contract
//! names; the bytes need not match it.

use std::collections::{BTreeMap, BTreeSet};
use std::io::Write;
use std::path::{Path, PathBuf};
use std::sync::atomic::{AtomicU64, Ordering};
use std::time::{SystemTime, UNIX_EPOCH};

use anyhow::{Context, Result, bail};
use serde_json::{Map, Value, json};
use sha2::{Digest, Sha256};

use super::json::{FramedDigest, canonical_bytes, parse_strict};
use super::pack::{LoadedPack, contained};
use super::schema::{PlanParticipant, RunPlan, Scenario, is_canonical_relative_path};
use crate::RepoRoot;

/// Contract name of the expectation digest.
const EXPECTATION_CONTRACT: &str = "classic-conformance-expectation-v1";
/// Contract name of the source identity digest.
const SOURCE_CONTRACT: &str = "classic-conformance-source-v1";
/// Contract name of the run-plan digest.
const RUN_PLAN_CONTRACT: &str = "classic-conformance-run-plan-v1";

/// A participant's role in a plan.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub(crate) enum Role {
    /// Runs scenarios and reports observations (`rust`, `cxx`).
    SemanticAdapter,
    /// Runs consumer obligations (`cli`, `gui`, `tui`).
    Consumer,
}

impl Role {
    /// The protocol spelling.
    pub fn as_str(self) -> &'static str {
        match self {
            Role::SemanticAdapter => "semantic-adapter",
            Role::Consumer => "consumer",
        }
    }
}

/// One declared fixture bound to its file.
#[derive(Debug, Clone)]
pub(crate) struct PackFixture {
    /// The fixture alias.
    pub reference: String,
    /// The `fixtureRoot`-relative path.
    pub relative: String,
    /// The canonical absolute path.
    pub path: PathBuf,
}

/// A pack with no findings, compiled and digested, ready to plan and to
/// validate receipts against.
#[derive(Debug, Clone)]
pub(crate) struct PreparedPack {
    /// Repo-relative pack path.
    pub file: String,
    /// The pack's family.
    pub family_id: String,
    /// The typed pack.
    pub pack: super::schema::Pack,
    /// Each scenario's compiled expectation, by scenario index.
    pub expected: Vec<Map<String, Value>>,
    /// Canonical bytes of the compiled pack document.
    pub canonical: Vec<u8>,
    /// The canonical absolute fixture root, as plans spell it.
    pub fixture_root: String,
    /// Declared fixtures, sorted by (relative path, alias).
    pub fixtures: Vec<PackFixture>,
    /// Repo-relative oracle files, in digest order.
    pub oracles: Vec<String>,
    /// The framed expectation digest.
    pub expectation_digest: String,
}

/// Renders a canonical path the way plans spell it: OS-native, without the
/// Windows verbatim prefix `canonicalize` adds (`\\?\C:\` becomes `C:\`, and
/// `\\?\UNC\server\share` becomes `\\server\share`).
pub(crate) fn native(path: &Path) -> String {
    let text = path.to_string_lossy();
    if let Some(rest) = text.strip_prefix(r"\\?\UNC\") {
        format!(r"\\{rest}")
    } else if let Some(rest) = text.strip_prefix(r"\\?\") {
        rest.to_owned()
    } else {
        text.into_owned()
    }
}

/// Compiles and digests a pack that loaded without findings.
///
/// # Errors
///
/// Fails when the pack had findings (it has no compiled expectations), or a
/// fixture or oracle cannot be resolved or read.
pub(crate) fn prepare(root: &RepoRoot, loaded: &LoadedPack) -> Result<PreparedPack> {
    let Some(compiled) = &loaded.compiled else {
        bail!(
            "{} has conformance findings; run `cargo xtask conformance check`",
            loaded.file
        );
    };
    let pack = &loaded.pack;
    let fixture_root = root
        .join(&pack.fixture_root)
        .canonicalize()
        .with_context(|| format!("resolving fixtureRoot of {}", loaded.file))?;
    let mut fixtures = Vec::new();
    for (reference, relative) in &pack.fixtures {
        let path = contained(&fixture_root, relative)
            .with_context(|| format!("fixture {reference} of {} does not resolve", loaded.file))?;
        fixtures.push(PackFixture {
            reference: reference.clone(),
            relative: relative.clone(),
            path,
        });
    }
    fixtures.sort_by(|a, b| (&a.relative, &a.reference).cmp(&(&b.relative, &b.reference)));

    let mut document = loaded.document.value().clone();
    for (index, expected) in compiled.expected.iter().enumerate() {
        document["scenarios"][index]["expected"] = Value::Object(expected.clone());
    }
    let canonical = canonical_bytes(&document);

    let mut digest = FramedDigest::new(EXPECTATION_CONTRACT);
    digest.frame("pack", &canonical);
    for oracle in &compiled.oracles {
        let bytes =
            std::fs::read(root.join(oracle)).with_context(|| format!("reading oracle {oracle}"))?;
        digest.frame("oracle-path", oracle.as_bytes());
        digest.frame("oracle-bytes", &bytes);
    }
    for fixture in &fixtures {
        let bytes = std::fs::read(&fixture.path)
            .with_context(|| format!("reading fixture {}", fixture.path.display()))?;
        digest.frame("fixture-path", fixture.relative.as_bytes());
        digest.frame("fixture-bytes", &bytes);
    }
    Ok(PreparedPack {
        file: loaded.file.clone(),
        family_id: pack.family_id.clone(),
        pack: pack.clone(),
        expected: compiled.expected.clone(),
        canonical,
        fixture_root: native(&fixture_root),
        fixtures,
        oracles: compiled.oracles.clone(),
        expectation_digest: digest.finish(),
    })
}

/// What a plan asks the participant to run.
#[derive(Debug, Clone)]
pub(crate) enum Payload {
    /// The scenario IDs, in pack order, a semantic adapter runs.
    Scenarios(Vec<String>),
    /// The obligations, `(id, scenarioIds)`, a consumer runs.
    Obligations(Vec<(String, Vec<String>)>),
}

/// The participant-specific part of a plan.
#[derive(Debug, Clone)]
pub(crate) struct PlanRequest {
    /// `rust`, `cxx`, `cli`, `gui` or `tui`.
    pub participant: String,
    /// The participant's role.
    pub role: Role,
    /// The execution instance.
    pub instance: String,
    /// Repo-relative source paths bound into the source identity.
    pub source_paths: Vec<String>,
    /// The scenarios or obligations to run.
    pub payload: Payload,
}

/// The plan without `invocation`: every member the pack, catalogs and request
/// determine. `sourcePaths` come out sorted.
fn core(prepared: &PreparedPack, request: &PlanRequest) -> Result<Map<String, Value>> {
    let mut paths: Vec<&String> = request.source_paths.iter().collect();
    paths.sort();
    if paths.windows(2).any(|pair| pair[0] == pair[1]) {
        bail!("source paths must name unique repository paths");
    }
    let fixtures: Map<String, Value> = prepared
        .fixtures
        .iter()
        .map(|fixture| (fixture.reference.clone(), json!(native(&fixture.path))))
        .collect();
    let mut plan = Map::new();
    plan.insert("schemaVersion".into(), json!(1));
    plan.insert("familyId".into(), json!(prepared.family_id));
    plan.insert("familyVersion".into(), json!(prepared.pack.family_version));
    plan.insert(
        "expectationDigest".into(),
        json!(prepared.expectation_digest),
    );
    plan.insert("fixtureRoot".into(), json!(prepared.fixture_root));
    plan.insert("fixtures".into(), Value::Object(fixtures));
    plan.insert("sourcePaths".into(), json!(paths));
    plan.insert(
        "participant".into(),
        json!({
            "id": request.participant,
            "role": request.role.as_str(),
            "executionInstanceId": request.instance,
        }),
    );
    match &request.payload {
        Payload::Scenarios(ids) => {
            let wanted: BTreeSet<&str> = ids.iter().map(String::as_str).collect();
            let scenarios: Vec<Value> = prepared
                .pack
                .scenarios
                .iter()
                .filter(|scenario| wanted.contains(scenario.id.as_str()))
                .map(plan_scenario)
                .collect();
            if scenarios.is_empty() {
                bail!("the plan selects no scenario");
            }
            plan.insert("scenarios".into(), Value::Array(scenarios));
        }
        Payload::Obligations(obligations) => {
            if obligations.is_empty() {
                bail!("the plan selects no consumer obligation");
            }
            let obligations: Vec<Value> = obligations
                .iter()
                .map(|(id, scenarios)| json!({"id": id, "scenarioIds": scenarios}))
                .collect();
            plan.insert("obligations".into(), Value::Array(obligations));
        }
    }
    Ok(plan)
}

/// A scenario as a participant sees it: the pack scenario without `expected`.
fn plan_scenario(scenario: &Scenario) -> Value {
    let normalization = &scenario.normalization;
    let mut rules = json!({
        "rootRelativePaths": normalization.root_relative_paths,
        "unorderedPaths": normalization.unordered_paths,
        "excludedPaths": normalization
            .excluded_paths
            .iter()
            .map(|exclusion| json!({"path": exclusion.path, "rationale": exclusion.rationale}))
            .collect::<Vec<_>>(),
    });
    if let Some(optional) = &normalization.optional_empty_files {
        rules["optionalEmptyFiles"] = optional
            .iter()
            .map(|file| {
                json!({"path": file.path, "relativePath": file.relative_path, "rationale": file.rationale})
            })
            .collect();
    }
    json!({
        "id": scenario.id,
        "action": scenario.action,
        "capabilityIds": scenario.capability_ids,
        "fixtureRefs": scenario.fixture_refs,
        "input": scenario.input,
        "normalization": rules,
    })
}

/// Builds a fresh plan for `request`, with a new invocation ID, the current
/// source identity and the run-plan digest.
///
/// # Errors
///
/// Fails when a source path is not a unique, existing, canonical repo-relative
/// path, git cannot name `HEAD`, a source file cannot be read, or the payload
/// selects nothing.
pub(crate) fn build(
    root: &RepoRoot,
    prepared: &PreparedPack,
    request: &PlanRequest,
) -> Result<Value> {
    let mut plan = core(prepared, request)?;
    let identity = source_identity(root, prepared, &request.source_paths)?;
    plan.insert(
        "invocation".into(),
        json!({"id": uuid_v4(), "sourceIdentity": identity}),
    );
    let digest = run_plan_digest(&Value::Object(plan.clone()));
    plan["invocation"]["runPlanDigest"] = json!(digest);
    Ok(Value::Object(plan))
}

/// The framed digest of `plan` with any `invocation.runPlanDigest` removed.
fn run_plan_digest(plan: &Value) -> String {
    let mut plan = plan.clone();
    if let Some(invocation) = plan.get_mut("invocation").and_then(Value::as_object_mut) {
        invocation.remove("runPlanDigest");
    }
    let mut digest = FramedDigest::new(RUN_PLAN_CONTRACT);
    digest.frame("plan", &canonical_bytes(&plan));
    digest.finish()
}

/// `git:<HEAD>:sha256:<hex>` over the pack, its oracles, its fixtures and
/// `source_paths` (directories expand to every file beneath them).
///
/// Each declared root is framed as `source-root`; each file as its lexical
/// repo-relative path (`source-path`), its resolved target (`source-target`,
/// which differs through a symlink) and its bytes (`source-bytes`).
///
/// # Errors
///
/// Fails when git cannot name `HEAD`, or a declared path is not canonical, is
/// missing, or resolves outside the repository.
pub(crate) fn source_identity(
    root: &RepoRoot,
    prepared: &PreparedPack,
    source_paths: &[String],
) -> Result<String> {
    let revision = head_revision(root)?;
    let repository = root
        .path()
        .canonicalize()
        .with_context(|| format!("resolving {}", root.path().display()))?;
    let mut candidates = vec![prepared.file.clone()];
    candidates.extend(prepared.oracles.iter().cloned());
    candidates.extend(
        prepared
            .fixtures
            .iter()
            .map(|fixture| format!("{}/{}", prepared.pack.fixture_root, fixture.relative)),
    );
    candidates.extend(source_paths.iter().cloned());

    let mut roots = BTreeSet::new();
    let mut files: BTreeMap<String, (String, PathBuf)> = BTreeMap::new();
    for candidate in candidates {
        if !is_canonical_relative_path(&candidate) {
            bail!("source path {candidate:?} must be a canonical repo-relative path");
        }
        let full = root.join(&candidate);
        let mut found = Vec::new();
        if full.is_file() {
            found.push(full);
        } else if full.is_dir() {
            for entry in walkdir::WalkDir::new(&full).sort_by_file_name() {
                let entry = entry.with_context(|| format!("walking {candidate}"))?;
                if entry.path().is_file() {
                    found.push(entry.into_path());
                }
            }
        } else {
            bail!("source path {candidate} must be an existing file or directory");
        }
        for path in found {
            let declared = root.relative(&path);
            let resolved = path
                .canonicalize()
                .with_context(|| format!("resolving {declared}"))?;
            let target = resolved.strip_prefix(&repository).map_err(|_| {
                anyhow::anyhow!("source input {declared} resolves outside the repository")
            })?;
            let target = target.to_string_lossy().replace('\\', "/");
            files.insert(declared, (target, path));
        }
        roots.insert(candidate);
    }
    let mut digest = FramedDigest::new(SOURCE_CONTRACT);
    for declared in &roots {
        digest.frame("source-root", declared.as_bytes());
    }
    for (declared, (target, path)) in &files {
        let bytes = std::fs::read(path).with_context(|| format!("reading {declared}"))?;
        digest.frame("source-path", declared.as_bytes());
        digest.frame("source-target", target.as_bytes());
        digest.frame("source-bytes", &bytes);
    }
    let hex = digest.finish();
    let hex = hex.strip_prefix("sha256:").unwrap_or(&hex);
    Ok(format!("git:{revision}:sha256:{hex}"))
}

/// The lowercase commit ID of `HEAD`.
fn head_revision(root: &RepoRoot) -> Result<String> {
    let output = std::process::Command::new("git")
        .arg("-C")
        .arg(root.path())
        .args(["rev-parse", "--verify", "HEAD"])
        .output()
        .context("running git rev-parse")?;
    if !output.status.success() {
        bail!(
            "cannot compute the source identity with git: {}",
            String::from_utf8_lossy(&output.stderr).trim()
        );
    }
    let revision = String::from_utf8_lossy(&output.stdout)
        .trim()
        .to_ascii_lowercase();
    let valid =
        (40..=64).contains(&revision.len()) && revision.bytes().all(|b| b.is_ascii_hexdigit());
    if !valid {
        bail!("git returned an invalid revision {revision:?}");
    }
    Ok(revision)
}

/// A fresh random UUID v4.
///
/// xtask has no random-number dependency, so the 122 random bits come from a
/// SHA-256 over the clock, the process ID, a process-wide counter and the
/// standard library's randomly keyed hasher. That is unique enough for
/// artifact directory names; nothing relies on it being unpredictable.
pub(crate) fn uuid_v4() -> String {
    use std::hash::{BuildHasher, RandomState};
    static COUNTER: AtomicU64 = AtomicU64::new(0);
    let nanos = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .map(|elapsed| elapsed.as_nanos())
        .unwrap_or_default();
    let mut hasher = Sha256::new();
    hasher.update(nanos.to_le_bytes());
    hasher.update(std::process::id().to_le_bytes());
    hasher.update(COUNTER.fetch_add(1, Ordering::Relaxed).to_le_bytes());
    hasher.update(RandomState::new().hash_one(nanos).to_le_bytes());
    let mut bytes: [u8; 16] = hasher.finalize()[..16].try_into().expect("16 bytes");
    bytes[6] = (bytes[6] & 0x0f) | 0x40;
    bytes[8] = (bytes[8] & 0x3f) | 0x80;
    let hex: String = bytes.iter().map(|byte| format!("{byte:02x}")).collect();
    format!(
        "{}-{}-{}-{}-{}",
        &hex[..8],
        &hex[8..12],
        &hex[12..16],
        &hex[16..20],
        &hex[20..]
    )
}

/// A plan written to disk for one invocation.
#[derive(Debug, Clone)]
pub(crate) struct Materialized {
    /// `<artifact root>/<participant>/<instance>/<invocation id>`.
    pub dir: PathBuf,
    /// `run_plan.json` in `dir`.
    pub run_plan: PathBuf,
    /// The reserved `receipt.json` in `dir` (not created).
    pub receipt: PathBuf,
    /// The plan document.
    pub plan: Value,
    /// The canonical bytes written.
    pub bytes: Vec<u8>,
}

/// Writes `plan` into a fresh invocation directory under `artifact_root`.
///
/// The plan goes to a temporary file first and is renamed into place, so a
/// participant never reads a partial plan.
///
/// # Errors
///
/// Fails when the invocation directory already exists or a write fails.
pub(crate) fn write(artifact_root: &Path, plan: &Value) -> Result<Materialized> {
    let participant = &plan["participant"];
    let dir = artifact_root
        .join(participant["id"].as_str().unwrap_or("unknown"))
        .join(
            participant["executionInstanceId"]
                .as_str()
                .unwrap_or("unknown"),
        );
    std::fs::create_dir_all(&dir).with_context(|| format!("creating {}", dir.display()))?;
    let dir = dir.join(plan["invocation"]["id"].as_str().unwrap_or("unknown"));
    std::fs::create_dir(&dir)
        .with_context(|| format!("creating the fresh invocation directory {}", dir.display()))?;
    let bytes = canonical_bytes(plan);
    let temporary = dir.join(".run_plan.tmp");
    let run_plan = dir.join("run_plan.json");
    {
        let mut file = std::fs::OpenOptions::new()
            .write(true)
            .create_new(true)
            .open(&temporary)
            .with_context(|| format!("creating {}", temporary.display()))?;
        file.write_all(&bytes)?;
        file.sync_all()?;
    }
    std::fs::rename(&temporary, &run_plan)
        .with_context(|| format!("publishing {}", run_plan.display()))?;
    Ok(Materialized {
        receipt: dir.join("receipt.json"),
        dir,
        run_plan,
        plan: plan.clone(),
        bytes,
    })
}

/// Reads a plan back and authenticates it against the current tree.
///
/// `expected` names what the plan's participant must have been handed (the
/// current applicability); it fails for a participant or instance that is no
/// longer applicable. Consumers also get their expected `sourcePaths` from it,
/// since only the obligation catalog may choose them.
///
/// # Errors
///
/// Returns why the plan cannot be trusted: unreadable, not strict canonical
/// JSON, not the closed plan shape, pack-owned fields that no longer match,
/// a digest that does not match its content, or a source identity that no
/// longer matches the tree.
pub(crate) fn reload(
    root: &RepoRoot,
    prepared: &PreparedPack,
    run_plan: &Path,
    expected: impl Fn(&PlanParticipant) -> std::result::Result<(Payload, Option<Vec<String>>), String>,
) -> std::result::Result<Materialized, String> {
    let bytes =
        std::fs::read(run_plan).map_err(|error| format!("cannot read the run plan: {error}"))?;
    let text =
        String::from_utf8(bytes.clone()).map_err(|_| "the run plan is not UTF-8".to_owned())?;
    let document =
        parse_strict(&text).map_err(|error| format!("the run plan is not strict JSON: {error}"))?;
    let value = document.value().clone();
    let plan: RunPlan = serde_json::from_value(value.clone())
        .map_err(|error| format!("the run plan has an invalid shape: {error}"))?;
    if canonical_bytes(&value) != bytes {
        return Err("the run plan is not canonical JSON".into());
    }
    let (payload, consumer_paths) = expected(&plan.participant)?;
    let role = match plan.participant.role.as_str() {
        "semantic-adapter" => Role::SemanticAdapter,
        "consumer" => Role::Consumer,
        other => return Err(format!("the run plan names unknown role {other:?}")),
    };
    let request = PlanRequest {
        participant: plan.participant.id.clone(),
        role,
        instance: plan.participant.execution_instance_id.clone(),
        source_paths: consumer_paths.unwrap_or_else(|| plan.source_paths.clone()),
        payload,
    };
    let current = core(prepared, &request).map_err(|error| error.to_string())?;
    let mut mismatched: Vec<&String> = Vec::new();
    for (key, expected_value) in &current {
        if value.get(key) != Some(expected_value) {
            mismatched.push(key);
        }
    }
    if let Some(object) = value.as_object() {
        for key in object.keys() {
            if key != "invocation" && !current.contains_key(key) {
                mismatched.push(key);
            }
        }
    }
    if !mismatched.is_empty() {
        mismatched.sort();
        let names: Vec<&str> = mismatched.iter().map(|key| key.as_str()).collect();
        return Err(format!(
            "the run plan no longer matches the current pack and catalogs: {}",
            names.join(", ")
        ));
    }
    if plan.invocation.run_plan_digest != run_plan_digest(&value) {
        return Err("the run plan digest does not match its content".into());
    }
    let identity = source_identity(root, prepared, &plan.source_paths)
        .map_err(|error| format!("{error:#}"))?;
    if plan.invocation.source_identity != identity {
        return Err(
            "the run plan's source identity does not match the current declared inputs".into(),
        );
    }
    let dir = run_plan.parent().map(Path::to_path_buf).unwrap_or_default();
    Ok(Materialized {
        receipt: dir.join("receipt.json"),
        dir,
        run_plan: run_plan.to_path_buf(),
        plan: value,
        bytes,
    })
}

#[cfg(test)]
#[path = "plan_tests.rs"]
mod tests;
