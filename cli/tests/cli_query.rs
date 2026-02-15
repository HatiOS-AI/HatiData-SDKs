use duckdb::types::Value;
use tempfile::TempDir;

/// Test executing a simple SELECT query and reading results with duckdb::types::Value.
/// IMPORTANT: DuckDB 1.4.4 requires executing the statement before calling
/// column_count()/column_name(). We use query_map() to execute and collect first,
/// which drops the mutable borrow, then read column metadata.
#[test]
fn test_query_select_literal() {
    let tmp = TempDir::new().expect("Failed to create temp dir");
    let db_path = tmp.path().join("test.duckdb");

    let conn = duckdb::Connection::open(&db_path).expect("Failed to open DuckDB");

    let mut stmt = conn.prepare("SELECT 1 AS num").expect("Failed to prepare");

    // query_map executes the statement and returns an iterator.
    // Collecting into Vec drops the mutable borrow on stmt.
    let rows: Vec<String> = stmt
        .query_map([], |row| {
            let val: Value = row.get(0)?;
            Ok(value_to_string(&val))
        })
        .expect("Failed to query")
        .map(|r| r.expect("Failed to read row"))
        .collect();

    // After collecting, the mutable borrow is released.
    // Now column_count()/column_name() are safe (statement was already executed).
    let column_count = stmt.column_count();
    assert_eq!(column_count, 1);
    assert_eq!(stmt.column_name(0).unwrap(), "num");

    assert_eq!(rows.len(), 1);
    assert_eq!(rows[0], "1");
}

/// Test executing a query with multiple types.
#[test]
fn test_query_multiple_types() {
    let tmp = TempDir::new().expect("Failed to create temp dir");
    let db_path = tmp.path().join("test.duckdb");

    let conn = duckdb::Connection::open(&db_path).expect("Failed to open DuckDB");

    conn.execute_batch(
        "CREATE TABLE mixed (id INTEGER, name VARCHAR, score DOUBLE, active BOOLEAN)",
    )
    .expect("Failed to create table");
    conn.execute_batch("INSERT INTO mixed VALUES (1, 'alice', 95.5, true)")
        .expect("Failed to insert");

    let mut stmt = conn
        .prepare("SELECT id, name, score, active FROM mixed")
        .expect("Failed to prepare");

    let rows: Vec<Vec<String>> = stmt
        .query_map([], |row| {
            let mut vals = Vec::new();
            for i in 0..4 {
                let val: Value = row.get(i)?;
                vals.push(value_to_string(&val));
            }
            Ok(vals)
        })
        .expect("Failed to query")
        .map(|r| r.expect("Failed to read row"))
        .collect();

    assert_eq!(rows.len(), 1);
    assert_eq!(rows[0][0], "1");
    assert_eq!(rows[0][1], "alice");
    assert!(rows[0][2].starts_with("95.5"));
    assert_eq!(rows[0][3], "true");
}

/// Test that DDL statements (CREATE TABLE) execute without returning rows.
#[test]
fn test_query_ddl_statement() {
    let tmp = TempDir::new().expect("Failed to create temp dir");
    let db_path = tmp.path().join("test.duckdb");

    let conn = duckdb::Connection::open(&db_path).expect("Failed to open DuckDB");

    // DDL should succeed without errors
    conn.execute_batch("CREATE TABLE test_ddl (id INTEGER PRIMARY KEY, value TEXT)")
        .expect("CREATE TABLE should succeed");

    // Verify table exists
    let mut stmt = conn
        .prepare(
            "SELECT table_name FROM information_schema.tables \
             WHERE table_name = 'test_ddl' AND table_type = 'BASE TABLE'",
        )
        .expect("Failed to prepare");

    let tables: Vec<String> = stmt
        .query_map([], |row| {
            let val: Value = row.get(0)?;
            Ok(value_to_string(&val))
        })
        .expect("Failed to query")
        .map(|r| r.expect("Failed to read row"))
        .collect();

    assert_eq!(tables.len(), 1);
    assert_eq!(tables[0], "test_ddl");
}

/// Test the LocalEngine wrapper directly.
#[test]
fn test_local_engine_query() {
    let tmp = TempDir::new().expect("Failed to create temp dir");
    let db_path = tmp.path().join("test.duckdb");

    // Create database with a table
    let conn = duckdb::Connection::open(&db_path).expect("Failed to open DuckDB");
    conn.execute_batch("CREATE TABLE agents (id INTEGER, name VARCHAR, framework VARCHAR)")
        .expect("Failed to create table");
    conn.execute_batch(
        "INSERT INTO agents VALUES (1, 'agent-1', 'langchain'), (2, 'agent-2', 'autogen')",
    )
    .expect("Failed to insert");
    drop(conn);

    // Use LocalEngine to query
    let engine = hatidata_cli::local_engine::LocalEngine::open(db_path.as_path())
        .expect("Failed to open engine");

    let result = engine
        .execute_query("SELECT * FROM agents ORDER BY id")
        .expect("Failed to query");

    assert_eq!(result.columns.len(), 3);
    assert_eq!(result.columns[0], "id");
    assert_eq!(result.columns[1], "name");
    assert_eq!(result.columns[2], "framework");
    assert_eq!(result.rows.len(), 2);
    assert_eq!(result.rows[0][0], "1");
    assert_eq!(result.rows[0][1], "agent-1");
    assert_eq!(result.rows[1][2], "autogen");
}

/// Test list_tables and table_row_count.
#[test]
fn test_local_engine_table_info() {
    let tmp = TempDir::new().expect("Failed to create temp dir");
    let db_path = tmp.path().join("test.duckdb");

    let conn = duckdb::Connection::open(&db_path).expect("Failed to open DuckDB");
    conn.execute_batch("CREATE TABLE t1 (id INTEGER)")
        .expect("Failed to create t1");
    conn.execute_batch("CREATE TABLE t2 (id INTEGER)")
        .expect("Failed to create t2");
    conn.execute_batch("INSERT INTO t1 VALUES (1), (2), (3)")
        .expect("Failed to insert into t1");
    conn.execute_batch("INSERT INTO t2 VALUES (10)")
        .expect("Failed to insert into t2");
    drop(conn);

    let engine = hatidata_cli::local_engine::LocalEngine::open(db_path.as_path())
        .expect("Failed to open engine");

    let tables = engine.list_tables().expect("Failed to list tables");
    assert_eq!(tables.len(), 2);

    let t1_count = engine.table_row_count("t1").expect("Failed to count t1");
    assert_eq!(t1_count, 3);

    let t2_count = engine.table_row_count("t2").expect("Failed to count t2");
    assert_eq!(t2_count, 1);
}

/// Helper to convert DuckDB Value to string (mirrors local_engine implementation).
fn value_to_string(value: &Value) -> String {
    match value {
        Value::Null => "NULL".to_string(),
        Value::Boolean(b) => b.to_string(),
        Value::TinyInt(n) => n.to_string(),
        Value::SmallInt(n) => n.to_string(),
        Value::Int(n) => n.to_string(),
        Value::BigInt(n) => n.to_string(),
        Value::HugeInt(n) => n.to_string(),
        Value::UTinyInt(n) => n.to_string(),
        Value::USmallInt(n) => n.to_string(),
        Value::UInt(n) => n.to_string(),
        Value::UBigInt(n) => n.to_string(),
        Value::Float(f) => f.to_string(),
        Value::Double(f) => f.to_string(),
        Value::Text(s) => s.clone(),
        Value::Blob(b) => format!("<blob {} bytes>", b.len()),
        _ => format!("{value:?}"),
    }
}
