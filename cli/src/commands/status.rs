use std::path::PathBuf;

use anyhow::{bail, Context, Result};
use colored::Colorize;

use crate::local_engine::LocalEngine;

pub async fn run() -> Result<()> {
    let hati_dir = find_hati_dir()?;
    let db_path = hati_dir.join("local.duckdb");
    let config_path = hati_dir.join("config.toml");

    // Header
    println!("{}", "HatiData Project Status".bold().underline());
    println!();

    // Location
    println!(
        "  {} {}",
        "Location:".bold(),
        hati_dir.display().to_string().dimmed()
    );

    // DuckDB file size
    let db_size = std::fs::metadata(&db_path)
        .map(|m| format_bytes(m.len()))
        .unwrap_or_else(|_| "not found".red().to_string());
    println!("  {} {}", "Database:".bold(), db_size);

    // Open engine and get stats
    if db_path.exists() {
        let engine = LocalEngine::open(&db_path).context("Failed to open local DuckDB")?;

        let tables = engine.list_tables()?;
        let table_count = tables.len();
        let mut total_rows: u64 = 0;

        if !tables.is_empty() {
            println!();
            println!("  {}", "Tables:".bold());
            for table in &tables {
                let row_count = engine.table_row_count(&table.name).unwrap_or(0);
                total_rows += row_count;
                println!(
                    "    {} {} ({} rows)",
                    "-".dimmed(),
                    table.name.cyan(),
                    row_count
                );
            }
        }

        println!();
        println!(
            "  {} {} table{}, {} total rows",
            "Summary:".bold(),
            table_count,
            if table_count == 1 { "" } else { "s" },
            total_rows
        );
    }

    // Config
    println!();
    println!("  {}", "Configuration:".bold());
    if config_path.exists() {
        let contents = std::fs::read_to_string(&config_path).unwrap_or_default();
        let config: toml::Value = contents.parse().unwrap_or(toml::Value::Table(Default::default()));

        if let Some(table) = config.as_table() {
            for (key, value) in table {
                let display_value = if key == "api_key" {
                    let s = value.as_str().unwrap_or("");
                    if s.is_empty() {
                        "(not set)".red().to_string()
                    } else if s.len() > 8 {
                        format!("{}...{}", &s[..8], "(redacted)".dimmed())
                    } else {
                        "(set)".green().to_string()
                    }
                } else {
                    let s = value.as_str().unwrap_or("");
                    if s.is_empty() {
                        "(not set)".dimmed().to_string()
                    } else {
                        s.to_string()
                    }
                };
                println!("    {} = {}", key.cyan(), display_value);
            }
        }
    } else {
        println!(
            "    {} config.toml not found",
            "!".yellow().bold()
        );
    }

    // Sync status
    println!();
    println!("  {}", "Sync:".bold());
    println!(
        "    {} No sync history yet",
        "-".dimmed()
    );

    Ok(())
}

fn find_hati_dir() -> Result<PathBuf> {
    let mut dir = std::env::current_dir().context("Failed to get current directory")?;
    loop {
        let candidate = dir.join(".hati");
        if candidate.is_dir() {
            return Ok(candidate);
        }
        if !dir.pop() {
            bail!(
                "No .hati/ directory found. Run {} first.",
                "hati init".cyan()
            );
        }
    }
}

fn format_bytes(bytes: u64) -> String {
    if bytes < 1024 {
        format!("{bytes} B")
    } else if bytes < 1024 * 1024 {
        format!("{:.1} KB", bytes as f64 / 1024.0)
    } else if bytes < 1024 * 1024 * 1024 {
        format!("{:.1} MB", bytes as f64 / (1024.0 * 1024.0))
    } else {
        format!("{:.1} GB", bytes as f64 / (1024.0 * 1024.0 * 1024.0))
    }
}
