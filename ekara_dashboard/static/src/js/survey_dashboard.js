/** @odoo-module **/

import { registry } from "@web/core/registry";
import { Component, onWillStart, useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

class SurveyDashboard extends Component {

    setup() {

        this.orm = useService("orm");

        this.state = useState({
            dashboard: {}
        });

        onWillStart(async () => {

            this.state.dashboard =
                await this.orm.call(
                    "survey.dashboard",
                    "get_dashboard_data",
                    []
                );
        });
    }
}

SurveyDashboard.template =
"ekara_dashboard.SurveyDashboard";


registry.category("actions").add(
    "survey_dashboard",
    SurveyDashboard
);