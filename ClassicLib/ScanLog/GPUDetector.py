"""
GPU detector module for CLASSIC.

This module detects GPU information from system specs including:
- Parsing system specs for GPU information
- Determining GPU manufacturer
- Identifying rival GPU for compatibility checks
"""

from typing import Literal


def scan_log_gpu(segment_system: list[str]) -> tuple[str, Literal["nvidia", "amd"] | None]:
    """
    Scan the log to determine the GPU information and its rival.
    
    This method analyzes a list of system log segments to identify the primary
    graphics processing unit (GPU) being used. It also determines the rival GPU
    manufacturer based on the GPU identified. If the GPU information cannot be
    determined, the method returns "Unknown" and the rival GPU is set to None.
    
    Args:
        segment_system: A list of log segments containing system
            information. Each log segment is expected to contain details about
            hardware components including GPUs.
            
    Returns:
        Tuple containing:
        - GPU name ("AMD", "Nvidia", or "Unknown")
        - Rival GPU manufacturer ("nvidia", "amd", or None)
    """
    gpu: str
    gpu_rival: Literal["nvidia", "amd"] | None
    
    if any("GPU #1" in elem and "AMD" in elem for elem in segment_system):
        gpu = "AMD"
        gpu_rival = "nvidia"
    elif any("GPU #1" in elem and "Nvidia" in elem for elem in segment_system):
        gpu = "Nvidia"
        gpu_rival = "amd"
    else:
        gpu = "Unknown"
        gpu_rival = None
        
    return gpu, gpu_rival
    

def get_gpu_info(segment_system: list[str]) -> dict[str, str]:
    """
    Extract detailed GPU information from system segment.
    
    Args:
        segment_system: System specification lines
        
    Returns:
        Dictionary containing GPU details
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