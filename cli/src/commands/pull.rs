use std::path::PathBuf;

use anyhow::{bail, Context, Result};
use colored::Colorize;

pub async fn run(tables: Option<String>) -> Result<()> {
    let _db_path = find_db_path()?;
    let config = load_config()?;

    let cloud_endpoint = config
        .get("cloud_endpoint")
        .and_then(|v| v.as_str())
        .unwrap_or("https://api.hatidata.com");
    let api_key = config.get("api_key").and_then(|v| v.as_str()).unwrap_or("");

    if api_key.is_empty() {
        bail!(
            "API key not configured. Run {} first.",
            "hati config set api_key hd_live_...".cyan()
        );
    }

    let table_filter = match &tables {
        Some(t) => {
            let list: Vec<&str> = t.split(',').map(|s| s.trim()).collect();
            format!(
                "{} table{}",
                list.len(),
                if list.len() == 1 { "" } else { "s" }
            )
        }
        None => "all tables".to_string(),
    };

    println!(
        "{} Pulling {} from {}",
        ">".cyan().bold(),
        table_filter.bold(),
        cloud_endpoint.dimmed()
    );
    println!();

    // TODO: Implement actual sync download
    // 1. Call SyncClient::pull_schema() to get remote table list
    // 2. For each table, call SyncClient::pull_table() to get Parquet bytes
    // 3. Load Parquet into local DuckDB via COPY ... FROM

    println!(
        "  {} Remote pull is not yet implemented.",
        "!".yellow().bold()
    );
    println!(
        "  {}",
        "This will download schema and data from the remote endpoint into local DuckDB.".dimmed()
    );
    println!();
    println!("{} When implemented, pull will:", "INFO".blue().bold());
    println!("  - Fetch remote table schemas");
    println!("  - Download data as Parquet");
    println!("  - Load into local .hati/local.duckdb");
    println!("  - Report row counts and sync status");

    Ok(())
}

fn find_db_path() -> Result<PathBuf> {
    let mut dir = std::env::current_dir().context("Failed to get current directory")?;
    loop {
        let candidate = dir.join(".hati").join("local.duckdb");
        if candidate.exists() {
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

fn load_config() -> Result<toml::Value> {
    let mut dir = std::env::current_dir().context("Failed to get current directory")?;
    loop {
        let config_path = dir.join(".hati").join("config.toml");
        if config_path.exists() {
            let contents =
                std::fs::read_to_string(&config_path).context("Failed to read config.toml")?;
            let config: toml::Value = contents.parse().context("Failed to parse config.toml")?;
            return Ok(config);
        }
        if !dir.pop() {
            bail!(
                "No .hati/config.toml found. Run {} first.",
                "hati init".cyan()
            );
        }
    }
}
