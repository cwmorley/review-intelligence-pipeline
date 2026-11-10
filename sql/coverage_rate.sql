-- Reviewer coverage rate from the synthetic CSVs, mirroring scoring.py with
-- recency decay disabled (half_life_days=None).
--
--   offered  = eligible placements for an active reviewer
--   covered  = offered placements marked as covered AND linked to an accepted
--              or corrected review by the same reviewer
--   posterior mean = (1 + covered) / (2 + offered), the Beta(1, 1) baseline
--
-- scoring.py excludes a reviewer whose coverage link is broken; this query
-- counts such a placement as not covered instead. The synthetic data has none.
WITH verified_reviews AS (
    SELECT review_id, candidate_id
    FROM reviews
    WHERE lower(trim(verification_status)) IN ('accepted', 'corrected')
),
placements AS (
    SELECT
        e.candidate_id,
        e.engagement_id,
        CASE
            WHEN lower(trim(e.coverage_observed)) IN ('1', 'true', 'yes', 'y')
                 AND r.review_id IS NOT NULL THEN 1
            ELSE 0
        END AS covered
    FROM engagements AS e
    LEFT JOIN verified_reviews AS r
        ON r.review_id = e.coverage_review_id
       AND r.candidate_id = e.candidate_id
    WHERE lower(trim(e.eligible_for_coverage)) IN ('1', 'true', 'yes', 'y')
),
per_reviewer AS (
    SELECT
        c.candidate_id,
        c.candidate_name,
        c.outlet_name,
        COUNT(p.engagement_id) AS placements_offered,
        COALESCE(SUM(p.covered), 0) AS placements_covered
    FROM candidates AS c
    LEFT JOIN placements AS p ON p.candidate_id = c.candidate_id
    WHERE lower(trim(c.active)) NOT IN ('0', 'false', 'no', 'n')
    GROUP BY c.candidate_id, c.candidate_name, c.outlet_name
)
SELECT
    candidate_id,
    candidate_name,
    outlet_name,
    placements_offered,
    placements_covered,
    CASE WHEN placements_offered > 0
         THEN 1.0 * placements_covered / placements_offered END AS coverage_rate,
    (1.0 + placements_covered) / (2.0 + placements_offered) AS coverage_posterior_mean,
    RANK() OVER (
        ORDER BY (1.0 + placements_covered) / (2.0 + placements_offered) DESC
    ) AS coverage_rank,
    1.0 * placements_offered / SUM(placements_offered) OVER () AS share_of_placements
FROM per_reviewer
ORDER BY coverage_rank, candidate_id;
