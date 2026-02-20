use anyhow::{bail, Result};
use colored::Colorize;

const VALID_PAGES: &[&str] = &[
    "billing",
    "onboarding",
    "agents",
    "triggers",
    "branches",
    "cot",
    "api-keys",
    "policies",
];

const DASHBOARD_BASE: &str = "https://app.hatidata.com";

/// Build the full dashboard URL for a given page.
pub fn build_url(page: &str) -> String {
    if page.is_empty() {
        DASHBOARD_BASE.to_string()
    } else {
        format!("{}/{}", DASHBOARD_BASE, page)
    }
}

pub async fn run(page: String) -> Result<()> {
    if !page.is_empty() && !VALID_PAGES.contains(&page.as_str()) {
        bail!(
            "Unknown page '{}'. Valid pages: {}",
            page,
            VALID_PAGES.join(", ")
        );
    }

    // Check that user has an API key configured
    match crate::context::load_config() {
        Ok(config) => {
            let api_key = config.get("api_key").and_then(|v| v.as_str()).unwrap_or("");
            if api_key.is_empty() {
                println!(
                    "{} No API key configured. Run {} first.",
                    "!".yellow().bold(),
                    "hati auth login".cyan()
                );
            }
        }
        Err(_) => {
            println!(
                "{} No .hati/ directory found. Run {} first.",
                "!".yellow().bold(),
                "hati init".cyan()
            );
        }
    }

    let url = build_url(&page);
    println!("{} Opening dashboard: {}", ">".cyan().bold(), url.cyan());
    if open::that(&url).is_err() {
        println!(
            "{} Could not open browser. Visit: {}",
            "!".yellow().bold(),
            url
        );
    }
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_dashboard_url_construction() {
        assert_eq!(build_url(""), "https://app.hatidata.com");
        assert_eq!(build_url("billing"), "https://app.hatidata.com/billing");
        assert_eq!(
            build_url("onboarding"),
            "https://app.hatidata.com/onboarding"
        );
        assert_eq!(build_url("api-keys"), "https://app.hatidata.com/api-keys");
    }

    #[test]
    fn test_valid_pages_list() {
        assert!(VALID_PAGES.contains(&"billing"));
        assert!(VALID_PAGES.contains(&"onboarding"));
        assert!(VALID_PAGES.contains(&"api-keys"));
        assert!(!VALID_PAGES.contains(&"nonexistent"));
    }

    #[tokio::test]
    async fn test_dashboard_invalid_page_rejected() {
        let result = run("invalid-page".to_string()).await;
        assert!(result.is_err());
        assert!(result.unwrap_err().to_string().contains("Unknown page"));
    }
}
