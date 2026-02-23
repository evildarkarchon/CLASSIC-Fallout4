//! Hardcoded default versions for Fallout 4.
//!
//! This module provides default version configurations when YAML loading
//! fails or the Version_Registry section is not present. It includes
//! the four standard Fallout 4 versions: OG, NG, AE (Anniversary Edition), and VR.

use std::collections::HashMap;

use crate::GameVersion;
use crate::models::{
    AddressLibFormat, AddressLibraryConfig, CompatibleRange, CrashgenConfig, LogLevel,
    UnknownVersionHandling, UnknownVersionStrategy, VersionInfo, XseConfig,
};

/// Create default Fallout 4 OG (Original) version info.
pub fn create_fo4_og() -> VersionInfo {
    let og_script_hashes = vec![
        ("Actor.pex".to_string(), "9333aa9b33d6009933afc3a1234a89ca93b5522ea186b44bc6c78846ed5a82c4".to_string()),
        ("ActorBase.pex".to_string(), "cb5d29fead7df77eca8674101abdc57349a8cf345f18c3ddd6ef8d94ad254da7".to_string()),
        ("Armor.pex".to_string(), "2bc34ab0d58f701e8684fc911742257e0768bd3e63b1eb8bdb2e043e7b67346b".to_string()),
        ("ArmorAddon.pex".to_string(), "5d9ff578b6e401526dbddedf93bdbccb4e202dba2b8b2e77809140b48fc8c1af".to_string()),
        ("Cell.pex".to_string(), "25d742d4fbe274fe5b8b3adc3775964ab9e22c1f32c47d5d3102b735c5b4e190".to_string()),
        ("Component.pex".to_string(), "80eef0f21bb7b1b9882c4a953a24aff3df8095f8464c006a96fafc0858f9b889".to_string()),
        ("ConstructibleObject.pex".to_string(), "51bdb39c81465bfbbbe509dc0a1ed40baebf4791cb35c978108e4334bcabc017".to_string()),
        ("DefaultObject.pex".to_string(), "715dff0394599587c4596488d66aab4d91311361a3ebec24a91d0ce1ddf39d77".to_string()),
        ("EncounterZone.pex".to_string(), "be0efccf70adc3a6a28f2465044d4df44cf7abe409c8624f6695d9a193eb96b6".to_string()),
        ("EquipSlot.pex".to_string(), "0e00da824263e60041086cc721896aeb304c7ec6d38fba1f548df96fda0c9ff3".to_string()),
        ("F4SE.pex".to_string(), "7d3b1be07259c9078c7f3f60cdf12041401024485750a303b0faec686a25047a".to_string()),
        ("FavoritesManager.pex".to_string(), "aed53963a5e725cea561f67525c1d50297c7a8410e6a5738b00356908d5daca7".to_string()),
        ("Form.pex".to_string(), "3ac9cd7ecb22d377800ca316413eb1d8f4def3ff3721a14b4c6fa61500f9f568".to_string()),
        ("Game.pex".to_string(), "19c858908f1a2054755b602121e5944dbbfb1ee0be38a24a532e6ab2f9390f4d".to_string()),
        ("HeadPart.pex".to_string(), "d25869fbf81b7d351e71cd17b6913cae01dd1b58ba76419050df6af1ed6525af".to_string()),
        ("Input.pex".to_string(), "9509a73024680963b8446b57247fdf160513a540531e87a0e2faedb610b1ffcd".to_string()),
        ("InstanceData.pex".to_string(), "57e68c4b355a94b709950ccec297b3d466f1d25e5029fed9e1423e8a12dd179f".to_string()),
        ("Location.pex".to_string(), "3538c0aaa4fe450828aee3848fe317c1654c8ed39bd811be9cff22a1e7618b49".to_string()),
        ("Math.pex".to_string(), "9bb0019795b85076837ac6845d0c79d65c9826739e59c43b97cfb949f611e822".to_string()),
        ("MatSwap.pex".to_string(), "b49d34fe1b6387d19df5140ddfbd9c340d3b10fc396e003142cdc755dc6815fc".to_string()),
        ("MiscObject.pex".to_string(), "7615656ab2867c5502507d1189cf7f938919dc585608698d2f31f782d858d23c".to_string()),
        ("ObjectMod.pex".to_string(), "d02235b5013375bf0c7785408380b3a567697879a966818df883256031b8a2b8".to_string()),
        ("ObjectReference.pex".to_string(), "97cfd2749b70545c9378955b09a898631fa03a0e235623b76f2c5631f2801be5".to_string()),
        ("Perk.pex".to_string(), "04a9d0309198cbeb3a419265490be03e051d35b17b7f8ce749ffc4ea0673e16c".to_string()),
        ("ScriptObject.pex".to_string(), "a395b7fc15b193b6d8ef0184dff6293100e79ec4dd431d85e10515da46e0502c".to_string()),
        ("UI.pex".to_string(), "6b7a65b8be433bcb99dbe07d4ca9e9de2fa94140d402247b877351c2b34a36d5".to_string()),
        ("Utility.pex".to_string(), "e10d65904d0a1e9ee568bdaba02636f0183bfa9565b4056758b1461540f9be75".to_string()),
        ("WaterType.pex".to_string(), "c4f8589ed33f72265e95a6bec2c9cab58667795e972bcf5f7d17c40deed43207".to_string()),
        ("Weapon.pex".to_string(), "f39cf899d90d47d694873ccaa2a72308c6717f5e36a302d6f95243e53672d77d".to_string()),
    ];
    VersionInfo {
        id: "FO4_OG".to_string(),
        game: "Fallout4".to_string(),
        is_vr: false,
        version: GameVersion::new(1, 10, 163, 0),
        display_name: "Fallout 4 Original".to_string(),
        short_name: "OG".to_string(),
        description: "Pre-Next-Gen Update version".to_string(),
        docs_name: "Fallout4".to_string(),
        steam_id: 377160,
        address_library: Some(AddressLibraryConfig::new(
            "version-1-10-163-0.bin",
            AddressLibFormat::Bin,
            "https://www.nexusmods.com/fallout4/mods/47327?tab=files",
        )),
        xse: Some(XseConfig::with_script_hashes(
            "F4SE",
            "Fallout 4 Script Extender (F4SE)",
            "0.6.23",
            "f4se_loader.exe",
            29,
            og_script_hashes,
        )),
        compatible_range: None,
        priority: 100,
        deprecated: false,
        exe_hash: Some(
            "55f57947db9e05575122fae1088f0b0247442f11e566b56036caa0ac93329c36".to_string(),
        ),
        crashgen_versions: vec![
            CrashgenConfig::with_range(
                "1.28.6",
                "Buffout 4",
                "BO4",
                "buffout4.dll",
                "Legacy version for OG",
                "https://www.nexusmods.com/fallout4/mods/47359",
                CompatibleRange::new(
                    GameVersion::new(1, 10, 163, 0),
                    GameVersion::new(1, 10, 163, 999),
                ),
            ),
            CrashgenConfig::new(
                "1.37.0",
                "Buffout 4",
                "BO4 NG",
                "buffout4.dll",
                "Buffout 4 NG",
                "https://www.nexusmods.com/fallout4/mods/64880",
            ),
        ],
    }
}

/// Create default Fallout 4 NG (Next-Gen) version info.
pub fn create_fo4_ng() -> VersionInfo {
    let ng_script_hashes = vec![
        ("Actor.pex".to_string(), "12175169977977bf382631272ae6dfda03f002c268434144eedf8653000b2b90".to_string()),
        ("ActorBase.pex".to_string(), "6c7f6b82306ef541673ebb31142c5f69d32f574d81f932d957e3e7f3b649863f".to_string()),
        ("Armor.pex".to_string(), "ddc0e2f1b84351932cd357d4917e50faa3e262e93e4d153ec3f88a819f6711ec".to_string()),
        ("ArmorAddon.pex".to_string(), "d46a9c0c567dfbabedb2db87f29b4647ea4eca7e3a0056ab75378f2b8966ce2c".to_string()),
        ("Cell.pex".to_string(), "d472ead545a6798143db57c42f11a88754cb34bcf99ea92bb6bf3388b24dac15".to_string()),
        ("Component.pex".to_string(), "a66d315f4161747d6edc0edb7f837f937cb7eb7d5a3414777914e7b9273ba777".to_string()),
        ("ConstructibleObject.pex".to_string(), "385950805c323fa8e20beca8a940f0806169ca5cc1d173360da66a252caea384".to_string()),
        ("DefaultObject.pex".to_string(), "cd249af625d426878215682f76d870d0fe1ec4a5191a9f973187d11d700dc9b7".to_string()),
        ("EncounterZone.pex".to_string(), "bcb823d3cc4c530fcc89650a116eedfea94e69383614fe61f2daf919d5fb885b".to_string()),
        ("EquipSlot.pex".to_string(), "6188c879cc982d1e9bb2d92ebc02c32545246fd0cfd0cd892a14f9d1cdb3dee2".to_string()),
        ("F4SE.pex".to_string(), "036da39002284853551bfc38dcb36c4f20ecafaf7c0e6200a18f3bc2d68841f2".to_string()),
        ("FavoritesManager.pex".to_string(), "435469503cf478cb05293bc8e3fbf1945516620b52846123a55c7c89ed7a61f0".to_string()),
        ("Form.pex".to_string(), "7afbf5bdf3e454dbf968c784807c6bef79fa88893083f1160bc4bb4e980228b3".to_string()),
        ("Game.pex".to_string(), "c0bba25948ddb5574d84d995ee71886f6aacab10f25d979145e684d9625d6cda".to_string()),
        ("HeadPart.pex".to_string(), "925eefd6e57f7b349d4fb3e66388bee1f884a19e0d07d06ed0e63c55f4b79303".to_string()),
        ("Input.pex".to_string(), "03e390c9b6ab30f3c15108baeff00936cf26053c3357ec0ea6811e5bd6014fd4".to_string()),
        ("InstanceData.pex".to_string(), "868ce9edda89b7ee0005311280804cda2ffa975d4f4c3a10c08298dab779e58c".to_string()),
        ("Location.pex".to_string(), "1c287c2db3e6522cbe024ed24992d3c2e0d6c5eb3a49da52163ca8793e33178a".to_string()),
        ("Math.pex".to_string(), "6e2efd94287e6571b95720e5bc944b2072849290ed52092972ad69c102617089".to_string()),
        ("MatSwap.pex".to_string(), "06858608fa2701c5c1d78c0eb21e864df84c164f66f1a82edd322c2300dccce0".to_string()),
        ("MiscObject.pex".to_string(), "6729e322508d5b06f9d56dd6f833fa048ec73bff8f0086759edf1295a8fd2c96".to_string()),
        ("ObjectMod.pex".to_string(), "816e2897c7853dd15001498a762284e3c71d53f3a5c97bce167ecd30b562574e".to_string()),
        ("ObjectReference.pex".to_string(), "c166855a4b2b34a1f07cb1bc928aed34a323b3a7da5fc90d6b6d9cfb6f7c22da".to_string()),
        ("Perk.pex".to_string(), "00364ee941b24ae7be7ed02f2d037da44ecf1458ce43d104de3ade6b1e2df3c7".to_string()),
        ("ScriptObject.pex".to_string(), "d7760385d670d69627408898f5b93455e8502428709fc007cd1fda2494d945c4".to_string()),
        ("UI.pex".to_string(), "a7605779bf4a29f79a8179913fca625de0f87517026a994e68bb1565c5f279b5".to_string()),
        ("Utility.pex".to_string(), "496aaa38ee6f850907d6172b996274109431d3fb8f2f459c0ab111bbbc01fe93".to_string()),
        ("WaterType.pex".to_string(), "7a1d41e063bdd8179a72b97869d27e636469988d088420c85f5297dcb1488d7a".to_string()),
        ("Weapon.pex".to_string(), "e6eee491b5a59f285a1482eb625ffb18bc63ed398bf5f8a4babca0b7edac918c".to_string()),
    ];
    VersionInfo {
        id: "FO4_NG".to_string(),
        game: "Fallout4".to_string(),
        is_vr: false,
        version: GameVersion::new(1, 10, 984, 0),
        display_name: "Fallout 4 Next-Gen".to_string(),
        short_name: "NG".to_string(),
        description: "Next-Gen Update version".to_string(),
        docs_name: "Fallout4".to_string(),
        steam_id: 377160,
        address_library: Some(AddressLibraryConfig::new(
            "version-1-10-984-0.bin",
            AddressLibFormat::Bin,
            "https://www.nexusmods.com/fallout4/mods/47327?tab=files",
        )),
        xse: Some(XseConfig::with_script_hashes(
            "F4SE",
            "Fallout 4 Script Extender (F4SE)",
            "0.7.2",
            "f4se_loader.exe",
            29,
            ng_script_hashes,
        )),
        compatible_range: None,
        priority: 200, // Higher priority - default for unknown versions
        deprecated: false,
        exe_hash: Some(
            "bcb8f9fe660ef4c33712b873fdc24e5ecbd6a77e629d6419f803c2c09c63eaf2".to_string(),
        ),
        crashgen_versions: vec![CrashgenConfig::with_range(
            "1.37.0",
            "Buffout 4",
            "BO4 NG",
            "buffout4.dll",
            "Buffout 4 NG",
            "https://www.nexusmods.com/fallout4/mods/64880",
            CompatibleRange::new(
                GameVersion::new(1, 10, 984, 0),
                GameVersion::new(1, 10, 999, 999),
            ),
        )],
    }
}

/// Create default Fallout 4 Anniversary Edition version info.
///
/// The Anniversary Edition covers game versions from 1.11.137/1.11.140 to 1.11.191
/// and beyond (as it's an active development branch). Uses a generous compatible
/// range to match future versions in this branch.
pub fn create_fo4_ae() -> VersionInfo {
    VersionInfo {
        id: "FO4_AE".to_string(),
        game: "Fallout4".to_string(),
        is_vr: false,
        version: GameVersion::new(1, 11, 191, 0), // Current max version
        display_name: "Fallout 4 Anniversary Edition".to_string(),
        short_name: "AE".to_string(),
        description: "Anniversary Edition version (active development branch)".to_string(),
        docs_name: "Fallout4".to_string(),
        steam_id: 377160,
        address_library: Some(AddressLibraryConfig::new(
            "version-1-11-191-0.bin",
            AddressLibFormat::Bin,
            "https://www.nexusmods.com/fallout4/mods/47327?tab=files",
        )),
        xse: Some(XseConfig::new("F4SE", "Fallout 4 Script Extender (F4SE)", "0.7.7", "f4se_loader.exe", 29)),
        // Generous compatible range: 1.11.137.0 through 1.11.999.0 (future-proof for active branch)
        compatible_range: Some(CompatibleRange::new(
            GameVersion::new(1, 11, 137, 0),
            GameVersion::new(1, 11, 999, 0),
        )),
        priority: 300, // Highest priority - most recent version branch
        deprecated: false,
        exe_hash: None, // AE exe hash not yet available
        crashgen_versions: vec![
            CrashgenConfig::with_range(
                "1.7.1",
                "Buffout 4",
                "BO4",
                "buffout4.dll",
                "AE-compatible Crash Logger",
                "https://www.nexusmods.com/fallout4/mods/99911",
                CompatibleRange::new(
                    GameVersion::new(1, 11, 137, 0),
                    GameVersion::new(1, 11, 999, 999),
                ),
            ),
            CrashgenConfig::with_range(
                "1.0.0",
                "Addictol",
                "Addictol",
                "addictol.dll",
                "AIO Engine fixes and Crash Logger",
                "https://www.nexusmods.com/fallout4/mods/84214",
                CompatibleRange::new(
                    GameVersion::new(1, 11, 137, 0),
                    GameVersion::new(1, 11, 999, 999),
                ),
            ),
        ],
    }
}

/// Create default Fallout 4 VR version info.
pub fn create_fo4_vr() -> VersionInfo {
    let vr_script_hashes = vec![
        ("Actor.pex".to_string(), "dfd7177ad93b78e3adf91a4a18ad26a9d8e4447e3dc173269798977054b82f17".to_string()),
        ("ActorBase.pex".to_string(), "659acecc1146734cf691d6d572f4c30edbbbc3ea3efb2502fd14bb91425828c8".to_string()),
        ("Armor.pex".to_string(), "3995537c4b5925b82079291d383da4bda6a284787794e65ee33a65752741f027".to_string()),
        ("ArmorAddon.pex".to_string(), "12bca4e4eddfb487c4f945fd5d6fe762475eb4d8a26ffd90fb7d0de4ddc165c7".to_string()),
        ("Cell.pex".to_string(), "34da9be5c267f599c466b9263f459b0704d7e87ccfee41fad85e93f25e76c636".to_string()),
        ("Component.pex".to_string(), "0243f0017f7190c38f17c848755a3675fb25a861dc09ef28d1dd5490a57876ff".to_string()),
        ("ConstructibleObject.pex".to_string(), "2a4de0c3190acec6ae13ee0cd936e6eefdcd5a8fb5cef8ecb845b01d67e6924e".to_string()),
        ("DefaultObject.pex".to_string(), "e7d2e193c2a9bd7e2600993da256fae6186c8fe579d0dc7592f9e27638649177".to_string()),
        ("EncounterZone.pex".to_string(), "facb76d19c4efdcd8f5b9e0329f214db130217e3e59154cf2568c30ff65916a1".to_string()),
        ("EquipSlot.pex".to_string(), "33858e7a68826a3afdccbe55e0cba34dbdbc21c3889eda6e6bcbb8f393f5dd40".to_string()),
        ("F4SE.pex".to_string(), "8b7de39f18695b2af5bdae2e3550291af1c72a7d0bbeefd65fcfe83b8d9d94bf".to_string()),
        ("FavoritesManager.pex".to_string(), "eb616c6fd7b6e9a1874fcf8840c7dac8070d1b5cb587eaf4a5a162b7f3532c0a".to_string()),
        ("Form.pex".to_string(), "bb436785aa3a8b9b6fd4c95f85982651e92dcc24cfb0a623e2dd616815bce5d8".to_string()),
        ("Game.pex".to_string(), "e9baa2e483fbbda20ab476d0df53c6c62c1410c13f288f8dc48b2853c2df73a7".to_string()),
        ("HeadPart.pex".to_string(), "6a8a34cc933b4a3a2274d2c59e3d078df42fcf2531e0518c54f16fb764d5f0fa".to_string()),
        ("Input.pex".to_string(), "ff7a9f5819b822867f9a3a2dea4a4ebfe31b3ed1fa013d82f6b9048fc8ae5e03".to_string()),
        ("InstanceData.pex".to_string(), "933f26d7185be5df62f44c9f47c95ad743a1605454c7aa9b01e16b696729b585".to_string()),
        ("Location.pex".to_string(), "130dd8512339a26cf57780dcfc093de19e4abaed7f0d7e07a8b5707af877c05d".to_string()),
        ("Math.pex".to_string(), "1375ffebd59f5070a07cccb6381624d4b5429ccf6a23fe0b9c464a135cd57b05".to_string()),
        ("MatSwap.pex".to_string(), "fa7df6ce66abde793efb8449c0e6517beafb5c88c0813ca8b81f4ceb912857bc".to_string()),
        ("MiscObject.pex".to_string(), "cec1b89d95e7ab8526dd90a1ae6f968c08c0b3b77851cc8e46e658b3049d14c6".to_string()),
        ("ObjectMod.pex".to_string(), "1385636404a733d6332cfaadd509eda8b317a319c8e3968eabae7e958c0e1522".to_string()),
        ("ObjectReference.pex".to_string(), "5f18adbfd777c6c265a46a5081c882737a350e30f336c225d509b8101f5fbecc".to_string()),
        ("Perk.pex".to_string(), "5f306d34f10168c9307d8ec98b83b3a0a49faf6c00949d5c83c8ce88791ab5d8".to_string()),
        ("ScriptObject.pex".to_string(), "6daa54faeedfefcb0da7a76ad4ab7fa48e427d5704b7367eea88c3bebc8fba4f".to_string()),
        ("UI.pex".to_string(), "523ba72eb4d17cd148ac39aaea3e5e5a64ef8484e287583987b4522b867f8414".to_string()),
        ("Utility.pex".to_string(), "9bff49b59e18636ea84033f362b45f1962c2b3740eb36ad9e9dcae94556f3490".to_string()),
        ("WaterType.pex".to_string(), "8711f4a818c1fed8b549f9cfb0fc49186bf6875cd2c8b0146c4e3154da91028f".to_string()),
        ("Weapon.pex".to_string(), "e9a18d4f7e3aa6b67fb79dee501b221e62e4fbe10baad0b47fb087735f7fb7a9".to_string()),
    ];
    VersionInfo {
        id: "FO4_VR".to_string(),
        game: "Fallout4".to_string(),
        is_vr: true,
        version: GameVersion::new(1, 2, 72, 0),
        display_name: "Fallout 4 VR".to_string(),
        short_name: "VR".to_string(),
        description: "Virtual Reality version".to_string(),
        docs_name: "Fallout4VR".to_string(),
        steam_id: 611660,
        address_library: Some(AddressLibraryConfig::new(
            "version-1-2-72-0.csv",
            AddressLibFormat::Csv,
            "https://www.nexusmods.com/fallout4/mods/64879?tab=files",
        )),
        xse: Some(XseConfig::with_script_hashes("F4SEVR", "Fallout 4 Script Extender VR (F4SEVR)", "0.6.20", "f4sevr_loader.exe", 29, vr_script_hashes)),
        compatible_range: None,
        priority: 100,
        deprecated: false,
        exe_hash: None, // VR exe hash not yet available
        crashgen_versions: vec![CrashgenConfig::new(
            "1.37.0",
            "Buffout 4",
            "BO4 NG",
            "buffout4.dll",
            "NG-compatible version for VR",
            "https://www.nexusmods.com/fallout4/mods/64880",
        )],
    }
}

/// Get all default Fallout 4 versions.
///
/// Returns a HashMap mapping version IDs to their VersionInfo.
pub fn get_default_versions() -> HashMap<String, VersionInfo> {
    let mut versions = HashMap::new();

    let og = create_fo4_og();
    let ng = create_fo4_ng();
    let ae = create_fo4_ae();
    let vr = create_fo4_vr();

    versions.insert(og.id.clone(), og);
    versions.insert(ng.id.clone(), ng);
    versions.insert(ae.id.clone(), ae);
    versions.insert(vr.id.clone(), vr);

    versions
}

/// Get default unknown version handling configuration.
pub fn get_default_unknown_handling() -> UnknownVersionHandling {
    let mut defaults = HashMap::new();
    defaults.insert("Fallout4".to_string(), "FO4_NG".to_string());
    defaults.insert("Fallout4VR".to_string(), "FO4_VR".to_string());

    UnknownVersionHandling::new(
        UnknownVersionStrategy::NearestMatch,
        defaults,
        LogLevel::Warning,
    )
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_default_versions() {
        let versions = get_default_versions();

        assert_eq!(versions.len(), 4);
        assert!(versions.contains_key("FO4_OG"));
        assert!(versions.contains_key("FO4_NG"));
        assert!(versions.contains_key("FO4_AE"));
        assert!(versions.contains_key("FO4_VR"));
    }

    #[test]
    fn test_og_version() {
        let og = create_fo4_og();

        assert_eq!(og.id, "FO4_OG");
        assert_eq!(og.version, GameVersion::new(1, 10, 163, 0));
        assert_eq!(og.short_name, "OG");
        assert!(!og.is_vr);
        assert_eq!(og.docs_name, "Fallout4");
        assert_eq!(og.steam_id, 377160);
        assert!(og.address_library.is_some());
        assert_eq!(
            og.address_library.as_ref().unwrap().format,
            AddressLibFormat::Bin
        );

        // XSE config
        let xse = og.xse.as_ref().expect("OG should have XSE");
        assert_eq!(xse.full_name, "Fallout 4 Script Extender (F4SE)");
        assert_eq!(xse.file_count, 29);
        assert_eq!(xse.script_hashes.len(), 29);

        // Crashgen config
        assert_eq!(og.crashgen_versions[0].acronym, "BO4");
        assert_eq!(og.crashgen_versions[0].dll_file, "buffout4.dll");
        assert_eq!(og.crashgen_versions[1].acronym, "BO4 NG");
        assert_eq!(og.crashgen_versions[1].dll_file, "buffout4.dll");

        // OG supports both Buffout 4 legacy and Buffout 4 NG
        assert_eq!(og.crashgen_versions.len(), 2);
        assert_eq!(og.crashgen_versions[0].version, "1.28.6");
        assert_eq!(og.crashgen_versions[0].name, "Buffout 4");
        // Buffout 4 legacy has OG-specific compatible_range
        let og_range = og.crashgen_versions[0].compatible_range.as_ref().unwrap();
        assert_eq!(og_range.min_version, GameVersion::new(1, 10, 163, 0));
        assert_eq!(og_range.max_version, GameVersion::new(1, 10, 163, 999));
        assert!(og.crashgen_versions[0].is_compatible_with(&GameVersion::new(1, 10, 163, 0)));
        assert!(!og.crashgen_versions[0].is_compatible_with(&GameVersion::new(1, 10, 984, 0)));

        assert_eq!(og.crashgen_versions[1].version, "1.37.0");
        assert_eq!(og.crashgen_versions[1].name, "Buffout 4"); // Name matches log output
        // Buffout 4 NG has no range restriction (universal within OG)
        assert!(og.crashgen_versions[1].compatible_range.is_none());
    }

    #[test]
    fn test_ng_version() {
        let ng = create_fo4_ng();

        assert_eq!(ng.id, "FO4_NG");
        assert_eq!(ng.version, GameVersion::new(1, 10, 984, 0));
        assert_eq!(ng.short_name, "NG");
        assert!(!ng.is_vr);
        assert_eq!(ng.docs_name, "Fallout4");
        assert_eq!(ng.steam_id, 377160);
        assert_eq!(ng.priority, 200); // Higher priority than OG

        // XSE config
        let xse = ng.xse.as_ref().expect("NG should have XSE");
        assert_eq!(xse.full_name, "Fallout 4 Script Extender (F4SE)");
        assert_eq!(xse.file_count, 29);
        assert_eq!(xse.script_hashes.len(), 29);

        // Crashgen config
        assert_eq!(ng.crashgen_versions[0].acronym, "BO4 NG");
        assert_eq!(ng.crashgen_versions[0].dll_file, "buffout4.dll");

        // NG only supports Buffout 4 NG (name matches log output, description identifies as NG)
        assert_eq!(ng.crashgen_versions.len(), 1);
        assert_eq!(ng.crashgen_versions[0].version, "1.37.0");
        assert_eq!(ng.crashgen_versions[0].name, "Buffout 4");
        // NG crashgen has compatible_range for NG game versions
        let ng_range = ng.crashgen_versions[0].compatible_range.as_ref().unwrap();
        assert_eq!(ng_range.min_version, GameVersion::new(1, 10, 984, 0));
        assert_eq!(ng_range.max_version, GameVersion::new(1, 10, 999, 999));
        assert!(ng.crashgen_versions[0].is_compatible_with(&GameVersion::new(1, 10, 984, 0)));
        assert!(!ng.crashgen_versions[0].is_compatible_with(&GameVersion::new(1, 10, 163, 0)));
    }

    #[test]
    fn test_ae_version() {
        let ae = create_fo4_ae();

        assert_eq!(ae.id, "FO4_AE");
        assert_eq!(ae.version, GameVersion::new(1, 11, 191, 0));
        assert_eq!(ae.short_name, "AE");
        assert!(!ae.is_vr);
        assert_eq!(ae.docs_name, "Fallout4");
        assert_eq!(ae.steam_id, 377160);
        assert_eq!(ae.priority, 300); // Highest priority - most recent version branch
        assert!(ae.compatible_range.is_some());

        // XSE config
        let xse = ae.xse.as_ref().expect("AE should have XSE");
        assert_eq!(xse.full_name, "Fallout 4 Script Extender (F4SE)");
        assert_eq!(xse.file_count, 29);

        // Crashgen configs
        assert_eq!(ae.crashgen_versions[0].acronym, "BO4");
        assert_eq!(ae.crashgen_versions[0].dll_file, "buffout4.dll");
        assert_eq!(ae.crashgen_versions[1].acronym, "Addictol");
        assert_eq!(ae.crashgen_versions[1].dll_file, "addictol.dll");

        // Test compatible range includes expected versions
        let range = ae.compatible_range.as_ref().unwrap();
        assert!(range.contains(&GameVersion::new(1, 11, 137, 0))); // Min version
        assert!(range.contains(&GameVersion::new(1, 11, 140, 0))); // Early AE version
        assert!(range.contains(&GameVersion::new(1, 11, 191, 0))); // Current max
        assert!(range.contains(&GameVersion::new(1, 11, 200, 0))); // Future version
        assert!(!range.contains(&GameVersion::new(1, 10, 984, 0))); // NG version
        assert!(!range.contains(&GameVersion::new(1, 12, 0, 0))); // Outside range

        // AE supports both Buffout 4 and Addictol
        assert_eq!(ae.crashgen_versions.len(), 2);
        assert_eq!(ae.crashgen_versions[0].version, "1.7.1");
        assert_eq!(ae.crashgen_versions[0].name, "Buffout 4");
        assert_eq!(ae.crashgen_versions[1].version, "1.0.0");
        assert_eq!(ae.crashgen_versions[1].name, "Addictol");

        // Both AE crashgen configs have compatible_range matching AE's version-level range
        let ae_cg_range_0 = ae.crashgen_versions[0].compatible_range.as_ref().unwrap();
        assert_eq!(ae_cg_range_0.min_version, GameVersion::new(1, 11, 137, 0));
        assert_eq!(ae_cg_range_0.max_version, GameVersion::new(1, 11, 999, 999));
        assert!(ae.crashgen_versions[0].is_compatible_with(&GameVersion::new(1, 11, 191, 0)));
        assert!(!ae.crashgen_versions[0].is_compatible_with(&GameVersion::new(1, 10, 984, 0)));

        let ae_cg_range_1 = ae.crashgen_versions[1].compatible_range.as_ref().unwrap();
        assert_eq!(ae_cg_range_1.min_version, GameVersion::new(1, 11, 137, 0));
        assert_eq!(ae_cg_range_1.max_version, GameVersion::new(1, 11, 999, 999));
        assert!(ae.crashgen_versions[1].is_compatible_with(&GameVersion::new(1, 11, 191, 0)));
        assert!(!ae.crashgen_versions[1].is_compatible_with(&GameVersion::new(1, 10, 984, 0)));
    }

    #[test]
    fn test_vr_version() {
        let vr = create_fo4_vr();

        assert_eq!(vr.id, "FO4_VR");
        assert_eq!(vr.version, GameVersion::new(1, 2, 72, 0));
        assert_eq!(vr.short_name, "VR");
        assert!(vr.is_vr);
        assert_eq!(vr.docs_name, "Fallout4VR");
        assert_eq!(vr.steam_id, 611660);
        assert!(vr.address_library.is_some());
        assert_eq!(
            vr.address_library.as_ref().unwrap().format,
            AddressLibFormat::Csv
        );

        // XSE config
        let xse = vr.xse.as_ref().expect("VR should have XSE");
        assert_eq!(xse.full_name, "Fallout 4 Script Extender VR (F4SEVR)");
        assert_eq!(xse.file_count, 29);
        assert_eq!(xse.script_hashes.len(), 29);

        // Crashgen config
        assert_eq!(vr.crashgen_versions[0].acronym, "BO4 NG");
        assert_eq!(vr.crashgen_versions[0].dll_file, "buffout4.dll");

        // VR supports Buffout 4 NG (name matches log output)
        assert_eq!(vr.crashgen_versions.len(), 1);
        assert_eq!(vr.crashgen_versions[0].version, "1.37.0");
        assert_eq!(vr.crashgen_versions[0].name, "Buffout 4");
        // VR crashgen has no compatible_range (universal within VR)
        assert!(vr.crashgen_versions[0].compatible_range.is_none());
    }

    #[test]
    fn test_default_unknown_handling() {
        let handling = get_default_unknown_handling();

        assert_eq!(handling.strategy, UnknownVersionStrategy::NearestMatch);
        assert_eq!(handling.get_default("Fallout4"), Some("FO4_NG"));
        assert_eq!(handling.get_default("Fallout4VR"), Some("FO4_VR"));
    }

    #[test]
    fn test_og_get_compatible_crashgens_filters_by_range() {
        let og = create_fo4_og();

        // OG game version (1.10.163.0) — both crashgens should be compatible:
        // - 1.28.6 has range 1.10.163.0–1.10.163.999 (contains 1.10.163.0)
        // - 1.37.0 has no range (universal)
        let compatible = og.get_compatible_crashgens(None);
        assert_eq!(compatible.len(), 2);

        // NG game version (1.10.984.0) — only 1.37.0 should be compatible:
        // - 1.28.6 range excludes NG versions
        // - 1.37.0 has no range (universal)
        let ng_version = GameVersion::new(1, 10, 984, 0);
        let compatible = og.get_compatible_crashgens(Some(&ng_version));
        assert_eq!(compatible.len(), 1);
        assert_eq!(compatible[0].version, "1.37.0");
    }

    #[test]
    fn test_ng_get_compatible_crashgens_filters_by_range() {
        let ng = create_fo4_ng();

        // NG game version (1.10.984.0) — 1.37.0 should be compatible (within range)
        let compatible = ng.get_compatible_crashgens(None);
        assert_eq!(compatible.len(), 1);
        assert_eq!(compatible[0].version, "1.37.0");

        // OG game version (1.10.163.0) — 1.37.0 should NOT be compatible (outside range)
        let og_version = GameVersion::new(1, 10, 163, 0);
        let compatible = ng.get_compatible_crashgens(Some(&og_version));
        assert!(compatible.is_empty());
    }

    #[test]
    fn test_ae_get_compatible_crashgens_filters_by_range() {
        let ae = create_fo4_ae();

        // AE game version (1.11.191.0) — both Buffout 4 and Addictol should be compatible
        let compatible = ae.get_compatible_crashgens(None);
        assert_eq!(compatible.len(), 2);
        assert_eq!(compatible[0].version, "1.7.1");
        assert_eq!(compatible[1].version, "1.0.0");

        // NG game version — neither AE crashgen should be compatible
        let ng_version = GameVersion::new(1, 10, 984, 0);
        let compatible = ae.get_compatible_crashgens(Some(&ng_version));
        assert!(compatible.is_empty());
    }

    #[test]
    fn test_vr_get_compatible_crashgens_no_range() {
        let vr = create_fo4_vr();

        // VR crashgen has no range — compatible with any version
        let compatible = vr.get_compatible_crashgens(None);
        assert_eq!(compatible.len(), 1);
        assert_eq!(compatible[0].version, "1.37.0");

        // Even with a random version, still compatible
        let random_version = GameVersion::new(99, 99, 99, 99);
        let compatible = vr.get_compatible_crashgens(Some(&random_version));
        assert_eq!(compatible.len(), 1);
    }
}
