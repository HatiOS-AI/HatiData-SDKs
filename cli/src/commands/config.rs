use std::path::PathBuf;

use anyhow::{bail, Context, Result};
use colored::Colorize;

const VALID_KEYS: &[&str] = &["cloud_endpoint", "api_key", "default_target", "org_id"];

pub async fn set(key: String, value: String) -> Result<()> {
    if !VALID_KEYS.contains(&key.as_str()) {
        bail!(
            "Unknown config key '{}'. Valid keys: {}",
            key,
            VALID_KEYS.join(", ")
        );
    }

    let config_path = find_config_path()?;
    let contents = std::fs::read_to_string(&config_path).context("Failed to read config.toml")?;
    let mut config: toml::Table = contents.parse().context("Failed to parse config.toml")?;

    config.insert(key.clone(), toml::Value::String(value.clone()));

    let output = toml::to_string_pretty(&config).context("Failed to serialize config")?;
    std::fs::write(&config_path, output).context("Failed to write config.toml")?;

    let display_value = if key == "api_key" {
        if value.len() > 8 {
            format!("{}...", &value[..8])
        } else {
            "(set)".to_string()
        }
    } else {
        value
    };

    println!(
        "{} {} = {}",
        "OK".green().bold(),
        key.cyan(),
        display_value
    );

    Ok(())
}

pub async fn get(key: String) -> Result<()> {
    if !VALID_KEYS.contains(&key.as_str()) {
        bail!(
            "Unknown config key '{}'. Valid keys: {}",
            key,
            VALID_KEYS.join(", ")
        );
    }

    let config_path = find_config_path()?;
    let contents = std::fs::read_to_string(&config_path).context("Failed to read config.toml")?;
    let config: toml::Table = contents.parse().context("Failed to parse config.toml")?;

    match config.get(&key) {
        Some(value) => {
            let display_value = if key == "api_key" {
                let s = value.as_str().unwrap_or("");
                if s.is_empty() {
                    "(not set)".to_string()
                } else if s.len() > 8 {
                    format!("{}...", &s[..8])
                } else {
                    "(set)".to_string()
                }
            } else {
                value.as_str().unwrap_or("").to_string()
            };
            println!("{} = {}", key.cyan(), display_value);
        }
        None => {
            println!("{} = {}", key.cyan(), "(not set)".dimmed());
        }
    }

    Ok(())
}

pub async fn list() -> Result<()> {
    let config_path = find_config_path()?;
    let contents = std::fs::read_to_string(&config_path).context("Failed to read config.toml")?;
    let config: toml::Table = contents.parse().context("Failed to parse config.toml")?;

    println!("{}", "HatiData Configuration".bold().underline());
    println!(
        "  {} {}",
        "File:".dimmed(),
        config_path.display().to_string().dimmed()
    );
    println!();

    for key in VALID_KEYS {
        let value = config.get(*key);
        let display_value = match value {
            Some(v) => {
                let s = v.as_str().unwrap_or("");
                if s.is_empty() {
                    "(not set)".dimmed().to_string()
                } else if *key == "api_key" {
                    if s.len() > 8 {
                        format!("{}...{}", &s[..8], "(redacted)".dimmed())
                    } else {
                        "(set)".green().to_string()
                    }
                } else {
                    s.to_string()
                }
            }
            None => "(not set)".dimmed().to_string(),
        };
        println!("  {} = {}", key.cyan(), display_value);
    }

    Ok(())
}

fn find_config_path() -> Result<PathBuf> {
    let mut dir = std::env::current_dir().context("Failed to get current directory")?;
    loop {
        let candidate = dir.join(".hati").join("config.toml");
        if candidate.exists() {
            return Ok(candidate);
        }
        if !dir.pop() {
            bail!(
                "No .hati/config.toml found. Run {} first.",
                "hati init".cyan()
            );
        }
    }
}
