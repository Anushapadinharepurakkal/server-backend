import {patch} from "@web/core/utils/patch";
import {ListController} from "@web/views/list/list_controller";

patch(ListController.prototype, {
    getStaticActionMenuItems() {
        const items = super.getStaticActionMenuItems();
        const xmlDoc = this.props.archInfo.xmlDoc;
        const archiveAllowed = xmlDoc ? xmlDoc.getAttribute("archive") !== "0" : true;

        if (!archiveAllowed) {
            delete items.archive;
            delete items.unarchive;
        }
        if (items.export) {
            const originalIsAvailable = items.export.isAvailable;
            items.export.isAvailable = () => {
                return originalIsAvailable() && this.activeActions.exportXlsx;
            };
        }
        return items;
    },
});
