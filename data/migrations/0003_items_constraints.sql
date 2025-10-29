BEGIN TRANSACTION;

-- Deduplicate catalog tables before enforcing uniqueness
DELETE FROM locations
 WHERE rowid NOT IN (
   SELECT MIN(rowid)
   FROM locations
   GROUP BY lower(name)
 );

DELETE FROM users
 WHERE rowid NOT IN (
   SELECT MIN(rowid)
   FROM users
   GROUP BY lower(name)
 );

DELETE FROM groups
 WHERE rowid NOT IN (
   SELECT MIN(rowid)
   FROM groups
   GROUP BY lower(name)
 );

DELETE FROM sub_types
 WHERE rowid NOT IN (
   SELECT MIN(rowid)
   FROM sub_types
   GROUP BY lower(name)
 );

CREATE TABLE items_rebuild (
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
  asset_tag TEXT NOT NULL UNIQUE,
  created_at_utc TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now')),
  updated_at_utc TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now')),
  archived INTEGER NOT NULL DEFAULT 0,
  UNIQUE(type_id, type_serial)
);

WITH ranked AS (
    SELECT
        i.*,
        ROW_NUMBER() OVER (PARTITION BY i.type_id ORDER BY datetime(i.created_at_utc), i.id) AS type_serial
    FROM items AS i
)
INSERT INTO items_rebuild(
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
    asset_tag,
    created_at_utc,
    updated_at_utc,
    archived
)
SELECT
    r.id,
    r.type_serial,
    r.name,
    r.model,
    r.type_id,
    r.mac_address,
    r.ip_address,
    r.location_id,
    r.user_id,
    r.group_id,
    r.sub_type_id,
    r.notes,
    'SDMM-' || ht.code || '-' || printf('%04d', r.type_serial),
    r.created_at_utc,
    r.updated_at_utc,
    r.archived
FROM ranked AS r
JOIN hardware_types AS ht ON ht.id = r.type_id;

DROP TABLE items;
ALTER TABLE items_rebuild RENAME TO items;

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

CREATE TABLE type_counters (
  type_id INTEGER PRIMARY KEY REFERENCES hardware_types(id)
    ON DELETE CASCADE ON UPDATE CASCADE,
  next_serial INTEGER NOT NULL
);

INSERT INTO type_counters(type_id, next_serial)
SELECT
  ht.id,
  COALESCE(MAX(it.type_serial), 0) + 1
FROM hardware_types AS ht
LEFT JOIN items AS it ON it.type_id = ht.id
GROUP BY ht.id;

CREATE UNIQUE INDEX ux_locations_name_lower ON locations(lower(name));
CREATE UNIQUE INDEX ux_users_name_lower ON users(lower(name));
CREATE UNIQUE INDEX ux_groups_name_lower ON groups(lower(name));
CREATE UNIQUE INDEX ux_sub_types_name_lower ON sub_types(lower(name));

COMMIT;
