use anyhow::{bail, Result};
use colored::Colorize;

use crate::context;
use crate::tier::{self, TierLimits};

pub async fn run(tables: Option<String>) -> Result<()> {
    // ── Auth gate: must be signed in ─────────────────────────────────────
    let config = context::load_config()?;
    let (_endpoint, _api_key) = tier::require_auth(&config)?;

    // ── Resolve tier ─────────────────────────────────────────────────────
    let effective_tier = tier::resolve_tier(&config, None);
    let limits = TierLimits::for_tier(effective_tier);

    // ── Tier gate: pull requires Cloud or higher ─────────────────────────
    if !limits.can_pull_data {
        println!(
            "{} Pull requires Cloud tier or higher. Current tier: {}",
            "!".yellow().bold(),
            effective_tier.display_name().bold()
        );
        println!();
        println!(
            "  {} Free tier supports local-only mode (query, push export).",
            "i".blue().bold()
        );
        println!(
            "  {} Upgrade to Cloud ($29/mo) for remote sync: {}",
            "i".blue().bold(),
            "https://hatidata.com/pricing".cyan()
        );
        bail!("Pull requires Cloud tier or higher");
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
        "{} Pulling {} (tier: {})",
        ">".cyan().bold(),
        table_filter.bold(),
        effective_tier.display_name().dimmed()
    );
    println!();
    println!(
        "  {} Remote pull endpoint coming soon.",
        "i".blue().bold(),
    );

    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[tokio::test]
    async fn test_pull_requires_auth() {
        // No .hati/ dir → fails at load_config or require_auth
        let result = run(None).await;
        assert!(result.is_err());
    }
}
