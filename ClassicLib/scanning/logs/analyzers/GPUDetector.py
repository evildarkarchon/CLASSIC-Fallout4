"""GPU detector module for CLASSIC.

This module detects GPU information from system specs including:
- Parsing system specs for GPU information
- Determining GPU manufacturer
- Identifying rival GPU for compatibility checks
"""


def get_gpu_info(segment_system: list[str]) -> dict[str, str | None]:
    """Extract and process GPU information from system specification.

    Identifies GPU-related details such as primary GPU name, secondary GPU
    name, GPU manufacturer, and the rival manufacturer using pattern matching
    on system specification data.

    Args:
        segment_system: A list of strings containing system specification
            information. Each string is a line that may contain GPU details.

    Returns:
        A dictionary containing GPU information with keys:
        - primary: Primary GPU name (defaults to "Unknown")
        - secondary: Secondary GPU name (defaults to None)
        - manufacturer: GPU manufacturer e.g., "AMD", "Nvidia" (defaults to "Unknown")
        - rival: Rival GPU manufacturer (defaults to None)

    """
    gpu_info: dict[str, str | None] = {
        "primary": "Unknown",
        "secondary": None,
        "manufacturer": "Unknown",
        "rival": None,
    }

    for line in segment_system:
        if "GPU #1" in line:
            if "AMD" in line:
                gpu_info["primary"] = "AMD"
                gpu_info["manufacturer"] = "AMD"
                gpu_info["rival"] = "nvidia"
            elif "Nvidia" in line:
                gpu_info["primary"] = "Nvidia"
                gpu_info["manufacturer"] = "Nvidia"
                gpu_info["rival"] = "amd"

            # Extract full GPU name if possible
            if ":" in line:
                gpu_info["primary"] = line.split(":", 1)[1].strip()

        elif "GPU #2" in line and ":" in line:
            gpu_info["secondary"] = line.split(":", 1)[1].strip()

    return gpu_info
