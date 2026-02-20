use std::path::{Path, PathBuf};

use anyhow::{Context, Result};
use colored::Colorize;

use crate::context;
use crate::local_engine::LocalEngine;
use crate::sync::SyncClient;

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
config.toml
session.json
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

    maybe_interactive_setup(&hati_dir).await?;

    Ok(())
}

fn create_local_db(path: &Path) -> Result<()> {
    let _engine = LocalEngine::open(path).context("Failed to create local DuckDB database")?;
    Ok(())
}

async fn maybe_interactive_setup(hati_dir: &std::path::Path) -> Result<()> {
    let config = context::load_config().unwrap_or_else(|_| toml::Value::Table(Default::default()));
    let api_key = config.get("api_key").and_then(|v| v.as_str()).unwrap_or("");

    if !api_key.is_empty() {
        return Ok(());
    }

    println!();
    println!(
        "{} No API key configured. How would you like to connect?",
        ">".cyan().bold()
    );
    println!();
    println!("  {} Sign up for a free account", "1.".dimmed());
    println!("  {} Enter an existing API key", "2.".dimmed());
    println!("  {} Continue in local-only mode", "3.".dimmed());
    println!();

    let selection = dialoguer::Select::new()
        .with_prompt("Choose an option")
        .items(&["Sign up free", "Enter API key", "Local-only"])
        .default(0)
        .interact_opt()
        .unwrap_or(Some(2))
        .unwrap_or(2);

    match selection {
        0 => do_signup_flow(hati_dir).await,
        1 => do_existing_key_flow(hati_dir).await,
        _ => {
            println!(
                "\n{} Continuing in local-only mode. Run {} to connect later.",
                ">".cyan().bold(),
                "hati auth login".cyan()
            );
            Ok(())
        }
    }
}

pub(crate) async fn do_signup_flow(hati_dir: &std::path::Path) -> Result<()> {
    let name: String = dialoguer::Input::new()
        .with_prompt("Your name")
        .interact_text()
        .context("Failed to read name")?;

    let email: String = dialoguer::Input::new()
        .with_prompt("Email")
        .interact_text()
        .context("Failed to read email")?;

    let password = rpassword::prompt_password("Password: ").context("Failed to read password")?;

    let company: String = dialoguer::Input::new()
        .with_prompt("Company/org name")
        .interact_text()
        .context("Failed to read company")?;

    let config = context::load_config().unwrap_or_else(|_| toml::Value::Table(Default::default()));
    let endpoint = config
        .get("cloud_endpoint")
        .and_then(|v| v.as_str())
        .unwrap_or("https://api.hatidata.com");

    let client = SyncClient::new_unauthenticated(endpoint);
    let req = crate::sync::SignupRequest {
        name,
        email: email.clone(),
        password,
        org_name: company,
        tier: "free".to_string(),
    };

    println!("\n{} Creating your account...", ">".cyan().bold());

    match client.signup(&req).await {
        Ok(resp) => {
            context::save_config_field(hati_dir, "org_id", &resp.org_id)?;
            if let Some(token) = &resp.token {
                let session = context::SessionData {
                    token: token.clone(),
                    email,
                    expires_at: String::new(),
                };
                context::save_session(hati_dir, &session)?;
            }
            println!(
                "{} Account created! Organization: {}",
                "OK".green().bold(),
                resp.org_id.dimmed()
            );
            Ok(())
        }
        Err(e) => {
            println!(
                "{} Signup failed: {}. You can try again with {}",
                "!".yellow().bold(),
                e,
                "hati auth signup".cyan()
            );
            Ok(())
        }
    }
}

pub(crate) async fn do_existing_key_flow(hati_dir: &std::path::Path) -> Result<()> {
    let key: String = dialoguer::Input::new()
        .with_prompt("API key (hd_live_... or hd_test_...)")
        .interact_text()
        .context("Failed to read API key")?;

    if !key.starts_with("hd_live_") && !key.starts_with("hd_test_") {
        println!(
            "{} API key must start with {} or {}",
            "!".yellow().bold(),
            "hd_live_".cyan(),
            "hd_test_".cyan()
        );
        return Ok(());
    }

    let config = context::load_config().unwrap_or_else(|_| toml::Value::Table(Default::default()));
    let endpoint = config
        .get("cloud_endpoint")
        .and_then(|v| v.as_str())
        .unwrap_or("https://api.hatidata.com");

    let client = SyncClient::new(endpoint, &key);
    println!("\n{} Verifying API key...", ">".cyan().bold());

    match client.auth_me().await {
        Ok(me) => {
            context::save_config_field(hati_dir, "api_key", &key)?;
            context::save_config_field(hati_dir, "org_id", &me.org_id)?;
            println!(
                "{} Verified! Logged in as {} (org: {})",
                "OK".green().bold(),
                me.email.bold(),
                me.org_id.dimmed()
            );
            Ok(())
        }
        Err(e) => {
            println!("{} Key verification failed: {}", "!".yellow().bold(), e);
            Ok(())
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use tempfile::TempDir;

    #[tokio::test]
    async fn test_init_creates_hati_directory() {
        let tmp = TempDir::new().unwrap();
        let base = tmp.path().to_path_buf();

        run(Some(base.to_string_lossy().to_string())).await.unwrap();

        let hati_dir = base.join(".hati");
        assert!(hati_dir.exists());
        assert!(hati_dir.join("config.toml").exists());
        assert!(hati_dir.join(".gitignore").exists());
        assert!(hati_dir.join("local.duckdb").exists());
    }

    #[tokio::test]
    async fn test_init_config_has_default_keys() {
        let tmp = TempDir::new().unwrap();
        let base = tmp.path().to_path_buf();

        run(Some(base.to_string_lossy().to_string())).await.unwrap();

        let config_content = std::fs::read_to_string(base.join(".hati/config.toml")).unwrap();
        assert!(config_content.contains("cloud_endpoint"));
        assert!(config_content.contains("api_key"));
        assert!(config_content.contains("default_target"));
        assert!(config_content.contains("org_id"));
    }

    #[tokio::test]
    async fn test_init_gitignore_excludes_duckdb() {
        let tmp = TempDir::new().unwrap();
        let base = tmp.path().to_path_buf();

        run(Some(base.to_string_lossy().to_string())).await.unwrap();

        let gitignore = std::fs::read_to_string(base.join(".hati/.gitignore")).unwrap();
        assert!(gitignore.contains("*.duckdb"));
        assert!(gitignore.contains("config.toml"));
        assert!(gitignore.contains("session.json"));
    }

    #[tokio::test]
    async fn test_init_already_initialized() {
        let tmp = TempDir::new().unwrap();
        let base = tmp.path().to_path_buf();

        // Initialize once
        run(Some(base.to_string_lossy().to_string())).await.unwrap();

        // Second init should succeed without error (early return)
        let result = run(Some(base.to_string_lossy().to_string())).await;
        assert!(result.is_ok());
    }

    #[test]
    fn test_create_local_db() {
        let tmp = TempDir::new().unwrap();
        let db_path = tmp.path().join("test.duckdb");

        create_local_db(&db_path).unwrap();
        assert!(db_path.exists());
    }

    #[test]
    fn test_default_config_is_valid_toml() {
        let config: toml::Value = DEFAULT_CONFIG.parse().unwrap();
        assert!(config.get("cloud_endpoint").is_some());
        assert!(config.get("api_key").is_some());
    }
}
