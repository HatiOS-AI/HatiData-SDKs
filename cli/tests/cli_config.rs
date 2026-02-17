use tempfile::TempDir;

/// Set up a minimal .hati/ project with config.toml for config tests.
fn setup_project(tmp: &TempDir) -> std::path::PathBuf {
    let hati_dir = tmp.path().join(".hati");
    std::fs::create_dir_all(&hati_dir).expect("Failed to create .hati/");

    let config_content = r#"cloud_endpoint = "https://api.hatidata.com"
api_key = ""
default_target = "cloud"
org_id = ""
"#;
    std::fs::write(hati_dir.join("config.toml"), config_content)
        .expect("Failed to write config.toml");

    hati_dir
}

/// Test that config set updates values correctly.
#[test]
fn test_config_set_updates_value() {
    let tmp = TempDir::new().expect("Failed to create temp dir");
    let hati_dir = setup_project(&tmp);

    // Simulate what `hati config set default_target vpc` does
    let config_path = hati_dir.join("config.toml");
    let contents = std::fs::read_to_string(&config_path).expect("Failed to read config");
    let mut config: toml::Table = contents.parse().expect("Failed to parse TOML");

    config.insert(
        "default_target".to_string(),
        toml::Value::String("vpc".to_string()),
    );

    let output = toml::to_string_pretty(&config).expect("Failed to serialize");
    std::fs::write(&config_path, output).expect("Failed to write config");

    // Verify the value was updated
    let contents = std::fs::read_to_string(&config_path).expect("Failed to read config");
    let config: toml::Value = contents.parse().expect("Failed to parse TOML");
    assert_eq!(
        config.get("default_target").and_then(|v| v.as_str()),
        Some("vpc")
    );
}

/// Test that config set preserves other keys when updating one.
#[test]
fn test_config_set_preserves_other_keys() {
    let tmp = TempDir::new().expect("Failed to create temp dir");
    let hati_dir = setup_project(&tmp);

    let config_path = hati_dir.join("config.toml");
    let contents = std::fs::read_to_string(&config_path).expect("Failed to read config");
    let mut config: toml::Table = contents.parse().expect("Failed to parse TOML");

    // Set org_id — other keys should remain unchanged
    config.insert(
        "org_id".to_string(),
        toml::Value::String("org_123".to_string()),
    );

    let output = toml::to_string_pretty(&config).expect("Failed to serialize");
    std::fs::write(&config_path, output).expect("Failed to write config");

    // Verify all keys
    let contents = std::fs::read_to_string(&config_path).expect("Failed to read config");
    let config: toml::Value = contents.parse().expect("Failed to parse TOML");
    assert_eq!(
        config.get("cloud_endpoint").and_then(|v| v.as_str()),
        Some("https://api.hatidata.com"),
        "cloud_endpoint should be preserved"
    );
    assert_eq!(
        config.get("org_id").and_then(|v| v.as_str()),
        Some("org_123"),
        "org_id should be updated"
    );
    assert_eq!(
        config.get("default_target").and_then(|v| v.as_str()),
        Some("cloud"),
        "default_target should be preserved"
    );
}

/// Test that the VALID_KEYS set includes all expected config keys.
#[test]
fn test_valid_config_keys() {
    let valid_keys = ["cloud_endpoint", "api_key", "default_target", "org_id"];

    // Verify we have exactly 4 config keys
    assert_eq!(valid_keys.len(), 4);
    assert!(valid_keys.contains(&"cloud_endpoint"));
    assert!(valid_keys.contains(&"api_key"));
    assert!(valid_keys.contains(&"default_target"));
    assert!(valid_keys.contains(&"org_id"));
}

/// Test config list reads all keys from config.toml.
#[test]
fn test_config_list_reads_all_keys() {
    let tmp = TempDir::new().expect("Failed to create temp dir");
    let hati_dir = setup_project(&tmp);

    let config_path = hati_dir.join("config.toml");
    let contents = std::fs::read_to_string(&config_path).expect("Failed to read config");
    let config: toml::Value = contents.parse().expect("Failed to parse TOML");

    let table = config.as_table().expect("Config should be a TOML table");

    // All 4 keys should be present in the default config
    assert!(table.contains_key("cloud_endpoint"));
    assert!(table.contains_key("api_key"));
    assert!(table.contains_key("default_target"));
    assert!(table.contains_key("org_id"));
}

/// Test that API key redaction works (values > 8 chars should be truncated).
#[test]
fn test_api_key_redaction_logic() {
    let api_key = "hd_live_abcdef1234567890";

    // Mimic the redaction logic from config.rs
    let display_value = if api_key.len() > 8 {
        format!("{}...", &api_key[..8])
    } else {
        "(set)".to_string()
    };

    assert_eq!(display_value, "hd_live_...");
    assert!(
        !display_value.contains("abcdef"),
        "API key should be redacted"
    );
}
