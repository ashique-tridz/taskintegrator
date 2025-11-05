// Copyright (c) 2025, Tridz and contributors
// For license information, please see license.txt

frappe.ui.form.on("Integration Settings", {
    refresh(frm) {
        // Show button only for Asana integration
        if (frm.doc.integration_name && frm.doc.enabled && !frm.doc.access_token) {
            frm.add_custom_button(__("Connect"), () => {
                // Open the Frappe endpoint in a *new tab*, NOT AJAX
                window.open(
                    window.location.origin + "/api/method/taskintegrator.api.start_auth",
                    "_self"
                );
            }).add_calss("btn-primary");
        }
    },

    after_save(frm) {
        // Reload tokens after save if they were fetched
        if (frm.doc.access_token) {
            frappe.show_alert({
                message: __("Access token fetched successfully!"),
                indicator: "green"
            });
            frm.reload_doc();
        }
    }
});
