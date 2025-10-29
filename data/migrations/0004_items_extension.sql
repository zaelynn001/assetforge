BEGIN TRANSACTION;

ALTER TABLE items ADD COLUMN extension TEXT;

-- Ensure non-landline records remain null
UPDATE items
   SET extension = NULL
 WHERE type_id != 3;

CREATE TABLE items_ext (
  id INTEGER PRIMARY KEY,
  type_serial INTEGER NOT NULL,
  name TEXT NOT NULL,
  model TEXT,
  type_id INTEGER NOT NULL REFERENCES hardware_types(id)
    ON DELETE CASCADE ON UPDATE CASCADE,
  mac_address TEXT,
  ip_address TEXT,
  location_id INTEGER REFERENCES locations(id) ON DELETE SET NULL,
  user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
  group_id INTEGER REFERENCES groups(id) ON DELETE SET NULL,
  sub_type_id INTEGER REFERENCES sub_types(id) ON DELETE SET NULL,
  notes TEXT,
  extension TEXT,
  asset_tag TEXT NOT NULL UNIQUE,
  created_at_utc TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now')),
  updated_at_utc TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now')),
  archived INTEGER NOT NULL DEFAULT 0,
  UNIQUE(type_id, type_serial),
  CHECK (extension IS NULL OR type_id = 3)
);

INSERT INTO items_ext(
  id,
  type_serial,
  name,
  model,
  type_id,
  mac_address,
  ip_address,
  location_id,
  user_id,
  group_id,
  sub_type_id,
  notes,
  extension,
  asset_tag,
  created_at_utc,
  updated_at_utc,
  archived
)
SELECT
  id,
  type_serial,
  name,
  model,
  type_id,
  mac_address,
  ip_address,
  location_id,
  user_id,
  group_id,
  sub_type_id,
  notes,
  CASE WHEN type_id = 3 THEN extension ELSE NULL END,
  asset_tag,
  created_at_utc,
  updated_at_utc,
  archived
FROM items;

DROP TABLE items;
ALTER TABLE items_ext RENAME TO items;

CREATE INDEX idx_items_type ON items(type_id);
CREATE INDEX idx_items_location ON items(location_id);
CREATE INDEX idx_items_user ON items(user_id);
CREATE INDEX idx_items_group ON items(group_id);
CREATE INDEX idx_items_sub_type ON items(sub_type_id);
CREATE UNIQUE INDEX ux_items_mac_lower ON items(lower(mac_address));
CREATE UNIQUE INDEX ux_items_ip_addr ON items(ip_address) WHERE ip_address IS NOT NULL;
CREATE INDEX idx_items_type_serial ON items(type_id, type_serial);

CREATE TRIGGER trg_items_touch_updated
AFTER UPDATE ON items
FOR EACH ROW
BEGIN
  UPDATE items
     SET updated_at_utc = strftime('%Y-%m-%dT%H:%M:%SZ','now')
   WHERE id = NEW.id;
END;

COMMIT;
