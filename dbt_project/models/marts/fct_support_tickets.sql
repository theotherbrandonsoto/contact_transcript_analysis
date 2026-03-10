with stg as (
    select * from {{ ref('stg_support_tickets') }}
)

select
    ticket_id,
    user_id,
    plan_type,
    channel,
    status,
    is_churned,
    primary_label,
    secondary_label,
    tertiary_label,
    sentiment,
    urgency,
    one_line_summary,
    ticket_body,
    created_at,

    -- Derived flags
    case
        when sentiment in ('Frustrated', 'Angry') then true
        else false
    end as is_negative_sentiment,

    case
        when urgency = 3 then true
        else false
    end as is_high_urgency,

    case
        when is_churned = true and sentiment in ('Frustrated', 'Angry') then true
        else false
    end as is_churn_risk_signal,

    -- Month bucket for trend analysis
    date_trunc('month', created_at) as ticket_month

from stg
