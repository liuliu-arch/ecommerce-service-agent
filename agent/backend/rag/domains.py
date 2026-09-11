"""Read-only knowledge scope; this never grants business tool permissions."""
PUBLIC_DOMAINS = frozenset({'faq', 'promotion_and_member_policy', 'after_sale_policy', 'received_return_policy'})


def public_domains(values):
    return sorted(set(values) & PUBLIC_DOMAINS)


def infer_public_domains(query: str) -> list[str]:
    groups = {
        'faq': ('发票', '开票', '抬头'),
        'promotion_and_member_policy': ('会员', '金卡', '优惠', '券', '满减', '618', '大促', '活动'),
        'after_sale_policy': ('退款', '退钱', '未发货', '未出库'),
        'received_return_policy': ('退货', '签收'),
    }
    return [domain for domain, terms in groups.items() if any(term in query for term in terms)]
