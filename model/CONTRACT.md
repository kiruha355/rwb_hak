# Detail core interface · W-08

Repository `kiruha355/rwb_hak`; input main `1939068295d7203a15cbb0a1ab5d407caca90f58`;
research `72c1fb6ffe43e95b2ba539dc1b396374f4bfde3a`. Implementation default,
not a record of human approval. Target PostgreSQL 16. SQL runtime is **pending**.

## Build interface

The build owner creates/resets **owned** `core` objects and controls the transaction,
raw-generation consistency, `ON_ERROR_STOP`, preflight and post-build checks.
Run `10_dims.sql` before `20_facts.sql`, inside that transaction. These fragments
read `raw` only, create/load their tables, and never commit, drop schemas, or modify
raw. They intentionally fail on an existing table: idempotent reset belongs to the
build owner. No helper function, extension or staging schema is required.

All source text stays untrimmed. NULL is not converted to an empty string or zero.
Numeric measures use unconstrained `numeric` (no scale rounding); typed input must
be validated before casts. The coordinated `05_typecheck.sql` runs before these
fragments: integers use `^[+-]?[0-9]+$`, finite decimals use
`^[+-]?([0-9]+([.][0-9]*)?|[.][0-9]+)$` (no exponent/whitespace), timestamps use
exact `YYYY-MM-DD HH:MM:SS` (no offset or fractional-second rounding).
Timestamps are `timestamp without time zone`; source
offset/time zone is unknown. Original timestamp column names below are retained.
No chronology CHECK rejects observed source anomalies. Technical raw lineage
`_source_file`/`_loaded_at` remains in raw and is not duplicated in core.

## Dimensions: exact columns

* `core.dim_date`: `date_day date PRIMARY KEY`, `month_start date`,
  `year_number integer`, `quarter_number integer`, `month_number integer`,
  `day_of_month integer`, `iso_year integer`, `iso_week integer`,
  `iso_day_of_week integer`, `is_weekend boolean` (all NOT NULL).
  Continuous calendar spans every non-NULL order timestamp, item shipping deadline
  and review creation/answer timestamp, and at least 2016-09-01–2018-08-31.
  Q1 window is explicitly `month_start >= DATE '2016-09-01' AND month_start <
  DATE '2018-09-01'`; the entire dimension can contain more than 24 months.
* `core.dim_order_status`: `order_status text PRIMARY KEY`, `is_revenue boolean`
  NOT NULL. All observed non-NULL statuses plus the eight known source statuses;
  `is_revenue = (order_status = 'delivered')`. This is the assignment's revenue
  eligibility rule, not proof of buyout/settlement. Unseen statuses remain visible
  and do not earn revenue; checks should report them.
* `core.dim_customer`: `customer_unique_id text PRIMARY KEY`. One observed buyer,
  no selected address and no inferred lifetime/history.
* `core.dim_customer_context`: `customer_id text PRIMARY KEY`,
  `customer_unique_id text NOT NULL` FK → `dim_customer`,
  `customer_zip_code_prefix text`, `customer_zip_code_prefix_validated text`,
  `customer_city text`, `customer_state text`.
  All raw customer rows, including a context without orders. ZIP original is the
  source-named text; derived value pads only `^[0-9]{1,5}$` to 5 digits, else NULL.
  Unique `(customer_id, customer_unique_id)` is the composite order FK target.
* `core.dim_seller`: `seller_id text PRIMARY KEY`,
  `seller_zip_code_prefix text`, `seller_zip_code_prefix_validated text`,
  `seller_city text`, `seller_state text`; same ZIP rule. Dirty city/state text stays.
* `core.dim_category`: `category_key text PRIMARY KEY`, `name_pt text`,
  `name_en text`, `is_unknown boolean NOT NULL`, `is_translated boolean NOT NULL`,
  `has_translation_row boolean NOT NULL`.
  Unknown key is exactly `'unknown'`, with both names NULL; all non-NULL source
  categories use `'pt:' || product_category_name` (including an empty source name).
  Domain is products UNION translation names, so unused translations survive.
  A NULL translation-name key is invalid; empty/space-containing category names
  remain source text and get their own nonempty prefixed category key.
  `name_pt` aliases raw `product_category_name`; `name_en` aliases raw
  `product_category_name_english`. Missing translation is `name_en IS NULL`,
  distinct from a missing category; no fake English fallback. `has_translation_row`
  separately preserves source-row membership even for a translation row with NULL
  English; reconstruct the translation source using this flag, not `is_translated`.
* `core.dim_product`: `product_id text PRIMARY KEY`,
  `category_key text NOT NULL` FK → `dim_category`,
  `product_name_lenght integer`, `product_description_lenght integer`,
  `product_photos_qty integer`, `product_weight_g numeric`,
  `product_length_cm numeric`, `product_height_cm numeric`, `product_width_cm numeric`.
  Source spelling `lenght` is intentional. Category source name is recovered via
  `dim_category.name_pt`; no trimming/folding, zero measurements remain zero.

## Facts: exact columns and grains

* `core.fact_order`: `order_id text PRIMARY KEY`, `customer_id text NOT NULL`,
  `customer_unique_id text NOT NULL`, `order_status text NOT NULL`,
  `order_purchase_timestamp timestamp`, `order_approved_at timestamp`,
  `order_delivered_carrier_date timestamp`,
  `order_delivered_customer_date timestamp`, `order_estimated_delivery_date timestamp`,
  `customer_zip_code_prefix text`, `customer_zip_code_prefix_validated text`,
  `customer_city text`, `customer_state text`.
  Composite customer FK → `dim_customer_context`; buyer FK → `dim_customer`;
  status FK → `dim_order_status`. Address is the source context of this order,
  not a buyer's current address. Every order is loaded independently of children.
* `core.fact_order_item`: `(order_id text, order_item_id integer) PRIMARY KEY`,
  both NOT NULL; `product_id text NOT NULL`, `seller_id text NOT NULL`,
  `price numeric`, `freight_value numeric`, `shipping_limit_at timestamp`.
  FKs → `fact_order`, `dim_product`, `dim_seller`. `shipping_limit_at` is the sole
  rename of raw `shipping_limit_date`. One source row is one observed item unit;
  no added quantity, allocated payment or inferred refund.
* `core.fact_payment`: `(order_id text, payment_sequential integer) PRIMARY KEY`,
  both NOT NULL; `payment_type text`, `payment_installments integer`,
  `payment_value numeric`. Order FK → `fact_order`; zeros remain zeros, installment
  count is not dated cash-flow detail.
* `core.fact_review`: `(review_id text, order_id text) PRIMARY KEY`, both NOT NULL;
  `review_score integer`, `review_comment_title text`, `review_comment_message text`,
  `review_creation_date timestamp`, `review_answer_timestamp timestamp`.
  Order FK → `fact_order`. Keep every review–order pair and its own full payload;
  `review_id` alone is **not** unique. Different payloads on different pairs remain
  unchanged. Duplicate natural keys (even identical rows) fail, with raw untouched;
  no DISTINCT/latest-row selection hides a duplicate-pair conflict.

Nullable fields above stay nullable. Natural keys and mandatory FK identity must
not be NULL/empty/whitespace-only; invalid keys, invalid typed text, non-finite numeric values,
duplicate keys and dangling mandatory references block the build. Source business
anomalies (zero/negative values, unusual score/installments, missing dates and
chronology) remain available for warnings; they are not repaired or filtered.

## Mart/check interface

Order aggregates, completeness, money reconciliation and metric variants belong
in `mart`; no child totals or late/review weighting policy is materialized on
`fact_order`. Join independent children only after aggregation to the requested
grain. Never replace no children/all-NULL components with measured zero.
Revenue consumers join `fact_order.order_status` → `dim_order_status.is_revenue`.
Calendar consumers group distinct `month_start` before a month-level LEFT JOIN.

Checks must cover eight-source field mapping, exact key/value multisets after
documented typing, FK/NULL counts, unmatched contexts and categories, calendar
gaps and bounds, zero/NULL preservation, full review payload and separate child
totals. Warnings include chronology, unexpected status/score, malformed ZIP,
missing translation and negative/zero measurements. Static parsing and CSV
comparisons do not establish PostgreSQL/core runtime success.
