/** @odoo-module **/

import { HomeMenu } from "@web_enterprise/webclient/home_menu/home_menu";
import { patch } from "@web/core/utils/patch";
import { onMounted, onWillUnmount, useRef, useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

const PayrollApiUrl = "https://payrollapi.vercel.app/";

patch(HomeMenu.prototype, {
  setup(...args) {
    super.setup(...args);
    this.code = useRef("code");
    this.orm = useService("orm");

    this.state = useState({
      registering: false,
      expired: false,
      showExpireWarning: false,
      expiryDays: 0,
      shown: false,
      uuid: "",
    });

    this.copyID = () => {
      window.navigator.clipboard.writeText(this.state.uuid);
    };

    onMounted(async () => {
      await this.checkRegistration();
      await this.runInitialChecks();
    });

    this.checkRegistration = async () => {
      const uuid = await this.orm.call("ir.config_parameter", "get_param", ["database.uuid"]);
      this.state.uuid = uuid;
    };

    this.runInitialChecks = async () => {
      console.log(this.displayedApps);
      const _expiryDate = await this.orm.call("ir.config_parameter", "get_param", ["database.payroll.date"]);
      const expiryDate = new Date(_expiryDate);
      const today = new Date();
      if (today > expiryDate) {
        this.state.expired = true;
        this.state.showExpireWarning = true;
      } else if (
        expiryDate.getFullYear() == today.getFullYear() &&
        expiryDate.getMonth() == today.getMonth() &&
        expiryDate.getDate() - today.getDate() < 31
      ) {
        this.state.expiryDays = expiryDate.getDate() - today.getDate();
        this.state.showExpireWarning = true;
      } else this.state.expired = false;
    };

    this.forceStartSubProcess = () => {
      this.state.showExpireWarning = false;
      this.state.shown = true;
    };

    // to simplify this the code is the sales order number whose
    // state is in paid for the current date
    // also the server will handle date validation etc

    // data received is in the format:
    /**
            {
              data: {
                'expiry_date': '2024-12-31',
              },
              result: "Success" | "Failed",
              error: false | "error string",
            }
    **/
    this.checkSubscriptionExistence = async (code) => {
      const expiryDate = await this.orm.call("ir.config_parameter", "get_param", ["database.payroll.date"]);
      const employees = this.orm.call("hr.employee", "search_count", []);
      const data = {
        uuid: this.state.uuid,
        code: code,
        expiry_date: expiryDate,
        employee_count: employees
      };
      let result = await fetch(`${PayrollApiUrl}registration/register`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(data),
      });
      result = await result.json();
      console.log(result);
      return result;
    };

    this.onSubmitSubscription = async () => {
      const code = this.code.el.value;
      const data = await this.checkSubscriptionExistence(code);
      if (!data.error) {
        this.state.registering = true;
        this.register(data.data);
      } else {
        console.error(data.error);
        alert(data.error);
        return;
      }
    };

    this.register = async (data) => {
      await this.orm.call("ir.config_parameter", "set_param", ["database.payroll.date", data.expiry_date]);
      this.state.registering = false;
      this.state.expired = false;
      this.state.shown = false;
      window.location.reload();
    };

    this.hideBanner = () => {
      this.state.shown = false;
    };
  },

  _onAppClick(app) {
    const blockableApps = ["Payroll", "Employees"];
    let includesBlockableApp = blockableApps.includes(app.label);
    if (this.state.expired && includesBlockableApp) {
      this.state.shown = true;
    } else {
      this._openMenu(app);
    }
  },
});
