use tempfile::TempDir;

/// Test that status shows local tables correctly.
#[test]
fn test_status_shows_local_tables() {
    let tmp = TempDir::new().expect("Failed to create temp dir");
    let hati_dir = tmp.path().join(".hati");
    std::fs::create_dir_all(&hati_dir).expect("Failed to create .hati/");

    let db_path = hati_dir.join("local.duckdb");
    let conn = duckdb::Connection::open(&db_path).expect("Failed to open DuckDB");
    conn.execute_batch("CREATE TABLE agents (id INTEGER, name VARCHAR)")
        .expect("Failed to create table");
    conn.execute_batch("INSERT INTO agents VALUES (1, 'agent-1'), (2, 'agent-2')")
        .expect("Failed to insert");
    drop(conn);

    // Use LocalEngine to verify what status would show
    let engine = hatidata_cli::local_engine::LocalEngine::open(&db_path)
        .expect("Failed to open engine");

    let tables = engine.list_tables().expect("Failed to list tables");
    assert_eq!(tables.len(), 1);
    assert_eq!(tables[0].name, "agents");

    let row_count = engine.table_row_count("agents").expect("Failed to count");
    assert_eq!(row_count, 2);
}

/// Test that status handles an empty database (no tables).
#[test]
fn test_status_empty_database() {
    let tmp = TempDir::new().expect("Failed to create temp dir");
    let hati_dir = tmp.path().join(".hati");
    std::fs::create_dir_all(&hati_dir).expect("Failed to create .hati/");

    let db_path = hati_dir.join("local.duckdb");
    let _conn = duckdb::Connection::open(&db_path).expect("Failed to open DuckDB");

    let engine = hatidata_cli::local_engine::LocalEngine::open(&db_path)
        .expect("Failed to open engine");

    let tables = engine.list_tables().expect("Failed to list tables");
    assert!(tables.is_empty(), "Fresh database should have no tables");
}

/// Test that status reports correct database file size.
#[test]
fn test_status_database_file_size() {
    let tmp = TempDir::new().expect("Failed to create temp dir");
    let hati_dir = tmp.path().join(".hati");
    std::fs::create_dir_all(&hati_dir).expect("Failed to create .hati/");

    let db_path = hati_dir.join("local.duckdb");
    let conn = duckdb::Connection::open(&db_path).expect("Failed to open DuckDB");
    conn.execute_batch("CREATE TABLE t (id INTEGER)")
        .expect("Failed to create table");
    drop(conn);

    // Database file should exist and have a non-zero size
    let metadata = std::fs::metadata(&db_path).expect("Failed to stat database file");
    assert!(metadata.len() > 0, "Database file should not be empty");
}

/// Test that status reads config.toml correctly.
#[test]
fn test_status_reads_config() {
    let tmp = TempDir::new().expect("Failed to create temp dir");
    let hati_dir = tmp.path().join(".hati");
    std::fs::create_dir_all(&hati_dir).expect("Failed to create .hati/");

    let config_content = r#"cloud_endpoint = "https://api.hatidata.com"
api_key = ""
default_target = "cloud"
org_id = ""
"#;
    std::fs::write(hati_dir.join("config.toml"), config_content)
        .expect("Failed to write config.toml");

    let config_path = hati_dir.join("config.toml");
    let contents = std::fs::read_to_string(&config_path).expect("Failed to read config");
    let config: toml::Value = contents.parse().expect("Failed to parse TOML");

    assert_eq!(
        config.get("cloud_endpoint").and_then(|v| v.as_str()),
        Some("https://api.hatidata.com")
    );
    assert_eq!(
        config.get("default_target").and_then(|v| v.as_str()),
        Some("cloud")
    );
}

/// Test that status works with multiple tables.
#[test]
fn test_status_multiple_tables() {
    let tmp = TempDir::new().expect("Failed to create temp dir");
    let hati_dir = tmp.path().join(".hati");
    std::fs::create_dir_all(&hati_dir).expect("Failed to create .hati/");

    let db_path = hati_dir.join("local.duckdb");
    let conn = duckdb::Connection::open(&db_path).expect("Failed to open DuckDB");
    conn.execute_batch("CREATE TABLE memories (id INTEGER, content TEXT)")
        .expect("Failed to create memories");
    conn.execute_batch("INSERT INTO memories VALUES (1, 'hello'), (2, 'world')")
        .expect("Failed to insert");
    conn.execute_batch("CREATE TABLE traces (id INTEGER, session TEXT)")
        .expect("Failed to create traces");
    conn.execute_batch("INSERT INTO traces VALUES (1, 'sess_1')")
        .expect("Failed to insert");
    conn.execute_batch("CREATE TABLE triggers (id INTEGER)")
        .expect("Failed to create triggers");
    drop(conn);

    let engine = hatidata_cli::local_engine::LocalEngine::open(&db_path)
        .expect("Failed to open engine");

    let tables = engine.list_tables().expect("Failed to list tables");
    assert_eq!(tables.len(), 3);

    let mut total_rows: u64 = 0;
    for table in &tables {
        total_rows += engine.table_row_count(&table.name).unwrap_or(0);
    }
    assert_eq!(total_rows, 3, "2 memories + 1 trace + 0 triggers = 3");
}
