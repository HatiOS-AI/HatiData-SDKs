//! Shared helpers for locating the HatiData project directory, database, and config.
//!
//! These functions walk up from the current working directory to find `.hati/`,
//! so CLI commands work from any subdirectory within a project.

use std::path::PathBuf;

use anyhow::{bail, Context, Result};
use colored::Colorize;

/// Locate the nearest `.hati/` directory by walking up from the current working directory.
pub fn find_hati_dir() -> Result<PathBuf> {
    let mut dir = std::env::current_dir().context("Failed to get current directory")?;
    loop {
        let candidate = dir.join(".hati");
        if candidate.is_dir() {
            return Ok(candidate);
        }
        if !dir.pop() {
            bail!(
                "No .hati/ directory found. Run {} first.",
                "hati init".cyan()
            );
        }
    }
}

/// Locate the DuckDB database file (`local.duckdb`) inside the nearest `.hati/` directory.
pub fn find_db_path() -> Result<PathBuf> {
    let hati_dir = find_hati_dir()?;
    let db_path = hati_dir.join("local.duckdb");
    if db_path.exists() {
        Ok(db_path)
    } else {
        bail!(
            "Database not found at {}. Run {} first.",
            db_path.display(),
            "hati init".cyan()
        );
    }
}

/// Load and parse `.hati/config.toml` as a `toml::Value`.
pub fn load_config() -> Result<toml::Value> {
    let hati_dir = find_hati_dir()?;
    let config_path = hati_dir.join("config.toml");
    if !config_path.exists() {
        bail!(
            "No .hati/config.toml found. Run {} first.",
            "hati init".cyan()
        );
    }
    let contents = std::fs::read_to_string(&config_path).context("Failed to read config.toml")?;
    let config: toml::Value = contents.parse().context("Failed to parse config.toml")?;
    Ok(config)
}

/// Load and parse `.hati/config.toml` as a `toml::Table` (for config set/get/list).
pub fn load_config_table() -> Result<(PathBuf, toml::Table)> {
    let hati_dir = find_hati_dir()?;
    let config_path = hati_dir.join("config.toml");
    if !config_path.exists() {
        bail!(
            "No .hati/config.toml found. Run {} first.",
            "hati init".cyan()
        );
    }
    let contents = std::fs::read_to_string(&config_path).context("Failed to read config.toml")?;
    let config: toml::Table = contents.parse().context("Failed to parse config.toml")?;
    Ok((config_path, config))
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::env;
    use std::sync::Mutex;
    use tempfile::TempDir;

    // Mutex to serialize tests that change the process-global cwd.
    static CWD_LOCK: Mutex<()> = Mutex::new(());

    /// Helper: run a closure with cwd temporarily set to `dir`.
    fn with_cwd<F, R>(dir: &std::path::Path, f: F) -> R
    where
        F: FnOnce() -> R,
    {
        let _guard = CWD_LOCK.lock().unwrap();
        let original = env::current_dir().unwrap();
        env::set_current_dir(dir).unwrap();
        let result = f();
        env::set_current_dir(&original).unwrap();
        result
    }

    #[test]
    fn test_find_hati_dir_from_project_root() {
        let tmp = TempDir::new().unwrap();
        let hati_dir = tmp.path().join(".hati");
        std::fs::create_dir_all(&hati_dir).unwrap();

        let result = with_cwd(tmp.path(), find_hati_dir);
        assert!(result.is_ok());
        let found = result.unwrap().canonicalize().unwrap();
        let expected = hati_dir.canonicalize().unwrap();
        assert_eq!(found, expected);
    }

    #[test]
    fn test_find_hati_dir_from_subdirectory() {
        let tmp = TempDir::new().unwrap();
        let hati_dir = tmp.path().join(".hati");
        std::fs::create_dir_all(&hati_dir).unwrap();
        let sub = tmp.path().join("src").join("deep");
        std::fs::create_dir_all(&sub).unwrap();

        let result = with_cwd(&sub, find_hati_dir);
        assert!(result.is_ok());
        let found = result.unwrap().canonicalize().unwrap();
        let expected = hati_dir.canonicalize().unwrap();
        assert_eq!(found, expected);
    }

    #[test]
    fn test_find_hati_dir_not_found() {
        let tmp = TempDir::new().unwrap();

        let result = with_cwd(tmp.path(), find_hati_dir);
        assert!(result.is_err());
        assert!(result.unwrap_err().to_string().contains("No .hati/"));
    }

    #[test]
    fn test_load_config_parses_toml() {
        let tmp = TempDir::new().unwrap();
        let hati_dir = tmp.path().join(".hati");
        std::fs::create_dir_all(&hati_dir).unwrap();
        std::fs::write(
            hati_dir.join("config.toml"),
            "cloud_endpoint = \"https://api.hatidata.com\"\napi_key = \"hd_live_test\"\n",
        )
        .unwrap();

        let config = with_cwd(tmp.path(), load_config);
        assert!(config.is_ok());
        let config = config.unwrap();
        assert_eq!(
            config.get("cloud_endpoint").and_then(|v| v.as_str()),
            Some("https://api.hatidata.com")
        );
    }

    #[test]
    fn test_load_config_missing_file() {
        let tmp = TempDir::new().unwrap();
        let hati_dir = tmp.path().join(".hati");
        std::fs::create_dir_all(&hati_dir).unwrap();

        let result = with_cwd(tmp.path(), load_config);
        assert!(result.is_err());
        assert!(result
            .unwrap_err()
            .to_string()
            .contains("No .hati/config.toml"));
    }

    #[test]
    fn test_find_db_path_exists() {
        let tmp = TempDir::new().unwrap();
        let hati_dir = tmp.path().join(".hati");
        std::fs::create_dir_all(&hati_dir).unwrap();
        std::fs::write(hati_dir.join("local.duckdb"), b"").unwrap();

        let result = with_cwd(tmp.path(), find_db_path);
        assert!(result.is_ok());
        assert!(result.unwrap().ends_with("local.duckdb"));
    }

    #[test]
    fn test_find_db_path_missing_db() {
        let tmp = TempDir::new().unwrap();
        let hati_dir = tmp.path().join(".hati");
        std::fs::create_dir_all(&hati_dir).unwrap();

        let result = with_cwd(tmp.path(), find_db_path);
        assert!(result.is_err());
        assert!(result
            .unwrap_err()
            .to_string()
            .contains("Database not found"));
    }
}
