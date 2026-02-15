use anyhow::Result;
use serde::{Deserialize, Serialize};

/// Response from the control plane sync API.
#[derive(Debug, Serialize, Deserialize)]
pub struct SyncResponse {
    pub success: bool,
    pub message: String,
    pub rows_synced: Option<u64>,
}

/// Remote table schema returned by the control plane.
#[derive(Debug, Serialize, Deserialize)]
pub struct TableSchema {
    pub name: String,
    pub columns: Vec<ColumnSchema>,
}

/// Column schema information.
#[derive(Debug, Serialize, Deserialize)]
pub struct ColumnSchema {
    pub name: String,
    pub data_type: String,
    pub nullable: bool,
}

/// Client for syncing data between local DuckDB and the HatiData control plane.
pub struct SyncClient {
    _client: reqwest::Client,
    _endpoint: String,
    _api_key: String,
}

impl SyncClient {
    /// Create a new sync client.
    pub fn new(endpoint: &str, api_key: &str) -> Self {
        Self {
            _client: reqwest::Client::new(),
            _endpoint: endpoint.trim_end_matches('/').to_string(),
            _api_key: api_key.to_string(),
        }
    }

    /// Push a table's Parquet data to the remote control plane.
    ///
    /// Calls `POST /v1/sync/push` with multipart form data.
    #[allow(unused_variables)]
    pub async fn push_table(
        &self,
        table_name: &str,
        parquet_data: Vec<u8>,
    ) -> Result<SyncResponse> {
        // TODO: Implement actual HTTP upload to control plane
        // The request should be:
        //   POST {endpoint}/v1/sync/push
        //   Authorization: Bearer {api_key}
        //   Content-Type: multipart/form-data
        //   Body: table_name + parquet file
        //
        // let form = reqwest::multipart::Form::new()
        //     .text("table_name", table_name.to_string())
        //     .part("data", reqwest::multipart::Part::bytes(parquet_data)
        //         .file_name(format!("{table_name}.parquet"))
        //         .mime_str("application/octet-stream")?);
        //
        // let response = self._client
        //     .post(format!("{}/v1/sync/push", self._endpoint))
        //     .bearer_auth(&self._api_key)
        //     .multipart(form)
        //     .send()
        //     .await?
        //     .json::<SyncResponse>()
        //     .await?;

        Ok(SyncResponse {
            success: false,
            message: "Push not yet implemented — waiting for control plane /v1/sync/push endpoint"
                .to_string(),
            rows_synced: None,
        })
    }

    /// Pull the list of table schemas from the remote control plane.
    #[allow(unused_variables)]
    pub async fn pull_schema(&self) -> Result<Vec<TableSchema>> {
        // TODO: Implement actual HTTP call to control plane
        // GET {endpoint}/v1/sync/schema
        // Authorization: Bearer {api_key}
        //
        // let response = self._client
        //     .get(format!("{}/v1/sync/schema", self._endpoint))
        //     .bearer_auth(&self._api_key)
        //     .send()
        //     .await?
        //     .json::<Vec<TableSchema>>()
        //     .await?;

        Ok(Vec::new())
    }

    /// Pull a single table's data as Parquet bytes.
    #[allow(unused_variables)]
    pub async fn pull_table(&self, table_name: &str) -> Result<Vec<u8>> {
        // TODO: Implement actual HTTP call to control plane
        // GET {endpoint}/v1/sync/pull/{table_name}
        // Authorization: Bearer {api_key}
        // Accept: application/octet-stream
        //
        // let response = self._client
        //     .get(format!("{}/v1/sync/pull/{table_name}", self._endpoint))
        //     .bearer_auth(&self._api_key)
        //     .send()
        //     .await?
        //     .bytes()
        //     .await?;

        Ok(Vec::new())
    }
}
