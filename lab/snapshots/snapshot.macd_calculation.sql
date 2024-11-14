{% snapshot snapshot_macd_calculation %}
{{
    config(
        target_schema='snapshot',
        unique_key='date',
        strategy='timestamp',
        updated_at='date',
        invalidate_hard_deletes=True
    )
}}
SELECT * FROM {{ ref('macd_calculation') }}
{% endsnapshot %}