mod commands;
mod context;
mod local_engine;
mod sync;

use clap::{Parser, Subcommand};
use colored::Colorize;

#[derive(Parser)]
#[command(
    name = "hati",
    about = "HatiData — RAM for Agents",
    long_about = "Local-first data warehouse for AI agents.\nLocal (free, DuckDB) → Cloud ($29/mo) → Enterprise (VPC)",
    version
)]
struct Cli {
    #[command(subcommand)]
    command: Commands,
}

#[derive(Subcommand)]
enum Commands {
    /// Initialize a new HatiData project in the current (or specified) directory
    Init {
        /// Path to initialize (defaults to current directory)
        path: Option<String>,
    },
    /// Run a SQL query against the local DuckDB database
    Query {
        /// SQL query to execute
        sql: Option<String>,

        /// Path to a .sql file to execute
        #[arg(short, long)]
        file: Option<String>,
    },
    /// Push local tables to cloud or VPC
    Push {
        /// Target environment: cloud or vpc
        #[arg(short, long, default_value = "cloud")]
        target: String,

        /// Comma-separated list of tables to push (default: all)
        #[arg(short = 'T', long)]
        tables: Option<String>,
    },
    /// Pull schema and data from remote into local DuckDB
    Pull {
        /// Comma-separated list of tables to pull (default: all)
        #[arg(short = 'T', long)]
        tables: Option<String>,
    },
    /// Show status of the local HatiData project
    Status,
    /// Manage HatiData configuration
    Config {
        #[command(subcommand)]
        action: ConfigAction,
    },
}

#[derive(Subcommand)]
enum ConfigAction {
    /// Set a configuration value
    Set {
        /// Configuration key (cloud_endpoint, api_key, default_target, org_id)
        key: String,
        /// Value to set
        value: String,
    },
    /// Get a configuration value
    Get {
        /// Configuration key to read
        key: String,
    },
    /// List all configuration values
    List,
}

#[tokio::main]
async fn main() -> anyhow::Result<()> {
    let cli = Cli::parse();

    println!(
        "{} {} {}",
        "hati".bold().cyan(),
        env!("CARGO_PKG_VERSION").dimmed(),
        "— RAM for Agents".dimmed()
    );
    println!();

    match cli.command {
        Commands::Init { path } => commands::init::run(path).await,
        Commands::Query { sql, file } => commands::query::run(sql, file).await,
        Commands::Push { target, tables } => commands::push::run(target, tables).await,
        Commands::Pull { tables } => commands::pull::run(tables).await,
        Commands::Status => commands::status::run().await,
        Commands::Config { action } => match action {
            ConfigAction::Set { key, value } => commands::config::set(key, value).await,
            ConfigAction::Get { key } => commands::config::get(key).await,
            ConfigAction::List => commands::config::list().await,
        },
    }
}
