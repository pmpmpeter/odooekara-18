/** @odoo-module **/
import { patch } from "@web/core/utils/patch";
import { ListRenderer } from "@web/views/list/list_renderer";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { _t } from "@web/core/l10n/translation";
import { dialogService } from "@web/core/dialog/dialog_service";

patch(ListRenderer.prototype, {
    async onDeleteRecord(record) {
        this.keepColumnWidths = true;
        const editedRecord = this.props.list.editedRecord;
        if (editedRecord && editedRecord !== record) {
            const leaved = await this.props.list.leaveEditMode();
            if (!leaved) {
                return;
            }
        }
        if (this.activeActions.onDelete) {
            this.dialogService.add(ConfirmationDialog, {
                title: _t("Confirmation"),
                body: _t("Are you sure you want to delete this record?"),
                confirmLabel: _t("Ok"),
                confirm: async () => {
                    this.activeActions.onDelete(record);
                },
                cancel: () => {},
            });
        }
    }
});