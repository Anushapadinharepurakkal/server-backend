/**
 * Copyright 2026 CIT Services
 * License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
 */

import {FormController} from "@web/views/form/form_controller";
import {ListController} from "@web/views/list/list_controller";
import {onWillStart} from "@odoo/owl";
import {patch} from "@web/core/utils/patch";
import {rpc} from "@web/core/network/rpc";

/**
 * Fetches perm_archive / perm_unarchive for the current user and model.
 * Returns { canArchive: bool, canUnarchive: bool }.
 */
async function fetchArchiveAccess(resModel) {
    const result = await rpc("/web/dataset/call_kw", {
        model: "ir.model.access",
        method: "get_archive_access",
        args: [resModel],
        kwargs: {},
    });
    return result;
}

// ─── List Controller ─────────────────────────────────────────────────────────
patch(ListController.prototype, {
    setup() {
        super.setup(...arguments);
        this._canArchive = true;
        this._canUnarchive = true;
        onWillStart(async () => {
            const access = await fetchArchiveAccess(this.props.resModel);
            this._canArchive = access.can_archive;
            this._canUnarchive = access.can_unarchive;
        });
    },

    getStaticActionMenuItems() {
        const items = super.getStaticActionMenuItems(...arguments);
        const baseArchiveEnabled = this.archiveEnabled;
        items.archive.isAvailable = () => baseArchiveEnabled && this._canArchive;
        items.unarchive.isAvailable = () => baseArchiveEnabled && this._canUnarchive;
        return items;
    },
});

// ─── Form Controller ──────────────────────────────────────────────────────────
patch(FormController.prototype, {
    setup() {
        super.setup(...arguments);
        this._canArchive = true;
        this._canUnarchive = true;
        onWillStart(async () => {
            const access = await fetchArchiveAccess(this.props.resModel);
            this._canArchive = access.can_archive;
            this._canUnarchive = access.can_unarchive;
        });
    },

    getStaticActionMenuItems() {
        const items = super.getStaticActionMenuItems(...arguments);
        items.archive.isAvailable = () =>
            this.archiveEnabled && this.model.root.isActive && this._canArchive;
        items.unarchive.isAvailable = () =>
            this.archiveEnabled && !this.model.root.isActive && this._canUnarchive;
        return items;
    },
});
