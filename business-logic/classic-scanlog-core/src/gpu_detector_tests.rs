use super::*;

#[test]
fn test_amd_gpu_detection() {
    let system_lines = vec!["GPU #1: AMD Radeon RX 6800 XT".to_string()];

    let gpu_info = GpuDetector::get_gpu_info(&system_lines);

    assert_eq!(gpu_info.manufacturer, "AMD");
    assert_eq!(gpu_info.primary, "AMD Radeon RX 6800 XT");
    assert_eq!(gpu_info.rival, Some("nvidia".to_string()));
}

#[test]
fn test_nvidia_gpu_detection() {
    let system_lines = vec!["GPU #1: Nvidia GeForce RTX 3080".to_string()];

    let gpu_info = GpuDetector::get_gpu_info(&system_lines);

    assert_eq!(gpu_info.manufacturer, "Nvidia");
    assert_eq!(gpu_info.primary, "Nvidia GeForce RTX 3080");
    assert_eq!(gpu_info.rival, Some("amd".to_string()));
}

#[test]
fn test_intel_gpu_detection() {
    let system_lines = vec!["GPU #1: Intel UHD Graphics 630".to_string()];

    let gpu_info = GpuDetector::get_gpu_info(&system_lines);

    assert_eq!(gpu_info.manufacturer, "Intel");
    assert_eq!(gpu_info.primary, "Intel UHD Graphics 630");
    assert_eq!(gpu_info.rival, None);
}

#[test]
fn test_dual_gpu_detection() {
    let system_lines = vec![
        "GPU #1: Nvidia GeForce RTX 3080".to_string(),
        "GPU #2: Intel UHD Graphics 630".to_string(),
    ];

    let gpu_info = GpuDetector::get_gpu_info(&system_lines);

    assert_eq!(gpu_info.manufacturer, "Nvidia");
    assert_eq!(gpu_info.primary, "Nvidia GeForce RTX 3080");
    assert_eq!(
        gpu_info.secondary,
        Some("Intel UHD Graphics 630".to_string())
    );
}

#[test]
fn test_unknown_gpu() {
    let system_lines = vec!["Some other line".to_string()];

    let gpu_info = GpuDetector::get_gpu_info(&system_lines);

    assert_eq!(gpu_info.manufacturer, "Unknown");
    assert_eq!(gpu_info.primary, "Unknown");
    assert_eq!(gpu_info.rival, None);
}

#[test]
fn test_batch_processing() {
    let batch = vec![
        vec!["GPU #1: AMD Radeon RX 6800 XT".to_string()],
        vec!["GPU #1: Nvidia GeForce RTX 3080".to_string()],
    ];

    let results = GpuDetector::get_gpu_info_batch(batch);

    assert_eq!(results.len(), 2);
    assert_eq!(results[0].manufacturer, "AMD");
    assert_eq!(results[1].manufacturer, "Nvidia");
}
