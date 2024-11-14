{% snapshot snapshot_RSI_Calculation %}
{{
    config(
        target_schema='snapshot',
        unique_key='date',
        strategy='timestamp',
        updated_at='date',
        invalidate_hard_deletes=True
    )
}}
SELECT * FROM {{ ref('RSI_Calculation') }}
{% endsnapshot %}