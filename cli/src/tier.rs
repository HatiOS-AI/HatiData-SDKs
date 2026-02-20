//! Tier definitions and free-tier quota enforcement for the public CLI.
//!
//! Users must be authenticated (have a valid API key) to use any cloud features.
//! Free tier has strict local limits; paid tiers unlock progressively more.

use anyhow::{bail, Result};
use colored::Colorize;

/// HatiData pricing tiers.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Tier {
    Free,
    Cloud,
    Growth,
    Enterprise,
}

impl Tier {
    /// Parse a tier string (case-insensitive).
    pub fn parse(s: &str) -> Option<Self> {
        match s.to_lowercase().as_str() {
            "free" => Some(Self::Free),
            "cloud" => Some(Self::Cloud),
            "growth" => Some(Self::Growth),
            "enterprise" => Some(Self::Enterprise),
            _ => None,
        }
    }

    /// Display name for user-facing output.
    pub fn display_name(&self) -> &str {
        match self {
            Self::Free => "Free",
            Self::Cloud => "Cloud",
            Self::Growth => "Growth",
            Self::Enterprise => "Enterprise",
        }
    }
}

/// Per-tier resource limits enforced by the CLI before pushing data.
#[derive(Debug)]
pub struct TierLimits {
    /// Maximum number of tables per push operation.
    pub max_tables: usize,
    /// Maximum rows per individual table.
    pub max_rows_per_table: u64,
    /// Maximum Parquet file size in bytes per table.
    pub max_push_size_bytes: u64,
    /// Whether the tier allows pulling data from the cloud.
    pub can_pull_data: bool,
    /// Whether the tier allows pushing to VPC targets.
    pub can_push_vpc: bool,
}

impl TierLimits {
    /// Return the resource limits for a given tier.
    pub fn for_tier(tier: Tier) -> Self {
        match tier {
            Tier::Free => Self {
                max_tables: 5,
                max_rows_per_table: 10_000,
                max_push_size_bytes: 10 * 1024 * 1024, // 10 MB
                can_pull_data: false,
                can_push_vpc: false,
            },
            Tier::Cloud => Self {
                max_tables: 50,
                max_rows_per_table: 1_000_000,
                max_push_size_bytes: 100 * 1024 * 1024, // 100 MB
                can_pull_data: true,
                can_push_vpc: false,
            },
            Tier::Growth => Self {
                max_tables: 500,
                max_rows_per_table: 100_000_000,
                max_push_size_bytes: 1024 * 1024 * 1024, // 1 GB
                can_pull_data: true,
                can_push_vpc: true,
            },
            Tier::Enterprise => Self {
                max_tables: usize::MAX,
                max_rows_per_table: u64::MAX,
                max_push_size_bytes: u64::MAX,
                can_pull_data: true,
                can_push_vpc: true,
            },
        }
    }
}

/// Require the user to be authenticated. Returns `(cloud_endpoint, api_key)`.
///
/// Bails if no API key is configured, prompting the user to sign up or log in.
pub fn require_auth(config: &toml::Value) -> Result<(String, String)> {
    let endpoint = config
        .get("cloud_endpoint")
        .and_then(|v| v.as_str())
        .unwrap_or("https://api.hatidata.com")
        .to_string();

    let api_key = config
        .get("api_key")
        .and_then(|v| v.as_str())
        .unwrap_or("")
        .to_string();

    if api_key.is_empty() {
        println!(
            "{} Authentication required for cloud features.",
            "!".yellow().bold()
        );
        println!();
        println!("  Sign up:  {}", "hati auth signup".cyan());
        println!("  Log in:   {}", "hati auth login".cyan());
        println!(
            "  Or set:   {}",
            "hati config set api_key hd_live_...".cyan()
        );
        bail!("Not authenticated. Sign up or log in to use cloud features.");
    }

    Ok((endpoint, api_key))
}

/// Resolve the effective tier from config and an optional CLI override.
///
/// Priority: `--tier` flag > `config.toml` `tier` field > default `Free`.
pub fn resolve_tier(config: &toml::Value, tier_override: Option<&str>) -> Tier {
    if let Some(t) = tier_override {
        Tier::parse(t).unwrap_or(Tier::Free)
    } else {
        config
            .get("tier")
            .and_then(|v| v.as_str())
            .and_then(Tier::parse)
            .unwrap_or(Tier::Free)
    }
}

/// Format a byte count into a human-readable string.
pub fn format_bytes(bytes: u64) -> String {
    if bytes < 1024 {
        format!("{bytes} B")
    } else if bytes < 1024 * 1024 {
        format!("{:.1} KB", bytes as f64 / 1024.0)
    } else if bytes < 1024 * 1024 * 1024 {
        format!("{:.1} MB", bytes as f64 / (1024.0 * 1024.0))
    } else {
        format!("{:.2} GB", bytes as f64 / (1024.0 * 1024.0 * 1024.0))
    }
}

/// Print a tier-limit upgrade hint.
pub fn print_upgrade_hint(tier: Tier) {
    match tier {
        Tier::Free => {
            println!(
                "  {} Upgrade to Cloud ($29/mo) for higher limits: {}",
                "i".blue().bold(),
                "https://hatidata.com/pricing".cyan()
            );
        }
        Tier::Cloud => {
            println!(
                "  {} Upgrade to Growth for VPC push and higher limits: {}",
                "i".blue().bold(),
                "https://hatidata.com/pricing".cyan()
            );
        }
        _ => {}
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_tier_parse_valid() {
        assert_eq!(Tier::parse("free"), Some(Tier::Free));
        assert_eq!(Tier::parse("Free"), Some(Tier::Free));
        assert_eq!(Tier::parse("FREE"), Some(Tier::Free));
        assert_eq!(Tier::parse("cloud"), Some(Tier::Cloud));
        assert_eq!(Tier::parse("Cloud"), Some(Tier::Cloud));
        assert_eq!(Tier::parse("growth"), Some(Tier::Growth));
        assert_eq!(Tier::parse("enterprise"), Some(Tier::Enterprise));
    }

    #[test]
    fn test_tier_parse_invalid() {
        assert_eq!(Tier::parse(""), None);
        assert_eq!(Tier::parse("pro"), None);
        assert_eq!(Tier::parse("team"), None);
    }

    #[test]
    fn test_tier_display_name() {
        assert_eq!(Tier::Free.display_name(), "Free");
        assert_eq!(Tier::Cloud.display_name(), "Cloud");
        assert_eq!(Tier::Growth.display_name(), "Growth");
        assert_eq!(Tier::Enterprise.display_name(), "Enterprise");
    }

    #[test]
    fn test_free_tier_limits() {
        let limits = TierLimits::for_tier(Tier::Free);
        assert_eq!(limits.max_tables, 5);
        assert_eq!(limits.max_rows_per_table, 10_000);
        assert_eq!(limits.max_push_size_bytes, 10 * 1024 * 1024);
        assert!(!limits.can_pull_data);
        assert!(!limits.can_push_vpc);
    }

    #[test]
    fn test_cloud_tier_limits() {
        let limits = TierLimits::for_tier(Tier::Cloud);
        assert_eq!(limits.max_tables, 50);
        assert_eq!(limits.max_rows_per_table, 1_000_000);
        assert!(limits.can_pull_data);
        assert!(!limits.can_push_vpc);
    }

    #[test]
    fn test_growth_tier_limits() {
        let limits = TierLimits::for_tier(Tier::Growth);
        assert_eq!(limits.max_tables, 500);
        assert!(limits.can_pull_data);
        assert!(limits.can_push_vpc);
    }

    #[test]
    fn test_enterprise_tier_limits() {
        let limits = TierLimits::for_tier(Tier::Enterprise);
        assert_eq!(limits.max_tables, usize::MAX);
        assert!(limits.can_pull_data);
        assert!(limits.can_push_vpc);
    }

    #[test]
    fn test_require_auth_missing_key() {
        let config: toml::Value = "cloud_endpoint = \"https://api.hatidata.com\"\n"
            .parse()
            .unwrap();
        let result = require_auth(&config);
        assert!(result.is_err());
        assert!(result.unwrap_err().to_string().contains("Not authenticated"));
    }

    #[test]
    fn test_require_auth_empty_key() {
        let config: toml::Value =
            "cloud_endpoint = \"https://api.hatidata.com\"\napi_key = \"\"\n"
                .parse()
                .unwrap();
        let result = require_auth(&config);
        assert!(result.is_err());
    }

    #[test]
    fn test_require_auth_valid_key() {
        let config: toml::Value =
            "cloud_endpoint = \"https://api.hatidata.com\"\napi_key = \"hd_live_test123\"\n"
                .parse()
                .unwrap();
        let (endpoint, key) = require_auth(&config).unwrap();
        assert_eq!(endpoint, "https://api.hatidata.com");
        assert_eq!(key, "hd_live_test123");
    }

    #[test]
    fn test_require_auth_default_endpoint() {
        let config: toml::Value = "api_key = \"hd_live_abc\"\n".parse().unwrap();
        let (endpoint, _) = require_auth(&config).unwrap();
        assert_eq!(endpoint, "https://api.hatidata.com");
    }

    #[test]
    fn test_resolve_tier_override() {
        let config: toml::Value = "tier = \"free\"\n".parse().unwrap();
        assert_eq!(resolve_tier(&config, Some("cloud")), Tier::Cloud);
        assert_eq!(resolve_tier(&config, Some("growth")), Tier::Growth);
    }

    #[test]
    fn test_resolve_tier_from_config() {
        let config: toml::Value = "tier = \"cloud\"\n".parse().unwrap();
        assert_eq!(resolve_tier(&config, None), Tier::Cloud);
    }

    #[test]
    fn test_resolve_tier_default_free() {
        let config: toml::Value = "api_key = \"x\"\n".parse().unwrap();
        assert_eq!(resolve_tier(&config, None), Tier::Free);
    }

    #[test]
    fn test_resolve_tier_invalid_override_falls_back_to_free() {
        let config: toml::Value = "tier = \"cloud\"\n".parse().unwrap();
        assert_eq!(resolve_tier(&config, Some("pro")), Tier::Free);
    }

    #[test]
    fn test_format_bytes() {
        assert_eq!(format_bytes(500), "500 B");
        assert_eq!(format_bytes(1536), "1.5 KB");
        assert_eq!(format_bytes(10 * 1024 * 1024), "10.0 MB");
        assert_eq!(format_bytes(1024 * 1024 * 1024), "1.00 GB");
    }
}
