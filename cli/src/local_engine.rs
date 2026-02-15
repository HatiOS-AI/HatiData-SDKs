use std::path::Path;

use anyhow::{Context, Result};
use duckdb::types::Value;
use duckdb::Connection;

/// Structured query result returned by `execute_query`.
pub struct QueryResult {
    pub columns: Vec<String>,
    pub rows: Vec<Vec<String>>,
}

/// Information about a table in the local DuckDB database.
pub struct TableInfo {
    pub name: String,
    #[allow(dead_code)]
    pub schema: String,
}

/// Local DuckDB engine wrapper for the HatiData CLI.
pub struct LocalEngine {
    conn: Connection,
}

impl LocalEngine {
    /// Open (or create) a DuckDB database at the given path.
    pub fn open(path: &Path) -> Result<Self> {
        let conn = Connection::open(path)
            .with_context(|| format!("Failed to open DuckDB at {}", path.display()))?;
        Ok(Self { conn })
    }

    /// Execute a SQL query and return structured results.
    ///
    /// IMPORTANT DuckDB 1.4.4 API note: `column_count()` and `column_name()`
    /// panic if called before the statement is executed. We must execute first
    /// (via `query`), then read column metadata.
    ///
    /// Uses `duckdb::types::Value` for reading cell values to handle all types
    /// correctly (the DuckDB Rust API's `row.get::<_, String>(i)` fails for
    /// non-String types).
    pub fn execute_query(&self, sql: &str) -> Result<QueryResult> {
        let trimmed = sql.trim().to_uppercase();
        let is_select = trimmed.starts_with("SELECT")
            || trimmed.starts_with("WITH")
            || trimmed.starts_with("SHOW")
            || trimmed.starts_with("DESCRIBE")
            || trimmed.starts_with("EXPLAIN")
            || trimmed.starts_with("PRAGMA");

        if !is_select {
            // DDL/DML: execute and return empty result
            self.conn
                .execute_batch(sql)
                .with_context(|| format!("Failed to execute SQL: {sql}"))?;
            return Ok(QueryResult {
                columns: Vec::new(),
                rows: Vec::new(),
            });
        }

        // SELECT-like: use query_map to execute and collect rows in one pass.
        // query_map internally executes the statement. We collect into a Vec
        // which drops the mutable borrow on stmt, allowing us to then call
        // column_count()/column_name() safely.
        let mut stmt = self
            .conn
            .prepare(sql)
            .with_context(|| format!("Failed to prepare SQL: {sql}"))?;

        // We don't know column_count before execution (DuckDB 1.4.4 panics).
        // Use a dynamic approach: read values until get() fails.
        let raw_rows: Vec<Vec<(usize, Value)>> = stmt
            .query_map([], |row| {
                let mut values = Vec::new();
                let mut i = 0;
                while let Ok(val) = row.get::<_, Value>(i) {
                    values.push((i, val));
                    i += 1;
                }
                Ok(values)
            })
            .with_context(|| format!("Failed to execute query: {sql}"))?
            .collect::<std::result::Result<Vec<_>, _>>()
            .context("Failed to read rows")?;

        // Now stmt's mutable borrow is released; column_count()/column_name() are safe
        let column_count = stmt.column_count();
        let column_names: Vec<String> = (0..column_count)
            .map(|i| {
                stmt.column_name(i)
                    .map_or("?".to_string(), |v| v.to_string())
            })
            .collect();

        let rows: Vec<Vec<String>> = raw_rows
            .into_iter()
            .map(|vals| vals.into_iter().map(|(_, v)| value_to_string(&v)).collect())
            .collect();

        Ok(QueryResult {
            columns: column_names,
            rows,
        })
    }

    /// List all user tables in the database.
    pub fn list_tables(&self) -> Result<Vec<TableInfo>> {
        let mut stmt = self
            .conn
            .prepare(
                "SELECT table_schema, table_name FROM information_schema.tables \
                 WHERE table_schema NOT IN ('information_schema', 'pg_catalog') \
                 AND table_type = 'BASE TABLE' \
                 ORDER BY table_schema, table_name",
            )
            .context("Failed to query information_schema")?;

        let rows = stmt
            .query_map([], |row| {
                let schema: Value = row.get(0)?;
                let name: Value = row.get(1)?;
                Ok(TableInfo {
                    schema: value_to_string(&schema),
                    name: value_to_string(&name),
                })
            })
            .context("Failed to list tables")?;

        let mut tables = Vec::new();
        for row in rows {
            tables.push(row.context("Failed to read table info")?);
        }

        Ok(tables)
    }

    /// Get the row count for a specific table.
    pub fn table_row_count(&self, table: &str) -> Result<u64> {
        // Validate table name to prevent SQL injection (alphanumeric + underscore only)
        if !table.chars().all(|c| c.is_alphanumeric() || c == '_') {
            anyhow::bail!("Invalid table name: {table}");
        }

        let sql = format!("SELECT COUNT(*) FROM \"{table}\"");
        let mut stmt = self.conn.prepare(&sql)?;
        let mut rows = stmt.query([])?;

        if let Some(row) = rows.next()? {
            let value: Value = row.get(0)?;
            match value {
                Value::BigInt(n) => Ok(n as u64),
                Value::Int(n) => Ok(n as u64),
                Value::HugeInt(n) => Ok(n as u64),
                _ => Ok(0),
            }
        } else {
            Ok(0)
        }
    }

    /// Export a table to a Parquet file.
    pub fn export_table_parquet(&self, table: &str, output: &Path) -> Result<()> {
        // Validate table name
        if !table.chars().all(|c| c.is_alphanumeric() || c == '_') {
            anyhow::bail!("Invalid table name: {table}");
        }

        let output_str = output.display().to_string();
        let sql = format!("COPY \"{table}\" TO '{output_str}' (FORMAT PARQUET)");
        self.conn
            .execute_batch(&sql)
            .with_context(|| format!("Failed to export {table} to parquet"))?;

        Ok(())
    }
}

/// Convert a DuckDB `Value` to a display string.
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
        Value::Date32(d) => d.to_string(),
        Value::Time64(..) => format!("{value:?}"),
        Value::Timestamp(..) => format!("{value:?}"),
        Value::Interval { .. } => format!("{value:?}"),
        _ => format!("{value:?}"),
    }
}
