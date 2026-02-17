use anyhow::{bail, Context, Result};
use colored::Colorize;

use crate::context;
use crate::local_engine::LocalEngine;

pub async fn run(target: String, tables: Option<String>) -> Result<()> {
    if target != "cloud" && target != "vpc" {
        bail!("Target must be 'cloud' or 'vpc', got '{target}'");
    }

    let db_path = context::find_db_path()?;
    let config = context::load_config()?;

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
        Some(t) => t
            .split(',')
            .map(|s| s.trim().to_string())
            .collect::<Vec<_>>(),
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

        let size = std::fs::metadata(&parquet_path)
            .map(|m| m.len())
            .unwrap_or(0);

        println!(
            "    {} Parquet export ready ({} bytes). Upgrade to Cloud tier for remote sync.",
            "i".blue().bold(),
            size
        );

        // Clean up
        let _ = std::fs::remove_file(&parquet_path);
        let _ = std::fs::remove_dir(&tmp_dir);
    }

    println!();
    println!(
        "{} Local export verified ({} table{})",
        "OK".green().bold(),
        table_list.len(),
        if table_list.len() == 1 { "" } else { "s" }
    );
    println!(
        "  {} Upgrade to Cloud tier for remote push/pull: {}",
        "i".blue().bold(),
        "https://hatidata.com/pricing".cyan()
    );

    Ok(())
}
