use std::time::Instant;

use anyhow::{bail, Context, Result};
use colored::Colorize;
use comfy_table::{Cell, Color, Table};

use crate::context;
use crate::local_engine::LocalEngine;

pub async fn run(sql: Option<String>, file: Option<String>) -> Result<()> {
    let sql = resolve_sql(sql, file)?;
    let db_path = context::find_db_path()?;

    println!(
        "{} Executing against {}",
        ">".cyan().bold(),
        db_path.display().to_string().dimmed()
    );
    println!();

    let engine = LocalEngine::open(&db_path).context("Failed to open local DuckDB")?;

    let start = Instant::now();
    let result = engine.execute_query(&sql)?;
    let elapsed = start.elapsed();

    if result.columns.is_empty() {
        println!(
            "{} Query executed successfully ({:.2?})",
            "OK".green().bold(),
            elapsed
        );
        return Ok(());
    }

    // Build table display
    let mut table = Table::new();
    table.set_header(
        result
            .columns
            .iter()
            .map(|c| Cell::new(c).fg(Color::Cyan))
            .collect::<Vec<_>>(),
    );

    for row in &result.rows {
        table.add_row(row.iter().map(Cell::new).collect::<Vec<_>>());
    }

    println!("{table}");
    println!();
    println!(
        "{} {} row{} in {:.2?}",
        "OK".green().bold(),
        result.rows.len(),
        if result.rows.len() == 1 { "" } else { "s" },
        elapsed
    );

    Ok(())
}

fn resolve_sql(sql: Option<String>, file: Option<String>) -> Result<String> {
    match (sql, file) {
        (Some(sql), _) => Ok(sql),
        (None, Some(path)) => {
            std::fs::read_to_string(&path).with_context(|| format!("Failed to read {path}"))
        }
        (None, None) => {
            bail!("Provide SQL as an argument or use --file <path.sql>")
        }
    }
}
