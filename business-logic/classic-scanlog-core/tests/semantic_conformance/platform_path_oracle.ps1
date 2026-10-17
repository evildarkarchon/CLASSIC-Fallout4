# Read-only test oracle. Callers compare these values in memory and never put host paths in receipts.
$ErrorActionPreference = 'Stop'
$documents = $null
$personal = [Microsoft.Win32.Registry]::CurrentUser.OpenSubKey('Software\Microsoft\Windows\CurrentVersion\Explorer\Shell Folders', $false)
try {
    if ($null -ne $personal) {
        $documents = $personal.GetValue('Personal', $null, [Microsoft.Win32.RegistryValueOptions]::DoNotExpandEnvironmentNames)
        if ($documents -isnot [string]) { $documents = $null }
    }
} finally {
    if ($null -ne $personal) { $personal.Dispose() }
}
$missing = [Microsoft.Win32.Registry]::LocalMachine.OpenSubKey('SOFTWARE\WOW6432Node\Bethesda Softworks\CLASSIC_Conformance_Missing_216', $false)
try {
    @{ documents = $documents; missingKeyAbsent = ($null -eq $missing) } | ConvertTo-Json -Compress
} finally {
    if ($null -ne $missing) { $missing.Dispose() }
}
