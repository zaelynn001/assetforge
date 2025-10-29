BEGIN TRANSACTION;

-- Consolidated items table replacing master_list + per-type tables.
CREATE TABLE items (
  id INTEGER PRIMARY KEY,
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
  asset_tag TEXT UNIQUE,
  created_at_utc TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now')),
  updated_at_utc TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now')),
  archived INTEGER NOT NULL DEFAULT 0
);

CREATE INDEX idx_items_type ON items(type_id);
CREATE INDEX idx_items_location ON items(location_id);
CREATE INDEX idx_items_user ON items(user_id);
CREATE INDEX idx_items_group ON items(group_id);
CREATE INDEX idx_items_sub_type ON items(sub_type_id);
CREATE UNIQUE INDEX ux_items_mac_lower ON items(lower(mac_address));
CREATE UNIQUE INDEX ux_items_ip_addr ON items(ip_address) WHERE ip_address IS NOT NULL;

INSERT INTO items(
  id,
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
  asset_tag,
  created_at_utc,
  updated_at_utc,
  archived
)
SELECT
  master_id,
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
  asset_tag,
  created_at_utc,
  updated_at_utc,
  archived
FROM master_list;

CREATE TABLE legacy_item_map (
  old_id INTEGER NOT NULL,
  type_id INTEGER NOT NULL,
  master_id INTEGER NOT NULL,
  PRIMARY KEY(old_id, type_id)
);

INSERT INTO legacy_item_map(old_id, type_id, master_id)
SELECT id, 1, master_id FROM laptops_pcs WHERE master_id IS NOT NULL
UNION ALL
SELECT id, 2, master_id FROM network_gear WHERE master_id IS NOT NULL
UNION ALL
SELECT id, 3, master_id FROM landline_phones WHERE master_id IS NOT NULL
UNION ALL
SELECT id, 4, master_id FROM printers WHERE master_id IS NOT NULL
UNION ALL
SELECT id, 5, master_id FROM payment_terminals WHERE master_id IS NOT NULL
UNION ALL
SELECT id, 6, master_id FROM lorex_cameras WHERE master_id IS NOT NULL
UNION ALL
SELECT id, 7, master_id FROM eufy_cameras WHERE master_id IS NOT NULL
UNION ALL
SELECT id, 8, master_id FROM peripheral_devices WHERE master_id IS NOT NULL
UNION ALL
SELECT id, 9, master_id FROM access_points WHERE master_id IS NOT NULL
UNION ALL
SELECT id, 10, master_id FROM misc WHERE master_id IS NOT NULL;

ALTER TABLE item_updates RENAME TO item_updates_legacy;

CREATE TABLE item_updates (
  id INTEGER PRIMARY KEY,
  item_id INTEGER NOT NULL REFERENCES items(id) ON DELETE CASCADE,
  reason TEXT NOT NULL,
  note TEXT,
  changed_fields TEXT,
  snapshot_before_json TEXT,
  snapshot_after_json TEXT,
  created_at_utc TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now'))
);

INSERT INTO item_updates(
  id,
  item_id,
  reason,
  note,
  changed_fields,
  snapshot_before_json,
  snapshot_after_json,
  created_at_utc
)
SELECT
  iu.id,
  COALESCE(map.master_id, ml.master_id, idx.id),
  iu.reason,
  iu.note,
  iu.changed_fields,
  iu.snapshot_before_json,
  iu.snapshot_after_json,
  iu.created_at_utc
FROM item_updates_legacy AS iu
LEFT JOIN item_index AS idx ON iu.item_id = idx.id
LEFT JOIN legacy_item_map AS map
  ON map.old_id = idx.id AND map.type_id = idx.type_id
LEFT JOIN master_list AS ml ON map.master_id = ml.master_id;

DROP TABLE item_updates_legacy;
DROP TABLE item_index;

DROP TABLE laptops_pcs;
DROP TABLE network_gear;
DROP TABLE landline_phones;
DROP TABLE printers;
DROP TABLE payment_terminals;
DROP TABLE lorex_cameras;
DROP TABLE eufy_cameras;
DROP TABLE peripheral_devices;
DROP TABLE access_points;
DROP TABLE misc;

DROP TABLE legacy_item_map;
DROP TABLE master_list;

CREATE TRIGGER trg_items_touch_updated
AFTER UPDATE ON items
FOR EACH ROW
BEGIN
  UPDATE items
     SET updated_at_utc = strftime('%Y-%m-%dT%H:%M:%SZ','now')
   WHERE id = NEW.id;
END;

COMMIT;
