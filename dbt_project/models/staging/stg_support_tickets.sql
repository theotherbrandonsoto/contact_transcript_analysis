with source as (
    select * from raw_support_tickets
)

select
    ticket_id,
    user_id,
    plan_type,
    channel,
    status,
    cast(is_churned as boolean)   as is_churned,
    primary_label,
    secondary_label,
    tertiary_label,
    sentiment,
    cast(urgency as integer)      as urgency,
    one_line_summary,
    ticket_body,
    cast(created_at as date)      as created_at
from source
where ticket_id is not null
  and user_id   is not null
