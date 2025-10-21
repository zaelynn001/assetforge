-- Rev 0.1.0

-- 0001_init.sql  (Rev 0.0.1)
-- Native Linux Inventory Control — initial schema
-- Conventions: *_at_utc timestamps in ISO-8601 Zulu, foreign keys ON

PRAGMA foreign_keys = ON;

BEGIN;

-- Reference tables
CREATE TABLE hardware_types (
  id     INTEGER PRIMARY KEY,
  name   TEXT NOT NULL UNIQUE,
  code   TEXT NOT NULL UNIQUE          -- e.g., LT, DT, SW, AP, SR, TP, PR
);

CREATE TABLE locations (
  id        INTEGER PRIMARY KEY,
  name      TEXT NOT NULL,
  parent_id INTEGER REFERENCES locations(id) ON DELETE SET NULL
);

CREATE TABLE users (
  id    INTEGER PRIMARY KEY,
  name  TEXT NOT NULL,
  email TEXT
);

CREATE TABLE groups (
  id   INTEGER PRIMARY KEY,
  name TEXT NOT NULL UNIQUE
);

-- Core items
CREATE TABLE hardware_items (
  id               INTEGER PRIMARY KEY,
  name             TEXT NOT NULL,
  model            TEXT,
  type_id          INTEGER NOT NULL REFERENCES hardware_types(id),
  mac_address      TEXT,                                  -- may be NULL
  location_id      INTEGER REFERENCES locations(id) ON DELETE SET NULL,
  user_id          INTEGER REFERENCES users(id) ON DELETE SET NULL,
  group_id         INTEGER REFERENCES groups(id) ON DELETE SET NULL,
  notes            TEXT,
  created_at_utc   TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now')),
  updated_at_utc   TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now')),
  asset_tag        TEXT NOT NULL UNIQUE
                     CHECK (asset_tag GLOB 'SDMM-??-[0-9][0-9][0-9][0-9]')
);

-- Case-insensitive uniqueness for non-NULL MACs (multiple NULLs allowed)
CREATE UNIQUE INDEX ux_items_mac_lower ON hardware_items (lower(mac_address));

-- Helpful lookup indexes
CREATE INDEX idx_items_type ON hardware_items(type_id);
CREATE INDEX idx_items_location ON hardware_items(location_id);
CREATE INDEX idx_items_user ON hardware_items(user_id);
CREATE INDEX idx_items_group ON hardware_items(group_id);

-- Flexible, type-specific attributes (key/value)
CREATE TABLE item_attributes (
  id               INTEGER PRIMARY KEY,
  item_id          INTEGER NOT NULL REFERENCES hardware_items(id) ON DELETE CASCADE,
  attr_key         TEXT NOT NULL,           -- e.g., "cpu", "ram_gb", "serial"
  attr_value       TEXT,
  created_at_utc   TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now')),
  updated_at_utc   TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now')),
  UNIQUE(item_id, attr_key)
);

-- Audit trail
CREATE TABLE item_updates (
  id                    INTEGER PRIMARY KEY,
  item_id               INTEGER NOT NULL REFERENCES hardware_items(id) ON DELETE CASCADE,
  reason                TEXT NOT NULL,        -- create|update|move|assign|audit|retire...
  note                  TEXT,                 -- human "why" string
  changed_fields        TEXT,                 -- comma-separated, app-supplied
  snapshot_before_json  TEXT,                 -- optional JSON snapshot
  snapshot_after_json   TEXT,                 -- optional JSON snapshot
  created_at_utc        TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now'))
);

-- ── Triggers ──────────────────────────────────────────────────────────────

-- Touch updated_at_utc after any item update.
-- (SQLite does not modify NEW.* in BEFORE triggers reliably; this AFTER pattern
-- assumes recursive triggers are disabled — the default.)
DROP TRIGGER IF EXISTS trg_items_touch_updated;
CREATE TRIGGER trg_items_touch_updated
AFTER UPDATE ON hardware_items
FOR EACH ROW
BEGIN
  UPDATE hardware_items
     SET updated_at_utc = strftime('%Y-%m-%dT%H:%M:%SZ','now')
   WHERE id = NEW.id;
END;

DROP TRIGGER IF EXISTS trg_items_asset_tag_after_insert;
CREATE TRIGGER trg_items_asset_tag_after_insert
AFTER INSERT ON hardware_items
FOR EACH ROW
BEGIN
  UPDATE hardware_items
     SET asset_tag = 'SDMM-' ||
                     (SELECT code FROM hardware_types WHERE id = NEW.type_id) ||
                     '-' || printf('%04d', NEW.id)
   WHERE id = NEW.id;
END;

-- Regenerate asset_tag when type changes
DROP TRIGGER IF EXISTS trg_items_asset_tag_after_type_change;
CREATE TRIGGER trg_items_asset_tag_after_type_change
AFTER UPDATE OF type_id ON hardware_items
FOR EACH ROW
BEGIN
  UPDATE hardware_items
     SET asset_tag = 'SDMM-' ||
                     (SELECT code FROM hardware_types WHERE id = NEW.type_id) ||
                     '-' || printf('%04d', NEW.id)
   WHERE id = NEW.id;
END;

COMMIT;

-- Optional: initial type seed (edit to taste)
INSERT INTO hardware_types (name, code) VALUES
  ('Laptop','LT'),
  ('Desktop','DT'),
  ('Switch','SW'),
  ('Access Point','AP'),
  ('Server','SR'),
  ('Phone','TP'),
  ('Printer','PR');
