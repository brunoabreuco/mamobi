-- Migration: create role_changes (auditoria de alterações de role)
-- Criado em: 2026-05-19

CREATE TABLE IF NOT EXISTS role_changes (
    id          VARCHAR(36)  PRIMARY KEY,
    user_id     VARCHAR(36)  NOT NULL REFERENCES users(id),
    changed_by  VARCHAR(36)  NOT NULL REFERENCES users(id),
    old_role    VARCHAR(20)  NOT NULL,
    new_role    VARCHAR(20)  NOT NULL,
    changed_at  TIMESTAMP    NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_role_changes_user_id    ON role_changes(user_id);
CREATE INDEX IF NOT EXISTS idx_role_changes_changed_by ON role_changes(changed_by);