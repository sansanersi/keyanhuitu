"""服务器版数据层定义。

当前阶段只提供 MySQL 三逻辑库的结构化建库 SQL，现有运行仍由 SQLite 兼容承载。
"""

try:
    from .database import logical_database_config
except ImportError:
    from database import logical_database_config


def _quote_identifier(value):
    cleaned = str(value).replace("`", "``")
    return f"`{cleaned}`"


def _create_database_statement(schema_name):
    schema = _quote_identifier(schema_name)
    return f"CREATE DATABASE IF NOT EXISTS {schema} CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"


def mysql_schema_statements(config=None):
    config = config or logical_database_config()
    schemas = config["schemas"]
    text_db = _quote_identifier(schemas["text"])
    image_db = _quote_identifier(schemas["image"])
    app_db = _quote_identifier(schemas["app"])

    return [
        "-- 科研绘图工作台服务器版 MySQL schema v1",
        _create_database_statement(schemas["text"]),
        _create_database_statement(schemas["image"]),
        _create_database_statement(schemas["app"]),
        f"""
CREATE TABLE IF NOT EXISTS {text_db}.`terms` (
    `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    `name` VARCHAR(255) NOT NULL,
    `english` VARCHAR(255) NOT NULL DEFAULT '',
    `domain` VARCHAR(64) NOT NULL DEFAULT '',
    `category` VARCHAR(128) NOT NULL DEFAULT '',
    `shape` VARCHAR(128) NOT NULL DEFAULT '',
    `color_scheme` JSON NULL,
    `tags` JSON NULL,
    `description` TEXT NULL,
    `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (`id`),
    UNIQUE KEY `uk_terms_name` (`name`),
    KEY `idx_terms_domain` (`domain`),
    KEY `idx_terms_category` (`category`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
""".strip(),
        f"""
CREATE TABLE IF NOT EXISTS {text_db}.`documents` (
    `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    `filename` VARCHAR(512) NOT NULL,
    `filepath` VARCHAR(1024) NOT NULL,
    `file_type` VARCHAR(64) NOT NULL DEFAULT '',
    `content` LONGTEXT NULL,
    `content_hash` CHAR(64) NULL,
    `vectorized` TINYINT(1) NOT NULL DEFAULT 0,
    `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (`id`),
    UNIQUE KEY `uk_documents_filepath` (`filepath`),
    KEY `idx_documents_vectorized` (`vectorized`),
    KEY `idx_documents_hash` (`content_hash`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
""".strip(),
        f"""
CREATE TABLE IF NOT EXISTS {text_db}.`document_chunks` (
    `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    `document_id` BIGINT UNSIGNED NOT NULL,
    `chunk_index` INT UNSIGNED NOT NULL,
    `content` TEXT NOT NULL,
    `embedding_ref` VARCHAR(255) NULL,
    `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (`id`),
    UNIQUE KEY `uk_document_chunks_order` (`document_id`, `chunk_index`),
    KEY `idx_document_chunks_embedding` (`embedding_ref`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
""".strip(),
        f"""
CREATE TABLE IF NOT EXISTS {image_db}.`image_assets` (
    `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    `name` VARCHAR(255) NOT NULL,
    `source` VARCHAR(64) NOT NULL DEFAULT 'local',
    `asset_type` VARCHAR(64) NOT NULL DEFAULT 'svg',
    `domain` VARCHAR(64) NOT NULL DEFAULT '',
    `category` VARCHAR(128) NOT NULL DEFAULT '',
    `file_path` VARCHAR(1024) NULL,
    `svg_content` MEDIUMTEXT NULL,
    `tags` JSON NULL,
    `metadata` JSON NULL,
    `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (`id`),
    KEY `idx_image_assets_name` (`name`),
    KEY `idx_image_assets_domain` (`domain`),
    KEY `idx_image_assets_source` (`source`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
""".strip(),
        f"""
CREATE TABLE IF NOT EXISTS {image_db}.`asset_aliases` (
    `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    `asset_id` BIGINT UNSIGNED NOT NULL,
    `alias` VARCHAR(255) NOT NULL,
    `language` VARCHAR(32) NOT NULL DEFAULT '',
    PRIMARY KEY (`id`),
    UNIQUE KEY `uk_asset_alias` (`asset_id`, `alias`),
    KEY `idx_asset_alias` (`alias`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
""".strip(),
        f"""
CREATE TABLE IF NOT EXISTS {image_db}.`asset_relations` (
    `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    `source_asset_id` BIGINT UNSIGNED NOT NULL,
    `target_asset_id` BIGINT UNSIGNED NOT NULL,
    `relation_type` VARCHAR(64) NOT NULL,
    `weight` DECIMAL(8,4) NOT NULL DEFAULT 1.0,
    `metadata` JSON NULL,
    PRIMARY KEY (`id`),
    KEY `idx_asset_relations_source` (`source_asset_id`),
    KEY `idx_asset_relations_target` (`target_asset_id`),
    KEY `idx_asset_relations_type` (`relation_type`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
""".strip(),
        f"""
CREATE TABLE IF NOT EXISTS {app_db}.`drawing_requests` (
    `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    `request_text` LONGTEXT NOT NULL,
    `domain` VARCHAR(64) NOT NULL DEFAULT 'biology',
    `figure_type` VARCHAR(128) NOT NULL DEFAULT '',
    `style` VARCHAR(128) NOT NULL DEFAULT '',
    `status` VARCHAR(64) NOT NULL DEFAULT 'created',
    `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (`id`),
    KEY `idx_drawing_requests_domain` (`domain`),
    KEY `idx_drawing_requests_status` (`status`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
""".strip(),
        f"""
CREATE TABLE IF NOT EXISTS {app_db}.`workflows` (
    `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    `request_id` BIGINT UNSIGNED NULL,
    `workflow_json` JSON NOT NULL,
    `quality_report` JSON NULL,
    `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (`id`),
    KEY `idx_workflows_request` (`request_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
""".strip(),
        f"""
CREATE TABLE IF NOT EXISTS {app_db}.`generated_figures` (
    `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    `request_id` BIGINT UNSIGNED NULL,
    `workflow_id` BIGINT UNSIGNED NULL,
    `output_type` VARCHAR(64) NOT NULL DEFAULT 'svg',
    `output_path` VARCHAR(1024) NULL,
    `svg_content` MEDIUMTEXT NULL,
    `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (`id`),
    KEY `idx_generated_figures_request` (`request_id`),
    KEY `idx_generated_figures_workflow` (`workflow_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
""".strip(),
        f"""
CREATE TABLE IF NOT EXISTS {app_db}.`model_configs` (
    `config_key` VARCHAR(128) NOT NULL,
    `config_value` TEXT NOT NULL,
    `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (`config_key`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
""".strip(),
    ]


def mysql_schema_sql(config=None):
    return "\n\n".join(mysql_schema_statements(config=config)) + "\n"
