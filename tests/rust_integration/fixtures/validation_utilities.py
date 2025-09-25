"""
Validation utilities for Rust integration testing.

This module provides utilities for validating test results, comparing
outputs between Rust and Python implementations, and performing
accuracy checks on extracted data.
"""

import re
import statistics
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple, Union


class ValidationUtilities:
    """
    Collection of validation utilities for Rust integration testing.

    This class provides methods to validate extracted data, compare
    results between implementations, and perform accuracy checks.
    """

    # FormID validation patterns
    FORMID_PATTERNS = {
        "hex_formid": re.compile(r'0x[0-9A-Fa-f]{8}'),
        "decimal_formid": re.compile(r'\b\d{1,10}\b'),
        "formid_with_plugin": re.compile(r'0x[0-9A-Fa-f]{8}\s*\([^)]+\)'),
        "base_game_formid": re.compile(r'0x00[0-9A-Fa-f]{6}'),
        "dlc_formid": re.compile(r'0x0[1-6][0-9A-Fa-f]{6}'),
        "esl_formid": re.compile(r'0xFE[0-9A-Fa-f]{6}'),
        "mod_formid": re.compile(r'0x[0-9A-Fa-f][7-9A-F][0-9A-Fa-f]{6}')
    }

    # Plugin validation patterns
    PLUGIN_PATTERNS = {
        "esm_file": re.compile(r'\.esm$', re.IGNORECASE),
        "esp_file": re.compile(r'\.esp$', re.IGNORECASE),
        "esl_file": re.compile(r'\.esl$', re.IGNORECASE),
        "valid_plugin": re.compile(r'^[^<>:"/\\|?*]+\.(esm|esp|esl)$', re.IGNORECASE),
        "load_order_entry": re.compile(r'^\s*\[([0-9A-F]{2}|FE:[0-9A-F]{3})\]\s*(.+)$', re.IGNORECASE),
        "master_file": re.compile(r'^(Fallout4|DLC\w+)\.esm$', re.IGNORECASE)
    }

    # Record type patterns
    RECORD_PATTERNS = {
        "tes_form": re.compile(r'\bTESForm\b'),
        "bgs_keyword": re.compile(r'\bBGSKeyword\b'),
        "tes_object": re.compile(r'\bTESObject\w+\b'),
        "bgs_object": re.compile(r'\bBGS\w+\b'),
        "memory_address": re.compile(r'\b0x[0-9A-Fa-f]{8,16}\b')
    }

    @staticmethod
    def validate_formids(formids: List[str],
                        strict: bool = True,
                        allow_decimal: bool = False) -> Dict[str, Any]:
        """
        Validate a list of extracted FormIDs for correctness.

        Args:
            formids: List of FormID strings to validate
            strict: Whether to apply strict validation rules
            allow_decimal: Whether to allow decimal FormIDs

        Returns:
            Dictionary containing validation results and statistics
        """
        results = {
            "total_formids": len(formids),
            "valid_formids": 0,
            "invalid_formids": 0,
            "hex_formids": 0,
            "decimal_formids": 0,
            "base_game_formids": 0,
            "dlc_formids": 0,
            "esl_formids": 0,
            "mod_formids": 0,
            "formids_with_plugins": 0,
            "validation_errors": [],
            "formid_distribution": {},
            "validity_ratio": 0.0
        }

        if not formids:
            return results

        for i, formid in enumerate(formids):
            if not isinstance(formid, str):
                results["validation_errors"].append(f"FormID {i} is not a string: {type(formid)}")
                results["invalid_formids"] += 1
                continue

            formid_stripped = formid.strip()

            # Check for hexadecimal FormID
            if ValidationUtilities.FORMID_PATTERNS["hex_formid"].search(formid_stripped):
                results["hex_formids"] += 1
                results["valid_formids"] += 1

                # Extract hex value for further classification
                hex_match = ValidationUtilities.FORMID_PATTERNS["hex_formid"].search(formid_stripped)
                if hex_match:
                    hex_value = hex_match.group()
                    try:
                        formid_int = int(hex_value, 16)

                        # Classify by source
                        if ValidationUtilities.FORMID_PATTERNS["base_game_formid"].search(hex_value):
                            results["base_game_formids"] += 1
                        elif ValidationUtilities.FORMID_PATTERNS["dlc_formid"].search(hex_value):
                            results["dlc_formids"] += 1
                        elif ValidationUtilities.FORMID_PATTERNS["esl_formid"].search(hex_value):
                            results["esl_formids"] += 1
                        elif ValidationUtilities.FORMID_PATTERNS["mod_formid"].search(hex_value):
                            results["mod_formids"] += 1

                        # Check for plugin association
                        if ValidationUtilities.FORMID_PATTERNS["formid_with_plugin"].search(formid_stripped):
                            results["formids_with_plugins"] += 1

                        # Track distribution by mod index
                        mod_index = (formid_int >> 24) & 0xFF
                        mod_key = f"0x{mod_index:02X}"
                        results["formid_distribution"][mod_key] = results["formid_distribution"].get(mod_key, 0) + 1

                    except ValueError:
                        results["validation_errors"].append(f"Invalid hex FormID: {hex_value}")
                        results["invalid_formids"] += 1
                        results["valid_formids"] -= 1

            # Check for decimal FormID (if allowed)
            elif allow_decimal and ValidationUtilities.FORMID_PATTERNS["decimal_formid"].search(formid_stripped):
                results["decimal_formids"] += 1
                results["valid_formids"] += 1

            else:
                results["invalid_formids"] += 1
                if strict:
                    results["validation_errors"].append(f"Invalid FormID format: {formid_stripped}")

        # Calculate validity ratio
        if results["total_formids"] > 0:
            results["validity_ratio"] = results["valid_formids"] / results["total_formids"]

        return results

    @staticmethod
    def validate_plugins(plugins: Union[List[str], Dict[str, str]],
                        check_load_order: bool = True) -> Dict[str, Any]:
        """
        Validate a list or dictionary of plugins for correctness.

        Args:
            plugins: List of plugin names or dict mapping indices to names
            check_load_order: Whether to validate load order format

        Returns:
            Dictionary containing validation results
        """
        if isinstance(plugins, dict):
            plugin_names = list(plugins.values())
            plugin_indices = list(plugins.keys())
        else:
            plugin_names = plugins
            plugin_indices = []

        results = {
            "total_plugins": len(plugin_names),
            "valid_plugins": 0,
            "invalid_plugins": 0,
            "esm_files": 0,
            "esp_files": 0,
            "esl_files": 0,
            "master_files": 0,
            "load_order_errors": [],
            "plugin_errors": [],
            "validity_ratio": 0.0,
            "has_essential_masters": False,
            "load_order_indices": []
        }

        essential_masters = {"Fallout4.esm", "DLCRobot.esm", "DLCworkshop01.esm",
                           "DLCCoast.esm", "DLCNukaWorld.esm"}
        found_masters = set()

        for i, plugin_name in enumerate(plugin_names):
            if not isinstance(plugin_name, str):
                results["plugin_errors"].append(f"Plugin {i} is not a string: {type(plugin_name)}")
                results["invalid_plugins"] += 1
                continue

            plugin_name_clean = plugin_name.strip()

            # Validate plugin file format
            if ValidationUtilities.PLUGIN_PATTERNS["valid_plugin"].match(plugin_name_clean):
                results["valid_plugins"] += 1

                # Classify by type
                if ValidationUtilities.PLUGIN_PATTERNS["esm_file"].search(plugin_name_clean):
                    results["esm_files"] += 1
                elif ValidationUtilities.PLUGIN_PATTERNS["esp_file"].search(plugin_name_clean):
                    results["esp_files"] += 1
                elif ValidationUtilities.PLUGIN_PATTERNS["esl_file"].search(plugin_name_clean):
                    results["esl_files"] += 1

                # Check for master files
                if ValidationUtilities.PLUGIN_PATTERNS["master_file"].search(plugin_name_clean):
                    results["master_files"] += 1
                    found_masters.add(plugin_name_clean)

            else:
                results["invalid_plugins"] += 1
                results["plugin_errors"].append(f"Invalid plugin format: {plugin_name_clean}")

        # Check for essential masters
        results["has_essential_masters"] = "Fallout4.esm" in found_masters

        # Validate load order indices if provided
        if check_load_order and plugin_indices:
            results["load_order_indices"] = plugin_indices

            for i, index in enumerate(plugin_indices):
                if isinstance(index, str):
                    # Check hex format
                    if not re.match(r'^([0-9A-F]{2}|FE:[0-9A-F]{3})$', index, re.IGNORECASE):
                        results["load_order_errors"].append(f"Invalid load order index: {index}")
                    else:
                        # Check for valid range
                        if index.startswith("FE:"):
                            esl_index = int(index[3:], 16)
                            if esl_index > 0x7FF:  # ESL limit
                                results["load_order_errors"].append(f"ESL index too high: {index}")
                        else:
                            esp_index = int(index, 16)
                            if esp_index > 0xFE:  # ESP limit (FE is reserved)
                                results["load_order_errors"].append(f"ESP index too high: {index}")

        # Calculate validity ratio
        if results["total_plugins"] > 0:
            results["validity_ratio"] = results["valid_plugins"] / results["total_plugins"]

        return results

    @staticmethod
    def validate_records(record_matches: List[str]) -> Dict[str, Any]:
        """
        Validate a list of record matches for correctness.

        Args:
            record_matches: List of record match strings

        Returns:
            Dictionary containing validation results
        """
        results = {
            "total_matches": len(record_matches),
            "valid_matches": 0,
            "invalid_matches": 0,
            "tes_forms": 0,
            "bgs_keywords": 0,
            "tes_objects": 0,
            "bgs_objects": 0,
            "memory_addresses": 0,
            "match_errors": [],
            "record_types": set(),
            "validity_ratio": 0.0
        }

        for i, match in enumerate(record_matches):
            if not isinstance(match, str):
                results["match_errors"].append(f"Match {i} is not a string: {type(match)}")
                results["invalid_matches"] += 1
                continue

            match_clean = match.strip()
            valid_match = False

            # Check for different record types
            if ValidationUtilities.RECORD_PATTERNS["tes_form"].search(match_clean):
                results["tes_forms"] += 1
                results["record_types"].add("TESForm")
                valid_match = True

            if ValidationUtilities.RECORD_PATTERNS["bgs_keyword"].search(match_clean):
                results["bgs_keywords"] += 1
                results["record_types"].add("BGSKeyword")
                valid_match = True

            if ValidationUtilities.RECORD_PATTERNS["tes_object"].search(match_clean):
                results["tes_objects"] += 1
                valid_match = True

            if ValidationUtilities.RECORD_PATTERNS["bgs_object"].search(match_clean):
                results["bgs_objects"] += 1
                valid_match = True

            if ValidationUtilities.RECORD_PATTERNS["memory_address"].search(match_clean):
                results["memory_addresses"] += 1
                valid_match = True

            if valid_match:
                results["valid_matches"] += 1
            else:
                results["invalid_matches"] += 1
                results["match_errors"].append(f"No valid record pattern in: {match_clean}")

        # Convert set to list for JSON serialization
        results["record_types"] = list(results["record_types"])

        # Calculate validity ratio
        if results["total_matches"] > 0:
            results["validity_ratio"] = results["valid_matches"] / results["total_matches"]

        return results

    @staticmethod
    def compare_extraction_results(rust_results: Dict[str, Any],
                                 python_results: Dict[str, Any],
                                 tolerance: float = 0.1) -> Dict[str, Any]:
        """
        Compare extraction results between Rust and Python implementations.

        Args:
            rust_results: Results from Rust implementation
            python_results: Results from Python implementation
            tolerance: Tolerance for numerical comparisons (0.1 = 10%)

        Returns:
            Dictionary containing comparison results
        """
        comparison = {
            "overall_match": True,
            "differences": [],
            "statistics": {},
            "rust_stats": {},
            "python_stats": {},
            "match_ratio": 1.0
        }

        # Compare common keys
        common_keys = set(rust_results.keys()) & set(python_results.keys())
        rust_only_keys = set(rust_results.keys()) - set(python_results.keys())
        python_only_keys = set(python_results.keys()) - set(rust_results.keys())

        if rust_only_keys:
            comparison["differences"].append(f"Rust-only keys: {list(rust_only_keys)}")
            comparison["overall_match"] = False

        if python_only_keys:
            comparison["differences"].append(f"Python-only keys: {list(python_only_keys)}")
            comparison["overall_match"] = False

        matches = 0
        total_comparisons = 0

        for key in common_keys:
            rust_value = rust_results[key]
            python_value = python_results[key]
            total_comparisons += 1

            if isinstance(rust_value, (list, tuple)) and isinstance(python_value, (list, tuple)):
                # Compare lists/tuples
                rust_set = set(rust_value) if rust_value else set()
                python_set = set(python_value) if python_value else set()

                intersection = rust_set & python_set
                union = rust_set | python_set

                if union:
                    similarity = len(intersection) / len(union)
                    if similarity >= (1.0 - tolerance):
                        matches += 1
                    else:
                        comparison["differences"].append(
                            f"{key}: similarity {similarity:.2f} < threshold {1.0-tolerance:.2f}"
                        )
                        comparison["overall_match"] = False
                else:
                    matches += 1  # Both empty

                comparison["statistics"][key] = {
                    "rust_count": len(rust_value),
                    "python_count": len(python_value),
                    "common_items": len(intersection),
                    "similarity": similarity if union else 1.0
                }

            elif isinstance(rust_value, (int, float)) and isinstance(python_value, (int, float)):
                # Compare numbers
                if rust_value == 0 and python_value == 0:
                    matches += 1
                elif rust_value != 0:
                    relative_diff = abs(rust_value - python_value) / abs(rust_value)
                    if relative_diff <= tolerance:
                        matches += 1
                    else:
                        comparison["differences"].append(
                            f"{key}: relative difference {relative_diff:.2f} > tolerance {tolerance}"
                        )
                        comparison["overall_match"] = False
                else:
                    # rust_value is 0 but python_value is not
                    comparison["differences"].append(f"{key}: rust=0, python={python_value}")
                    comparison["overall_match"] = False

                comparison["statistics"][key] = {
                    "rust_value": rust_value,
                    "python_value": python_value,
                    "absolute_diff": abs(rust_value - python_value),
                    "relative_diff": relative_diff if rust_value != 0 else float('inf')
                }

            else:
                # Direct comparison
                if rust_value == python_value:
                    matches += 1
                else:
                    comparison["differences"].append(
                        f"{key}: rust={rust_value}, python={python_value}"
                    )
                    comparison["overall_match"] = False

        if total_comparisons > 0:
            comparison["match_ratio"] = matches / total_comparisons

        return comparison

    @staticmethod
    def validate_performance_results(benchmark_results: Dict[str, Any],
                                   expected_targets: Dict[str, float],
                                   performance_multipliers: Dict[str, str] = None) -> Dict[str, Any]:
        """
        Validate performance benchmark results against expected targets.

        Args:
            benchmark_results: Results from performance benchmarking
            expected_targets: Expected performance targets by component
            performance_multipliers: Expected Rust performance multipliers

        Returns:
            Dictionary containing performance validation results
        """
        validation = {
            "meets_targets": True,
            "target_violations": [],
            "performance_summary": {},
            "multiplier_validation": {},
            "overall_grade": "A"
        }

        violations = 0
        total_targets = len(expected_targets)

        for component, target_time in expected_targets.items():
            if component in benchmark_results:
                actual_time = benchmark_results[component]["statistics"]["avg_time"]

                meets_target = actual_time <= target_time
                performance_ratio = actual_time / target_time if target_time > 0 else float('inf')

                validation["performance_summary"][component] = {
                    "target_time": target_time,
                    "actual_time": actual_time,
                    "meets_target": meets_target,
                    "performance_ratio": performance_ratio,
                    "margin": (target_time - actual_time) / target_time if target_time > 0 else 0.0
                }

                if not meets_target:
                    violations += 1
                    validation["target_violations"].append(
                        f"{component}: {actual_time:.3f}s > {target_time:.3f}s target"
                    )
                    validation["meets_targets"] = False

        # Validate performance multipliers if provided
        if performance_multipliers:
            for component, expected_multiplier in performance_multipliers.items():
                if component in benchmark_results:
                    # This would need baseline Python performance for comparison
                    # For now, just record the expected multiplier
                    validation["multiplier_validation"][component] = {
                        "expected_multiplier": expected_multiplier,
                        "validation_status": "requires_baseline_comparison"
                    }

        # Calculate overall grade
        if total_targets > 0:
            success_rate = (total_targets - violations) / total_targets
            if success_rate >= 0.95:
                validation["overall_grade"] = "A"
            elif success_rate >= 0.85:
                validation["overall_grade"] = "B"
            elif success_rate >= 0.70:
                validation["overall_grade"] = "C"
            elif success_rate >= 0.50:
                validation["overall_grade"] = "D"
            else:
                validation["overall_grade"] = "F"

        return validation

    @staticmethod
    def create_validation_report(validation_results: Dict[str, Dict[str, Any]]) -> str:
        """
        Create a comprehensive validation report from multiple validation results.

        Args:
            validation_results: Dictionary mapping validation names to results

        Returns:
            Formatted validation report as string
        """
        report_lines = [
            "=" * 80,
            "RUST INTEGRATION VALIDATION REPORT",
            "=" * 80,
            ""
        ]

        # Summary section
        report_lines.append("VALIDATION SUMMARY:")
        total_validations = len(validation_results)
        passed_validations = 0

        for validation_name, results in validation_results.items():
            if "validity_ratio" in results:
                validity = results["validity_ratio"]
                status = "PASS" if validity >= 0.9 else "WARN" if validity >= 0.7 else "FAIL"
                if status == "PASS":
                    passed_validations += 1
                report_lines.append(f"  {validation_name:<30}: {status} ({validity:.1%})")
            elif "overall_match" in results:
                match = results["overall_match"]
                status = "PASS" if match else "FAIL"
                if status == "PASS":
                    passed_validations += 1
                report_lines.append(f"  {validation_name:<30}: {status}")
            elif "meets_targets" in results:
                meets = results["meets_targets"]
                grade = results.get("overall_grade", "?")
                status = "PASS" if meets else "FAIL"
                if status == "PASS":
                    passed_validations += 1
                report_lines.append(f"  {validation_name:<30}: {status} (Grade: {grade})")
            else:
                report_lines.append(f"  {validation_name:<30}: UNKNOWN")

        overall_success_rate = passed_validations / total_validations if total_validations > 0 else 0.0
        report_lines.append("")
        report_lines.append(f"Overall Success Rate: {overall_success_rate:.1%} ({passed_validations}/{total_validations})")
        report_lines.append("")

        # Detailed results section
        report_lines.append("DETAILED RESULTS:")
        for validation_name, results in validation_results.items():
            report_lines.append(f"\n{validation_name.upper()}:")

            if "validity_ratio" in results:
                # Data validation results
                report_lines.append(f"  Total Items: {results.get('total_formids', results.get('total_plugins', results.get('total_matches', 0)))}")
                report_lines.append(f"  Valid Items: {results.get('valid_formids', results.get('valid_plugins', results.get('valid_matches', 0)))}")
                report_lines.append(f"  Invalid Items: {results.get('invalid_formids', results.get('invalid_plugins', results.get('invalid_matches', 0)))}")
                report_lines.append(f"  Validity Ratio: {results['validity_ratio']:.1%}")

                errors = results.get('validation_errors', results.get('plugin_errors', results.get('match_errors', [])))
                if errors:
                    report_lines.append("  Errors:")
                    for error in errors[:5]:  # Show first 5 errors
                        report_lines.append(f"    - {error}")
                    if len(errors) > 5:
                        report_lines.append(f"    ... and {len(errors) - 5} more errors")

            elif "overall_match" in results:
                # Comparison results
                report_lines.append(f"  Overall Match: {results['overall_match']}")
                report_lines.append(f"  Match Ratio: {results.get('match_ratio', 0.0):.1%}")

                if results.get('differences'):
                    report_lines.append("  Differences:")
                    for diff in results['differences'][:5]:
                        report_lines.append(f"    - {diff}")
                    if len(results['differences']) > 5:
                        report_lines.append(f"    ... and {len(results['differences']) - 5} more differences")

            elif "meets_targets" in results:
                # Performance results
                report_lines.append(f"  Meets Targets: {results['meets_targets']}")
                report_lines.append(f"  Overall Grade: {results.get('overall_grade', 'N/A')}")

                if results.get('target_violations'):
                    report_lines.append("  Target Violations:")
                    for violation in results['target_violations']:
                        report_lines.append(f"    - {violation}")

        report_lines.extend([
            "",
            "=" * 80,
            f"Report generated at {__import__('datetime').datetime.now().isoformat()}",
            "=" * 80
        ])

        return "\n".join(report_lines)
