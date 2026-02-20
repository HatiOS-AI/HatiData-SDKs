use anyhow::{bail, Result};
use serde::{Deserialize, Serialize};

/// Response from the control plane sync API.
#[derive(Debug, Serialize, Deserialize)]
#[allow(dead_code)]
pub struct SyncResponse {
    pub success: bool,
    pub message: String,
    pub rows_synced: Option<u64>,
}

/// Remote table schema returned by the control plane.
#[derive(Debug, Serialize, Deserialize)]
#[allow(dead_code)]
pub struct TableSchema {
    pub name: String,
    pub columns: Vec<ColumnSchema>,
}

/// Column schema information.
#[derive(Debug, Serialize, Deserialize)]
#[allow(dead_code)]
pub struct ColumnSchema {
    pub name: String,
    pub data_type: String,
    pub nullable: bool,
}

/// Request body for `POST /v1/signup`.
#[derive(Debug, Serialize)]
pub struct SignupRequest {
    pub name: String,
    pub email: String,
    pub password: String,
    pub org_name: String,
    pub tier: String,
}

/// Response from `POST /v1/signup`.
#[derive(Debug, Deserialize)]
#[allow(dead_code)]
pub struct SignupResponse {
    pub token: Option<String>,
    pub org_id: String,
    pub checkout_url: Option<String>,
}

/// Response from `POST /v1/auth/login`.
#[derive(Debug, Deserialize)]
pub struct LoginResponse {
    pub token: String,
}

/// Response from `GET /v1/auth/me`.
#[derive(Debug, Deserialize)]
#[allow(dead_code)]
pub struct AuthMeResponse {
    pub user_id: String,
    pub email: String,
    pub org_id: String,
    pub role: String,
    /// Organization tier (free, cloud, growth, enterprise). Optional for backwards compat.
    #[serde(default)]
    pub tier: Option<String>,
}

/// Client for syncing data between local DuckDB and the HatiData control plane.
pub struct SyncClient {
    client: reqwest::Client,
    endpoint: String,
    api_key: String,
}

impl SyncClient {
    /// Create a new sync client.
    pub fn new(endpoint: &str, api_key: &str) -> Self {
        Self {
            client: reqwest::Client::new(),
            endpoint: endpoint.trim_end_matches('/').to_string(),
            api_key: api_key.to_string(),
        }
    }

    /// Return the configured endpoint URL.
    pub fn endpoint(&self) -> &str {
        &self.endpoint
    }

    /// Create an unauthenticated sync client (for signup/login).
    pub fn new_unauthenticated(endpoint: &str) -> Self {
        Self::new(endpoint, "")
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

        Ok(Vec::new())
    }

    /// Pull a single table's data as Parquet bytes.
    #[allow(unused_variables)]
    pub async fn pull_table(&self, table_name: &str) -> Result<Vec<u8>> {
        // TODO: Implement actual HTTP call to control plane
        // GET {endpoint}/v1/sync/pull/{table_name}
        // Authorization: Bearer {api_key}
        // Accept: application/octet-stream

        Ok(Vec::new())
    }

    /// Sign up for a new account via `POST /v1/signup`.
    pub async fn signup(&self, req: &SignupRequest) -> Result<SignupResponse> {
        let response = self
            .client
            .post(format!("{}/v1/signup", self.endpoint))
            .json(req)
            .send()
            .await?;

        let status = response.status();
        if !status.is_success() {
            let body = response.text().await.unwrap_or_default();
            bail!("Signup failed (HTTP {}): {}", status, body);
        }

        let result = response.json::<SignupResponse>().await?;
        Ok(result)
    }

    /// Login via `POST /v1/auth/login`.
    pub async fn login(&self, email: &str, password: &str) -> Result<LoginResponse> {
        let body = serde_json::json!({
            "email": email,
            "password": password,
        });

        let response = self
            .client
            .post(format!("{}/v1/auth/login", self.endpoint))
            .json(&body)
            .send()
            .await?;

        let status = response.status();
        if !status.is_success() {
            let body = response.text().await.unwrap_or_default();
            bail!("Login failed (HTTP {}): {}", status, body);
        }

        let result = response.json::<LoginResponse>().await?;
        Ok(result)
    }

    /// Verify API key via `GET /v1/auth/me`.
    pub async fn auth_me(&self) -> Result<AuthMeResponse> {
        let response = self
            .client
            .get(format!("{}/v1/auth/me", self.endpoint))
            .header("Authorization", format!("ApiKey {}", self.api_key))
            .send()
            .await?;

        let status = response.status();
        if !status.is_success() {
            let body = response.text().await.unwrap_or_default();
            bail!("Auth verification failed (HTTP {}): {}", status, body);
        }

        let result = response.json::<AuthMeResponse>().await?;
        Ok(result)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_sync_client_construction() {
        let client = SyncClient::new("https://api.hatidata.com/", "hd_live_test123");
        assert_eq!(client.endpoint(), "https://api.hatidata.com");
        assert_eq!(client.api_key, "hd_live_test123");
    }

    #[test]
    fn test_sync_client_trims_trailing_slash() {
        let client = SyncClient::new("https://api.hatidata.com///", "key");
        assert_eq!(client.endpoint(), "https://api.hatidata.com");
    }

    #[test]
    fn test_sync_client_unauthenticated() {
        let client = SyncClient::new_unauthenticated("https://api.hatidata.com");
        assert_eq!(client.endpoint(), "https://api.hatidata.com");
        assert_eq!(client.api_key, "");
    }

    #[test]
    fn test_signup_request_serialization() {
        let req = SignupRequest {
            name: "Test User".to_string(),
            email: "test@example.com".to_string(),
            password: "password123".to_string(),
            org_name: "Test Org".to_string(),
            tier: "free".to_string(),
        };
        let json = serde_json::to_value(&req).unwrap();
        assert_eq!(json["email"], "test@example.com");
        assert_eq!(json["tier"], "free");
    }

    #[test]
    fn test_signup_response_deserialize() {
        let json = r#"{"token":"jwt_123","org_id":"org-abc","checkout_url":null}"#;
        let resp: SignupResponse = serde_json::from_str(json).unwrap();
        assert_eq!(resp.token, Some("jwt_123".to_string()));
        assert_eq!(resp.org_id, "org-abc");
        assert!(resp.checkout_url.is_none());
    }

    #[test]
    fn test_login_response_deserialize() {
        let json = r#"{"token":"jwt_token_456"}"#;
        let resp: LoginResponse = serde_json::from_str(json).unwrap();
        assert_eq!(resp.token, "jwt_token_456");
    }

    #[test]
    fn test_auth_me_response_deserialize() {
        let json =
            r#"{"user_id":"u-1","email":"test@example.com","org_id":"org-1","role":"owner"}"#;
        let resp: AuthMeResponse = serde_json::from_str(json).unwrap();
        assert_eq!(resp.email, "test@example.com");
        assert_eq!(resp.role, "owner");
        assert!(resp.tier.is_none()); // tier is optional for backwards compat
    }

    #[test]
    fn test_auth_me_response_with_tier() {
        let json = r#"{"user_id":"u-1","email":"test@example.com","org_id":"org-1","role":"owner","tier":"cloud"}"#;
        let resp: AuthMeResponse = serde_json::from_str(json).unwrap();
        assert_eq!(resp.tier, Some("cloud".to_string()));
    }

    #[test]
    fn test_sync_response_deserialize() {
        let json = r#"{"success":true,"message":"ok","rows_synced":42}"#;
        let resp: SyncResponse = serde_json::from_str(json).unwrap();
        assert!(resp.success);
        assert_eq!(resp.rows_synced, Some(42));
    }

    #[test]
    fn test_table_schema_deserialize() {
        let json =
            r#"{"name":"users","columns":[{"name":"id","data_type":"INTEGER","nullable":false}]}"#;
        let schema: TableSchema = serde_json::from_str(json).unwrap();
        assert_eq!(schema.name, "users");
        assert_eq!(schema.columns.len(), 1);
        assert_eq!(schema.columns[0].name, "id");
    }
}
