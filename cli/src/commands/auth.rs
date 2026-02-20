use anyhow::{Context, Result};
use colored::Colorize;

use crate::context;
use crate::sync::SyncClient;

/// Run the `hati auth login` subcommand.
pub async fn login() -> Result<()> {
    let hati_dir = context::find_hati_dir()?;
    let config = context::load_config()?;
    let endpoint = config
        .get("cloud_endpoint")
        .and_then(|v| v.as_str())
        .unwrap_or("https://api.hatidata.com");

    let email: String = dialoguer::Input::new()
        .with_prompt("Email")
        .interact_text()
        .context("Failed to read email")?;

    let password = rpassword::prompt_password("Password: ").context("Failed to read password")?;

    let client = SyncClient::new_unauthenticated(endpoint);
    println!("\n{} Logging in...", ">".cyan().bold());

    let resp = client.login(&email, &password).await?;
    let session = context::SessionData {
        token: resp.token,
        email: email.clone(),
        expires_at: String::new(),
    };
    context::save_session(&hati_dir, &session)?;

    println!("{} Logged in as {}", "OK".green().bold(), email.bold());
    Ok(())
}

/// Run the `hati auth signup` subcommand.
pub async fn signup() -> Result<()> {
    let hati_dir = context::find_hati_dir()?;
    super::init::do_signup_flow(&hati_dir).await
}

/// Run the `hati auth status` subcommand.
pub async fn status() -> Result<()> {
    let config = context::load_config()?;
    let api_key = config.get("api_key").and_then(|v| v.as_str()).unwrap_or("");
    let org_id = config.get("org_id").and_then(|v| v.as_str()).unwrap_or("");
    let endpoint = config
        .get("cloud_endpoint")
        .and_then(|v| v.as_str())
        .unwrap_or("https://api.hatidata.com");

    println!("{} Auth Status", ">".cyan().bold());
    println!();
    println!("  {:<16} {}", "Endpoint:".dimmed(), endpoint);
    println!(
        "  {:<16} {}",
        "Org ID:".dimmed(),
        if org_id.is_empty() {
            "(not set)"
        } else {
            org_id
        }
    );
    println!(
        "  {:<16} {}",
        "API Key:".dimmed(),
        if api_key.is_empty() {
            "(not set)".to_string()
        } else {
            context::mask_api_key(api_key)
        }
    );

    match context::load_session() {
        Ok(session) => {
            println!("  {:<16} {}", "Email:".dimmed(), session.email);
            println!("  {:<16} {}", "Session:".dimmed(), "active".green());
            if !session.expires_at.is_empty() {
                println!("  {:<16} {}", "Expires:".dimmed(), session.expires_at);
            }
        }
        Err(_) => {
            println!("  {:<16} {}", "Session:".dimmed(), "none".yellow());
        }
    }

    Ok(())
}

/// Run the `hati auth logout` subcommand.
pub async fn logout() -> Result<()> {
    context::remove_session()?;
    println!("{} Logged out.", "OK".green().bold());
    Ok(())
}

/// Run the `hati auth upgrade` subcommand.
pub async fn upgrade() -> Result<()> {
    let url = "https://app.hatidata.com/billing";
    println!("{} Opening billing page: {}", ">".cyan().bold(), url.cyan());
    if open::that(url).is_err() {
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
    use crate::context;

    #[test]
    fn test_api_key_mask_logic() {
        assert_eq!(
            context::mask_api_key("hd_live_abcdef123456"),
            "hd_live_...3456"
        );
        assert_eq!(context::mask_api_key("hd_test_xyz"), "****");
        assert_eq!(context::mask_api_key(""), "****");
    }
}
