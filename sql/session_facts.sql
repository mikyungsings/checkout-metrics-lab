-- One row per checkout session, joined to its charge, refund and dispute.
-- Every metric in metrics.yml is computed from this view.
create or replace view session_facts as
select
    s.session_id,
    s.merchant_id,
    m.industry,
    s.started_at,
    date_trunc('week', s.started_at)                as week,
    s.country,
    s.device,
    s.payment_method,
    s.variant,
    s.submitted_payment,
    coalesce(c.status = 'succeeded', false)         as charge_succeeded,
    coalesce(c.amount_usd, 0)                       as amount_usd,
    r.refund_id is not null                         as refunded,
    d.dispute_id is not null                        as disputed
from sessions s
join merchants m      using (merchant_id)
left join charges c   using (session_id)
left join refunds r   on r.charge_id = c.charge_id
left join disputes d  on d.charge_id = c.charge_id;
