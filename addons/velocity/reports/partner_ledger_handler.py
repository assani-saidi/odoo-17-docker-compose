from odoo import models, fields, api, _
from datetime import datetime

INDEX_OF_BALANCE_COLUMN_FROM_END = -2
INDEX_OF_FOREIGN_BALANCE_COLUMN_FROM_END = -1


class PartnerLedgerHandler(models.AbstractModel):
    _inherit = 'account.partner.ledger.report.handler'

    def _manipulate_lines(self, default_result):
        currency = int(self.env.ref("velocity.velocity_secondary_currency").value)
        currency = self.env['res.currency'].browse(currency)
        balance_result_line = default_result['columns'][INDEX_OF_BALANCE_COLUMN_FROM_END]
        default_result['columns'][INDEX_OF_FOREIGN_BALANCE_COLUMN_FROM_END] = balance_result_line.copy()
        result_line = default_result['columns'][INDEX_OF_FOREIGN_BALANCE_COLUMN_FROM_END]
        result_line['expression_label'] = "foreign_balance"
        amount_value = round(balance_result_line['no_format'] * currency.rate, 2)
        result_line['name'] = f"{currency.symbol} {amount_value}"
        result_line['no_format'] = amount_value
        return default_result

    def _dynamic_lines_generator(self, report, options, all_column_groups_expression_totals, warnings=None):
        default_result = super(PartnerLedgerHandler, self)._dynamic_lines_generator(report, options,
                                                                                    all_column_groups_expression_totals,
                                                                                    warnings=None)
        currency = int(self.env.ref("velocity.velocity_secondary_currency").value)
        currency = self.env['res.currency'].browse(currency)
        for line in default_result:
            balance_result_line = line[1]['columns'][INDEX_OF_BALANCE_COLUMN_FROM_END]
            line[1]['columns'][INDEX_OF_FOREIGN_BALANCE_COLUMN_FROM_END] = balance_result_line.copy()
            result_line = line[1]['columns'][INDEX_OF_FOREIGN_BALANCE_COLUMN_FROM_END]
            amount_value = round(result_line['no_format'] * currency.rate, 2)
            result_line['name'] = f"{currency.symbol} {amount_value}"
            result_line['no_format'] = amount_value if result_line['currency'] == currency.symbol else 0.0
            result_line['expression_label'] = "foreign_balance"
        return default_result

    def _get_report_line_move_line(self, options, aml_query_result, partner_line_id, init_bal_by_col_group, level_shift=0):
        default_result = super(PartnerLedgerHandler, self)._get_report_line_move_line(options, aml_query_result, partner_line_id, init_bal_by_col_group, level_shift=0)
        return self._manipulate_lines(default_result)

    # def _get_aml_line(self, report, parent_line_id, options, eval_dict, init_bal_by_col_group):
    #     default_result = super(PartnerLedgerHandler, self)._get_aml_line(report, parent_line_id, options, eval_dict,
    #                                                                      init_bal_by_col_group)
    #     return self._manipulate_lines(default_result)

    # def _get_account_title_line(self, report, options, account, has_lines, eval_dict):
    #     default_result = super(PartnerLedgerHandler, self)._get_account_title_line(report, options, account, has_lines,
    #                                                                                eval_dict)
    #     return self._manipulate_lines(default_result)

    # def _report_expand_unfoldable_line_general_ledger(self, line_dict_id, groupby, options, progress, offset,
    #                                                   unfold_all_batch_data=None):
    #     default_result = super(PartnerLedgerHandler, self)._report_expand_unfoldable_line_general_ledger(line_dict_id, groupby, options, progress, offset, unfold_all_batch_data)
    #     currency = int(self.env.ref("velocity.velocity_secondary_currency").value)
    #     currency = self.env['res.currency'].browse(currency)
    #     try:
    #         result_line = default_result[0]['columns'][INDEX_OF_FOREIGN_BALANCE_COLUMN_FROM_END]
    #     except Exception:
    #         result_line = default_result['lines'][0]['columns'][INDEX_OF_FOREIGN_BALANCE_COLUMN_FROM_END]
    #     if result_line['expression_label'] == "balance":
    #         amount_value = round(result_line['no_format'] * currency.rate, 2)
    #         result_line['name'] = f"{currency.symbol} {amount_value}"
    #         result_line['no_format'] = amount_value
    #     return default_result
