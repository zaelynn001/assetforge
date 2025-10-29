-- Rev 1.2.0 - Distro


-- Combined schema initialization for AssetForge.

PRAGMA foreign_keys = ON;


BEGIN;


CREATE TABLE hardware_types (
  id     INTEGER PRIMARY KEY,
  name   TEXT NOT NULL UNIQUE,
  code   TEXT NOT NULL UNIQUE
);

CREATE TABLE sub_types (
  id   INTEGER PRIMARY KEY,
  name TEXT NOT NULL UNIQUE
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

CREATE TABLE ip_addresses (
  id INTEGER PRIMARY KEY,
  ip_address TEXT NOT NULL UNIQUE
);

WITH RECURSIVE octets(n) AS (
  SELECT 0
  UNION ALL
  SELECT n + 1 FROM octets WHERE n < 255
)
INSERT INTO ip_addresses(ip_address)
SELECT '192.168.120.' || n FROM octets;

INSERT OR IGNORE INTO ip_addresses(ip_address) VALUES ('None');

INSERT OR IGNORE INTO sub_types(name) VALUES ('Laptop');
INSERT OR IGNORE INTO sub_types(name) VALUES ('Desktop');
INSERT OR IGNORE INTO sub_types(name) VALUES ('Managed PoE Switch');
INSERT OR IGNORE INTO sub_types(name) VALUES ('Managed Switch');
INSERT OR IGNORE INTO sub_types(name) VALUES ('Unmanaged PoE Switch');
INSERT OR IGNORE INTO sub_types(name) VALUES ('Unmanaged Switch');
INSERT OR IGNORE INTO sub_types(name) VALUES ('Firewall');
INSERT OR IGNORE INTO sub_types(name) VALUES ('Printer');
INSERT OR IGNORE INTO sub_types(name) VALUES ('Thermal Printer');
INSERT OR IGNORE INTO sub_types(name) VALUES ('Label Printer');
INSERT OR IGNORE INTO sub_types(name) VALUES ('NVR');
INSERT OR IGNORE INTO sub_types(name) VALUES ('Solar Camera');
INSERT OR IGNORE INTO sub_types(name) VALUES ('Homebase');
INSERT OR IGNORE INTO sub_types(name) VALUES ('PTZ Camera');
INSERT OR IGNORE INTO sub_types(name) VALUES ('IP Camera');
INSERT OR IGNORE INTO sub_types(name) VALUES ('Dock');
INSERT OR IGNORE INTO sub_types(name) VALUES ('Upgraded Dock');
INSERT OR IGNORE INTO sub_types(name) VALUES ('Patch Panel (12)');
INSERT OR IGNORE INTO sub_types(name) VALUES ('Patch Panel (24)');
INSERT OR IGNORE INTO sub_types(name) VALUES ('Patch Panel (48)');
INSERT OR IGNORE INTO sub_types(name) VALUES ('Fiber Modem');
INSERT OR IGNORE INTO sub_types(name) VALUES ('AP Controller');
INSERT OR IGNORE INTO sub_types(name) VALUES ('Server');
INSERT OR IGNORE INTO sub_types(name) VALUES ('Loudspeaker Controller');
INSERT OR IGNORE INTO sub_types(name) VALUES ('Landline');
INSERT OR IGNORE INTO sub_types(name) VALUES ('Upgraded Landline');

CREATE TABLE master_list (
  master_id INTEGER PRIMARY KEY,
  name TEXT NOT NULL,
  model TEXT,
  type_id INTEGER NOT NULL REFERENCES hardware_types(id),
  mac_address TEXT,
  ip_address TEXT,
  location_id INTEGER REFERENCES locations(id) ON DELETE SET NULL,
  user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
  group_id INTEGER REFERENCES groups(id) ON DELETE SET NULL,
  sub_type_id INTEGER REFERENCES sub_types(id) ON DELETE SET NULL,
  notes TEXT,
  created_at_utc TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now')),
  updated_at_utc TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now')),
  asset_tag TEXT NOT NULL UNIQUE,
  archived INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE archive (
  id INTEGER PRIMARY KEY,
  name TEXT NOT NULL,
  model TEXT,
  type_id INTEGER NOT NULL REFERENCES hardware_types(id),
  mac_address TEXT,
  ip_address TEXT,
  location_id INTEGER,
  user_id INTEGER,
  group_id INTEGER,
  sub_type_id INTEGER,
  notes TEXT,
  asset_tag TEXT NOT NULL UNIQUE,
  created_at_utc TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now')),
  updated_at_utc TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now')),
  archived INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE item_index (
  id INTEGER PRIMARY KEY,
  type_id INTEGER NOT NULL REFERENCES hardware_types(id)
    ON DELETE CASCADE ON UPDATE CASCADE,
  created_at_utc TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now'))
);

CREATE TABLE item_updates (
  id INTEGER PRIMARY KEY,
  item_id INTEGER NOT NULL REFERENCES item_index(id) ON DELETE CASCADE,
  reason TEXT NOT NULL,
  note TEXT,
  changed_fields TEXT,
  snapshot_before_json TEXT,
  snapshot_after_json TEXT,
  created_at_utc TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now'))
);

CREATE TABLE laptops_pcs (
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
  created_at_utc TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now')),
  updated_at_utc TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now')),
  asset_tag TEXT NOT NULL UNIQUE,
  master_id INTEGER REFERENCES master_list(master_id) ON DELETE CASCADE
    DEFERRABLE INITIALLY DEFERRED
);

CREATE TABLE network_gear (
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
  created_at_utc TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now')),
  updated_at_utc TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now')),
  asset_tag TEXT NOT NULL UNIQUE,
  master_id INTEGER REFERENCES master_list(master_id) ON DELETE CASCADE
    DEFERRABLE INITIALLY DEFERRED
);

CREATE TABLE landline_phones (
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
  created_at_utc TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now')),
  updated_at_utc TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now')),
  asset_tag TEXT NOT NULL UNIQUE,
  master_id INTEGER REFERENCES master_list(master_id) ON DELETE CASCADE
    DEFERRABLE INITIALLY DEFERRED
);

CREATE TABLE printers (
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
  created_at_utc TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now')),
  updated_at_utc TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now')),
  asset_tag TEXT NOT NULL UNIQUE,
  master_id INTEGER REFERENCES master_list(master_id) ON DELETE CASCADE
    DEFERRABLE INITIALLY DEFERRED
);

CREATE TABLE payment_terminals (
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
  created_at_utc TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now')),
  updated_at_utc TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now')),
  asset_tag TEXT NOT NULL UNIQUE,
  master_id INTEGER REFERENCES master_list(master_id) ON DELETE CASCADE
    DEFERRABLE INITIALLY DEFERRED
);

CREATE TABLE lorex_cameras (
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
  created_at_utc TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now')),
  updated_at_utc TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now')),
  asset_tag TEXT NOT NULL UNIQUE,
  master_id INTEGER REFERENCES master_list(master_id) ON DELETE CASCADE
    DEFERRABLE INITIALLY DEFERRED
);

CREATE TABLE eufy_cameras (
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
  created_at_utc TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now')),
  updated_at_utc TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now')),
  asset_tag TEXT NOT NULL UNIQUE,
  master_id INTEGER REFERENCES master_list(master_id) ON DELETE CASCADE
    DEFERRABLE INITIALLY DEFERRED
);

CREATE TABLE peripheral_devices (
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
  created_at_utc TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now')),
  updated_at_utc TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now')),
  asset_tag TEXT NOT NULL UNIQUE,
  master_id INTEGER REFERENCES master_list(master_id) ON DELETE CASCADE
    DEFERRABLE INITIALLY DEFERRED
);

CREATE TABLE access_points (
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
  created_at_utc TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now')),
  updated_at_utc TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now')),
  asset_tag TEXT NOT NULL UNIQUE,
  master_id INTEGER REFERENCES master_list(master_id) ON DELETE CASCADE
    DEFERRABLE INITIALLY DEFERRED
);

CREATE TABLE misc (
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
  created_at_utc TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now')),
  updated_at_utc TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now')),
  asset_tag TEXT NOT NULL UNIQUE,
  master_id INTEGER NOT NULL REFERENCES master_list(master_id) ON DELETE CASCADE
    DEFERRABLE INITIALLY DEFERRED
);

CREATE UNIQUE INDEX ux_master_list_mac_lower ON master_list (lower(mac_address));

CREATE INDEX idx_master_list_type ON master_list(type_id);

CREATE INDEX idx_master_list_location ON master_list(location_id);

CREATE INDEX idx_master_list_user ON master_list(user_id);

CREATE INDEX idx_master_list_group ON master_list(group_id);

CREATE UNIQUE INDEX ux_archive_mac_lower ON archive (lower(mac_address));

CREATE INDEX idx_archive_type ON archive(type_id);

CREATE INDEX idx_archive_location ON archive(location_id);

CREATE INDEX idx_archive_user ON archive(user_id);

CREATE INDEX idx_archive_group ON archive(group_id);

CREATE UNIQUE INDEX ux_master_list_ip_addr ON master_list(ip_address) WHERE ip_address IS NOT NULL;

CREATE INDEX idx_item_index_type ON item_index(type_id);

CREATE INDEX idx_item_updates_item ON item_updates(item_id);

CREATE UNIQUE INDEX ux_laptops_pcs_mac_lower ON laptops_pcs (lower(mac_address));

CREATE INDEX idx_laptops_pcs_location ON laptops_pcs(location_id);

CREATE INDEX idx_laptops_pcs_user ON laptops_pcs(user_id);

CREATE INDEX idx_laptops_pcs_group ON laptops_pcs(group_id);

CREATE UNIQUE INDEX ux_network_gear_mac_lower ON network_gear (lower(mac_address));

CREATE INDEX idx_network_gear_location ON network_gear(location_id);

CREATE INDEX idx_network_gear_user ON network_gear(user_id);

CREATE INDEX idx_network_gear_group ON network_gear(group_id);

CREATE UNIQUE INDEX ux_landline_phones_mac_lower ON landline_phones (lower(mac_address));

CREATE INDEX idx_landline_phones_location ON landline_phones(location_id);

CREATE INDEX idx_landline_phones_user ON landline_phones(user_id);

CREATE INDEX idx_landline_phones_group ON landline_phones(group_id);

CREATE UNIQUE INDEX ux_printers_mac_lower ON printers (lower(mac_address));

CREATE INDEX idx_printers_location ON printers(location_id);

CREATE INDEX idx_printers_user ON printers(user_id);

CREATE INDEX idx_printers_group ON printers(group_id);

CREATE UNIQUE INDEX ux_payment_terminals_mac_lower ON payment_terminals (lower(mac_address));

CREATE INDEX idx_payment_terminals_location ON payment_terminals(location_id);

CREATE INDEX idx_payment_terminals_user ON payment_terminals(user_id);

CREATE INDEX idx_payment_terminals_group ON payment_terminals(group_id);

CREATE UNIQUE INDEX ux_lorex_cameras_mac_lower ON lorex_cameras (lower(mac_address));

CREATE INDEX idx_lorex_cameras_location ON lorex_cameras(location_id);

CREATE INDEX idx_lorex_cameras_user ON lorex_cameras(user_id);

CREATE INDEX idx_lorex_cameras_group ON lorex_cameras(group_id);

CREATE UNIQUE INDEX ux_eufy_cameras_mac_lower ON eufy_cameras (lower(mac_address));

CREATE INDEX idx_eufy_cameras_location ON eufy_cameras(location_id);

CREATE INDEX idx_eufy_cameras_user ON eufy_cameras(user_id);

CREATE INDEX idx_eufy_cameras_group ON eufy_cameras(group_id);

CREATE UNIQUE INDEX ux_peripheral_devices_mac_lower ON peripheral_devices (lower(mac_address));

CREATE INDEX idx_peripheral_devices_location ON peripheral_devices(location_id);

CREATE INDEX idx_peripheral_devices_user ON peripheral_devices(user_id);

CREATE INDEX idx_peripheral_devices_group ON peripheral_devices(group_id);

CREATE UNIQUE INDEX ux_access_points_mac_lower ON access_points (lower(mac_address));

CREATE INDEX idx_access_points_location ON access_points(location_id);

CREATE INDEX idx_access_points_user ON access_points(user_id);

CREATE INDEX idx_access_points_group ON access_points(group_id);

CREATE UNIQUE INDEX ux_misc_mac_lower ON misc (lower(mac_address));

CREATE INDEX idx_misc_location ON misc(location_id);

CREATE INDEX idx_misc_user ON misc(user_id);

CREATE INDEX idx_misc_group ON misc(group_id);

CREATE TRIGGER trg_master_list_touch_updated
AFTER UPDATE ON master_list
FOR EACH ROW
BEGIN
  UPDATE master_list
     SET updated_at_utc = strftime('%Y-%m-%dT%H:%M:%SZ','now')
   WHERE master_id = NEW.master_id;
END;

CREATE TRIGGER trg_master_list_asset_tag_after_insert
AFTER INSERT ON master_list
FOR EACH ROW
BEGIN
  UPDATE master_list
     SET asset_tag = 'SDMM-' ||
                     (SELECT code FROM hardware_types WHERE id = NEW.type_id) ||
                     '-' || printf('%04d', NEW.master_id)
   WHERE master_id = NEW.master_id;
END;

CREATE TRIGGER trg_master_list_asset_tag_after_type_change
AFTER UPDATE OF type_id ON master_list
FOR EACH ROW
BEGIN
  UPDATE master_list
     SET asset_tag = 'SDMM-' ||
                     (SELECT code FROM hardware_types WHERE id = NEW.type_id) ||
                     '-' || printf('%04d', NEW.master_id)
   WHERE master_id = NEW.master_id;
END;

CREATE TRIGGER trg_laptops_pcs_touch_updated
AFTER UPDATE ON laptops_pcs
FOR EACH ROW
BEGIN
  UPDATE laptops_pcs
     SET updated_at_utc = strftime('%Y-%m-%dT%H:%M:%SZ','now')
   WHERE id = NEW.id;
END;

CREATE TRIGGER trg_laptops_pcs_asset_tag_after_insert
AFTER INSERT ON laptops_pcs
FOR EACH ROW
BEGIN
  UPDATE laptops_pcs
     SET asset_tag = 'SDMM-' ||
                     (SELECT code FROM hardware_types WHERE id = NEW.type_id) ||
                     '-' || printf('%04d', NEW.id)
   WHERE id = NEW.id;
END;

CREATE TRIGGER trg_laptops_pcs_asset_tag_after_type_change
AFTER UPDATE OF type_id ON laptops_pcs
FOR EACH ROW
BEGIN
  UPDATE laptops_pcs
     SET asset_tag = 'SDMM-' ||
                     (SELECT code FROM hardware_types WHERE id = NEW.type_id) ||
                     '-' || printf('%04d', NEW.id)
   WHERE id = NEW.id;
END;

CREATE TRIGGER trg_network_gear_touch_updated
AFTER UPDATE ON network_gear
FOR EACH ROW
BEGIN
  UPDATE network_gear
     SET updated_at_utc = strftime('%Y-%m-%dT%H:%M:%SZ','now')
   WHERE id = NEW.id;
END;

CREATE TRIGGER trg_network_gear_asset_tag_after_insert
AFTER INSERT ON network_gear
FOR EACH ROW
BEGIN
  UPDATE network_gear
     SET asset_tag = 'SDMM-' ||
                     (SELECT code FROM hardware_types WHERE id = NEW.type_id) ||
                     '-' || printf('%04d', NEW.id)
   WHERE id = NEW.id;
END;

CREATE TRIGGER trg_network_gear_asset_tag_after_type_change
AFTER UPDATE OF type_id ON network_gear
FOR EACH ROW
BEGIN
  UPDATE network_gear
     SET asset_tag = 'SDMM-' ||
                     (SELECT code FROM hardware_types WHERE id = NEW.type_id) ||
                     '-' || printf('%04d', NEW.id)
   WHERE id = NEW.id;
END;

CREATE TRIGGER trg_landline_phones_touch_updated
AFTER UPDATE ON landline_phones
FOR EACH ROW
BEGIN
  UPDATE landline_phones
     SET updated_at_utc = strftime('%Y-%m-%dT%H:%M:%SZ','now')
   WHERE id = NEW.id;
END;

CREATE TRIGGER trg_landline_phones_asset_tag_after_insert
AFTER INSERT ON landline_phones
FOR EACH ROW
BEGIN
  UPDATE landline_phones
     SET asset_tag = 'SDMM-' ||
                     (SELECT code FROM hardware_types WHERE id = NEW.type_id) ||
                     '-' || printf('%04d', NEW.id)
   WHERE id = NEW.id;
END;

CREATE TRIGGER trg_landline_phones_asset_tag_after_type_change
AFTER UPDATE OF type_id ON landline_phones
FOR EACH ROW
BEGIN
  UPDATE landline_phones
     SET asset_tag = 'SDMM-' ||
                     (SELECT code FROM hardware_types WHERE id = NEW.type_id) ||
                     '-' || printf('%04d', NEW.id)
   WHERE id = NEW.id;
END;

CREATE TRIGGER trg_printers_touch_updated
AFTER UPDATE ON printers
FOR EACH ROW
BEGIN
  UPDATE printers
     SET updated_at_utc = strftime('%Y-%m-%dT%H:%M:%SZ','now')
   WHERE id = NEW.id;
END;

CREATE TRIGGER trg_printers_asset_tag_after_insert
AFTER INSERT ON printers
FOR EACH ROW
BEGIN
  UPDATE printers
     SET asset_tag = 'SDMM-' ||
                     (SELECT code FROM hardware_types WHERE id = NEW.type_id) ||
                     '-' || printf('%04d', NEW.id)
   WHERE id = NEW.id;
END;

CREATE TRIGGER trg_printers_asset_tag_after_type_change
AFTER UPDATE OF type_id ON printers
FOR EACH ROW
BEGIN
  UPDATE printers
     SET asset_tag = 'SDMM-' ||
                     (SELECT code FROM hardware_types WHERE id = NEW.type_id) ||
                     '-' || printf('%04d', NEW.id)
   WHERE id = NEW.id;
END;

CREATE TRIGGER trg_payment_terminals_touch_updated
AFTER UPDATE ON payment_terminals
FOR EACH ROW
BEGIN
  UPDATE payment_terminals
     SET updated_at_utc = strftime('%Y-%m-%dT%H:%M:%SZ','now')
   WHERE id = NEW.id;
END;

CREATE TRIGGER trg_payment_terminals_asset_tag_after_insert
AFTER INSERT ON payment_terminals
FOR EACH ROW
BEGIN
  UPDATE payment_terminals
     SET asset_tag = 'SDMM-' ||
                     (SELECT code FROM hardware_types WHERE id = NEW.type_id) ||
                     '-' || printf('%04d', NEW.id)
   WHERE id = NEW.id;
END;

CREATE TRIGGER trg_payment_terminals_asset_tag_after_type_change
AFTER UPDATE OF type_id ON payment_terminals
FOR EACH ROW
BEGIN
  UPDATE payment_terminals
     SET asset_tag = 'SDMM-' ||
                     (SELECT code FROM hardware_types WHERE id = NEW.type_id) ||
                     '-' || printf('%04d', NEW.id)
   WHERE id = NEW.id;
END;

CREATE TRIGGER trg_lorex_cameras_touch_updated
AFTER UPDATE ON lorex_cameras
FOR EACH ROW
BEGIN
  UPDATE lorex_cameras
     SET updated_at_utc = strftime('%Y-%m-%dT%H:%M:%SZ','now')
   WHERE id = NEW.id;
END;

CREATE TRIGGER trg_lorex_cameras_asset_tag_after_insert
AFTER INSERT ON lorex_cameras
FOR EACH ROW
BEGIN
  UPDATE lorex_cameras
     SET asset_tag = 'SDMM-' ||
                     (SELECT code FROM hardware_types WHERE id = NEW.type_id) ||
                     '-' || printf('%04d', NEW.id)
   WHERE id = NEW.id;
END;

CREATE TRIGGER trg_lorex_cameras_asset_tag_after_type_change
AFTER UPDATE OF type_id ON lorex_cameras
FOR EACH ROW
BEGIN
  UPDATE lorex_cameras
     SET asset_tag = 'SDMM-' ||
                     (SELECT code FROM hardware_types WHERE id = NEW.type_id) ||
                     '-' || printf('%04d', NEW.id)
   WHERE id = NEW.id;
END;

CREATE TRIGGER trg_eufy_cameras_touch_updated
AFTER UPDATE ON eufy_cameras
FOR EACH ROW
BEGIN
  UPDATE eufy_cameras
     SET updated_at_utc = strftime('%Y-%m-%dT%H:%M:%SZ','now')
   WHERE id = NEW.id;
END;

CREATE TRIGGER trg_eufy_cameras_asset_tag_after_insert
AFTER INSERT ON eufy_cameras
FOR EACH ROW
BEGIN
  UPDATE eufy_cameras
     SET asset_tag = 'SDMM-' ||
                     (SELECT code FROM hardware_types WHERE id = NEW.type_id) ||
                     '-' || printf('%04d', NEW.id)
   WHERE id = NEW.id;
END;

CREATE TRIGGER trg_eufy_cameras_asset_tag_after_type_change
AFTER UPDATE OF type_id ON eufy_cameras
FOR EACH ROW
BEGIN
  UPDATE eufy_cameras
     SET asset_tag = 'SDMM-' ||
                     (SELECT code FROM hardware_types WHERE id = NEW.type_id) ||
                     '-' || printf('%04d', NEW.id)
   WHERE id = NEW.id;
END;

CREATE TRIGGER trg_peripheral_devices_touch_updated
AFTER UPDATE ON peripheral_devices
FOR EACH ROW
BEGIN
  UPDATE peripheral_devices
     SET updated_at_utc = strftime('%Y-%m-%dT%H:%M:%SZ','now')
   WHERE id = NEW.id;
END;

CREATE TRIGGER trg_peripheral_devices_asset_tag_after_insert
AFTER INSERT ON peripheral_devices
FOR EACH ROW
BEGIN
  UPDATE peripheral_devices
     SET asset_tag = 'SDMM-' ||
                     (SELECT code FROM hardware_types WHERE id = NEW.type_id) ||
                     '-' || printf('%04d', NEW.id)
   WHERE id = NEW.id;
END;

CREATE TRIGGER trg_peripheral_devices_asset_tag_after_type_change
AFTER UPDATE OF type_id ON peripheral_devices
FOR EACH ROW
BEGIN
  UPDATE peripheral_devices
     SET asset_tag = 'SDMM-' ||
                     (SELECT code FROM hardware_types WHERE id = NEW.type_id) ||
                     '-' || printf('%04d', NEW.id)
   WHERE id = NEW.id;
END;

CREATE TRIGGER trg_access_points_touch_updated
AFTER UPDATE ON access_points
FOR EACH ROW
BEGIN
  UPDATE access_points
     SET updated_at_utc = strftime('%Y-%m-%dT%H:%M:%SZ','now')
   WHERE id = NEW.id;
END;

CREATE TRIGGER trg_access_points_asset_tag_after_insert
AFTER INSERT ON access_points
FOR EACH ROW
BEGIN
  UPDATE access_points
     SET asset_tag = 'SDMM-' ||
                     (SELECT code FROM hardware_types WHERE id = NEW.type_id) ||
                     '-' || printf('%04d', NEW.id)
   WHERE id = NEW.id;
END;

CREATE TRIGGER trg_access_points_asset_tag_after_type_change
AFTER UPDATE OF type_id ON access_points
FOR EACH ROW
BEGIN
  UPDATE access_points
     SET asset_tag = 'SDMM-' ||
                     (SELECT code FROM hardware_types WHERE id = NEW.type_id) ||
                     '-' || printf('%04d', NEW.id)
   WHERE id = NEW.id;
END;

CREATE TRIGGER trg_misc_touch_updated
AFTER UPDATE ON misc
FOR EACH ROW
BEGIN
  UPDATE misc
     SET updated_at_utc = strftime('%Y-%m-%dT%H:%M:%SZ','now')
   WHERE id = NEW.id;
END;

CREATE TRIGGER trg_misc_asset_tag_after_insert
AFTER INSERT ON misc
FOR EACH ROW
BEGIN
  UPDATE misc
     SET asset_tag = 'SDMM-' ||
                     (SELECT code FROM hardware_types WHERE id = NEW.type_id) ||
                     '-' || printf('%04d', NEW.id)
   WHERE id = NEW.id;
END;

CREATE TRIGGER trg_misc_asset_tag_after_type_change
AFTER UPDATE OF type_id ON misc
FOR EACH ROW
BEGIN
  UPDATE misc
     SET asset_tag = 'SDMM-' ||
                     (SELECT code FROM hardware_types WHERE id = NEW.type_id) ||
                     '-' || printf('%04d', NEW.id)
   WHERE id = NEW.id;
END;

CREATE TRIGGER trg_archive_touch_updated
AFTER UPDATE ON archive
FOR EACH ROW
BEGIN
  UPDATE archive
     SET updated_at_utc = strftime('%Y-%m-%dT%H:%M:%SZ','now')
   WHERE id = NEW.id;
END;

CREATE TRIGGER trg_archive_asset_tag_after_insert
AFTER INSERT ON archive
FOR EACH ROW
BEGIN
  UPDATE archive
     SET asset_tag = 'SDMM-' ||
                     (SELECT code FROM hardware_types WHERE id = NEW.type_id) ||
                     '-' || printf('%04d', NEW.id)
   WHERE id = NEW.id;
END;

CREATE TRIGGER trg_archive_asset_tag_after_type_change
AFTER UPDATE OF type_id ON archive
FOR EACH ROW
BEGIN
  UPDATE archive
     SET asset_tag = 'SDMM-' ||
                     (SELECT code FROM hardware_types WHERE id = NEW.type_id) ||
                     '-' || printf('%04d', NEW.id)
   WHERE id = NEW.id;
END;

INSERT INTO hardware_types (id, name, code) VALUES
  (1, 'Laptops/PCs', 'PC'),
  (2, 'Network Gear', 'NX'),
  (3, 'Landline Phones', 'TP'),
  (4, 'Printers', 'PX'),
  (5, 'Payment Terminals', 'CC'),
  (6, 'Lorex Cameras', 'LX'),
  (7, 'Eufy Cameras', 'EX'),
  (8, 'Periperal Devices', 'PD'),
  (9, 'Access Points', 'AP'),
  (10, 'Misc', 'MX');


COMMIT;
