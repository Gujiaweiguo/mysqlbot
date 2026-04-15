-- PostgreSQL demo BI schema for commercial operations.
-- Source reference: 招商蛇口数据智能平台_商业板块指标清单_v2.0_0827.xlsx
-- Suggested usage:
--   1) CREATE DATABASE cre_bi_demo;
--   2) \c cre_bi_demo
--   3) \i postgres_demo_schema.sql
--   4) \i postgres_demo_seed.sql

create schema if not exists cre_bi_demo;
set search_path to cre_bi_demo, public;

create table if not exists dim_date (
    date_key integer primary key,
    calendar_date date not null unique,
    year_num integer not null,
    quarter_num integer not null,
    month_num integer not null,
    year_month char(7) not null,
    week_num integer not null,
    day_num integer not null,
    day_of_week integer not null,
    day_name text not null,
    is_weekend boolean not null,
    is_month_start boolean not null,
    is_month_end boolean not null
);

create table if not exists dim_org (
    org_id integer primary key,
    org_code varchar(50) not null unique,
    org_name varchar(100) not null,
    management_level varchar(20) not null,
    region_name varchar(50),
    city_name varchar(50),
    parent_org_id integer references dim_org(org_id)
);

create table if not exists dim_project (
    project_id integer primary key,
    project_code varchar(50) not null unique,
    project_name varchar(100) not null,
    org_id integer not null references dim_org(org_id),
    project_type varchar(30) not null,
    operation_status varchar(30) not null,
    opening_date date,
    city_name varchar(50) not null,
    gross_floor_area numeric(14,2),
    rentable_area numeric(14,2),
    shop_count integer,
    parking_spaces integer,
    management_mode varchar(30),
    remark text
);

create table if not exists dim_floor (
    floor_id integer primary key,
    project_id integer not null references dim_project(project_id),
    floor_code varchar(20) not null,
    floor_name varchar(30) not null,
    floor_sequence integer not null,
    above_ground_flag boolean not null,
    unique (project_id, floor_code)
);

create table if not exists dim_shop (
    shop_id integer primary key,
    project_id integer not null references dim_project(project_id),
    floor_id integer not null references dim_floor(floor_id),
    shop_code varchar(30) not null,
    shop_name varchar(100) not null,
    shop_status varchar(30) not null,
    gla_area numeric(14,2) not null,
    gfa_area numeric(14,2) not null,
    business_category varchar(50) not null,
    sub_business_category varchar(50),
    lease_type varchar(30),
    shop_attribute varchar(30),
    unique (project_id, shop_code)
);

create table if not exists dim_brand (
    brand_id integer primary key,
    brand_code varchar(50) not null unique,
    brand_name varchar(100) not null,
    brand_level varchar(30),
    business_category varchar(50) not null,
    sub_business_category varchar(50),
    origin_type varchar(30),
    is_local_brand boolean not null default false
);

create table if not exists dim_member_level (
    member_level_id integer primary key,
    level_code varchar(30) not null unique,
    level_name varchar(50) not null,
    points_threshold integer not null,
    level_rank integer not null
);

create table if not exists dim_campaign (
    campaign_id integer primary key,
    campaign_code varchar(50) not null unique,
    campaign_name varchar(100) not null,
    project_id integer not null references dim_project(project_id),
    campaign_type varchar(30) not null,
    start_date date not null,
    end_date date not null,
    budget_amount numeric(14,2) not null,
    status varchar(20) not null
);

create table if not exists dim_coupon (
    coupon_id integer primary key,
    campaign_id integer not null references dim_campaign(campaign_id),
    coupon_code varchar(50) not null unique,
    coupon_name varchar(100) not null,
    coupon_type varchar(30) not null,
    coupon_amount numeric(12,2) not null,
    issue_channel varchar(30) not null
);

create table if not exists dim_marketing_channel (
    channel_id integer primary key,
    channel_code varchar(50) not null unique,
    channel_name varchar(100) not null,
    channel_group varchar(30) not null,
    is_online boolean not null default true
);

create table if not exists dim_indicator_catalog (
    indicator_id integer primary key,
    indicator_code varchar(50) not null unique,
    theme_name varchar(30) not null,
    category_name varchar(100) not null,
    indicator_name varchar(200) not null,
    indicator_unit varchar(50),
    source_sheet_name varchar(100) not null,
    grain_suggestion varchar(100),
    mapped_object_name varchar(255) not null,
    definition text,
    formula text
);

create table if not exists dim_fee_subject (
    subject_id integer primary key,
    subject_code varchar(30) not null unique,
    subject_name varchar(50) not null,
    subject_category varchar(30) not null,
    display_order integer not null
);

create table if not exists dim_tenant_customer (
    customer_id integer primary key,
    customer_code varchar(50) not null unique,
    customer_name varchar(100) not null,
    customer_type varchar(30) not null,
    industry_category varchar(50),
    project_id integer not null references dim_project(project_id),
    brand_id integer references dim_brand(brand_id),
    contract_id integer,
    active_flag boolean not null default true
);

create table if not exists dim_area (
    area_id integer primary key,
    project_id integer not null references dim_project(project_id),
    floor_code varchar(20) not null,
    area_code varchar(30) not null,
    area_name varchar(100) not null,
    area_type varchar(30) not null,
    managed_area numeric(14,2) not null,
    unique (project_id, area_code)
);

create table if not exists dim_equipment_system (
    system_id integer primary key,
    system_code varchar(30) not null unique,
    system_name varchar(50) not null,
    engineering_domain varchar(30) not null
);

create table if not exists dim_vendor (
    vendor_id integer primary key,
    vendor_code varchar(30) not null unique,
    vendor_name varchar(100) not null,
    vendor_type varchar(30) not null,
    service_scope varchar(100)
);

create table if not exists dim_equipment (
    equipment_id integer primary key,
    project_id integer not null references dim_project(project_id),
    area_id integer not null references dim_area(area_id),
    system_id integer not null references dim_equipment_system(system_id),
    vendor_id integer references dim_vendor(vendor_id),
    equipment_code varchar(50) not null unique,
    equipment_name varchar(100) not null,
    equipment_type varchar(50) not null,
    brand_name varchar(50),
    install_date date,
    warranty_end_date date,
    critical_flag boolean not null default false,
    asset_status varchar(20) not null,
    constraint ck_equipment_status
        check (asset_status in ('running', 'standby', 'maintenance', 'disabled'))
);

create table if not exists dim_work_order_type (
    work_order_type_id integer primary key,
    type_code varchar(30) not null unique,
    type_name varchar(50) not null,
    major_category varchar(30) not null,
    sla_minutes integer not null
);

create table if not exists dim_complaint_type (
    complaint_type_id integer primary key,
    type_code varchar(30) not null unique,
    type_name varchar(50) not null,
    complaint_domain varchar(30) not null
);

create table if not exists fact_leasing_contract (
    contract_id integer primary key,
    project_id integer not null references dim_project(project_id),
    shop_id integer not null references dim_shop(shop_id),
    brand_id integer not null references dim_brand(brand_id),
    contract_no varchar(50) not null unique,
    contract_status varchar(30) not null,
    cooperation_mode varchar(30) not null,
    rent_type varchar(30) not null,
    payment_cycle varchar(20) not null,
    sign_date date not null,
    lease_start_date date not null,
    lease_end_date date not null,
    handover_date date,
    opening_date date,
    closing_date date,
    rent_area numeric(14,2) not null,
    fixed_rent_monthly numeric(14,2) not null,
    commission_rate numeric(6,4),
    deposit_amount numeric(14,2),
    sales_target_monthly numeric(14,2),
    brand_category varchar(50),
    brand_sub_category varchar(50),
    constraint ck_contract_status
        check (contract_status in ('signed', 'fitout', 'operating', 'closed', 'terminated')),
    constraint ck_rent_type
        check (rent_type in ('fixed', 'fixed_plus_commission', 'commission_only')),
    constraint ck_payment_cycle
        check (payment_cycle in ('monthly', 'quarterly', 'semiannual', 'annual'))
);

create table if not exists fact_shop_daily_operation (
    operation_id bigint primary key,
    date_key integer not null references dim_date(date_key),
    project_id integer not null references dim_project(project_id),
    shop_id integer not null references dim_shop(shop_id),
    brand_id integer references dim_brand(brand_id),
    business_status varchar(30) not null,
    sales_amount numeric(14,2) not null default 0,
    sales_orders integer not null default 0,
    customer_flow integer not null default 0,
    operating_area numeric(14,2) not null default 0,
    rent_income numeric(14,2) not null default 0,
    management_fee_income numeric(14,2) not null default 0,
    active_member_sales numeric(14,2) not null default 0,
    coupon_writeoff_amount numeric(14,2) not null default 0,
    coupon_writeoff_qty integer not null default 0,
    constraint uq_shop_day unique (date_key, shop_id),
    constraint ck_business_status
        check (business_status in ('vacant', 'pre_open', 'fitout', 'operating', 'closed'))
);

create table if not exists fact_tc_process (
    tc_id integer primary key,
    project_id integer not null references dim_project(project_id),
    shop_id integer not null references dim_shop(shop_id),
    brand_id integer references dim_brand(brand_id),
    contract_id integer unique references fact_leasing_contract(contract_id),
    tc_status varchar(30) not null,
    planned_handover_date date,
    actual_handover_date date,
    design_submission_date date,
    drawing_submission_date date,
    entry_date date,
    acceptance_date date,
    planned_open_date date,
    actual_open_date date,
    exit_notice_date date,
    actual_close_date date,
    vacancy_days integer,
    fitout_days integer,
    constraint ck_tc_status
        check (tc_status in ('planning', 'handover', 'fitout', 'operating', 'exit'))
);

create table if not exists fact_member_daily (
    member_fact_id bigint primary key,
    date_key integer not null references dim_date(date_key),
    project_id integer not null references dim_project(project_id),
    member_level_id integer not null references dim_member_level(member_level_id),
    total_members integer not null,
    valid_members integer not null,
    new_members integer not null,
    upgraded_members integer not null default 0,
    downgraded_members integer not null default 0,
    lost_members integer not null default 0,
    active_members integer not null,
    member_sales_amount numeric(14,2) not null default 0,
    member_orders integer not null default 0,
    retention_rate numeric(7,4),
    active_rate numeric(7,4),
    constraint uq_member_day unique (date_key, project_id, member_level_id)
);

create table if not exists fact_campaign_coupon_daily (
    campaign_fact_id bigint primary key,
    date_key integer not null references dim_date(date_key),
    project_id integer not null references dim_project(project_id),
    campaign_id integer not null references dim_campaign(campaign_id),
    coupon_id integer not null references dim_coupon(coupon_id),
    issue_qty integer not null default 0,
    sold_qty integer not null default 0,
    redeemed_qty integer not null default 0,
    redeemed_amount numeric(14,2) not null default 0,
    refunded_qty integer not null default 0,
    refunded_amount numeric(14,2) not null default 0,
    expired_qty integer not null default 0,
    order_qty integer not null default 0,
    order_amount numeric(14,2) not null default 0,
    induced_sales_amount numeric(14,2) not null default 0,
    constraint uq_campaign_coupon_day unique (date_key, coupon_id)
);

create table if not exists fact_campaign_channel_daily (
    campaign_channel_fact_id bigint primary key,
    date_key integer not null references dim_date(date_key),
    project_id integer not null references dim_project(project_id),
    campaign_id integer not null references dim_campaign(campaign_id),
    channel_id integer not null references dim_marketing_channel(channel_id),
    exposure_count integer not null default 0,
    click_count integer not null default 0,
    lead_count integer not null default 0,
    spend_amount numeric(14,2) not null default 0,
    settled_amount numeric(14,2) not null default 0,
    constraint uq_campaign_channel_day unique (date_key, campaign_id, channel_id)
);

create table if not exists fact_campaign_daily_performance (
    campaign_performance_fact_id bigint primary key,
    date_key integer not null references dim_date(date_key),
    project_id integer not null references dim_project(project_id),
    campaign_id integer not null references dim_campaign(campaign_id),
    activity_visitors integer not null default 0,
    participating_shop_count integer not null default 0,
    new_members integer not null default 0,
    activated_members integer not null default 0,
    member_sales_amount numeric(14,2) not null default 0,
    onsite_orders integer not null default 0,
    constraint uq_campaign_perf_day unique (date_key, campaign_id)
);

create table if not exists fact_work_order (
    work_order_id bigint primary key,
    ticket_no varchar(50) not null unique,
    project_id integer not null references dim_project(project_id),
    area_id integer references dim_area(area_id),
    equipment_id integer references dim_equipment(equipment_id),
    work_order_type_id integer not null references dim_work_order_type(work_order_type_id),
    vendor_id integer references dim_vendor(vendor_id),
    reported_date_key integer not null references dim_date(date_key),
    assigned_date_key integer references dim_date(date_key),
    arrived_date_key integer references dim_date(date_key),
    closed_date_key integer references dim_date(date_key),
    priority_level varchar(20) not null,
    work_order_status varchar(20) not null,
    source_channel varchar(30) not null,
    response_minutes integer,
    repair_minutes integer,
    close_minutes integer,
    first_fix_flag boolean,
    overtime_flag boolean,
    satisfaction_score integer,
    constraint ck_priority_level
        check (priority_level in ('low', 'medium', 'high', 'urgent')),
    constraint ck_work_order_status
        check (work_order_status in ('new', 'assigned', 'in_progress', 'closed', 'cancelled'))
);

create table if not exists fact_inspection_record (
    inspection_id bigint primary key,
    project_id integer not null references dim_project(project_id),
    area_id integer not null references dim_area(area_id),
    equipment_id integer references dim_equipment(equipment_id),
    vendor_id integer references dim_vendor(vendor_id),
    inspection_date_key integer not null references dim_date(date_key),
    inspection_type varchar(30) not null,
    planned_count integer not null,
    completed_count integer not null,
    abnormal_count integer not null default 0,
    rectified_count integer not null default 0,
    constraint ck_inspection_type
        check (inspection_type in ('daily', 'weekly', 'monthly', 'special'))
);

create table if not exists fact_energy_daily (
    energy_fact_id bigint primary key,
    date_key integer not null references dim_date(date_key),
    project_id integer not null references dim_project(project_id),
    area_id integer not null references dim_area(area_id),
    system_id integer references dim_equipment_system(system_id),
    electricity_kwh numeric(14,2) not null default 0,
    water_ton numeric(14,2) not null default 0,
    gas_ton numeric(14,2) not null default 0,
    cooling_ton_hour numeric(14,2) not null default 0,
    energy_cost_amount numeric(14,2) not null default 0,
    customer_flow integer not null default 0,
    operating_hours numeric(8,2) not null default 0
);

create table if not exists fact_safety_issue (
    safety_issue_id bigint primary key,
    project_id integer not null references dim_project(project_id),
    area_id integer references dim_area(area_id),
    issue_date_key integer not null references dim_date(date_key),
    rectify_due_date_key integer references dim_date(date_key),
    closed_date_key integer references dim_date(date_key),
    issue_category varchar(30) not null,
    risk_level varchar(20) not null,
    issue_status varchar(20) not null,
    overtime_flag boolean not null default false,
    constraint ck_issue_category
        check (issue_category in ('fire', 'electrical', 'equipment', 'construction', 'environment', 'security')),
    constraint ck_risk_level
        check (risk_level in ('low', 'medium', 'high', 'critical')),
    constraint ck_issue_status
        check (issue_status in ('open', 'rectifying', 'closed'))
);

create table if not exists fact_service_complaint (
    complaint_id bigint primary key,
    project_id integer not null references dim_project(project_id),
    area_id integer references dim_area(area_id),
    complaint_type_id integer not null references dim_complaint_type(complaint_type_id),
    reported_date_key integer not null references dim_date(date_key),
    closed_date_key integer references dim_date(date_key),
    source_channel varchar(30) not null,
    complaint_status varchar(20) not null,
    close_minutes integer,
    satisfaction_score integer,
    repeat_flag boolean not null default false,
    overtime_flag boolean not null default false,
    constraint ck_complaint_status
        check (complaint_status in ('open', 'processing', 'closed'))
);

create table if not exists fact_parking_daily (
    parking_fact_id bigint primary key,
    date_key integer not null references dim_date(date_key),
    project_id integer not null references dim_project(project_id),
    parking_entries integer not null default 0,
    parking_exits integer not null default 0,
    avg_turnover_times numeric(8,2) not null default 0,
    avg_queue_minutes numeric(8,2) not null default 0,
    abnormal_event_count integer not null default 0,
    parking_revenue_amount numeric(14,2) not null default 0
);

create table if not exists fact_finance_monthly (
    finance_fact_id bigint primary key,
    month_key integer not null references dim_date(date_key),
    project_id integer not null references dim_project(project_id),
    revenue_amount numeric(16,2) not null,
    operating_cost_amount numeric(16,2) not null,
    gross_profit_amount numeric(16,2) not null,
    gross_margin numeric(7,4) not null,
    net_profit_amount numeric(16,2) not null,
    net_margin numeric(7,4) not null,
    budget_revenue_amount numeric(16,2) not null,
    budget_cost_amount numeric(16,2) not null,
    rent_revenue_amount numeric(16,2) not null,
    property_fee_amount numeric(16,2) not null,
    parking_revenue_amount numeric(16,2) not null,
    marketing_expense_amount numeric(16,2) not null,
    admin_expense_amount numeric(16,2) not null,
    cash_in_amount numeric(16,2) not null,
    cash_out_amount numeric(16,2) not null,
    occupancy_rate numeric(7,4),
    opening_rate numeric(7,4),
    constraint uq_finance_month unique (month_key, project_id)
);

create table if not exists fact_rental_budget_monthly (
    rental_budget_id bigint primary key,
    month_key integer not null references dim_date(date_key),
    project_id integer not null references dim_project(project_id),
    subject_id integer not null references dim_fee_subject(subject_id),
    budget_amount numeric(16,2) not null,
    constraint uq_rental_budget unique (month_key, project_id, subject_id)
);

create table if not exists fact_receivable_bill (
    bill_id bigint primary key,
    bill_no varchar(50) not null unique,
    bill_month_key integer not null references dim_date(date_key),
    bill_date_key integer not null references dim_date(date_key),
    due_date_key integer not null references dim_date(date_key),
    project_id integer not null references dim_project(project_id),
    customer_id integer not null references dim_tenant_customer(customer_id),
    contract_id integer references fact_leasing_contract(contract_id),
    shop_id integer references dim_shop(shop_id),
    subject_id integer not null references dim_fee_subject(subject_id),
    fee_period_start date not null,
    fee_period_end date not null,
    bill_amount numeric(16,2) not null,
    reduction_amount numeric(16,2) not null default 0,
    receivable_amount numeric(16,2) not null,
    bill_status varchar(20) not null default 'issued',
    constraint ck_bill_status
        check (bill_status in ('draft', 'issued', 'partially_paid', 'paid', 'overdue'))
);

create table if not exists fact_cash_receipt (
    receipt_id bigint primary key,
    receipt_no varchar(50) not null unique,
    receipt_date_key integer not null references dim_date(date_key),
    project_id integer not null references dim_project(project_id),
    customer_id integer not null references dim_tenant_customer(customer_id),
    bill_id bigint not null references fact_receivable_bill(bill_id),
    subject_id integer not null references dim_fee_subject(subject_id),
    receipt_amount numeric(16,2) not null,
    payment_channel varchar(30) not null,
    payment_method varchar(30) not null
);

create table if not exists fact_ar_aging_snapshot (
    aging_snapshot_id bigint primary key,
    snapshot_date_key integer not null references dim_date(date_key),
    bill_id bigint not null references fact_receivable_bill(bill_id),
    project_id integer not null references dim_project(project_id),
    customer_id integer not null references dim_tenant_customer(customer_id),
    subject_id integer not null references dim_fee_subject(subject_id),
    outstanding_amount numeric(16,2) not null,
    days_past_due integer not null,
    aging_bucket varchar(30) not null,
    constraint uq_aging_snapshot unique (snapshot_date_key, bill_id)
);

create index if not exists idx_project_org on dim_project(org_id);
create index if not exists idx_floor_project on dim_floor(project_id);
create index if not exists idx_shop_project on dim_shop(project_id);
create index if not exists idx_area_project on dim_area(project_id);
create index if not exists idx_equipment_project on dim_equipment(project_id);
create index if not exists idx_equipment_system on dim_equipment(system_id);
create index if not exists idx_contract_project on fact_leasing_contract(project_id);
create index if not exists idx_contract_brand on fact_leasing_contract(brand_id);
create index if not exists idx_shop_daily_project_date on fact_shop_daily_operation(project_id, date_key);
create index if not exists idx_member_daily_project_date on fact_member_daily(project_id, date_key);
create index if not exists idx_campaign_daily_project_date on fact_campaign_coupon_daily(project_id, date_key);
create index if not exists idx_campaign_channel_daily on fact_campaign_channel_daily(project_id, date_key);
create index if not exists idx_campaign_perf_daily on fact_campaign_daily_performance(project_id, date_key);
create index if not exists idx_work_order_project_date on fact_work_order(project_id, reported_date_key);
create index if not exists idx_work_order_status on fact_work_order(work_order_status, overtime_flag);
create index if not exists idx_inspection_project_date on fact_inspection_record(project_id, inspection_date_key);
create index if not exists idx_energy_project_date on fact_energy_daily(project_id, date_key);
create index if not exists idx_safety_project_date on fact_safety_issue(project_id, issue_date_key);
create index if not exists idx_complaint_project_date on fact_service_complaint(project_id, reported_date_key);
create index if not exists idx_parking_project_date on fact_parking_daily(project_id, date_key);
create index if not exists idx_finance_month_project on fact_finance_monthly(project_id, month_key);
create index if not exists idx_customer_project on dim_tenant_customer(project_id);
create index if not exists idx_budget_month_project on fact_rental_budget_monthly(project_id, month_key);
create index if not exists idx_bill_month_project on fact_receivable_bill(project_id, bill_month_key);
create index if not exists idx_bill_customer on fact_receivable_bill(customer_id);
create index if not exists idx_bill_subject on fact_receivable_bill(subject_id);
create index if not exists idx_receipt_project_date on fact_cash_receipt(project_id, receipt_date_key);
create index if not exists idx_receipt_bill on fact_cash_receipt(bill_id);
create index if not exists idx_aging_snapshot_project on fact_ar_aging_snapshot(project_id, snapshot_date_key);

create or replace view vw_project_daily_kpi as
select
    o.date_key,
    d.calendar_date,
    o.project_id,
    p.project_name,
    sum(o.sales_amount) as sales_amount,
    sum(o.sales_orders) as sales_orders,
    case when sum(o.sales_orders) = 0 then 0
         else round(sum(o.sales_amount) / sum(o.sales_orders), 2)
    end as avg_ticket_amount,
    sum(o.customer_flow) as customer_flow,
    count(*) filter (where o.business_status in ('pre_open', 'fitout', 'operating')) as leased_shop_count,
    count(*) filter (where o.business_status = 'operating') as opened_shop_count,
    sum(o.operating_area) filter (where o.business_status in ('fitout', 'operating')) as leased_area,
    sum(o.operating_area) filter (where o.business_status = 'operating') as opened_area,
    sum(o.rent_income) as rent_income,
    sum(o.management_fee_income) as management_fee_income,
    sum(o.active_member_sales) as member_sales_amount,
    sum(o.coupon_writeoff_amount) as coupon_writeoff_amount
from fact_shop_daily_operation o
join dim_date d on d.date_key = o.date_key
join dim_project p on p.project_id = o.project_id
group by o.date_key, d.calendar_date, o.project_id, p.project_name;

create or replace view vw_project_monthly_kpi as
with op_month as (
    select
        cast(to_char(date_trunc('month', calendar_date), 'YYYYMMDD') as integer) as month_key,
        project_id,
        sum(sales_amount) as sales_amount,
        sum(sales_orders) as sales_orders,
        sum(customer_flow) as customer_flow,
        avg(leased_shop_count)::numeric(14,2) as avg_leased_shop_count,
        avg(opened_shop_count)::numeric(14,2) as avg_opened_shop_count,
        avg(leased_area)::numeric(14,2) as avg_leased_area,
        avg(opened_area)::numeric(14,2) as avg_opened_area,
        sum(rent_income) as rent_income,
        sum(management_fee_income) as management_fee_income,
        sum(member_sales_amount) as member_sales_amount,
        sum(coupon_writeoff_amount) as coupon_writeoff_amount
    from vw_project_daily_kpi
    group by cast(to_char(date_trunc('month', calendar_date), 'YYYYMMDD') as integer), project_id
),
member_month as (
    with member_day as (
        select
            m.date_key,
            d.calendar_date,
            m.project_id,
            sum(m.total_members) as total_members,
            sum(m.valid_members) as valid_members,
            sum(m.new_members) as new_members,
            sum(m.active_members) as active_members
        from fact_member_daily m
        join dim_date d on d.date_key = m.date_key
        group by m.date_key, d.calendar_date, m.project_id
    )
    select
        cast(to_char(date_trunc('month', calendar_date), 'YYYYMMDD') as integer) as month_key,
        project_id,
        max(total_members) as total_members,
        max(valid_members) as valid_members,
        sum(new_members) as new_members,
        avg(active_members)::numeric(14,2) as active_members
    from member_day
    group by cast(to_char(date_trunc('month', calendar_date), 'YYYYMMDD') as integer), project_id
),
campaign_month as (
    select
        cast(to_char(date_trunc('month', d.calendar_date), 'YYYYMMDD') as integer) as month_key,
        c.project_id,
        sum(c.issue_qty) as issue_qty,
        sum(c.redeemed_qty) as redeemed_qty,
        sum(c.redeemed_amount) as redeemed_amount,
        sum(c.induced_sales_amount) as induced_sales_amount
    from fact_campaign_coupon_daily c
    join dim_date d on d.date_key = c.date_key
    group by cast(to_char(date_trunc('month', d.calendar_date), 'YYYYMMDD') as integer), c.project_id
),
finance_month as (
    with receipt_bill as (
        select
            b.bill_month_key as month_key,
            b.project_id,
            sum(b.receivable_amount) as receivable_amount,
            sum(
                coalesce((
                    select sum(r.receipt_amount)
                    from fact_cash_receipt r
                    where r.bill_id = b.bill_id
                ), 0)
            ) as total_received_amount
        from fact_receivable_bill b
        group by b.bill_month_key, b.project_id
    )
    select
        month_key,
        project_id,
        receivable_amount,
        total_received_amount,
        receivable_amount - total_received_amount as outstanding_amount,
        case
            when receivable_amount = 0 then 0
            else round(total_received_amount / receivable_amount, 4)
        end as collection_rate
    from receipt_bill
)
select
    f.month_key,
    d.calendar_date as month_begin_date,
    f.project_id,
    p.project_name,
    f.revenue_amount,
    f.operating_cost_amount,
    f.gross_profit_amount,
    f.gross_margin,
    f.net_profit_amount,
    f.net_margin,
    f.budget_revenue_amount,
    f.cash_in_amount,
    f.cash_out_amount,
    coalesce(o.sales_amount, 0) as operating_sales_amount,
    coalesce(o.sales_orders, 0) as operating_sales_orders,
    coalesce(o.customer_flow, 0) as customer_flow,
    coalesce(o.avg_leased_shop_count, 0) as avg_leased_shop_count,
    coalesce(o.avg_opened_shop_count, 0) as avg_opened_shop_count,
    coalesce(o.avg_leased_area, 0) as avg_leased_area,
    coalesce(o.avg_opened_area, 0) as avg_opened_area,
    coalesce(m.total_members, 0) as total_members,
    coalesce(m.valid_members, 0) as valid_members,
    coalesce(m.new_members, 0) as new_members,
    coalesce(m.active_members, 0) as active_members,
    coalesce(c.issue_qty, 0) as coupon_issue_qty,
    coalesce(c.redeemed_qty, 0) as coupon_redeemed_qty,
    coalesce(c.redeemed_amount, 0) as coupon_redeemed_amount,
    coalesce(c.induced_sales_amount, 0) as induced_sales_amount,
    coalesce(fc.receivable_amount, 0) as receivable_amount,
    coalesce(fc.total_received_amount, 0) as received_amount,
    coalesce(fc.outstanding_amount, 0) as outstanding_amount,
    coalesce(fc.collection_rate, 0) as collection_rate
from fact_finance_monthly f
join dim_date d on d.date_key = f.month_key
join dim_project p on p.project_id = f.project_id
left join op_month o on o.month_key = f.month_key and o.project_id = f.project_id
left join member_month m on m.month_key = f.month_key and m.project_id = f.project_id
left join campaign_month c on c.month_key = f.month_key and c.project_id = f.project_id
left join finance_month fc on fc.month_key = f.month_key and fc.project_id = f.project_id;

create or replace view vw_leasing_daily_kpi as
select
    o.date_key,
    d.calendar_date,
    o.project_id,
    p.project_name,
    count(*) as total_shop_count,
    count(*) filter (where o.business_status = 'vacant') as vacant_shop_count,
    count(*) filter (where o.business_status = 'pre_open') as signed_not_handover_shop_count,
    count(*) filter (where o.business_status = 'fitout') as handover_not_open_shop_count,
    count(*) filter (where o.business_status = 'operating') as operating_shop_count,
    round(sum(s.gla_area), 2) as total_gla_area,
    round(coalesce(sum(s.gla_area) filter (where o.business_status in ('pre_open', 'fitout', 'operating')), 0), 2) as leased_gla_area,
    round(coalesce(sum(s.gla_area) filter (where o.business_status = 'operating'), 0), 2) as operating_gla_area,
    case
        when sum(s.gla_area) = 0 then 0
        else round(
            coalesce(sum(s.gla_area) filter (where o.business_status in ('pre_open', 'fitout', 'operating')), 0) / sum(s.gla_area),
            4
        )
    end as leased_area_rate,
    case
        when coalesce(sum(s.gla_area) filter (where o.business_status in ('pre_open', 'fitout', 'operating')), 0) = 0 then 0
        else round(
            coalesce(sum(s.gla_area) filter (where o.business_status = 'operating'), 0)
            / nullif(sum(s.gla_area) filter (where o.business_status in ('pre_open', 'fitout', 'operating')), 0),
            4
        )
    end as opening_area_rate,
    round(sum(o.sales_amount), 2) as sales_amount,
    case
        when coalesce(sum(o.operating_area) filter (where o.business_status = 'operating'), 0) = 0 then 0
        else round(
            sum(o.sales_amount) / nullif(sum(o.operating_area) filter (where o.business_status = 'operating'), 0),
            2
        )
    end as sales_per_sqm,
    round(avg(c.fixed_rent_monthly / nullif(c.rent_area, 0)) filter (
        where d.calendar_date between c.lease_start_date and c.lease_end_date
    ), 2) as avg_fixed_rent_unit_price,
    case
        when sum(o.sales_amount) = 0 then 0
        else round(sum(o.rent_income) / sum(o.sales_amount), 4)
    end as rent_to_sales_ratio
from fact_shop_daily_operation o
join dim_date d on d.date_key = o.date_key
join dim_project p on p.project_id = o.project_id
join dim_shop s on s.shop_id = o.shop_id
left join fact_leasing_contract c on c.shop_id = o.shop_id
group by o.date_key, d.calendar_date, o.project_id, p.project_name;

create or replace view vw_member_daily_kpi as
select
    m.date_key,
    d.calendar_date,
    m.project_id,
    p.project_name,
    sum(m.total_members) as total_members,
    sum(m.valid_members) as valid_members,
    sum(m.new_members) as new_members,
    sum(m.upgraded_members) as upgraded_members,
    sum(m.downgraded_members) as downgraded_members,
    sum(m.lost_members) as lost_members,
    sum(m.active_members) as active_members,
    sum(m.member_sales_amount) as member_sales_amount,
    sum(m.member_orders) as member_orders,
    case
        when sum(m.total_members) = 0 then 0
        else round(sum(m.new_members)::numeric / sum(m.total_members), 4)
    end as new_member_ratio,
    case
        when sum(m.valid_members) = 0 then 0
        else round(sum(m.active_members)::numeric / sum(m.valid_members), 4)
    end as active_member_rate,
    case
        when coalesce(o.sales_amount, 0) = 0 then 0
        else round(sum(m.member_sales_amount) / o.sales_amount, 4)
    end as member_sales_ratio,
    case
        when coalesce(o.sales_orders, 0) = 0 then 0
        else round(sum(m.member_orders)::numeric / o.sales_orders, 4)
    end as member_order_ratio
from fact_member_daily m
join dim_date d on d.date_key = m.date_key
join dim_project p on p.project_id = m.project_id
left join vw_project_daily_kpi o
    on o.date_key = m.date_key and o.project_id = m.project_id
group by m.date_key, d.calendar_date, m.project_id, p.project_name, o.sales_amount, o.sales_orders;

create or replace view vw_campaign_daily_kpi as
select
    c.date_key,
    d.calendar_date,
    c.project_id,
    p.project_name,
    count(distinct c.campaign_id) as active_campaign_count,
    sum(c.issue_qty) as coupon_issue_qty,
    sum(c.sold_qty) as coupon_sold_qty,
    sum(c.redeemed_qty) as coupon_redeemed_qty,
    sum(c.redeemed_amount) as coupon_redeemed_amount,
    sum(c.refunded_qty) as coupon_refunded_qty,
    sum(c.refunded_amount) as coupon_refunded_amount,
    sum(c.expired_qty) as coupon_expired_qty,
    sum(c.order_qty) as campaign_order_qty,
    sum(c.order_amount) as campaign_order_amount,
    sum(c.induced_sales_amount) as induced_sales_amount,
    case
        when sum(c.issue_qty) = 0 then 0
        else round(sum(c.redeemed_qty)::numeric / sum(c.issue_qty), 4)
    end as coupon_redeem_rate,
    case
        when coalesce(o.sales_amount, 0) = 0 then 0
        else round(sum(c.induced_sales_amount) / o.sales_amount, 4)
    end as induced_sales_ratio
from fact_campaign_coupon_daily c
join dim_date d on d.date_key = c.date_key
join dim_project p on p.project_id = c.project_id
left join vw_project_daily_kpi o
    on o.date_key = c.date_key and o.project_id = c.project_id
group by c.date_key, d.calendar_date, c.project_id, p.project_name, o.sales_amount;

create or replace view vw_campaign_channel_performance as
select
    c.date_key,
    d.calendar_date,
    c.project_id,
    p.project_name,
    c.campaign_id,
    cp.campaign_name,
    c.channel_id,
    ch.channel_name,
    c.exposure_count,
    c.click_count,
    c.lead_count,
    c.spend_amount,
    c.settled_amount,
    case
        when c.exposure_count = 0 then 0
        else round(c.click_count::numeric / c.exposure_count, 4)
    end as click_through_rate,
    case
        when c.click_count = 0 then 0
        else round(c.lead_count::numeric / c.click_count, 4)
    end as lead_conversion_rate,
    case
        when c.lead_count = 0 then 0
        else round(c.spend_amount / c.lead_count, 2)
    end as cost_per_lead
from fact_campaign_channel_daily c
join dim_date d on d.date_key = c.date_key
join dim_project p on p.project_id = c.project_id
join dim_campaign cp on cp.campaign_id = c.campaign_id
join dim_marketing_channel ch on ch.channel_id = c.channel_id;

create or replace view vw_campaign_roi_summary as
with coupon_summary as (
    select
        campaign_id,
        project_id,
        sum(issue_qty) as issue_qty,
        sum(redeemed_qty) as redeemed_qty,
        sum(redeemed_amount) as redeemed_amount,
        sum(order_qty) as order_qty,
        sum(order_amount) as order_amount,
        sum(induced_sales_amount) as induced_sales_amount
    from fact_campaign_coupon_daily
    group by campaign_id, project_id
),
channel_summary as (
    select
        campaign_id,
        project_id,
        sum(exposure_count) as exposure_count,
        sum(click_count) as click_count,
        sum(lead_count) as lead_count,
        sum(spend_amount) as spend_amount,
        sum(settled_amount) as settled_amount
    from fact_campaign_channel_daily
    group by campaign_id, project_id
),
perf_summary as (
    select
        campaign_id,
        project_id,
        sum(activity_visitors) as activity_visitors,
        avg(participating_shop_count)::numeric(14,2) as avg_participating_shop_count,
        sum(new_members) as new_members,
        sum(activated_members) as activated_members,
        sum(member_sales_amount) as member_sales_amount,
        sum(onsite_orders) as onsite_orders
    from fact_campaign_daily_performance
    group by campaign_id, project_id
)
select
    cp.campaign_id,
    cp.project_id,
    p.project_name,
    cp.campaign_name,
    cp.campaign_type,
    cp.start_date,
    cp.end_date,
    cp.budget_amount,
    coalesce(ch.spend_amount, 0) as actual_spend_amount,
    coalesce(ch.settled_amount, 0) as settled_amount,
    coalesce(ch.exposure_count, 0) as exposure_count,
    coalesce(ch.click_count, 0) as click_count,
    coalesce(ch.lead_count, 0) as lead_count,
    coalesce(pf.activity_visitors, 0) as activity_visitors,
    coalesce(pf.avg_participating_shop_count, 0) as avg_participating_shop_count,
    coalesce(pf.new_members, 0) as new_members,
    coalesce(pf.activated_members, 0) as activated_members,
    coalesce(pf.member_sales_amount, 0) as member_sales_amount,
    coalesce(pf.onsite_orders, 0) as onsite_orders,
    coalesce(cs.issue_qty, 0) as coupon_issue_qty,
    coalesce(cs.redeemed_qty, 0) as coupon_redeemed_qty,
    coalesce(cs.redeemed_amount, 0) as coupon_redeemed_amount,
    coalesce(cs.order_qty, 0) as campaign_order_qty,
    coalesce(cs.order_amount, 0) as campaign_order_amount,
    coalesce(cs.induced_sales_amount, 0) as induced_sales_amount,
    case
        when cp.budget_amount = 0 then 0
        else round(coalesce(ch.spend_amount, 0) / cp.budget_amount, 4)
    end as budget_execution_rate,
    case
        when coalesce(ch.spend_amount, 0) = 0 then 0
        else round(coalesce(cs.induced_sales_amount, 0) / ch.spend_amount, 4)
    end as sales_roi,
    case
        when coalesce(ch.spend_amount, 0) = 0 then 0
        else round((coalesce(cs.induced_sales_amount, 0) - ch.spend_amount) / ch.spend_amount, 4)
    end as incremental_roi,
    case
        when coalesce(pf.new_members, 0) = 0 then 0
        else round(coalesce(ch.spend_amount, 0) / pf.new_members, 2)
    end as cost_per_new_member,
    case
        when coalesce(pf.activity_visitors, 0) = 0 then 0
        else round(coalesce(ch.spend_amount, 0) / pf.activity_visitors, 2)
    end as cost_per_visitor
from dim_campaign cp
join dim_project p on p.project_id = cp.project_id
left join coupon_summary cs on cs.campaign_id = cp.campaign_id and cs.project_id = cp.project_id
left join channel_summary ch on ch.campaign_id = cp.campaign_id and ch.project_id = cp.project_id
left join perf_summary pf on pf.campaign_id = cp.campaign_id and pf.project_id = cp.project_id;

create or replace view vw_campaign_monthly_roi as
select
    cast(to_char(date_trunc('month', cp.start_date), 'YYYYMMDD') as integer) as month_key,
    cp.project_id,
    p.project_name,
    count(*) as campaign_count,
    sum(cp.budget_amount) as budget_amount,
    sum(coalesce(r.actual_spend_amount, 0)) as actual_spend_amount,
    sum(coalesce(r.induced_sales_amount, 0)) as induced_sales_amount,
    sum(coalesce(r.new_members, 0)) as new_members,
    sum(coalesce(r.activity_visitors, 0)) as activity_visitors,
    case
        when sum(cp.budget_amount) = 0 then 0
        else round(sum(coalesce(r.actual_spend_amount, 0)) / sum(cp.budget_amount), 4)
    end as budget_execution_rate,
    case
        when sum(coalesce(r.actual_spend_amount, 0)) = 0 then 0
        else round(sum(coalesce(r.induced_sales_amount, 0)) / sum(coalesce(r.actual_spend_amount, 0)), 4)
    end as sales_roi
from dim_campaign cp
join dim_project p on p.project_id = cp.project_id
left join vw_campaign_roi_summary r on r.campaign_id = cp.campaign_id and r.project_id = cp.project_id
group by cast(to_char(date_trunc('month', cp.start_date), 'YYYYMMDD') as integer), cp.project_id, p.project_name;

create or replace view vw_work_order_sla_daily as
select
    w.reported_date_key as date_key,
    d.calendar_date,
    w.project_id,
    p.project_name,
    count(*) as work_order_count,
    count(*) filter (where w.work_order_status = 'closed') as closed_work_order_count,
    count(*) filter (where w.overtime_flag) as overtime_work_order_count,
    count(*) filter (where w.first_fix_flag) as first_fix_work_order_count,
    round(avg(w.response_minutes), 2) as avg_response_minutes,
    round(avg(w.close_minutes), 2) as avg_close_minutes,
    case
        when count(*) = 0 then 0
        else round((count(*) filter (where not w.overtime_flag))::numeric / count(*), 4)
    end as sla_achievement_rate,
    case
        when count(*) = 0 then 0
        else round((count(*) filter (where w.first_fix_flag))::numeric / count(*), 4)
    end as first_fix_rate
from fact_work_order w
join dim_date d on d.date_key = w.reported_date_key
join dim_project p on p.project_id = w.project_id
group by w.reported_date_key, d.calendar_date, w.project_id, p.project_name;

create or replace view vw_equipment_o_and_m_monthly as
with inspection_month as (
    select
        equipment_id,
        cast(to_char(date_trunc('month', d.calendar_date), 'YYYYMMDD') as integer) as month_key,
        avg(i.completed_count::numeric / nullif(i.planned_count, 0)) as inspection_completion_rate
    from fact_inspection_record i
    join dim_date d on d.date_key = i.inspection_date_key
    group by equipment_id, cast(to_char(date_trunc('month', d.calendar_date), 'YYYYMMDD') as integer)
)
select
    cast(to_char(date_trunc('month', d.calendar_date), 'YYYYMMDD') as integer) as month_key,
    e.project_id,
    p.project_name,
    e.system_id,
    s.system_name,
    count(distinct e.equipment_id) as equipment_count,
    count(distinct w.work_order_id) as work_order_count,
    count(distinct w.work_order_id) filter (where w.overtime_flag) as overtime_work_order_count,
    round(avg(w.close_minutes), 2) as avg_close_minutes,
    case
        when count(distinct e.equipment_id) = 0 then 0
        else round(count(distinct w.work_order_id)::numeric / count(distinct e.equipment_id), 4)
    end as equipment_failure_rate,
    round(avg(im.inspection_completion_rate), 4) as inspection_completion_rate
from dim_equipment e
join dim_project p on p.project_id = e.project_id
join dim_equipment_system s on s.system_id = e.system_id
left join fact_work_order w on w.equipment_id = e.equipment_id
left join dim_date d on d.date_key = w.reported_date_key
left join inspection_month im
    on im.equipment_id = e.equipment_id
   and im.month_key = cast(to_char(date_trunc('month', d.calendar_date), 'YYYYMMDD') as integer)
where d.calendar_date is not null
group by cast(to_char(date_trunc('month', d.calendar_date), 'YYYYMMDD') as integer), e.project_id, p.project_name, e.system_id, s.system_name;

create or replace view vw_energy_efficiency_daily as
select
    e.date_key,
    d.calendar_date,
    e.project_id,
    p.project_name,
    round(sum(e.electricity_kwh), 2) as electricity_kwh,
    round(sum(e.water_ton), 2) as water_ton,
    round(sum(e.gas_ton), 2) as gas_ton,
    round(sum(e.cooling_ton_hour), 2) as cooling_ton_hour,
    round(sum(e.energy_cost_amount), 2) as energy_cost_amount,
    sum(e.customer_flow) as customer_flow,
    round(avg(e.operating_hours), 2) as avg_operating_hours,
    case
        when sum(a.managed_area) = 0 then 0
        else round(sum(e.electricity_kwh) / sum(a.managed_area), 4)
    end as electricity_per_sqm,
    case
        when sum(e.customer_flow) = 0 then 0
        else round(sum(e.energy_cost_amount) / sum(e.customer_flow), 4)
    end as energy_cost_per_customer
from fact_energy_daily e
join dim_date d on d.date_key = e.date_key
join dim_project p on p.project_id = e.project_id
join dim_area a on a.area_id = e.area_id
group by e.date_key, d.calendar_date, e.project_id, p.project_name;

create or replace view vw_service_safety_daily as
with safety_daily as (
    select
        issue_date_key as date_key,
        project_id,
        count(*) as safety_issue_count,
        count(*) filter (where overtime_flag) as overdue_safety_issue_count,
        count(*) filter (where risk_level in ('high', 'critical')) as high_risk_issue_count
    from fact_safety_issue
    group by issue_date_key, project_id
),
complaint_daily as (
    select
        reported_date_key as date_key,
        project_id,
        count(*) as complaint_count,
        count(*) filter (where repeat_flag) as repeat_complaint_count,
        count(*) filter (where overtime_flag) as overtime_complaint_count,
        round(avg(close_minutes), 2) as avg_close_minutes,
        round(avg(satisfaction_score), 2) as avg_satisfaction_score
    from fact_service_complaint
    group by reported_date_key, project_id
),
parking_daily as (
    select
        date_key,
        project_id,
        parking_entries,
        avg_turnover_times,
        avg_queue_minutes,
        abnormal_event_count
    from fact_parking_daily
)
select
    d.date_key,
    d.calendar_date,
    p.project_id,
    p.project_name,
    coalesce(s.safety_issue_count, 0) as safety_issue_count,
    coalesce(s.overdue_safety_issue_count, 0) as overdue_safety_issue_count,
    coalesce(s.high_risk_issue_count, 0) as high_risk_issue_count,
    coalesce(c.complaint_count, 0) as complaint_count,
    coalesce(c.repeat_complaint_count, 0) as repeat_complaint_count,
    coalesce(c.overtime_complaint_count, 0) as overtime_complaint_count,
    coalesce(c.avg_close_minutes, 0) as avg_complaint_close_minutes,
    coalesce(c.avg_satisfaction_score, 0) as avg_satisfaction_score,
    coalesce(pk.parking_entries, 0) as parking_entries,
    coalesce(pk.avg_turnover_times, 0) as avg_turnover_times,
    coalesce(pk.avg_queue_minutes, 0) as avg_queue_minutes,
    coalesce(pk.abnormal_event_count, 0) as parking_abnormal_event_count
from dim_date d
cross join dim_project p
left join safety_daily s on s.date_key = d.date_key and s.project_id = p.project_id
left join complaint_daily c on c.date_key = d.date_key and c.project_id = p.project_id
left join parking_daily pk on pk.date_key = d.date_key and pk.project_id = p.project_id;

create or replace view vw_tc_project_kpi as
select
    t.project_id,
    p.project_name,
    count(*) as total_tc_shop_count,
    count(*) filter (where t.planned_handover_date is not null) as planned_handover_shop_count,
    count(*) filter (where t.tc_status = 'fitout') as fitout_shop_count,
    count(*) filter (where t.tc_status = 'operating') as tc_operating_shop_count,
    count(*) filter (where t.tc_status = 'exit') as exit_shop_count,
    count(*) filter (where t.design_submission_date is not null) as design_submitted_shop_count,
    count(*) filter (where t.drawing_submission_date is not null) as drawing_submitted_shop_count,
    count(*) filter (where t.actual_handover_date is not null) as handover_shop_count,
    count(*) filter (where t.entry_date is not null) as entry_shop_count,
    count(*) filter (where t.acceptance_date is not null) as acceptance_shop_count,
    count(*) filter (where t.actual_open_date is not null) as opened_shop_count,
    round(sum(s.gla_area), 2) as total_tc_gla_area,
    round(coalesce(sum(s.gla_area) filter (where t.tc_status = 'fitout'), 0), 2) as fitout_gla_area,
    round(coalesce(sum(s.gla_area) filter (where t.tc_status = 'operating'), 0), 2) as tc_operating_gla_area,
    round(coalesce(sum(s.gla_area) filter (where t.actual_handover_date is not null), 0), 2) as handover_gla_area,
    round(coalesce(sum(s.gla_area) filter (where t.actual_open_date is not null), 0), 2) as opened_gla_area,
    case
        when count(*) = 0 then 0
        else round((count(*) filter (where t.actual_handover_date is not null))::numeric / count(*), 4)
    end as handover_shop_rate,
    case
        when count(*) = 0 then 0
        else round((count(*) filter (where t.actual_open_date is not null))::numeric / count(*), 4)
    end as opened_shop_rate,
    round(avg(t.fitout_days), 2) as avg_fitout_days,
    round(avg(t.vacancy_days), 2) as avg_vacancy_days
from fact_tc_process t
join dim_project p on p.project_id = t.project_id
join dim_shop s on s.shop_id = t.shop_id
group by t.project_id, p.project_name;

create or replace view vw_finance_collection_monthly as
with month_end as (
    select
        cast(to_char(date_trunc('month', calendar_date), 'YYYYMMDD') as integer) as month_key,
        max(calendar_date) as month_end_date
    from dim_date
    group by cast(to_char(date_trunc('month', calendar_date), 'YYYYMMDD') as integer)
),
bill_base as (
    select
        b.bill_id,
        b.bill_month_key as month_key,
        b.project_id,
        b.customer_id,
        b.subject_id,
        b.receivable_amount,
        ddue.calendar_date as due_date,
        me.month_end_date
    from fact_receivable_bill b
    join dim_date ddue on ddue.date_key = b.due_date_key
    join month_end me on me.month_key = b.bill_month_key
),
receipt_all as (
    select
        bill_id,
        sum(receipt_amount) as received_total_amount
    from fact_cash_receipt
    group by bill_id
),
receipt_month as (
    select
        cast(to_char(date_trunc('month', d.calendar_date), 'YYYYMMDD') as integer) as month_key,
        r.project_id,
        sum(r.receipt_amount) as actual_received_in_month_amount
    from fact_cash_receipt r
    join dim_date d on d.date_key = r.receipt_date_key
    group by cast(to_char(date_trunc('month', d.calendar_date), 'YYYYMMDD') as integer), r.project_id
),
receipt_by_month_end as (
    select
        b.month_key,
        b.project_id,
        sum(
            coalesce((
                select sum(r.receipt_amount)
                from fact_cash_receipt r
                join dim_date dr on dr.date_key = r.receipt_date_key
                where r.bill_id = b.bill_id
                  and dr.calendar_date <= b.month_end_date
            ), 0)
        ) as received_by_month_end_amount
    from bill_base b
    group by b.month_key, b.project_id
),
budget_month as (
    select
        month_key,
        project_id,
        sum(budget_amount) as budget_amount,
        sum(budget_amount) filter (where subject_id = 1) as rent_budget_amount
    from fact_rental_budget_monthly
    group by month_key, project_id
),
subject_received as (
    select
        cast(to_char(date_trunc('month', d.calendar_date), 'YYYYMMDD') as integer) as month_key,
        r.project_id,
        sum(r.receipt_amount) filter (where r.subject_id = 1) as rent_received_amount,
        sum(r.receipt_amount) filter (where r.subject_id = 2) as property_received_amount,
        sum(r.receipt_amount) filter (where r.subject_id = 3) as multi_received_amount
    from fact_cash_receipt r
    join dim_date d on d.date_key = r.receipt_date_key
    group by cast(to_char(date_trunc('month', d.calendar_date), 'YYYYMMDD') as integer), r.project_id
)
select
    me.month_key,
    d.calendar_date as month_begin_date,
    p.project_id,
    p.project_name,
    coalesce(sum(b.receivable_amount), 0) as receivable_amount,
    coalesce(rm.actual_received_in_month_amount, 0) as actual_received_in_month_amount,
    coalesce(rbe.received_by_month_end_amount, 0) as received_by_month_end_amount,
    round(coalesce(sum(b.receivable_amount), 0) - coalesce(rbe.received_by_month_end_amount, 0), 2) as outstanding_amount,
    case
        when coalesce(sum(b.receivable_amount), 0) = 0 then 0
        else round(coalesce(rbe.received_by_month_end_amount, 0) / sum(b.receivable_amount), 4)
    end as collection_rate,
    coalesce(bm.budget_amount, 0) as budget_amount,
    case
        when coalesce(bm.budget_amount, 0) = 0 then 0
        else round(coalesce(rm.actual_received_in_month_amount, 0) / bm.budget_amount, 4)
    end as budget_completion_rate,
    coalesce(sr.rent_received_amount, 0) as rent_received_amount,
    coalesce(sr.property_received_amount, 0) as property_received_amount,
    coalesce(sr.multi_received_amount, 0) as multi_received_amount,
    coalesce(aux.occupancy_rate, 0) as occupancy_rate,
    coalesce(aux.opening_rate, 0) as opening_rate
from (
    select distinct bill_month_key as month_key, project_id
    from fact_receivable_bill
) me
join dim_project p on p.project_id = me.project_id
join dim_date d on d.date_key = me.month_key
left join fact_receivable_bill b
    on b.bill_month_key = me.month_key and b.project_id = me.project_id
left join receipt_month rm
    on rm.month_key = me.month_key and rm.project_id = me.project_id
left join receipt_by_month_end rbe
    on rbe.month_key = me.month_key and rbe.project_id = me.project_id
left join budget_month bm
    on bm.month_key = me.month_key and bm.project_id = me.project_id
left join subject_received sr
    on sr.month_key = me.month_key and sr.project_id = me.project_id
left join fact_finance_monthly aux
    on aux.month_key = me.month_key and aux.project_id = me.project_id
group by
    me.month_key,
    d.calendar_date,
    p.project_id,
    p.project_name,
    rm.actual_received_in_month_amount,
    rbe.received_by_month_end_amount,
    bm.budget_amount,
    sr.rent_received_amount,
    sr.property_received_amount,
    sr.multi_received_amount,
    aux.occupancy_rate,
    aux.opening_rate;

create or replace view vw_finance_collection_by_subject as
with month_end as (
    select
        cast(to_char(date_trunc('month', calendar_date), 'YYYYMMDD') as integer) as month_key,
        max(calendar_date) as month_end_date
    from dim_date
    group by cast(to_char(date_trunc('month', calendar_date), 'YYYYMMDD') as integer)
),
receipt_month_subject as (
    select
        cast(to_char(date_trunc('month', d.calendar_date), 'YYYYMMDD') as integer) as month_key,
        r.project_id,
        r.subject_id,
        sum(r.receipt_amount) as actual_received_in_month_amount
    from fact_cash_receipt r
    join dim_date d on d.date_key = r.receipt_date_key
    group by cast(to_char(date_trunc('month', d.calendar_date), 'YYYYMMDD') as integer), r.project_id, r.subject_id
),
receipt_by_month_end_bill as (
    select
        b.bill_id,
        sum(r.receipt_amount) as received_by_month_end_amount
    from fact_receivable_bill b
    join month_end me on me.month_key = b.bill_month_key
    left join fact_cash_receipt r on r.bill_id = b.bill_id
    left join dim_date dr on dr.date_key = r.receipt_date_key
    where dr.calendar_date <= me.month_end_date or dr.calendar_date is null
    group by b.bill_id
)
select
    b.bill_month_key as month_key,
    d.calendar_date as month_begin_date,
    b.project_id,
    p.project_name,
    b.subject_id,
    s.subject_name,
    sum(b.receivable_amount) as receivable_amount,
    coalesce(rms.actual_received_in_month_amount, 0) as actual_received_in_month_amount,
    coalesce(sum(rbe.received_by_month_end_amount), 0) as received_by_month_end_amount,
    round(sum(b.receivable_amount) - coalesce(sum(rbe.received_by_month_end_amount), 0), 2) as outstanding_amount,
    case
        when sum(b.receivable_amount) = 0 then 0
        else round(coalesce(sum(rbe.received_by_month_end_amount), 0) / sum(b.receivable_amount), 4)
    end as subject_collection_rate,
    coalesce(sum(bg.budget_amount), 0) as budget_amount
from fact_receivable_bill b
join dim_project p on p.project_id = b.project_id
join dim_fee_subject s on s.subject_id = b.subject_id
join dim_date d on d.date_key = b.bill_month_key
left join receipt_month_subject rms
    on rms.month_key = b.bill_month_key and rms.project_id = b.project_id and rms.subject_id = b.subject_id
left join receipt_by_month_end_bill rbe on rbe.bill_id = b.bill_id
left join fact_rental_budget_monthly bg
    on bg.month_key = b.bill_month_key and bg.project_id = b.project_id and bg.subject_id = b.subject_id
group by
    b.bill_month_key, d.calendar_date, b.project_id, p.project_name, b.subject_id, s.subject_name, rms.actual_received_in_month_amount;

create or replace view vw_finance_collection_by_customer as
with month_end as (
    select
        cast(to_char(date_trunc('month', calendar_date), 'YYYYMMDD') as integer) as month_key,
        max(calendar_date) as month_end_date
    from dim_date
    group by cast(to_char(date_trunc('month', calendar_date), 'YYYYMMDD') as integer)
)
select
    b.bill_month_key as month_key,
    d.calendar_date as month_begin_date,
    b.project_id,
    p.project_name,
    b.customer_id,
    c.customer_name,
    sum(b.receivable_amount) as receivable_amount,
    coalesce(sum(r.receipt_amount), 0) as total_received_amount,
    round(sum(b.receivable_amount) - coalesce(sum(r.receipt_amount), 0), 2) as outstanding_amount,
    case
        when sum(b.receivable_amount) = 0 then 0
        else round(coalesce(sum(r.receipt_amount), 0) / sum(b.receivable_amount), 4)
    end as customer_collection_rate
from fact_receivable_bill b
join dim_project p on p.project_id = b.project_id
join dim_tenant_customer c on c.customer_id = b.customer_id
join dim_date d on d.date_key = b.bill_month_key
join month_end me on me.month_key = b.bill_month_key
left join fact_cash_receipt r on r.bill_id = b.bill_id
left join dim_date dr on dr.date_key = r.receipt_date_key
where dr.calendar_date <= me.month_end_date or dr.calendar_date is null
group by b.bill_month_key, d.calendar_date, b.project_id, p.project_name, b.customer_id, c.customer_name;

create or replace view vw_finance_ar_aging as
select
    a.snapshot_date_key,
    d.calendar_date as snapshot_date,
    a.project_id,
    p.project_name,
    a.subject_id,
    s.subject_name,
    a.aging_bucket,
    sum(a.outstanding_amount) as outstanding_amount,
    count(*) as overdue_bill_count
from fact_ar_aging_snapshot a
join dim_date d on d.date_key = a.snapshot_date_key
join dim_project p on p.project_id = a.project_id
join dim_fee_subject s on s.subject_id = a.subject_id
group by a.snapshot_date_key, d.calendar_date, a.project_id, p.project_name, a.subject_id, s.subject_name, a.aging_bucket;

create or replace view vw_finance_monthly_kpi as
select
    m.month_key,
    m.month_begin_date,
    m.project_id,
    m.project_name,
    m.receivable_amount,
    m.actual_received_in_month_amount,
    m.received_by_month_end_amount,
    m.outstanding_amount,
    m.collection_rate,
    m.budget_amount,
    m.budget_completion_rate,
    m.rent_received_amount,
    m.property_received_amount,
    m.multi_received_amount,
    m.occupancy_rate,
    m.opening_rate
from vw_finance_collection_monthly m;
