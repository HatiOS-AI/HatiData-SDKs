use anyhow::{bail, Context, Result};
use colored::Colorize;

use crate::context;
use crate::local_engine::LocalEngine;
use crate::tier::{self, Tier, TierLimits};

pub async fn run(target: String, tables: Option<String>, tier_flag: Option<String>) -> Result<()> {
    if target != "cloud" && target != "vpc" {
        bail!("Target must be 'cloud' or 'vpc', got '{target}'");
    }

    // ── Auth gate: must be signed in ─────────────────────────────────────
    let config = context::load_config()?;
    let (_endpoint, _api_key) = tier::require_auth(&config)?;

    // ── Resolve tier ─────────────────────────────────────────────────────
    let effective_tier = tier::resolve_tier(&config, tier_flag.as_deref());
    let limits = TierLimits::for_tier(effective_tier);

    // ── VPC gate ─────────────────────────────────────────────────────────
    if target == "vpc" && !limits.can_push_vpc {
        println!(
            "{} VPC push requires Growth or Enterprise tier. Current tier: {}",
            "!".yellow().bold(),
            effective_tier.display_name().bold()
        );
        println!(
            "  Upgrade at: {}",
            "https://app.hatidata.com/billing".cyan()
        );
        println!("  Or use {} for cloud sync.", "hati push --target cloud".cyan());
        bail!("VPC push requires Growth tier or higher");
    }

    println!(
        "{} Pushing to {} (tier: {})",
        ">".cyan().bold(),
        target.bold(),
        effective_tier.display_name().dimmed()
    );
    println!();

    let db_path = context::find_db_path()?;
    let engine = LocalEngine::open(&db_path).context("Failed to open local DuckDB")?;

    // ── Determine which tables to push ───────────────────────────────────
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

    // ── Table count limit ────────────────────────────────────────────────
    if table_list.len() > limits.max_tables {
        println!(
            "{} {} tier allows max {} tables per push, got {}.",
            "!".red().bold(),
            effective_tier.display_name(),
            limits.max_tables,
            table_list.len()
        );
        tier::print_upgrade_hint(effective_tier);
        bail!(
            "{} tier limit: max {} tables per push (requested {})",
            effective_tier.display_name(),
            limits.max_tables,
            table_list.len()
        );
    }

    let mut success_count = 0u32;

    for table_name in &table_list {
        let row_count = engine.table_row_count(table_name).unwrap_or(0);

        // ── Row count limit ──────────────────────────────────────────────
        if row_count > limits.max_rows_per_table {
            println!(
                "  {} {} has {} rows (limit: {} for {} tier). Skipping.",
                "!".red().bold(),
                table_name.bold(),
                row_count,
                limits.max_rows_per_table,
                effective_tier.display_name()
            );
            tier::print_upgrade_hint(effective_tier);
            continue;
        }

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

        // ── File size limit ──────────────────────────────────────────────
        if size > limits.max_push_size_bytes {
            println!(
                "    {} Parquet file {} exceeds {} tier limit ({}). Skipping.",
                "!".red().bold(),
                tier::format_bytes(size),
                effective_tier.display_name(),
                tier::format_bytes(limits.max_push_size_bytes)
            );
            tier::print_upgrade_hint(effective_tier);
            let _ = std::fs::remove_file(&parquet_path);
            let _ = std::fs::remove_dir(&tmp_dir);
            continue;
        }

        println!(
            "    {} Parquet ready ({})",
            "OK".green().bold(),
            tier::format_bytes(size)
        );

        // Clean up
        let _ = std::fs::remove_file(&parquet_path);
        let _ = std::fs::remove_dir(&tmp_dir);
        success_count += 1;
    }

    println!();
    if success_count > 0 {
        println!(
            "{} Verified {} table{} for push",
            "OK".green().bold(),
            success_count,
            if success_count == 1 { "" } else { "s" }
        );
    } else {
        println!(
            "{} No tables passed tier validation.",
            "!".yellow().bold()
        );
    }

    if effective_tier == Tier::Free {
        println!();
        println!(
            "  {} Free tier: local export only. Upgrade to Cloud for remote sync.",
            "i".blue().bold(),
        );
        println!(
            "    {}",
            "https://hatidata.com/pricing".cyan()
        );
    }

    Ok(())
}

/// Format an HTTP error with upgrade hints for 402/403 responses.
pub fn format_push_error(err: &anyhow::Error) -> String {
    let err_str = err.to_string();
    if err_str.contains("402") || err_str.contains("Payment Required") {
        format!(
            "{}. Upgrade your plan at: https://app.hatidata.com/billing",
            err_str
        )
    } else if err_str.contains("403") || err_str.contains("Forbidden") {
        format!(
            "{}. Insufficient permissions — check your API key scope or upgrade tier.",
            err_str
        )
    } else {
        err_str
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[tokio::test]
    async fn test_push_invalid_target_rejected() {
        let result = run("s3".to_string(), None, None).await;
        assert!(result.is_err());
        assert!(result
            .unwrap_err()
            .to_string()
            .contains("Target must be 'cloud' or 'vpc'"));
    }

    #[tokio::test]
    async fn test_push_vpc_requires_growth_tier() {
        // VPC push fails at auth gate (no .hati/ dir) or tier gate
        let result = run("vpc".to_string(), None, None).await;
        assert!(result.is_err());
    }

    #[tokio::test]
    async fn test_push_cloud_requires_auth() {
        // No .hati/ dir → fails at load_config or require_auth
        let result = run("cloud".to_string(), None, None).await;
        assert!(result.is_err());
        // Should NOT contain the target validation error
        assert!(!result.unwrap_err().to_string().contains("Target must be"));
    }

    #[test]
    fn test_format_push_error_402() {
        let err = anyhow::anyhow!("Push failed (HTTP 402 Payment Required): quota exceeded");
        let msg = format_push_error(&err);
        assert!(msg.contains("Upgrade your plan"));
        assert!(msg.contains("billing"));
    }

    #[test]
    fn test_format_push_error_403() {
        let err = anyhow::anyhow!("Push failed (HTTP 403 Forbidden): access denied");
        let msg = format_push_error(&err);
        assert!(msg.contains("Insufficient permissions"));
    }

    #[test]
    fn test_format_push_error_other() {
        let err = anyhow::anyhow!("Connection refused");
        let msg = format_push_error(&err);
        assert_eq!(msg, "Connection refused");
    }

    #[test]
    fn test_tier_flag_override() {
        // Verify that Tier::parse works for the flag values
        assert_eq!(Tier::parse("cloud"), Some(Tier::Cloud));
        assert_eq!(Tier::parse("growth"), Some(Tier::Growth));
    }

    #[test]
    fn test_free_tier_blocks_vpc() {
        let limits = TierLimits::for_tier(Tier::Free);
        assert!(!limits.can_push_vpc);
    }

    #[test]
    fn test_growth_tier_allows_vpc() {
        let limits = TierLimits::for_tier(Tier::Growth);
        assert!(limits.can_push_vpc);
    }
}
