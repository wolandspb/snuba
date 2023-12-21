use rust_arroyo::backends::kafka::types::KafkaPayload;
use rust_arroyo::types::BrokerMessage;
use serde::{Deserialize, Serialize};
use uuid::Uuid;

use crate::types::{InsertBatch, RowData};

pub fn process_message(
    mut msg: ProfileMessage,
    raw_msg: BrokerMessage<KafkaPayload>,
) -> anyhow::Result<InsertBatch> {
    // we always want an empty string at least
    msg.device_classification = Some(msg.device_classification.unwrap_or_default());
    msg.offset = raw_msg.offset;
    msg.partition = raw_msg.partition.index;

    let serialized = serde_json::to_vec(&msg)?;

    Ok(InsertBatch {
        rows: RowData::from_rows(vec![serialized]),
        origin_timestamp: None,
        sentry_received_timestamp: None,
    })
}

#[derive(Debug, Deserialize, Serialize)]
pub struct ProfileMessage {
    #[serde(default)]
    android_api_level: Option<u32>,
    #[serde(default)]
    architecture: Option<String>,
    #[serde(default)]
    device_classification: Option<String>,
    device_locale: String,
    device_manufacturer: String,
    device_model: String,
    #[serde(default)]
    device_os_build_number: Option<String>,
    device_os_name: String,
    device_os_version: String,
    duration_ns: u64,
    #[serde(default)]
    environment: Option<String>,
    organization_id: u64,
    platform: String,
    profile_id: Uuid,
    project_id: u64,
    received: i64,
    retention_days: u32,
    trace_id: Uuid,
    transaction_id: Uuid,
    transaction_name: String,
    version_code: String,
    version_name: String,

    #[serde(default)]
    offset: u64,
    #[serde(default)]
    partition: u16,
}

#[cfg(test)]
mod tests {
    use crate::processors::make_test_message;

    use super::*;

    #[test]
    fn test_profile() {
        let data = r#"{
            "android_api_level": null,
            "architecture": "aarch64",
            "device_classification": "high",
            "device_locale": "fr_FR",
            "device_manufacturer": "Pierre",
            "device_model": "ThePierrePhone",
            "device_os_build_number": "13",
            "device_os_name": "PierreOS",
            "device_os_version": "47",
            "duration_ns": 50000000000,
            "environment": "production",
            "organization_id": 1,
            "platform": "python",
            "profile_id": "a6cd859435584c3391412390168dcb93",
            "project_id": 1,
            "received": 1694357860,
            "retention_days": 30,
            "trace_id": "40300eb2e77c46908de27f4603befa45",
            "transaction_id": "b716a5ee27db49dcbb534dcca61a9df8",
            "transaction_name": "lets-get-ready-to-party",
            "version_code": "1337",
            "version_name": "v42.0.0"
        }"#;
        let (value, msg) = make_test_message(data);

        process_message(value, msg).expect("The message should be processed");
    }
}
