
  create or replace view
    "lakehouse"."dev_silver"."fact_review"
  security definer
  as
    WITH review_raw AS (
    SELECT
        rr.review_id as review_id,
        rr.business_id as restaurant_id,
        rr.user_id as user_id,
        rr.stars as stars,
        rr.cool as cool,
        rr.funny as funny,
        rr.useful as useful,
        CAST(rr.date AS VARCHAR) as review_date,
        rr.text as review_description
    FROM "lakehouse"."bronze"."review" rr
)
SELECT * FROM review_raw
  ;
