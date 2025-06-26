"""
GPU detector module for CLASSIC.

This module detects GPU information from system specs including:
- Parsing system specs for GPU information
- Determining GPU manufacturer
- Identifying rival GPU for compatibility checks
"""


def get_gpu_info(segment_system: list[str]) -> dict[str, str | None]:
    """
    Extracts and processes GPU information from a given system specification.

    This function takes a list of system specification data typically in string
    format and identifies GPU-related details such as the primary GPU name,
    secondary GPU name, GPU manufacturer, and the rival manufacturer. It uses
    pattern matching to extract GPU details based on keywords present in the
    system information. Default values are used when the required information
    is not present or cannot be determined.

    Parameters:
    segment_system: list[str]
        A list of strings containing system specification information. Each
        string represents a line of system description that may or may not
        include GPU-related details.

    Returns:
    dict[str, str]
        A dictionary containing GPU information with the following keys:
            - primary: str
                The name of the primary GPU. If not found, defaults to "Unknown".
            - secondary: str
                The name of the secondary GPU. If not found, defaults to None.
            - manufacturer: str
                The name of the GPU manufacturer (e.g., "AMD", "Nvidia"). If not
                found, defaults to "Unknown".
            - rival: str
                The name of the rival GPU manufacturer. If not found, defaults to
                None.
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
