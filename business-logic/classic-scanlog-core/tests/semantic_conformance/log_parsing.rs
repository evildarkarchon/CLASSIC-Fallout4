//! Native parser and literal matcher observations without expectation access.

use super::{RunnerResult, invalid, text};
use classic_scanlog_core::{LogParser, PatternMatcher};
use serde_json::{Value, json};
use std::sync::Arc;

/// Reads a fixture-owned array of strings without coercing malformed input.
fn strings(value: &Value) -> RunnerResult<Vec<String>> {
    value
        .as_array()
        .ok_or_else(|| invalid("parser input must be an array"))?
        .iter()
        .map(text)
        .collect()
}

/// Executes public parser/matcher operations and returns actual values and cache state.
pub(super) fn observe(fixture: &Value) -> RunnerResult<Value> {
    if fixture["operation"] == "crashgen-version" {
        use classic_scanlog_core::version::{
            CrashgenVersion, CrashgenVersionStatus, check_crashgen_version_status,
        };
        let input = text(&fixture["version"])?;
        let value = CrashgenVersion::parse(&input);
        let supported = strings(&fixture["supported"])?;
        let refs = supported.iter().map(String::as_str).collect::<Vec<_>>();
        if let Some(parsed) = &value {
            let constructed = CrashgenVersion::new(parsed.major, parsed.minor, parsed.patch);
            if constructed != *parsed {
                return Err(invalid("version numeric identity changed").into());
            }
        }
        let status = match check_crashgen_version_status(&input, &refs) {
            CrashgenVersionStatus::Valid => "valid",
            CrashgenVersionStatus::Outdated => "outdated",
            CrashgenVersionStatus::NewerThanKnown => "newer_than_known",
            CrashgenVersionStatus::NoSupportedVersion => "no_supported_version",
        };
        return Ok(
            json!({"operation":"crashgen-version","version":value.map(|value|value.to_tuple()),"status":status}),
        );
    }
    if fixture["operation"] == "node-parser" {
        let parser = LogParser::new(None)?;
        let content = text(&fixture["content"])?;
        let lines = content.lines().map(str::to_owned).collect::<Vec<_>>();
        let sections = parser.parse_all_sections(&lines);
        let header = parser
            .extract_section(&lines, "[Compatibility]", "SYSTEM SPECS:")
            .unwrap_or_default();
        let system = sections.get("system").cloned().unwrap_or_default();
        let stack = sections.get("callstack").cloned().unwrap_or_default();
        let modules = sections.get("modules").cloned().unwrap_or_default();
        let plugins = sections.get("plugins").cloned().unwrap_or_default();
        let count = [&header, &system, &stack, &modules, &plugins]
            .iter()
            .filter(|lines| !lines.is_empty())
            .count();
        return Ok(
            json!({"operation":"node-parser","segments":{"header":header,"system":system,"stack":stack,"modules":modules,"plugins":plugins,"segmentCount":count},"formids":parser.extract_formids(&lines),"plugins":parser.extract_plugins(&lines).into_iter().map(|(name,_)|name).collect::<Vec<_>>()}),
        );
    }
    if fixture["operation"] == "gpu" {
        use classic_scanlog_core::{GpuDetector, GpuInfo, GpuVendor};
        let _detector = GpuDetector::new();
        let lines = strings(&fixture["lines"])?;
        let info = GpuDetector::get_gpu_info(&lines);
        let vendor = match text(&fixture["vendor"])?.to_uppercase().as_str() {
            "AMD" => GpuVendor::AMD,
            "NVIDIA" => GpuVendor::Nvidia,
            "INTEL" => GpuVendor::Intel,
            _ => GpuVendor::Unknown,
        };
        if vendor.to_string() != info.manufacturer {
            return Err(invalid("GPU vendor conversion changed").into());
        }
        let empty = GpuInfo::new().to_dict();
        if GpuDetector::get_gpu_info(&[]).to_dict() != empty {
            return Err(invalid("GPU default state differs from empty detection").into());
        }
        return Ok(
            json!({"operation":"gpu","info":info.to_dict(),"empty":empty,
            "batch":GpuDetector::get_gpu_info_batch(vec![lines,vec![]]).into_iter().map(|value|value.to_dict()).collect::<Vec<_>>()}),
        );
    }
    if matches!(
        fixture["operation"].as_str(),
        Some("formids" | "plugins" | "records")
    ) {
        return observe_extractors(fixture);
    }
    if fixture["operation"] == "patterns" {
        let matcher = PatternMatcher::new(strings(&fixture["patterns"])?)?;
        let input = text(&fixture["text"])?;
        let before = matcher.get_stats();
        let matches = matcher.find_all(&input);
        let cached = matcher.get_stats();
        let mut result = json!({"operation":"patterns","before":before,"matches":matches,
            "first":matcher.find_first(&input),"hasMatch":matcher.has_match(&input),
            "replaced":matcher.replace_all(&input,&text(&fixture["replacement"])?),"cached":cached});
        matcher.clear_cache();
        result["afterClear"] = json!(matcher.get_stats());
        if matcher.find_all(&input) != matches {
            return Err(invalid("matcher cache clear changed results").into());
        }
        return Ok(result);
    }
    if fixture["operation"] != "parser" {
        return Err(invalid("unknown parser operation").into());
    }
    let parser = LogParser::new(None)?;
    parser.add_pattern("custom", &text(&fixture["pattern"])?)?;
    let pattern_lines = strings(&fixture["patternLines"])?;
    let mut patterns = parser.find_patterns(&pattern_lines);
    patterns.sort();
    let mut chunked = parser.find_patterns_chunked(&pattern_lines, Some(1));
    chunked.sort();
    if patterns != chunked {
        return Err(invalid("chunked patterns disagree").into());
    }
    let lines = strings(&fixture["lines"])?;
    let arc_lines = lines
        .iter()
        .map(|line| Arc::<str>::from(line.as_str()))
        .collect::<Vec<_>>();
    let sections = parser.parse_all_sections(&lines);
    let headers = parser.parse_crash_header(&lines)?;
    let complete = parser.parse_complete(&lines, &[], "F4SE")?;
    let header_values = ["game_version", "crashgen_version", "main_error"]
        .map(|key| headers.get(key).map_or("UNKNOWN", String::as_str));
    if [
        complete.0.as_str(),
        complete.1.as_str(),
        complete.2.as_str(),
    ] != header_values
    {
        return Err(invalid("complete parser changed header values").into());
    }
    let benchmark = parser.benchmark(&arc_lines, 16);
    let mut benchmark_keys = benchmark.keys().cloned().collect::<Vec<_>>();
    benchmark_keys.sort();
    let section_lines = strings(&fixture["sectionLines"])?;
    let extraction_lines = strings(&fixture["extractLines"])?;
    let mut result = json!({"operation":"parser","patterns":patterns,
        "section":parser.extract_section(&section_lines,"START","END"),
        "sectionBatch":parser.extract_sections_batch(&section_lines,&[("START".into(),"END".into()),("ABSENT".into(),"END".into())]),
        "headers":headers,"sections":sections,"system":parser.get_section(&lines,"system"),
        "sizes":parser.get_segment_sizes(&lines),"formids":parser.extract_formids(&extraction_lines),
        "plugins":parser.extract_plugins(&extraction_lines),"addresses":parser.extract_addresses(&extraction_lines),
        "errors":parser.find_errors(&extraction_lines),"benchmarkKeys":benchmark_keys,
        "benchmarkFinite":benchmark.values().all(|value| value.is_finite() && *value >= 0.0)});
    parser.clear_caches();
    result["afterClear"] = json!(parser.get_stats());
    Ok(result)
}

/// Executes object and free-function extractors while preserving source order.
fn observe_extractors(fixture: &Value) -> RunnerResult<Value> {
    use classic_scanlog_core::{
        PluginAnalyzer, RecordScanner, RustFormIDAnalyzer, contains_plugin, contains_record,
        detect_plugins_batch, extract_formids_batch, is_valid_formid, try_scan_records_batch,
        validate_formids_batch,
    };
    let lines = strings(&fixture["lines"])?;
    let operation = text(&fixture["operation"])?;
    if operation == "formids" {
        let analyzer = RustFormIDAnalyzer::new();
        let ids = strings(&fixture["ids"])?;
        let plugins = serde_json::from_value(fixture["plugins"].clone())?;
        let resolved = analyzer.analyze_batch(ids.clone(), &plugins);
        let mut result = json!({"operation":operation,"extracted":analyzer.extract_formids(&lines),
            "extractedBatch":extract_formids_batch(vec![lines,vec![]]),
            "parsed":ids.iter().map(|value|analyzer.parse_formid(value)).collect::<Vec<_>>(),
            "resolved":resolved,"valid":ids.iter().map(|value|is_valid_formid(value)).collect::<Vec<_>>(),
            "validBatch":validate_formids_batch(ids.clone()),"cache":analyzer.cache_stats()});
        analyzer.clear_cache();
        result["afterClear"] = json!(analyzer.cache_stats());
        if analyzer.analyze_batch(ids, &plugins) != resolved {
            return Err(invalid("FormID cache clear changed resolution").into());
        }
        return Ok(result);
    }
    let ignored = strings(&fixture["ignore"])?;
    if operation == "plugins" {
        let analyzer = PluginAnalyzer::new(
            vec![],
            ignored,
            "Buffout 4".into(),
            "1.10.163".into(),
            "1.2.72".into(),
        )?;
        let (plugins, triggered, disabled) =
            analyzer.loadorder_scan_log(&lines, Some("1.10.163"), Some("1.28.6"))?;
        let filtered = analyzer.filter_ignored_plugins(plugins.clone())?;
        return Ok(
            json!({"operation":operation,"plugins":plugins.into_iter().collect::<Vec<_>>(),
            "limits":[triggered,disabled],"checkedLimits":analyzer.check_plugin_limit(&lines,"1.10.163","1.28.6")?,
            "filtered":filtered.into_iter().collect::<Vec<_>>(),
            "batch":detect_plugins_batch(vec![lines.join("\n"),String::new()]).into_iter().map(|map|map.into_iter().collect::<Vec<_>>()).collect::<Vec<_>>(),
            "contains":lines.iter().map(|line|contains_plugin(line)).collect::<Vec<_>>() }),
        );
    }
    let targets = strings(&fixture["targets"])?;
    let scanner = RecordScanner::new(targets.clone(), ignored.clone());
    let records = scanner.try_extract_records(&lines)?;
    let mut result = json!({"operation":operation,"records":records,
        "batch":try_scan_records_batch(vec![lines.clone(),vec![]],targets.clone(),ignored.clone())?,
        "contains":lines.iter().map(|line|contains_record(line,&targets,&ignored)).collect::<Vec<_>>()});
    scanner.clear_cache();
    result["afterClear"] = json!(scanner.try_extract_records(&lines)?);
    Ok(result)
}
