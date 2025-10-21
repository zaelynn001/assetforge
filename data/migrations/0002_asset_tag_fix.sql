-- Rev 0.1.0

-- 0002_asset_tag_fix.sql
-- Remove legacy asset_tag guard trigger and ensure AFTER INSERT trigger exists.

PRAGMA foreign_keys = ON;
BEGIN;

DROP TRIGGER IF EXISTS trg_items_asset_tag_before_insert;
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

DROP TRIGGER IF EXISTS trg_items_asset_tag_block_manual_update;

COMMIT;
