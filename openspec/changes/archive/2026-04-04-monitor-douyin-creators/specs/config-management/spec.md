## ADDED Requirements

### Requirement: Load non-sensitive configuration from YAML file
The system SHALL load configuration from `config.yaml` located in the project root directory, including: TikHub base URL and endpoint, Feishu bitable identifiers, creator list, and schedule settings.

#### Scenario: Valid config.yaml loaded successfully
- **WHEN** a valid `config.yaml` exists in the project root with all required fields
- **THEN** the system SHALL parse and validate the configuration into a typed settings object

#### Scenario: config.yaml missing or invalid
- **WHEN** `config.yaml` is missing or contains invalid/missing required fields
- **THEN** the system SHALL raise a clear error message indicating what is missing or invalid

### Requirement: Load sensitive credentials from .env file
The system SHALL load sensitive credentials (TikHub API Key, Feishu App ID, Feishu App Secret) from a `.env` file in the project root, separate from the YAML configuration.

#### Scenario: Valid .env file loaded successfully
- **WHEN** a valid `.env` file exists with all required keys (TIKHUB_API_KEY, FEISHU_APP_ID, FEISHU_APP_SECRET)
- **THEN** the system SHALL load the credentials and make them available to the modules that need them

#### Scenario: .env file missing required keys
- **WHEN** the `.env` file is missing or does not contain all required keys
- **THEN** the system SHALL raise a clear error message listing the missing keys

### Requirement: Configuration model validation
The system SHALL use pydantic-settings to define a typed configuration model that validates all required fields at load time, failing fast on invalid configuration.

#### Scenario: Creator entry missing required fields
- **WHEN** a creator entry in config.yaml is missing `name` or `sec_uid`
- **THEN** the system SHALL raise a validation error identifying the invalid entry
