use anyhow::{bail, Result};
use colored::Colorize;

use crate::context;

pub async fn run(tables: Option<String>) -> Result<()> {
    let _db_path = context::find_db_path()?;
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
    println!(
        "  {} Remote pull requires Cloud tier. Upgrade at: {}",
        "i".blue().bold(),
        "https://hatidata.com/pricing".cyan()
    );

    Ok(())
}
