from odoo import http
from odoo.http import request
from odoo.addons.website_portal_sale.controllers.main import website_account


class website_account(website_account):

    @http.route()
    def portal_my_quotes(self, page=1, date_begin=None, date_end=None, **kw):
    	values = self._prepare_portal_layout_values()
        partner = request.env.user.partner_id
        SaleOrder = request.env['sale.order']

        domain = [
            ('message_partner_ids', 'child_of', [
                partner.commercial_partner_id.id]),
            ('state', 'in', ['draft', 'sent', 'cancel'])
        ]

        archive_groups = self._get_archive_groups('sale.order', domain)

        if date_begin and date_end:
            domain += [('create_date', '>', date_begin),
                       ('create_date', '<=', date_end)]

        # count for pager
        quotation_count = SaleOrder.search_count(domain)

        # make pager
        pager = request.website.pager(
        	url="/my/quotes",
        	url_args={'date_begin': date_begin, 'date_end': date_end},
        	total=quotation_count,
        	page=page,
        	step=self._items_per_page
        )
        # search the count to display, according to the pager data
        quotations = SaleOrder.search(
        	domain, limit=self._items_per_page, offset=pager['offset'])
        print("&&&&&&&", domain)
        print("$$$$$$$$", quotations)
        values.update({
        	'date': date_begin,
        	'quotations': quotations,
        	'pager': pager,
        	'archive_groups': archive_groups,
        	'default_url': '/my/quotes',
        })
        return request.render("website_portal_sale.portal_my_quotations", values)
