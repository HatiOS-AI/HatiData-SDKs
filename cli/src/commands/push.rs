use std::path::PathBuf;

use anyhow::{bail, Context, Result};
use colored::Colorize;

use crate::local_engine::LocalEngine;
use crate::sync::SyncClient;

pub async fn run(target: String, tables: Option<String>) -> Result<()> {
    if target != "cloud" && target != "vpc" {
        bail!("Target must be 'cloud' or 'vpc', got '{target}'");
    }

    let db_path = find_db_path()?;
    let config = load_config()?;

    let cloud_endpoint = config
        .get("cloud_endpoint")
        .and_then(|v| v.as_str())
        .unwrap_or("https://api.hatidata.com");
    let api_key = config
        .get("api_key")
        .and_then(|v| v.as_str())
        .unwrap_or("");

    if api_key.is_empty() {
        bail!(
            "API key not configured. Run {} first.",
            "hati config set api_key hd_live_...".cyan()
        );
    }

    println!(
        "{} Pushing to {} ({})",
        ">".cyan().bold(),
        target.bold(),
        cloud_endpoint.dimmed()
    );
    println!();

    let engine = LocalEngine::open(&db_path).context("Failed to open local DuckDB")?;

    // Determine which tables to push
    let table_list = match tables {
        Some(t) => t.split(',').map(|s| s.trim().to_string()).collect::<Vec<_>>(),
        None => {
            let infos = engine.list_tables()?;
            infos.into_iter().map(|t| t.name).collect()
        }
    };

    if table_list.is_empty() {
        println!(
            "{} No tables found. Create some tables first with {}",
            "!".yellow().bold(),
            "hati query".cyan()
        );
        return Ok(());
    }

    let _client = SyncClient::new(cloud_endpoint, api_key);

    for table_name in &table_list {
        let row_count = engine.table_row_count(table_name).unwrap_or(0);
        println!(
            "  {} {} ({} rows)",
            ">".cyan().bold(),
            table_name.bold(),
            row_count
        );

        // Export table to parquet in a temp directory
        let tmp_dir = std::env::temp_dir().join(format!("hati-push-{}", std::process::id()));
        std::fs::create_dir_all(&tmp_dir).context("Failed to create temp directory")?;
        let parquet_path = tmp_dir.join(format!("{table_name}.parquet"));
        engine.export_table_parquet(table_name, &parquet_path)?;

        let _parquet_data = std::fs::read(&parquet_path)
            .with_context(|| format!("Failed to read exported parquet for {table_name}"))?;

        // TODO: Implement actual sync upload
        // client.push_table(table_name, parquet_data).await?;
        println!(
            "    {} Sync not yet implemented — parquet export ready ({} bytes)",
            "!".yellow().bold(),
            std::fs::metadata(&parquet_path)
                .map(|m| m.len())
                .unwrap_or(0)
        );
    }

    println!();
    println!(
        "{} Push complete ({} table{})",
        "OK".green().bold(),
        table_list.len(),
        if table_list.len() == 1 { "" } else { "s" }
    );
    println!(
        "  {}",
        "Note: Remote sync is not yet implemented. Parquet export verified locally.".dimmed()
    );

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
