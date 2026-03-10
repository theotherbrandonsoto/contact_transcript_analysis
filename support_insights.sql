with fct as (
    select * from {{ ref('fct_support_tickets') }}
)

select
    primary_label,
    secondary_label,
    plan_type,
    ticket_month,

    count(*)                                                        as total_tickets,
    sum(case when is_churned     = true  then 1 else 0 end)        as churned_customer_tickets,
    sum(case when is_negative_sentiment = true then 1 else 0 end)  as negative_sentiment_tickets,
    sum(case when is_high_urgency       = true then 1 else 0 end)  as high_urgency_tickets,
    sum(case when is_churn_risk_signal  = true then 1 else 0 end)  as churn_risk_signals,
    sum(case when status = 'Escalated'  then 1 else 0 end)         as escalated_tickets,

    round(
        100.0 * sum(case when is_churned = true then 1 else 0 end) / count(*),
        1
    ) as pct_from_churned_customers,

    round(
        100.0 * sum(case when is_negative_sentiment = true then 1 else 0 end) / count(*),
        1
    ) as pct_negative_sentiment

from fct
group by 1, 2, 3, 4
