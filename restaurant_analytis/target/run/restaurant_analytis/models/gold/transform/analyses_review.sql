
  create or replace view
    "lakehouse"."dev_gold"."analyses_review"
  security definer
  as
    WITH analyses AS (
    SELECT 
        fr.*,
        dr.restaurant_name as restaurant_name,
        dr.categories as categories,
        dr.city as city,
        dr.latitude as latitude,
        dr.longitude as longitude,
        dr.stars as restaurant_stars,
        dr.state as state,
        dr.review_count as review_count,
        dr.hours as hours,
        du.user_name
    FROM "lakehouse"."dev_silver"."fact_review" fr
    LEFT JOIN "lakehouse"."dev_silver"."dim_restaurant" dr
    ON fr.restaurant_id = dr.restaurant_id
    LEFT JOIN "lakehouse"."dev_silver"."dim_user" du 
    ON fr.user_id = du.user_id
)
SELECT * FROM analyses
  ;
