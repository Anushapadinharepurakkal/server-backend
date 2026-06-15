import {patch} from "@web/core/utils/patch";
import {FormController} from "@web/views/form/form_controller";

patch(FormController.prototype, {
    getStaticActionMenuItems() {
        const items = super.getStaticActionMenuItems();
        const xmlDoc = this.props.archInfo.xmlDoc;
        const archiveAllowed = xmlDoc ? xmlDoc.getAttribute("archive") !== "0" : true;

        if (!archiveAllowed) {
            delete items.archive;
            delete items.unarchive;
        }
        return items;
    },
});
