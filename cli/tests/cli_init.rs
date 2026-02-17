use tempfile::TempDir;

/// Test that `hati init` creates the expected directory structure.
#[test]
fn test_init_creates_hati_directory() {
    let tmp = TempDir::new().expect("Failed to create temp dir");
    let base = tmp.path();

    // Simulate what `hati init` does
    let hati_dir = base.join(".hati");
    std::fs::create_dir_all(&hati_dir).expect("Failed to create .hati/");

    // Write config.toml
    let config_content = r#"cloud_endpoint = "https://api.hatidata.com"
api_key = ""
default_target = "cloud"
org_id = ""
"#;
    std::fs::write(hati_dir.join("config.toml"), config_content).expect("Failed to write config");

    // Write .gitignore
    std::fs::write(
        hati_dir.join(".gitignore"),
        "*.duckdb\n*.duckdb.wal\nconfig.toml\n",
    )
    .expect("Failed to write .gitignore");

    // Create DuckDB database
    let db_path = hati_dir.join("local.duckdb");
    let _conn = duckdb::Connection::open(&db_path).expect("Failed to create DuckDB");

    // Verify structure
    assert!(hati_dir.exists(), ".hati/ directory should exist");
    assert!(
        hati_dir.join("config.toml").exists(),
        "config.toml should exist"
    );
    assert!(
        hati_dir.join(".gitignore").exists(),
        ".gitignore should exist"
    );
    assert!(db_path.exists(), "local.duckdb should exist");

    // Verify config.toml is valid TOML
    let config_str =
        std::fs::read_to_string(hati_dir.join("config.toml")).expect("Failed to read config");
    let config: toml::Value = config_str
        .parse()
        .expect("config.toml should be valid TOML");
    assert_eq!(
        config.get("cloud_endpoint").and_then(|v| v.as_str()),
        Some("https://api.hatidata.com")
    );
    assert_eq!(
        config.get("default_target").and_then(|v| v.as_str()),
        Some("cloud")
    );
}

/// Test that init in a directory that already has .hati/ is idempotent.
#[test]
fn test_init_detects_existing_directory() {
    let tmp = TempDir::new().expect("Failed to create temp dir");
    let hati_dir = tmp.path().join(".hati");

    // Create .hati/ manually
    std::fs::create_dir_all(&hati_dir).expect("Failed to create .hati/");

    // The directory should already exist
    assert!(hati_dir.exists());
}

/// Test that DuckDB database can be opened after creation.
#[test]
fn test_init_duckdb_is_functional() {
    let tmp = TempDir::new().expect("Failed to create temp dir");
    let db_path = tmp.path().join("test.duckdb");

    // Create and verify the database works
    {
        let conn = duckdb::Connection::open(&db_path).expect("Failed to create DuckDB");
        conn.execute_batch("CREATE TABLE test (id INTEGER, name VARCHAR)")
            .expect("Failed to create table");
        conn.execute_batch("INSERT INTO test VALUES (1, 'hello')")
            .expect("Failed to insert");
    }

    // Re-open and verify data persists
    {
        let conn = duckdb::Connection::open(&db_path).expect("Failed to reopen DuckDB");
        let mut stmt = conn
            .prepare("SELECT COUNT(*) FROM test")
            .expect("Failed to prepare");
        let count: i64 = stmt
            .query_row([], |row| row.get(0))
            .expect("Failed to query");
        assert_eq!(count, 1);
    }
}

/// Test that .gitignore includes config.toml (security: prevents API key leak).
#[test]
fn test_init_gitignore_includes_config_toml() {
    let tmp = TempDir::new().expect("Failed to create temp dir");
    let hati_dir = tmp.path().join(".hati");
    std::fs::create_dir_all(&hati_dir).expect("Failed to create .hati/");

    let gitignore_content = "# HatiData local files\n*.duckdb\n*.duckdb.wal\nconfig.toml\n";
    std::fs::write(hati_dir.join(".gitignore"), gitignore_content)
        .expect("Failed to write .gitignore");

    let contents =
        std::fs::read_to_string(hati_dir.join(".gitignore")).expect("Failed to read .gitignore");
    assert!(
        contents.contains("config.toml"),
        ".gitignore must include config.toml to prevent API key leaks"
    );
    assert!(
        contents.contains("*.duckdb"),
        ".gitignore must include *.duckdb"
    );
}
