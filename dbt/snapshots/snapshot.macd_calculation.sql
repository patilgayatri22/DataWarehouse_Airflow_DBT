{% snapshot snapshot_session_summary %}
{{
    config(
        target_schema='snapshot',
        unique_key='date',
        strategy='timestamp',
        updated_at='ts',
        invalidate_hard_deletes=True
    )
}}
SELECT * FROM {{ ref('macd_calculation') }}
{% endsnapshot %}