use std::path::{Path, PathBuf};

use anyhow::{Context, Result};
use colored::Colorize;

use crate::local_engine::LocalEngine;

const DEFAULT_CONFIG: &str = r#"# HatiData configuration
# Docs: https://docs.hatidata.com/cli

# Cloud endpoint for push/pull
cloud_endpoint = "https://api.hatidata.com"

# API key (set via `hati config set api_key hd_live_...`)
api_key = ""

# Default push target: "cloud" or "vpc"
default_target = "cloud"

# Organization ID
org_id = ""
"#;

const GITIGNORE: &str = r#"# HatiData local files
*.duckdb
*.duckdb.wal
"#;

pub async fn run(path: Option<String>) -> Result<()> {
    let base_dir = match path {
        Some(p) => PathBuf::from(p),
        None => std::env::current_dir().context("Failed to get current directory")?,
    };

    let hati_dir = base_dir.join(".hati");

    if hati_dir.exists() {
        println!(
            "{} HatiData project already initialized at {}",
            "!".yellow().bold(),
            hati_dir.display().to_string().dimmed()
        );
        return Ok(());
    }

    println!(
        "{} Initializing HatiData project in {}",
        ">".cyan().bold(),
        base_dir.display().to_string().bold()
    );

    // Create .hati directory
    std::fs::create_dir_all(&hati_dir)
        .with_context(|| format!("Failed to create {}", hati_dir.display()))?;
    println!("  {} Created {}", "+".green().bold(), ".hati/".dimmed());

    // Write config.toml
    let config_path = hati_dir.join("config.toml");
    std::fs::write(&config_path, DEFAULT_CONFIG)
        .with_context(|| format!("Failed to write {}", config_path.display()))?;
    println!(
        "  {} Created {}",
        "+".green().bold(),
        "config.toml".dimmed()
    );

    // Write .gitignore
    let gitignore_path = hati_dir.join(".gitignore");
    std::fs::write(&gitignore_path, GITIGNORE)
        .with_context(|| format!("Failed to write {}", gitignore_path.display()))?;
    println!("  {} Created {}", "+".green().bold(), ".gitignore".dimmed());

    // Create empty DuckDB database
    let db_path = hati_dir.join("local.duckdb");
    create_local_db(&db_path)?;
    println!(
        "  {} Created {}",
        "+".green().bold(),
        "local.duckdb".dimmed()
    );

    println!();
    println!("{} HatiData project initialized!", "OK".green().bold());
    println!();
    println!("Next steps:");
    println!("  {} Set your API key", "1.".dimmed());
    println!("     {}", "hati config set api_key hd_live_...".cyan());
    println!("  {} Run a query", "2.".dimmed());
    println!(
        "     {}",
        "hati query \"CREATE TABLE test (id INT, name VARCHAR)\"".cyan()
    );
    println!("  {} Push to cloud", "3.".dimmed());
    println!("     {}", "hati push".cyan());

    Ok(())
}

fn create_local_db(path: &Path) -> Result<()> {
    let _engine = LocalEngine::open(path).context("Failed to create local DuckDB database")?;
    Ok(())
}
