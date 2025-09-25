"""
Realistic test data generator for comprehensive CLASSIC benchmarking.

This module generates authentic test data that represents real-world usage
patterns of CLASSIC, including various crash log formats, plugin configurations,
FormID patterns, and system scenarios.

The generator creates:
- Crash logs with realistic structure and content
- Plugin load orders with authentic mod patterns
- FormID databases with proper hierarchies
- Call stacks with realistic memory addresses
- System information reflecting actual configurations
- Error conditions and edge cases for robustness testing

Data generation is configurable for different:
- Test sizes (from tiny validation sets to large stress tests)
- Complexity levels (simple to highly complex scenarios)
- Error rates (clean data to heavily corrupted scenarios)
- Game types (Fallout 4, Skyrim, etc.)
"""

from __future__ import annotations

import logging
import random
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Set, Tuple

logger = logging.getLogger(__name__)


class RealisticDataGenerator:
    """
    Comprehensive generator for realistic CLASSIC test data.

    This generator creates authentic test scenarios that closely match
    real-world usage patterns, enabling accurate performance testing
    and validation of optimization improvements.
    """

    def __init__(self, seed: Optional[int] = None):
        """
        Initialize the realistic data generator.

        Args:
            seed: Random seed for reproducible data generation
        """
        if seed is not None:
            random.seed(seed)

        # Realistic game data templates
        self.game_templates = {
            'fallout4': {
                'game_exe': 'Fallout4.exe',
                'crashgen_name': 'Buffout 4',
                'xse_name': 'F4SE',
                'xse_version': '0.6.23',
                'game_version': '1.10.163.0',
                'steam_version': True,
            },
            'skyrimse': {
                'game_exe': 'SkyrimSE.exe',
                'crashgen_name': 'Crash Logger SSE',
                'xse_name': 'SKSE64',
                'xse_version': '2.2.6',
                'game_version': '1.6.640.0',
                'steam_version': True,
            },
            'skyrim': {
                'game_exe': 'TESV.exe',
                'crashgen_name': 'SKSE Crash Fixes',
                'xse_name': 'SKSE',
                'xse_version': '1.7.3',
                'game_version': '1.9.32.0',
                'steam_version': True,
            },
        }

        # Common crash patterns and their typical contexts
        self.crash_patterns = {
            'access_violation': {
                'exception_code': 'EXCEPTION_ACCESS_VIOLATION',
                'typical_causes': ['null_pointer', 'invalid_memory', 'use_after_free'],
                'frequency': 0.6,  # 60% of crashes
            },
            'stack_overflow': {
                'exception_code': 'EXCEPTION_STACK_OVERFLOW',
                'typical_causes': ['infinite_recursion', 'large_local_variables'],
                'frequency': 0.15,
            },
            'illegal_instruction': {
                'exception_code': 'EXCEPTION_ILLEGAL_INSTRUCTION',
                'typical_causes': ['corrupted_memory', 'bad_plugin'],
                'frequency': 0.10,
            },
            'breakpoint': {
                'exception_code': 'EXCEPTION_BREAKPOINT',
                'typical_causes': ['debug_assertion', 'forced_crash'],
                'frequency': 0.10,
            },
            'other': {
                'exception_code': 'EXCEPTION_UNKNOWN',
                'typical_causes': ['hardware_failure', 'driver_issue'],
                'frequency': 0.05,
            },
        }

        # Realistic module patterns (common DLLs and executables)
        self.common_modules = [
            # Game modules
            ('Fallout4.exe', 'main_executable'),
            ('F4SE_1_10_163.dll', 'script_extender'),

            # Windows system modules
            ('ntdll.dll', 'system'),
            ('kernel32.dll', 'system'),
            ('user32.dll', 'system'),
            ('d3d11.dll', 'graphics'),
            ('dxgi.dll', 'graphics'),

            # Common mod framework DLLs
            ('BufOutOfSightNE.dll', 'mod_framework'),
            ('XAudio2_7.dll', 'audio'),
            ('steam_api64.dll', 'steam'),

            # Plugin DLLs
            ('achievements.dll', 'plugin'),
            ('BetterConsole.dll', 'plugin'),
        ]

        # FormID patterns for different plugin types
        self.formid_patterns = {
            'master_files': {
                'fallout4_esm': range(0x00000000, 0x01000000),  # 00xxxxxx
                'dlc_esm': range(0x01000000, 0x06000000),       # 01-05xxxxxx
            },
            'plugin_files': {
                'esp_files': range(0x06000000, 0xFE000000),     # 06-FDxxxxxx
                'light_plugins': range(0xFE000000, 0xFF000000), # FExxxxxx
                'temporary': range(0xFF000000, 0xFFFFFFFF),     # FFxxxxxx
            }
        }

        # Realistic plugin name patterns
        self.plugin_name_patterns = {
            'official': [
                'Fallout4.esm', 'DLCRobot.esm', 'DLCworkshop01.esm',
                'DLCCoast.esm', 'DLCworkshop02.esm', 'DLCworkshop03.esm',
                'DLCNukaWorld.esm'
            ],
            'framework': [
                'Unofficial Fallout 4 Patch.esp', 'F4SE.esp',
                'MCM.esp', 'HUDFramework.esp'
            ],
            'content': [
                'WeaponModExpansion.esp', 'SettlementExpansion.esp',
                'QuestMod{}.esp', 'NPCOverhaul{}.esp'
            ],
            'utility': [
                'BetterInventory.esp', 'FastTravel.esp',
                'AutoSave{}.esp', 'PerformanceFix{}.esp'
            ],
        }

    def generate_comprehensive_dataset(
        self,
        num_crash_logs: int = 50,
        lines_per_log: int = 1000,
        num_plugins: int = 200,
        include_formids: bool = True,
        include_edge_cases: bool = True,
        corruption_probability: float = 0.02,
        vary_formats: bool = True,
        game_type: str = 'fallout4'
    ) -> Dict[str, Any]:
        """
        Generate a comprehensive dataset for benchmarking.

        Args:
            num_crash_logs: Number of crash logs to generate
            lines_per_log: Average lines per crash log
            num_plugins: Number of plugins in load order
            include_formids: Whether to include FormID patterns
            include_edge_cases: Whether to include edge cases and errors
            corruption_probability: Probability of data corruption (0.0-1.0)
            vary_formats: Whether to vary log formats
            game_type: Type of game data to generate

        Returns:
            Comprehensive dataset with all benchmark data
        """
        logger.info(f"Generating comprehensive dataset: {num_crash_logs} logs, {lines_per_log} lines each")

        dataset = {
            'metadata': {
                'generation_time': datetime.now().isoformat(),
                'generator_version': '1.0',
                'game_type': game_type,
                'num_crash_logs': num_crash_logs,
                'lines_per_log': lines_per_log,
                'num_plugins': num_plugins,
                'include_formids': include_formids,
                'include_edge_cases': include_edge_cases,
                'corruption_probability': corruption_probability,
            },
            'crash_logs': [],
            'callstacks': [],
            'plugin_segments': [],
            'plugins': {},
            'formid_queries': [],
            'test_files': [],
            'report_fragments': [],
        }

        # Generate game template
        game_template = self.game_templates.get(game_type, self.game_templates['fallout4'])

        # Generate plugin load order
        plugins = self._generate_plugin_load_order(num_plugins, game_type)
        dataset['plugins'] = plugins

        # Generate crash logs with realistic content
        for i in range(num_crash_logs):
            # Vary log complexity
            log_lines = lines_per_log + random.randint(-lines_per_log//4, lines_per_log//4)

            crash_log = self._generate_realistic_crash_log(
                log_lines, game_template, plugins, include_formids,
                corruption_probability if random.random() < corruption_probability else 0.0,
                vary_formats
            )

            dataset['crash_logs'].append(crash_log['log_lines'])
            dataset['callstacks'].append(crash_log['callstack'])
            dataset['plugin_segments'].append(crash_log['plugin_segment'])

            # Extract FormIDs for database queries
            if include_formids and crash_log.get('formids'):
                dataset['formid_queries'].extend(crash_log['formids'][:20])  # Limit per log

            # Generate report fragments
            dataset['report_fragments'].append([
                f"Crash Report {i+1}",
                f"Game: {game_template['game_exe']}",
                f"Error: {crash_log.get('error_type', 'Unknown')}",
                f"FormIDs: {len(crash_log.get('formids', []))}",
                f"Plugins: {len(plugins)}",
                "--- End Report ---"
            ])

        # Generate test files for file I/O benchmarking
        for i in range(min(50, num_crash_logs // 4)):  # Fewer files for I/O testing
            file_content = self._generate_test_file_content(i, game_type)
            dataset['test_files'].append({
                'filename': f'test_file_{i:03d}.txt',
                'content': file_content,
                'size': len(file_content),
                'encoding': 'utf-8',
            })

        # Add edge cases if requested
        if include_edge_cases:
            dataset = self._add_edge_cases(dataset, corruption_probability)

        # Remove duplicates from FormID queries
        dataset['formid_queries'] = list(set(dataset['formid_queries']))[:1000]  # Limit total

        logger.info(f"Dataset generation complete:")
        logger.info(f"  Crash logs: {len(dataset['crash_logs'])}")
        logger.info(f"  Total lines: {sum(len(log) for log in dataset['crash_logs'])}")
        logger.info(f"  Plugins: {len(dataset['plugins'])}")
        logger.info(f"  FormID queries: {len(dataset['formid_queries'])}")
        logger.info(f"  Test files: {len(dataset['test_files'])}")

        return dataset

    def _generate_realistic_crash_log(
        self,
        target_lines: int,
        game_template: Dict[str, Any],
        plugins: Dict[str, str],
        include_formids: bool,
        corruption_probability: float,
        vary_formats: bool
    ) -> Dict[str, Any]:
        """
        Generate a single realistic crash log with all segments.

        Args:
            target_lines: Target number of lines in the log
            game_template: Game-specific template data
            plugins: Plugin load order
            include_formids: Whether to include FormID patterns
            corruption_probability: Probability of corruption per line
            vary_formats: Whether to vary the log format

        Returns:
            Dictionary with complete crash log data
        """
        crash_data = {
            'log_lines': [],
            'callstack': [],
            'plugin_segment': [],
            'formids': [],
            'error_type': '',
        }

        # Choose crash type
        crash_type = self._choose_weighted_crash_type()
        crash_data['error_type'] = crash_type

        # Generate log header
        header_lines = self._generate_crash_log_header(game_template, crash_type, vary_formats)
        crash_data['log_lines'].extend(header_lines)

        # Generate system information segment
        system_lines = self._generate_system_info_segment()
        crash_data['log_lines'].extend(system_lines)

        # Generate call stack segment
        callstack_lines, formids = self._generate_callstack_segment(
            target_lines // 4, game_template, include_formids
        )
        crash_data['log_lines'].extend(callstack_lines)
        crash_data['callstack'] = callstack_lines
        crash_data['formids'].extend(formids)

        # Generate modules segment
        modules_lines = self._generate_modules_segment(target_lines // 6)
        crash_data['log_lines'].extend(modules_lines)

        # Generate plugins segment
        plugin_lines = self._generate_plugins_segment(plugins, game_template)
        crash_data['log_lines'].extend(plugin_lines)
        crash_data['plugin_segment'] = plugin_lines

        # Pad to target length with additional detail
        current_lines = len(crash_data['log_lines'])
        if current_lines < target_lines:
            padding_lines = self._generate_padding_lines(target_lines - current_lines, include_formids)
            crash_data['log_lines'].extend(padding_lines)
            crash_data['formids'].extend([line for line in padding_lines if any(c in line for c in '0123456789ABCDEF')])

        # Apply corruption if specified
        if corruption_probability > 0:
            crash_data['log_lines'] = self._apply_corruption(crash_data['log_lines'], corruption_probability)

        return crash_data

    def _choose_weighted_crash_type(self) -> str:
        """Choose crash type based on realistic frequency weights."""
        rand_val = random.random()
        cumulative = 0.0

        for crash_type, data in self.crash_patterns.items():
            cumulative += data['frequency']
            if rand_val <= cumulative:
                return crash_type

        return 'access_violation'  # Fallback

    def _generate_crash_log_header(
        self,
        game_template: Dict[str, Any],
        crash_type: str,
        vary_formats: bool
    ) -> List[str]:
        """Generate realistic crash log header section."""
        crash_info = self.crash_patterns[crash_type]
        exception_code = crash_info['exception_code']

        # Generate random but realistic memory address
        crash_address = f"0x{random.randint(0x100000, 0xFFFFFFFF):08X}"

        header = [
            f"{game_template['crashgen_name']} v1.28.6",
            f"{game_template['game_exe']} v{game_template['game_version']}",
            f"{game_template['xse_name']} v{game_template['xse_version']}",
            "",
            f"Unhandled exception \"{exception_code}\" at {crash_address} {game_template['game_exe']}+{random.randint(1000000, 9999999):07X}",
        ]

        # Add timestamp with some variation
        crash_time = datetime.now() - timedelta(
            days=random.randint(0, 30),
            hours=random.randint(0, 23),
            minutes=random.randint(0, 59)
        )
        header.append(f"Crash occurred at {crash_time.strftime('%Y-%m-%d %H:%M:%S')}")
        header.append("")

        # Add compatibility section header
        header.append("\t[Compatibility]")
        header.append("")

        return header

    def _generate_system_info_segment(self) -> List[str]:
        """Generate realistic system information segment."""
        # Realistic system configurations
        cpu_models = [
            "Intel(R) Core(TM) i7-12700K CPU @ 3.60GHz",
            "AMD Ryzen 7 5800X 8-Core Processor",
            "Intel(R) Core(TM) i5-11600K CPU @ 3.90GHz",
            "AMD Ryzen 5 5600X 6-Core Processor",
        ]

        gpu_models = [
            "NVIDIA GeForce RTX 4080",
            "NVIDIA GeForce RTX 3070 Ti",
            "AMD Radeon RX 7800 XT",
            "NVIDIA GeForce RTX 4070 SUPER",
        ]

        ram_amounts = [16384, 32768, 65536]  # 16GB, 32GB, 64GB
        win_versions = [
            "Windows 11 Professional (Build 22621.2715)",
            "Windows 10 Professional (Build 19044.3570)",
            "Windows 11 Home (Build 22000.2538)",
        ]

        system_info = [
            "SYSTEM SPECS:",
            f"\tOS: {random.choice(win_versions)}",
            f"\tCPU: {random.choice(cpu_models)}",
            f"\tRAM: {random.choice(ram_amounts)} MB ({random.randint(12000, ram_amounts[-1]-4000)} MB available)",
            f"\tGPU: {random.choice(gpu_models)} (Driver: {random.randint(520, 560)}.{random.randint(10, 99)})",
            f"\tDISK: {random.randint(1000, 4000)} GB available / {random.randint(2000, 8000)} GB total",
            "",
        ]

        return system_info

    def _generate_callstack_segment(
        self,
        target_lines: int,
        game_template: Dict[str, Any],
        include_formids: bool
    ) -> Tuple[List[str], List[str]]:
        """
        Generate realistic call stack segment with FormID patterns.

        Returns:
            Tuple of (callstack_lines, formids_found)
        """
        callstack = ["PROBABLE CALL STACK:"]
        formids = []

        # Generate stack frames with realistic patterns
        for i in range(target_lines - 1):
            frame_num = i
            module_name, module_type = random.choice(self.common_modules)

            # Generate realistic memory addresses
            base_addr = random.randint(0x7FF600000000, 0x7FF6FFFFFFFF)
            offset = random.randint(0x1000, 0x9FFFFF)
            full_addr = base_addr + offset

            # Create stack frame
            frame = f"\t[{frame_num:2d}] 0x{full_addr:012X} {module_name}+0x{offset:06X}"

            # Add FormIDs to some frames (especially game executable frames)
            if include_formids and (module_type == 'main_executable' or random.random() < 0.3):
                formid = self._generate_realistic_formid()
                formids.append(formid)

                # Add FormID reference in various realistic formats
                formid_formats = [
                    f" -> FormID: {formid}",
                    f" [FormID: {formid}]",
                    f" ({formid})",
                ]
                frame += random.choice(formid_formats)

            # Add function names occasionally for realism
            if random.random() < 0.4:
                function_names = [
                    "UpdateAnimation", "ProcessInput", "RenderFrame",
                    "LoadAsset", "ProcessScript", "HandleCollision",
                    "UpdatePhysics", "PlaySound", "SaveGame"
                ]
                frame += f" [{random.choice(function_names)}]"

            callstack.append(frame)

        callstack.append("")  # Empty line after call stack
        return callstack, formids

    def _generate_realistic_formid(self) -> str:
        """Generate a realistic FormID based on plugin patterns."""
        # Choose FormID type based on realistic distribution
        formid_type = random.choices(
            ['master_files', 'plugin_files'],
            weights=[0.4, 0.6]  # 40% master files, 60% plugin files
        )[0]

        if formid_type == 'master_files':
            if random.random() < 0.7:  # 70% base game
                formid_range = self.formid_patterns['master_files']['fallout4_esm']
            else:  # 30% DLC
                formid_range = self.formid_patterns['master_files']['dlc_esm']
        else:
            sub_type = random.choices(
                ['esp_files', 'light_plugins', 'temporary'],
                weights=[0.8, 0.15, 0.05]
            )[0]
            formid_range = self.formid_patterns['plugin_files'][sub_type]

        # Generate FormID within range
        formid_int = random.choice(list(formid_range)[:10000])  # Limit range for performance
        return f"{formid_int:08X}"

    def _generate_modules_segment(self, target_lines: int) -> List[str]:
        """Generate realistic modules/DLL segment."""
        modules = ["MODULES:"]

        # Add game and system modules
        used_modules = set()
        for i in range(min(target_lines - 1, len(self.common_modules) * 2)):
            module_name, module_type = random.choice(self.common_modules)

            # Avoid exact duplicates but allow similar ones
            module_key = f"{module_name}_{i//3}"  # Allow some repetition
            if module_key in used_modules:
                continue
            used_modules.add(module_key)

            # Generate realistic module information
            base_addr = random.randint(0x7FF600000000, 0x7FF6FFFFFFFF)
            size = random.randint(0x10000, 0x2000000)  # 64KB to 32MB

            modules.append(f"\t0x{base_addr:012X} - 0x{base_addr + size:012X} {module_name}")

        modules.append("")
        return modules

    def _generate_plugins_segment(
        self,
        plugins: Dict[str, str],
        game_template: Dict[str, Any]
    ) -> List[str]:
        """Generate realistic plugins segment from load order."""
        segment = [f"{game_template['xse_name'].upper()} PLUGINS:"]

        # Add some XSE plugins
        xse_plugins = [
            f"achievements.dll v1.3.0.0",
            f"BetterConsole.dll v1.2.1.0",
            f"BufOutOfSightNE.dll v2.1.0.0",
        ]

        for plugin in xse_plugins[:random.randint(2, len(xse_plugins))]:
            segment.append(f"\t{plugin}")

        segment.append("")
        segment.append("PLUGINS:")

        # Add plugin load order
        for load_order, plugin_name in sorted(plugins.items()):
            # Add plugin flags and metadata
            flags = []
            if plugin_name.endswith('.esm'):
                flags.append('Master')
            if plugin_name.endswith('.esl'):
                flags.append('Light')
            if random.random() < 0.1:  # 10% chance of being active
                flags.append('Active')

            flag_str = f" [{', '.join(flags)}]" if flags else ""
            segment.append(f"\t[{load_order}] {plugin_name}{flag_str}")

        return segment

    def _generate_plugin_load_order(self, num_plugins: int, game_type: str) -> Dict[str, str]:
        """
        Generate realistic plugin load order with authentic naming patterns.

        Args:
            num_plugins: Target number of plugins
            game_type: Type of game for appropriate plugins

        Returns:
            Dictionary mapping load order indices to plugin names
        """
        plugins = {}
        used_names = set()

        # Start with official plugins (always first)
        official_plugins = self.plugin_name_patterns['official'][:7]  # Limit official count
        for i, plugin in enumerate(official_plugins):
            plugins[f"{i:02X}"] = plugin
            used_names.add(plugin.lower())

        current_index = len(official_plugins)

        # Add framework plugins
        framework_plugins = self.plugin_name_patterns['framework']
        for plugin in framework_plugins:
            if current_index >= num_plugins:
                break
            if plugin.lower() not in used_names:
                plugins[f"{current_index:02X}"] = plugin
                used_names.add(plugin.lower())
                current_index += 1

        # Add content and utility plugins with variations
        content_patterns = self.plugin_name_patterns['content'] + self.plugin_name_patterns['utility']

        for pattern in content_patterns * 10:  # Repeat patterns to generate enough plugins
            if current_index >= num_plugins:
                break

            # Generate plugin name with variation
            if '{}' in pattern:
                plugin_name = pattern.format(random.randint(1, 999))
            else:
                plugin_name = pattern

            # Add random prefixes/suffixes occasionally
            if random.random() < 0.3:
                prefixes = ['Enhanced', 'Improved', 'Better', 'Ultimate', 'Advanced']
                plugin_name = f"{random.choice(prefixes)} {plugin_name}"

            # Ensure unique name
            base_name = plugin_name.lower()
            counter = 1
            final_name = plugin_name
            while base_name in used_names:
                final_name = f"{plugin_name} v{counter}"
                base_name = final_name.lower()
                counter += 1

            plugins[f"{current_index:02X}"] = final_name
            used_names.add(base_name)
            current_index += 1

        return plugins

    def _generate_test_file_content(self, file_index: int, game_type: str) -> str:
        """Generate content for file I/O benchmarking."""
        # Simulate different types of files CLASSIC might process
        file_types = ['crash_log', 'plugin_list', 'config_file', 'data_file']
        file_type = random.choice(file_types)

        if file_type == 'crash_log':
            # Simplified crash log content
            lines = [
                f"Crash Report #{file_index}",
                f"Game: {self.game_templates[game_type]['game_exe']}",
                "Exception: EXCEPTION_ACCESS_VIOLATION",
                "Call Stack:",
            ]
            # Add call stack entries
            for i in range(random.randint(20, 80)):
                addr = random.randint(0x7FF600000000, 0x7FF6FFFFFFFF)
                lines.append(f"  [{i:02d}] 0x{addr:012X} SomeModule.dll+0x{random.randint(1000, 999999):06X}")

        elif file_type == 'plugin_list':
            # Plugin list content
            lines = [f"Plugin List - File {file_index}", "Load Order:"]
            for i in range(random.randint(50, 200)):
                plugin = f"SomePlugin{i:03d}.esp"
                lines.append(f"  [{i:02X}] {plugin}")

        elif file_type == 'config_file':
            # Configuration file content
            lines = [
                f"[Configuration File {file_index}]",
                f"Version=1.{random.randint(0, 9)}",
                f"EnableFeature={random.choice(['true', 'false'])}",
                f"MaxMemory={random.randint(1024, 8192)}MB",
            ]
            # Add random config entries
            for i in range(random.randint(20, 100)):
                lines.append(f"Setting{i}=Value{random.randint(1, 1000)}")

        else:  # data_file
            # Generic data file
            lines = [f"Data File {file_index}", "Data Entries:"]
            for i in range(random.randint(100, 500)):
                lines.append(f"Entry{i:04d}={uuid.uuid4().hex[:8]}")

        return "\n".join(lines)

    def _generate_padding_lines(self, num_lines: int, include_formids: bool) -> List[str]:
        """Generate additional lines to reach target line count."""
        padding = []

        for i in range(num_lines):
            line_types = ['debug_info', 'memory_info', 'thread_info', 'additional_data']
            line_type = random.choice(line_types)

            if line_type == 'debug_info':
                addr = random.randint(0x1000, 0xFFFFFF)
                padding.append(f"\tDebug Info: Address 0x{addr:06X}, Size: {random.randint(64, 4096)} bytes")

            elif line_type == 'memory_info':
                padding.append(f"\tMemory: {random.randint(1, 100)}% usage, "
                             f"{random.randint(8, 64)}GB total, {random.randint(2, 32)}GB available")

            elif line_type == 'thread_info':
                thread_id = random.randint(1000, 9999)
                padding.append(f"\tThread {thread_id}: State=Running, Priority=Normal")

            else:  # additional_data
                if include_formids and random.random() < 0.4:
                    formid = self._generate_realistic_formid()
                    padding.append(f"\tAdditional FormID reference: {formid}")
                else:
                    padding.append(f"\tAdditional data entry {i}: {uuid.uuid4().hex[:16]}")

        return padding

    def _apply_corruption(self, lines: List[str], corruption_probability: float) -> List[str]:
        """Apply realistic corruption patterns to simulate real-world data issues."""
        corrupted_lines = []

        for line in lines:
            if random.random() < corruption_probability:
                # Apply various corruption types
                corruption_type = random.choice(['truncate', 'garble', 'duplicate', 'empty'])

                if corruption_type == 'truncate':
                    # Truncate line at random point
                    if len(line) > 10:
                        truncate_point = random.randint(10, len(line) - 5)
                        line = line[:truncate_point]

                elif corruption_type == 'garble':
                    # Replace some characters with garbage
                    garbled = list(line)
                    num_garbled = min(5, len(line) // 4)
                    for _ in range(num_garbled):
                        if len(garbled) > 0:
                            pos = random.randint(0, len(garbled) - 1)
                            garbled[pos] = random.choice('���???###@@@')
                    line = ''.join(garbled)

                elif corruption_type == 'duplicate':
                    # Duplicate part of the line
                    if len(line) > 20:
                        dup_start = random.randint(0, len(line) // 2)
                        dup_end = random.randint(dup_start, len(line) - 10)
                        line = line + line[dup_start:dup_end]

                elif corruption_type == 'empty':
                    # Make line empty or very short
                    line = random.choice(['', '?', '???', '---CORRUPTED---'])

            corrupted_lines.append(line)

        return corrupted_lines

    def _add_edge_cases(self, dataset: Dict[str, Any], corruption_probability: float) -> Dict[str, Any]:
        """Add edge cases and stress-test scenarios to the dataset."""
        logger.debug("Adding edge cases and stress test scenarios")

        # Add extremely large crash log
        if len(dataset['crash_logs']) > 0:
            large_log = dataset['crash_logs'][0] * 5  # Multiply first log by 5
            dataset['crash_logs'].append(large_log)

        # Add extremely small crash log
        tiny_log = [
            "Minimal crash log",
            "EXCEPTION_ACCESS_VIOLATION",
            "No additional data"
        ]
        dataset['crash_logs'].append(tiny_log)

        # Add highly corrupted crash log
        if len(dataset['crash_logs']) > 1:
            corrupted_log = self._apply_corruption(dataset['crash_logs'][1], 0.5)  # 50% corruption
            dataset['crash_logs'].append(corrupted_log)

        # Add edge case FormIDs
        edge_formids = [
            "00000000",  # NULL FormID
            "FFFFFFFF",  # Invalid FormID
            "DEADBEEF",  # Common placeholder
            "CAFEBABE",  # Another placeholder
            "12345678",  # Simple pattern
            "ABCDEFGH",  # Invalid hex
        ]
        dataset['formid_queries'].extend(edge_formids)

        # Add edge case plugins
        edge_plugins = {
            "FE": "EdgeCase_Light.esl",
            "FF": "EdgeCase_Temp.esp",
            "00": "EdgeCase_Master.esm",
        }
        dataset['plugins'].update(edge_plugins)

        # Add empty test file
        dataset['test_files'].append({
            'filename': 'empty_file.txt',
            'content': '',
            'size': 0,
            'encoding': 'utf-8',
        })

        # Add large test file
        large_content = "Large file content line.\n" * 10000  # 10k lines
        dataset['test_files'].append({
            'filename': 'large_file.txt',
            'content': large_content,
            'size': len(large_content),
            'encoding': 'utf-8',
        })

        return dataset


# Convenience functions for quick data generation
def generate_small_dataset(seed: Optional[int] = None) -> Dict[str, Any]:
    """Generate small dataset for quick testing."""
    generator = RealisticDataGenerator(seed=seed)
    return generator.generate_comprehensive_dataset(
        num_crash_logs=10,
        lines_per_log=100,
        num_plugins=50,
        include_formids=True,
        include_edge_cases=False,
        corruption_probability=0.01
    )


def generate_medium_dataset(seed: Optional[int] = None) -> Dict[str, Any]:
    """Generate medium dataset for standard benchmarking."""
    generator = RealisticDataGenerator(seed=seed)
    return generator.generate_comprehensive_dataset(
        num_crash_logs=50,
        lines_per_log=500,
        num_plugins=150,
        include_formids=True,
        include_edge_cases=True,
        corruption_probability=0.02
    )


def generate_large_dataset(seed: Optional[int] = None) -> Dict[str, Any]:
    """Generate large dataset for stress testing."""
    generator = RealisticDataGenerator(seed=seed)
    return generator.generate_comprehensive_dataset(
        num_crash_logs=200,
        lines_per_log=1000,
        num_plugins=300,
        include_formids=True,
        include_edge_cases=True,
        corruption_probability=0.02
    )


def generate_stress_dataset(seed: Optional[int] = None) -> Dict[str, Any]:
    """Generate maximum size dataset for stress testing."""
    generator = RealisticDataGenerator(seed=seed)
    return generator.generate_comprehensive_dataset(
        num_crash_logs=1000,
        lines_per_log=2000,
        num_plugins=500,
        include_formids=True,
        include_edge_cases=True,
        corruption_probability=0.03
    )


if __name__ == "__main__":
    # Example usage and testing
    print("Generating sample dataset...")
    generator = RealisticDataGenerator(seed=42)
    sample_data = generator.generate_comprehensive_dataset(
        num_crash_logs=5,
        lines_per_log=50,
        num_plugins=20
    )

    print(f"Generated {len(sample_data['crash_logs'])} crash logs")
    print(f"First log has {len(sample_data['crash_logs'][0])} lines")
    print(f"Generated {len(sample_data['plugins'])} plugins")
    print(f"Generated {len(sample_data['formid_queries'])} FormID queries")

    # Show sample of first crash log
    print("\nFirst few lines of first crash log:")
    for i, line in enumerate(sample_data['crash_logs'][0][:10]):
        print(f"  {i+1:2d}: {line}")
    print("  ...")

    # Show sample plugins
    print(f"\nSample plugins (first 5):")
    for load_order, plugin in list(sample_data['plugins'].items())[:5]:
        print(f"  [{load_order}] {plugin}")
    print("  ...")
