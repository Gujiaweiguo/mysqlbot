-- Demo seed data for cre_bi_demo.
-- All business data below is synthetic demo data built from the indicator system in
-- 招商蛇口数据智能平台_商业板块指标清单_v2.0_0827.xlsx.

set search_path to cre_bi_demo, public;

insert into dim_date (
    date_key,
    calendar_date,
    year_num,
    quarter_num,
    month_num,
    year_month,
    week_num,
    day_num,
    day_of_week,
    day_name,
    is_weekend,
    is_month_start,
    is_month_end
)
select
    cast(to_char(dt, 'YYYYMMDD') as integer) as date_key,
    dt as calendar_date,
    extract(year from dt)::integer as year_num,
    extract(quarter from dt)::integer as quarter_num,
    extract(month from dt)::integer as month_num,
    to_char(dt, 'YYYY-MM') as year_month,
    extract(week from dt)::integer as week_num,
    extract(day from dt)::integer as day_num,
    extract(isodow from dt)::integer as day_of_week,
    case extract(isodow from dt)::integer
        when 1 then '周一'
        when 2 then '周二'
        when 3 then '周三'
        when 4 then '周四'
        when 5 then '周五'
        when 6 then '周六'
        else '周日'
    end as day_name,
    extract(isodow from dt) in (6, 7) as is_weekend,
    dt = date_trunc('month', dt)::date as is_month_start,
    dt = (date_trunc('month', dt) + interval '1 month - 1 day')::date as is_month_end
from generate_series(date '2024-01-01', date '2024-12-31', interval '1 day') as g(dt)
on conflict (date_key) do nothing;

insert into dim_org (org_id, org_code, org_name, management_level, region_name, city_name, parent_org_id) values
    (1, 'CRE-HQ', '招商蛇口商业管理总部', '总部', '全国', '深圳', null),
    (11, 'CRE-SOUTH', '华南区域', '区域', '华南', '深圳', 1),
    (12, 'CRE-EAST', '华东区域', '区域', '华东', '上海', 1),
    (13, 'CRE-WEST', '西南区域', '区域', '西南', '成都', 1)
on conflict (org_id) do nothing;

insert into dim_project (
    project_id,
    project_code,
    project_name,
    org_id,
    project_type,
    operation_status,
    opening_date,
    city_name,
    gross_floor_area,
    rentable_area,
    shop_count,
    parking_spaces,
    management_mode,
    remark
) values
    (101, 'PJT-SZ-001', '招商汇港天地', 11, '集中商业', '在营', date '2021-09-30', '深圳', 120000.00, 68000.00, 126, 980, '自持运营', '用于演示成熟项目的招商、营运、会员与财务分析'),
    (102, 'PJT-SH-001', '招商花园里', 12, '集中商业', '在营', date '2022-06-18', '上海', 98000.00, 56000.00, 102, 760, '轻资产运营', '用于演示高线城市存量商业项目'),
    (103, 'PJT-CD-001', '招商城南天地', 13, '集中商业', '培育期', date '2023-12-22', '成都', 86000.00, 48000.00, 88, 620, '自持运营', '用于演示新开业项目爬坡期分析')
on conflict (project_id) do nothing;

insert into dim_floor (floor_id, project_id, floor_code, floor_name, floor_sequence, above_ground_flag) values
    (1011, 101, 'B1', '地下一层', -1, false),
    (1012, 101, 'L1', '一层', 1, true),
    (1013, 101, 'L2', '二层', 2, true),
    (1014, 101, 'L3', '三层', 3, true),
    (1021, 102, 'B1', '地下一层', -1, false),
    (1022, 102, 'L1', '一层', 1, true),
    (1023, 102, 'L2', '二层', 2, true),
    (1024, 102, 'L3', '三层', 3, true),
    (1031, 103, 'B1', '地下一层', -1, false),
    (1032, 103, 'L1', '一层', 1, true),
    (1033, 103, 'L2', '二层', 2, true),
    (1034, 103, 'L3', '三层', 3, true)
on conflict (floor_id) do nothing;

insert into dim_brand (
    brand_id,
    brand_code,
    brand_name,
    brand_level,
    business_category,
    sub_business_category,
    origin_type,
    is_local_brand
) values
    (201, 'BR-ENT-001', '星河影院', '主力店', '娱乐', '影院', '全国连锁', false),
    (202, 'BR-FNB-001', '海味食集', '主力店', '餐饮', '正餐', '全国连锁', false),
    (203, 'BR-RTL-001', '都市优选', '主力店', '零售', '精品超市', '全国连锁', false),
    (204, 'BR-SVC-001', '乐活健身', '次主力店', '配套', '健身', '全国连锁', false),
    (205, 'BR-RTL-002', '青木书店', '标杆店', '零售', '文化零售', '区域连锁', true),
    (206, 'BR-FNB-002', '茶语时光', '标杆店', '餐饮', '饮品', '区域连锁', true),
    (207, 'BR-RTL-003', '光感数码', '标杆店', '零售', '数码', '全国连锁', false),
    (208, 'BR-KID-001', '童趣星球', '主力店', '儿童', '亲子娱乐', '区域连锁', true),
    (209, 'BR-SVC-002', '云上美学', '品牌店', '配套', '生活服务', '区域连锁', true),
    (210, 'BR-FNB-003', '川味小馆', '品牌店', '餐饮', '快餐', '区域连锁', true)
on conflict (brand_id) do nothing;

insert into dim_member_level (member_level_id, level_code, level_name, points_threshold, level_rank) values
    (1, 'L1_SILVER', '银卡', 0, 1),
    (2, 'L2_GOLD', '金卡', 3000, 2),
    (3, 'L3_PLATINUM', '铂金卡', 10000, 3),
    (4, 'L4_DIAMOND', '钻石卡', 30000, 4)
on conflict (member_level_id) do nothing;

insert into dim_shop (
    shop_id,
    project_id,
    floor_id,
    shop_code,
    shop_name,
    shop_status,
    gla_area,
    gfa_area,
    business_category,
    sub_business_category,
    lease_type,
    shop_attribute
) values
    (1001, 101, 1011, 'SZ-B1-001', '都市优选生活超市', '在营', 6800.00, 8400.00, '零售', '精品超市', '标准铺', '主力店'),
    (1002, 101, 1012, 'SZ-L1-018', '茶语时光旗舰店', '在营', 180.00, 220.00, '餐饮', '饮品', '标准铺', '街区铺'),
    (1003, 101, 1014, 'SZ-L3-001', '星河影院IMAX', '在营', 5200.00, 6600.00, '娱乐', '影院', '主力铺', '主力店'),
    (1004, 101, 1013, 'SZ-L2-016', '青木书店城市会客厅', '在营', 850.00, 980.00, '零售', '文化零售', '标准铺', '形象店'),
    (1005, 101, 1014, 'SZ-L3-011', '乐活健身能量场', '在营', 2400.00, 2850.00, '配套', '健身', '主力铺', '次主力店'),
    (1006, 101, 1012, 'SZ-L1-029', '海味食集新店', '装修中', 320.00, 380.00, '餐饮', '正餐', '标准铺', '餐饮店'),
    (1007, 102, 1022, 'SH-L1-006', '海味食集花园里店', '在营', 650.00, 760.00, '餐饮', '正餐', '标准铺', '餐饮店'),
    (1008, 102, 1023, 'SH-L2-013', '光感数码体验中心', '在营', 420.00, 500.00, '零售', '数码', '标准铺', '品牌店'),
    (1009, 102, 1024, 'SH-L3-003', '童趣星球探索馆', '在营', 1800.00, 2200.00, '儿童', '亲子娱乐', '主力铺', '主力店'),
    (1010, 102, 1023, 'SH-L2-021', '云上美学生活馆', '在营', 260.00, 310.00, '配套', '生活服务', '标准铺', '服务店'),
    (1011, 102, 1022, 'SH-L1-015', '茶语时光轻饮站', '在营', 160.00, 200.00, '餐饮', '饮品', '标准铺', '餐饮店'),
    (1012, 102, 1021, 'SH-B1-010', '川味小馆原店', '空铺', 280.00, 340.00, '餐饮', '快餐', '标准铺', '餐饮店'),
    (1013, 103, 1031, 'CD-B1-001', '都市优选城南店', '在营', 5200.00, 6500.00, '零售', '精品超市', '主力铺', '主力店'),
    (1014, 103, 1032, 'CD-L1-009', '川味小馆城南店', '在营', 220.00, 260.00, '餐饮', '快餐', '标准铺', '餐饮店'),
    (1015, 103, 1033, 'CD-L2-008', '青木书店城南店', '在营', 700.00, 820.00, '零售', '文化零售', '标准铺', '品牌店'),
    (1016, 103, 1034, 'CD-L3-002', '乐活健身城南店', '在营', 2100.00, 2550.00, '配套', '健身', '主力铺', '次主力店'),
    (1017, 103, 1034, 'CD-L3-006', '童趣星球成长馆', '装修中', 1500.00, 1800.00, '儿童', '亲子娱乐', '主力铺', '主力店'),
    (1018, 103, 1033, 'CD-L2-019', '预留招商铺位', '空铺', 300.00, 360.00, '零售', '潮流零售', '标准铺', '招商储备')
on conflict (shop_id) do nothing;

insert into dim_campaign (
    campaign_id,
    campaign_code,
    campaign_name,
    project_id,
    campaign_type,
    start_date,
    end_date,
    budget_amount,
    status
) values
    (401, 'CMP-SZ-202402', '新春焕新季', 101, '节庆营销', date '2024-02-01', date '2024-02-29', 600000.00, '已结束'),
    (402, 'CMP-SZ-202407', '夏日餐饮节', 101, '品类营销', date '2024-07-05', date '2024-07-28', 450000.00, '已结束'),
    (403, 'CMP-SH-202406', '618品牌焕新节', 102, '会员营销', date '2024-06-01', date '2024-06-20', 500000.00, '已结束'),
    (404, 'CMP-SH-202410', '国庆会员宠粉季', 102, '节庆营销', date '2024-09-25', date '2024-10-07', 700000.00, '已结束'),
    (405, 'CMP-CD-202407', '亲子欢乐月', 103, '家庭营销', date '2024-07-10', date '2024-08-18', 380000.00, '已结束'),
    (406, 'CMP-CD-202412', '年终答谢季', 103, '会员营销', date '2024-12-01', date '2024-12-31', 550000.00, '已结束')
on conflict (campaign_id) do nothing;

insert into dim_coupon (
    coupon_id,
    campaign_id,
    coupon_code,
    coupon_name,
    coupon_type,
    coupon_amount,
    issue_channel
) values
    (801, 401, 'CPN-SZ-401-A', '50元餐饮券', '代金券', 50.00, '会员中心'),
    (802, 401, 'CPN-SZ-401-B', '100元零售券', '代金券', 100.00, '小程序'),
    (803, 402, 'CPN-SZ-402-A', '30元饮品券', '代金券', 30.00, '停车联动'),
    (804, 403, 'CPN-SH-403-A', '80元零售券', '代金券', 80.00, '会员中心'),
    (805, 404, 'CPN-SH-404-A', '120元餐饮团购券', '团购券', 120.00, '小程序'),
    (806, 404, 'CPN-SH-404-B', '50元停车券', '停车券', 50.00, '停车系统'),
    (807, 405, 'CPN-CD-405-A', '60元亲子体验券', '体验券', 60.00, '会员中心'),
    (808, 406, 'CPN-CD-406-A', '100元跨店礼券', '代金券', 100.00, '小程序')
on conflict (coupon_id) do nothing;

insert into dim_marketing_channel (channel_id, channel_code, channel_name, channel_group, is_online) values
    (1, 'CH_WECHAT', '微信公众号', '私域', true),
    (2, 'CH_MINIPROG', '小程序', '私域', true),
    (3, 'CH_DOUYIN', '抖音投放', '公域', true),
    (4, 'CH_OUTDOOR', '户外广告', '线下', false),
    (5, 'CH_MALL_SCENE', '场内资源位', '线下', false),
    (6, 'CH_COMMUNITY', '社群运营', '私域', true)
on conflict (channel_id) do nothing;

insert into dim_area (
    area_id,
    project_id,
    floor_code,
    area_code,
    area_name,
    area_type,
    managed_area
) values
    (10011, 101, 'B1', 'SZ-B1-PUB', 'B1公共区', 'public_area', 8200.00),
    (10012, 101, 'L1', 'SZ-L1-AT', 'L1中庭', 'atrium', 3600.00),
    (10013, 101, 'L2', 'SZ-L2-COR', 'L2走廊区', 'corridor', 5100.00),
    (10014, 101, 'L3', 'SZ-L3-PLANT', 'L3机房区', 'plant_room', 1800.00),
    (10021, 102, 'B1', 'SH-B1-PUB', 'B1公共区', 'public_area', 7600.00),
    (10022, 102, 'L1', 'SH-L1-AT', 'L1中庭', 'atrium', 3200.00),
    (10023, 102, 'L2', 'SH-L2-COR', 'L2走廊区', 'corridor', 4700.00),
    (10024, 102, 'L3', 'SH-L3-PLANT', 'L3机房区', 'plant_room', 1600.00),
    (10031, 103, 'B1', 'CD-B1-PUB', 'B1公共区', 'public_area', 6900.00),
    (10032, 103, 'L1', 'CD-L1-AT', 'L1中庭', 'atrium', 2900.00),
    (10033, 103, 'L2', 'CD-L2-COR', 'L2走廊区', 'corridor', 4300.00),
    (10034, 103, 'L3', 'CD-L3-PLANT', 'L3机房区', 'plant_room', 1500.00)
on conflict (area_id) do nothing;

insert into dim_equipment_system (
    system_id,
    system_code,
    system_name,
    engineering_domain
) values
    (1, 'HVAC', '暖通空调系统', '机电'),
    (2, 'ELEC', '供配电系统', '机电'),
    (3, 'LIFT', '电扶梯系统', '垂直交通'),
    (4, 'FIRE', '消防系统', '安全'),
    (5, 'WATER', '给排水系统', '机电'),
    (6, 'PARK', '停车管理系统', '停车')
on conflict (system_id) do nothing;

insert into dim_vendor (
    vendor_id,
    vendor_code,
    vendor_name,
    vendor_type,
    service_scope
) values
    (1, 'VND-HVAC', '华南暖通维保有限公司', '维保单位', '暖通与冷站'),
    (2, 'VND-ELEC', '城光机电服务有限公司', '维保单位', '配电与照明'),
    (3, 'VND-LIFT', '通达电梯服务有限公司', '维保单位', '电梯与扶梯'),
    (4, 'VND-PROP', '万象物业服务有限公司', '物业服务', '保洁安保客服'),
    (5, 'VND-PARK', '智行停车科技有限公司', '系统服务', '停车系统')
on conflict (vendor_id) do nothing;

insert into dim_equipment (
    equipment_id,
    project_id,
    area_id,
    system_id,
    vendor_id,
    equipment_code,
    equipment_name,
    equipment_type,
    brand_name,
    install_date,
    warranty_end_date,
    critical_flag,
    asset_status
) values
    (20001, 101, 10014, 1, 1, 'EQ-SZ-HVAC-01', '1号冷水机组', '冷机', '开利', date '2021-07-01', date '2024-06-30', true, 'running'),
    (20002, 101, 10014, 2, 2, 'EQ-SZ-ELEC-01', '1号高压配电柜', '配电柜', '施耐德', date '2021-07-10', date '2024-07-09', true, 'running'),
    (20003, 101, 10011, 3, 3, 'EQ-SZ-LIFT-01', '中庭扶梯A', '扶梯', '三菱', date '2021-08-01', date '2024-07-31', false, 'running'),
    (20004, 101, 10011, 4, 2, 'EQ-SZ-FIRE-01', '消防报警主机', '消防主机', '海湾', date '2021-08-15', date '2024-08-14', true, 'running'),
    (20005, 102, 10024, 1, 1, 'EQ-SH-HVAC-01', '2号冷水机组', '冷机', '约克', date '2022-03-01', date '2025-02-28', true, 'running'),
    (20006, 102, 10024, 2, 2, 'EQ-SH-ELEC-01', '2号高压配电柜', '配电柜', 'ABB', date '2022-03-12', date '2025-03-11', true, 'running'),
    (20007, 102, 10021, 6, 5, 'EQ-SH-PARK-01', '停车道闸控制器', '停车控制器', '捷顺', date '2022-04-01', date '2025-03-31', false, 'running'),
    (20008, 102, 10021, 3, 3, 'EQ-SH-LIFT-01', 'B1-L1客梯A', '客梯', '日立', date '2022-04-15', date '2025-04-14', false, 'running'),
    (20009, 103, 10034, 1, 1, 'EQ-CD-HVAC-01', '3号冷水机组', '冷机', '麦克维尔', date '2023-09-01', date '2026-08-31', true, 'running'),
    (20010, 103, 10034, 2, 2, 'EQ-CD-ELEC-01', '3号低压配电柜', '配电柜', '西门子', date '2023-09-18', date '2026-09-17', true, 'running'),
    (20011, 103, 10031, 4, 2, 'EQ-CD-FIRE-01', '消防喷淋控制柜', '消防控制柜', '赋安', date '2023-10-01', date '2026-09-30', true, 'running'),
    (20012, 103, 10031, 6, 5, 'EQ-CD-PARK-01', '停车识别控制器', '停车控制器', '科拓', date '2023-10-12', date '2026-10-11', false, 'running')
on conflict (equipment_id) do nothing;

insert into dim_work_order_type (
    work_order_type_id,
    type_code,
    type_name,
    major_category,
    sla_minutes
) values
    (1, 'WO_HVAC', '暖通维修', '工程', 90),
    (2, 'WO_ELEC', '供配电维修', '工程', 60),
    (3, 'WO_LIFT', '电梯扶梯维修', '工程', 45),
    (4, 'WO_FIRE', '消防整改', '安全', 30),
    (5, 'WO_CLEAN', '保洁服务', '物业', 120),
    (6, 'WO_PARK', '停车服务', '物业', 30),
    (7, 'WO_ENV', '环境整治', '物业', 180)
on conflict (work_order_type_id) do nothing;

insert into dim_complaint_type (
    complaint_type_id,
    type_code,
    type_name,
    complaint_domain
) values
    (1, 'CP_CLEAN', '保洁投诉', '服务'),
    (2, 'CP_PARK', '停车投诉', '服务'),
    (3, 'CP_TEMP', '温控投诉', '设施'),
    (4, 'CP_ESC', '扶梯投诉', '设施'),
    (5, 'CP_SECURITY', '安保投诉', '安全')
on conflict (complaint_type_id) do nothing;

insert into dim_fee_subject (subject_id, subject_code, subject_name, subject_category, display_order) values
    (1, 'RENT', '租金', '租赁收入', 1),
    (2, 'PROPERTY', '物业费', '租赁收入', 2),
    (3, 'MULTI', '多经', '租赁收入', 3),
    (4, 'ADVERTISING', '广告位', '租赁收入', 4),
    (5, 'PARKING', '停车', '其他收入', 5),
    (6, 'OTHER', '其他', '其他收入', 6)
on conflict (subject_id) do nothing;

insert into dim_indicator_catalog (
    indicator_id,
    indicator_code,
    theme_name,
    category_name,
    indicator_name,
    indicator_unit,
    source_sheet_name,
    grain_suggestion,
    mapped_object_name,
    definition,
    formula
) values
    (1, 'CRE-LS10001', '招商', '01 项目基础信息', '开业时间', null, '2.4 招商主题指标标准', '项目', 'dim_project.opening_date', '项目开业日期', '直接取数，格式YYYY-MM-DD'),
    (2, 'CRE-LS10003', '招商', '01 项目基础信息', '店铺总数', null, '2.4 招商主题指标标准', '项目/日', 'vw_leasing_daily_kpi.total_shop_count', '各状态下的店铺和铺位数量加总', '统计项目日店铺总量'),
    (3, 'CRE-LS10004', '招商', '01 项目基础信息', '总租赁面积', '平方米', '2.4 招商主题指标标准', '项目', 'dim_project.rentable_area', '选定时间点在铺位有效期内，铺位的GLA之和', '项目可租赁面积'),
    (4, 'CRE-LS10010', '招商', '04 销售租金管理', '销售金额', '元', '2.4 招商主题指标标准', '项目/店铺/日', 'fact_shop_daily_operation.sales_amount', '期间内门店店铺的销售总额', '期间内每日销售金额加总'),
    (5, 'CRE-LS10011', '招商', '04 销售租金管理', '销售坪效', '元/平方米', '2.4 招商主题指标标准', '项目/日', 'vw_leasing_daily_kpi.sales_per_sqm', '选定期间内店铺单位经营面积销售产出', '销售金额/经营面积'),
    (6, 'CRE-LS10012', '招商', '04 销售租金管理', '固定租金单价', '元/平方米', '2.4 招商主题指标标准', '项目/日', 'vw_leasing_daily_kpi.avg_fixed_rent_unit_price', '期间内店铺每平米固定租金金额按经营月份加权', '固定租金/月租赁面积'),
    (7, 'CRE-LS10018', '招商', '02 招商进度管理', '在营店铺数量', '家', '2.4 招商主题指标标准', '项目/日', 'vw_leasing_daily_kpi.operating_shop_count', '查询日期为在营状态的店铺数量', '按日统计状态为 operating 的店铺'),
    (8, 'CRE-LS10024', '招商', '02 招商进度管理', '空铺状态店铺数量', '家', '2.4 招商主题指标标准', '项目/日', 'vw_leasing_daily_kpi.vacant_shop_count', '查询日期为空铺状态的店铺数量', '按日统计状态为 vacant 的店铺'),
    (9, 'CRE-OP1003', '营运', '基础信息', '已出租面积', '平方米', '2.5 营运主题指标标准', '项目/日', 'vw_leasing_daily_kpi.leased_gla_area', '项目上已出租的铺位面积', '已签约、已接场、在营面积汇总'),
    (10, 'CRE-OP1004', '营运', '基础信息', '开业租户数', '家', '2.5 营运主题指标标准', '项目/日', 'vw_leasing_daily_kpi.operating_shop_count', '已开业的店铺数量', '按日统计状态为 operating 的店铺'),
    (11, 'CRE-OP1006', '营运', '基础信息', '出租面积开业率', '%', '2.5 营运主题指标标准', '项目/月', 'fact_finance_monthly.opening_rate', '项目上已出租面积中开业面积所占比例', '开业面积/已出租面积'),
    (12, 'CRE-OP1009', '营运', '基础信息', '营销活动数量', '次', '2.5 营运主题指标标准', '项目/日', 'vw_campaign_daily_kpi.active_campaign_count', '项目活动的数量', '按日统计活动数'),
    (13, 'CRE-OP1010', '营运', '基础信息', '月坪效', '万元/坪', '2.5 营运主题指标标准', '项目/月', 'vw_project_monthly_kpi.operating_sales_amount', '平均每平米的销售额', '月销售额/平均经营面积'),
    (14, 'CRE-OP1016', '营运', '运营情况', '客单价', '元', '2.5 营运主题指标标准', '项目/日', 'vw_project_daily_kpi.avg_ticket_amount', '每单平均销售额', '销售额/销售单量'),
    (15, 'CRE-OP1023', '营运', '运营情况', '经营面积', '平方米', '2.5 营运主题指标标准', '项目/日', 'vw_project_daily_kpi.opened_area', '项目经营中的面积', '状态为 operating 的面积'),
    (16, 'CRE-OP1024', '营运', '运营情况', '销售额', '万元', '2.5 营运主题指标标准', '项目/日', 'vw_project_daily_kpi.sales_amount', '项目经营销售额', '店铺日销售汇总'),
    (17, 'CRE-TC10003', 'TC', '01 装修效率', '装修店铺数量', '家', '2.6 TC主题指标标准', '项目', 'vw_tc_project_kpi.fitout_shop_count', '处于装修状态中的铺位总数', '统计 tc_status=fitout 的铺位'),
    (18, 'CRE-TC10004', 'TC', '01 装修效率', '装修店铺面积', '平方米', '2.6 TC主题指标标准', '项目', 'vw_tc_project_kpi.fitout_gla_area', '处于装修状态中的店铺面积', '统计 tc_status=fitout 的铺位面积'),
    (19, 'CRE-TC10011', 'TC', '01 装修效率', '接场店铺数量占比', '%', '2.6 TC主题指标标准', '项目', 'vw_tc_project_kpi.handover_shop_rate', '接场店铺/店铺总数', '已接场店铺数/TC 店铺总数'),
    (20, 'CRE-TC10017', 'TC', '01 装修效率', '开业店铺数量占比', '%', '2.6 TC主题指标标准', '项目', 'vw_tc_project_kpi.opened_shop_rate', '开业店铺/店铺总数', '已开业店铺数/TC 店铺总数'),
    (21, 'CRE-TC10025', 'TC', '03 移交效率', '招商预移交店铺数', '家', '2.6 TC主题指标标准', '项目', 'vw_tc_project_kpi.planned_handover_shop_count', '进入预移交计划的店铺数', '维护 planned_handover_date 的店铺数量'),
    (22, 'CRE-TC10026', 'TC', '03 移交效率', '招商移交店铺数', '家', '2.6 TC主题指标标准', '项目', 'vw_tc_project_kpi.handover_shop_count', '已完成移交的店铺数', '维护 actual_handover_date 的店铺'),
    (23, 'CRE-CM1001', '会员', '会员信息', '新增会员人数', '人', '2.7 会员主题指标标准', '项目/日', 'vw_member_daily_kpi.new_members', '历年的注册会员数量增量', '按日新增会员'),
    (24, 'CRE-CM1004', '会员', '会员信息', '流失会员数量', '人', '2.7 会员主题指标标准', '项目/日', 'vw_member_daily_kpi.lost_members', '流失会员数', '按日流失会员'),
    (25, 'CRE-CM1008', '会员', '会员信息', '活跃会员率', '%', '2.7 会员主题指标标准', '项目/日', 'vw_member_daily_kpi.active_member_rate', '消费日期在近一年内的消费会员数量/所有会员数量', '活跃会员/有效会员'),
    (26, 'CRE-CM1010', '会员', '会员信息', '会员保留率', '%', '2.7 会员主题指标标准', '项目/日', 'fact_member_daily.retention_rate', '期初会员在统计期内仍有活跃行为的占比', '由会员日事实直接维护'),
    (27, 'CRE-CM1011', '会员', '会员信息', '会员总量', '人', '2.7 会员主题指标标准', '项目/日', 'vw_member_daily_kpi.total_members', '会员总量', '各等级会员总量汇总'),
    (28, 'CRE-CM1024', '会员', '会员消费行为', '会员消费占全场销售的比例', '%', '2.7 会员主题指标标准', '项目/日', 'vw_member_daily_kpi.member_sales_ratio', '会员消费金额/全场销售金额', '会员销售额/项目销售额'),
    (29, 'CRE-MT1002', '活动', '卡券分析', '投放数量', '张', '2.8 活动主题指标标准', '项目/日', 'vw_campaign_daily_kpi.coupon_issue_qty', '投放的卡券数量', '按活动日投放总数'),
    (30, 'CRE-MT1004', '活动', '卡券分析', '实际核销总张数', '张', '2.8 活动主题指标标准', '项目/日', 'vw_campaign_daily_kpi.coupon_redeemed_qty', '已核销卡券张数', '按活动日核销总张数'),
    (31, 'CRE-MT1005', '活动', '卡券分析', '已核销总金额', '元', '2.8 活动主题指标标准', '项目/日', 'vw_campaign_daily_kpi.coupon_redeemed_amount', '已核销卡券金额', '核销张数*券额'),
    (32, 'CRE-MT1009', '活动', '卡券分析', '失效总张数', '张', '2.8 活动主题指标标准', '项目/日', 'vw_campaign_daily_kpi.coupon_expired_qty', '失效卡券数量', '活动结束未使用卡券数量'),
    (33, 'CRE-MT1015', '活动', '卡券分析', '活动期间消费笔数', '笔', '2.8 活动主题指标标准', '项目/日', 'vw_campaign_daily_kpi.campaign_order_qty', '活动期间参与订单笔数', '活动带动订单数'),
    (34, 'CRE-MT1016', '活动', '卡券分析', '活动期间销售金额', '元', '2.8 活动主题指标标准', '项目/日', 'vw_campaign_daily_kpi.induced_sales_amount', '活动期间销售金额', '活动带动销售额'),
    (35, 'GRP-FI-001', '财务', '收缴分析', '租金收缴率', '%', '1_集团BI数据分析 指标及模型1205.pdf', '项目/月', 'vw_finance_monthly_kpi.collection_rate', '租金收缴率=实收租金/应收租金', 'received_by_month_end_amount/receivable_amount'),
    (36, 'GRP-FI-002', '财务', '收缴分析', '物业费收缴率', '%', '1_集团BI数据分析 指标及模型1205.pdf', '项目/月/科目', 'vw_finance_collection_by_subject.subject_collection_rate', '物业费收缴率=实收物业费/应收物业费', '按物业费科目汇总实收与应收'),
    (37, 'GRP-FI-003', '财务', '收缴分析', '客户收缴率', '%', '上海江桥万达月报0509.pptx', '项目/月/客户', 'vw_finance_collection_by_customer.customer_collection_rate', '客户收缴率=客户累计实收/客户累计应收', '按客户汇总实收与应收'),
    (38, 'GRP-FI-004', '财务', '收缴分析', '科目收缴率', '%', '上海江桥万达月报0509.pptx', '项目/月/科目', 'vw_finance_collection_by_subject.subject_collection_rate', '科目收缴率=科目实收/科目应收', '按租金、物业费、多经等科目统计'),
    (39, 'GRP-FI-005', '财务', '收缴分析', '账单应收金额', '元', '上海江桥万达月报0509.pptx', '项目/月', 'vw_finance_monthly_kpi.receivable_amount', '账单应收金额', '项目月账单应收汇总'),
    (40, 'GRP-FI-006', '财务', '收缴分析', '账单实际收款金额', '元', '上海江桥万达月报0509.pptx', '项目/月', 'vw_finance_monthly_kpi.received_by_month_end_amount', '账单实际收款金额', '截至月末针对本月账单的实收金额'),
    (41, 'GRP-FI-007', '财务', '账龄分析', '账龄余额', '元', '集团月报 .xlsx-9.基础表-欠缴租金', '项目/月/账龄', 'vw_finance_ar_aging.outstanding_amount', '账龄余额', '按账龄桶汇总未收余额'),
    (42, 'GRP-FI-008', '财务', '预算分析', '总租金指标完成率', '%', '上海江桥万达月报0509.pptx', '项目/月', 'vw_finance_monthly_kpi.budget_completion_rate', '总租金指标完成率', 'actual_received_in_month_amount/budget_amount'),
    (43, 'GRP-FI-009', '财务', '预算分析', '月度实收金额', '元', '集团月报 .xlsx-5.基础表-租金类', '项目/月', 'vw_finance_monthly_kpi.actual_received_in_month_amount', '当月实际收款金额', '按收款日期归属到当月的实收金额'),
    (44, 'GRP-FI-010', '财务', '预算分析', '月末未收金额', '元', '集团月报 .xlsx-9.基础表-欠缴租金', '项目/月', 'vw_finance_monthly_kpi.outstanding_amount', '截至月末未收金额', '应收金额-截至月末已收金额'),
    (45, 'GRP-FI-011', '财务', '租赁收入分析', '租金坪效', '元/平方米/月', '1_集团BI数据分析 指标及模型1205.pdf', '项目/月', '辅助计算: vw_finance_monthly_kpi.rent_received_amount / vw_project_monthly_kpi.avg_opened_area', '租金坪效=实收月租金收入/租户计租面积', '结合租金实收和经营面积进行分析'),
    (46, 'GRP-FI-012', '财务', '租赁收入分析', '租售比', '%', '1_集团BI数据分析 指标及模型1205.pdf', '项目/月', '辅助计算: (vw_finance_monthly_kpi.rent_received_amount + vw_finance_monthly_kpi.property_received_amount) / vw_project_monthly_kpi.operating_sales_amount', '租售比=(月租金收入+月物业费收入)/租户月销售额', '租金收入与销售表现联动分析'),
    (47, 'MKT-ROI-001', '企划', '活动 ROI', '活动预算执行率', '%', '商业地产看板规划清单.md', '活动', 'vw_campaign_roi_summary.budget_execution_rate', '活动实际花费相对预算的执行比例', 'actual_spend_amount/budget_amount'),
    (48, 'MKT-ROI-002', '企划', '活动 ROI', '活动销售 ROI', '倍', '商业地产看板规划清单.md', '活动', 'vw_campaign_roi_summary.sales_roi', '活动带动销售额与活动实际成本的比值', 'induced_sales_amount/actual_spend_amount'),
    (49, 'MKT-ROI-003', '企划', '活动 ROI', '活动新增会员数', '人', '商业地产看板规划清单.md', '活动', 'vw_campaign_roi_summary.new_members', '活动期间新增会员数', '活动期间新增会员加总'),
    (50, 'MKT-ROI-004', '企划', '活动 ROI', '活动到访人数', '人', '商业地产看板规划清单.md', '活动', 'vw_campaign_roi_summary.activity_visitors', '活动期间到访人次', '活动期间活动到访人数加总'),
    (51, 'MKT-ROI-005', '企划', '渠道投放', '渠道点击率', '%', '商业地产看板规划清单.md', '活动/渠道/日', 'vw_campaign_channel_performance.click_through_rate', '点击率=点击量/曝光量', 'click_count/exposure_count'),
    (52, 'MKT-ROI-006', '企划', '渠道投放', '单会员获客成本', '元/人', '商业地产看板规划清单.md', '活动', 'vw_campaign_roi_summary.cost_per_new_member', '活动成本/活动新增会员数', 'actual_spend_amount/new_members')
on conflict (indicator_id) do nothing;

insert into fact_leasing_contract (
    contract_id,
    project_id,
    shop_id,
    brand_id,
    contract_no,
    contract_status,
    cooperation_mode,
    rent_type,
    payment_cycle,
    sign_date,
    lease_start_date,
    lease_end_date,
    handover_date,
    opening_date,
    closing_date,
    rent_area,
    fixed_rent_monthly,
    commission_rate,
    deposit_amount,
    sales_target_monthly,
    brand_category,
    brand_sub_category
) values
    (5001, 101, 1001, 203, 'HT-SZ-2023-001', 'operating', '联营', 'fixed_plus_commission', 'monthly', date '2023-08-01', date '2023-09-01', date '2028-08-31', date '2023-08-15', date '2023-09-29', null, 6800.00, 980000.00, 0.0180, 1960000.00, 1750000.00, '零售', '精品超市'),
    (5002, 101, 1002, 206, 'HT-SZ-2024-006', 'operating', '纯租赁', 'fixed', 'monthly', date '2024-02-15', date '2024-03-01', date '2027-02-28', date '2024-03-05', date '2024-03-10', null, 180.00, 52000.00, 0.0000, 104000.00, 280000.00, '餐饮', '饮品'),
    (5003, 101, 1003, 201, 'HT-SZ-2023-003', 'operating', '联营', 'fixed_plus_commission', 'monthly', date '2023-10-01', date '2023-11-01', date '2029-10-31', date '2023-10-20', date '2023-12-20', null, 5200.00, 760000.00, 0.0320, 1520000.00, 1450000.00, '娱乐', '影院'),
    (5004, 101, 1004, 205, 'HT-SZ-2024-011', 'operating', '纯租赁', 'fixed', 'quarterly', date '2024-03-20', date '2024-04-01', date '2028-03-31', date '2024-04-06', date '2024-04-26', null, 850.00, 148000.00, 0.0000, 296000.00, 360000.00, '零售', '文化零售'),
    (5005, 101, 1005, 204, 'HT-SZ-2024-018', 'operating', '纯租赁', 'fixed', 'monthly', date '2024-05-10', date '2024-06-01', date '2029-05-31', date '2024-06-05', date '2024-06-30', null, 2400.00, 280000.00, 0.0000, 560000.00, 420000.00, '配套', '健身'),
    (5006, 101, 1006, 202, 'HT-SZ-2024-022', 'fitout', '联营', 'fixed_plus_commission', 'monthly', date '2024-09-15', date '2024-10-01', date '2028-09-30', date '2024-10-10', null, null, 320.00, 86000.00, 0.0450, 172000.00, 350000.00, '餐饮', '正餐'),
    (5007, 102, 1007, 202, 'HT-SH-2023-002', 'operating', '联营', 'fixed_plus_commission', 'monthly', date '2023-12-15', date '2024-01-01', date '2028-12-31', date '2024-01-05', date '2024-01-28', null, 650.00, 132000.00, 0.0400, 264000.00, 520000.00, '餐饮', '正餐'),
    (5008, 102, 1008, 207, 'HT-SH-2024-005', 'operating', '纯租赁', 'fixed', 'monthly', date '2024-02-20', date '2024-03-01', date '2027-02-28', date '2024-03-03', date '2024-03-25', null, 420.00, 98000.00, 0.0000, 196000.00, 360000.00, '零售', '数码'),
    (5009, 102, 1009, 208, 'HT-SH-2024-013', 'operating', '联营', 'fixed_plus_commission', 'monthly', date '2024-04-26', date '2024-05-01', date '2028-04-30', date '2024-05-08', date '2024-05-30', null, 1800.00, 240000.00, 0.0280, 480000.00, 620000.00, '儿童', '亲子娱乐'),
    (5010, 102, 1010, 209, 'HT-SH-2024-003', 'operating', '纯租赁', 'fixed', 'monthly', date '2024-01-15', date '2024-02-01', date '2026-01-31', date '2024-02-03', date '2024-02-18', null, 260.00, 42000.00, 0.0000, 84000.00, 120000.00, '配套', '生活服务'),
    (5011, 102, 1011, 206, 'HT-SH-2024-021', 'operating', '纯租赁', 'fixed', 'monthly', date '2024-06-12', date '2024-07-01', date '2027-06-30', date '2024-07-03', date '2024-07-12', null, 160.00, 45000.00, 0.0000, 90000.00, 220000.00, '餐饮', '饮品'),
    (5012, 102, 1012, 210, 'HT-SH-2024-007', 'terminated', '纯租赁', 'fixed', 'monthly', date '2024-01-03', date '2024-02-01', date '2024-08-31', date '2024-02-05', date '2024-03-01', date '2024-08-20', 280.00, 56000.00, 0.0000, 112000.00, 180000.00, '餐饮', '快餐'),
    (5013, 103, 1013, 203, 'HT-CD-2023-001', 'operating', '联营', 'fixed_plus_commission', 'monthly', date '2023-11-20', date '2024-01-01', date '2028-12-31', date '2024-01-03', date '2024-01-20', null, 5200.00, 720000.00, 0.0160, 1440000.00, 1320000.00, '零售', '精品超市'),
    (5014, 103, 1014, 210, 'HT-CD-2024-004', 'operating', '联营', 'fixed_plus_commission', 'monthly', date '2024-01-20', date '2024-02-01', date '2027-01-31', date '2024-02-02', date '2024-02-22', null, 220.00, 46000.00, 0.0350, 92000.00, 210000.00, '餐饮', '快餐'),
    (5015, 103, 1015, 205, 'HT-CD-2024-009', 'operating', '纯租赁', 'fixed', 'quarterly', date '2024-03-28', date '2024-04-15', date '2028-04-14', date '2024-04-18', date '2024-05-01', null, 700.00, 126000.00, 0.0000, 252000.00, 250000.00, '零售', '文化零售'),
    (5016, 103, 1016, 204, 'HT-CD-2024-015', 'operating', '纯租赁', 'fixed', 'monthly', date '2024-05-18', date '2024-06-01', date '2029-05-31', date '2024-06-04', date '2024-06-25', null, 2100.00, 250000.00, 0.0000, 500000.00, 330000.00, '配套', '健身'),
    (5017, 103, 1017, 208, 'HT-CD-2024-024', 'fitout', '联营', 'fixed_plus_commission', 'monthly', date '2024-11-01', date '2024-11-15', date '2028-11-14', date '2024-11-20', null, null, 1500.00, 188000.00, 0.0260, 376000.00, 480000.00, '儿童', '亲子娱乐')
on conflict (contract_id) do nothing;

insert into dim_tenant_customer (
    customer_id,
    customer_code,
    customer_name,
    customer_type,
    industry_category,
    project_id,
    brand_id,
    contract_id,
    active_flag
) values
    (9001, 'CUST-SZ-203', '都市优选商业管理有限公司', '租户', '精品超市', 101, 203, 5001, true),
    (9002, 'CUST-SZ-206', '茶语时光餐饮管理有限公司', '租户', '饮品', 101, 206, 5002, true),
    (9003, 'CUST-SZ-201', '星河影院投资有限公司', '租户', '影院', 101, 201, 5003, true),
    (9004, 'CUST-SZ-205', '青木书店文化发展有限公司', '租户', '文化零售', 101, 205, 5004, true),
    (9005, 'CUST-SZ-204', '乐活健身服务有限公司', '租户', '健身', 101, 204, 5005, true),
    (9006, 'CUST-SZ-202', '海味食集餐饮管理有限公司', '租户', '正餐', 101, 202, 5006, true),
    (9007, 'CUST-SH-202', '海味食集上海有限公司', '租户', '正餐', 102, 202, 5007, true),
    (9008, 'CUST-SH-207', '光感数码科技有限公司', '租户', '数码', 102, 207, 5008, true),
    (9009, 'CUST-SH-208', '童趣星球文旅有限公司', '租户', '亲子娱乐', 102, 208, 5009, true),
    (9010, 'CUST-SH-209', '云上美学生活服务有限公司', '租户', '生活服务', 102, 209, 5010, true),
    (9011, 'CUST-SH-206', '茶语时光上海餐饮有限公司', '租户', '饮品', 102, 206, 5011, true),
    (9012, 'CUST-SH-210', '川味小馆餐饮有限公司', '租户', '快餐', 102, 210, 5012, false),
    (9013, 'CUST-CD-203', '都市优选成都商业有限公司', '租户', '精品超市', 103, 203, 5013, true),
    (9014, 'CUST-CD-210', '川味小馆成都餐饮有限公司', '租户', '快餐', 103, 210, 5014, true),
    (9015, 'CUST-CD-205', '青木书店成都文化有限公司', '租户', '文化零售', 103, 205, 5015, true),
    (9016, 'CUST-CD-204', '乐活健身成都有限公司', '租户', '健身', 103, 204, 5016, true),
    (9017, 'CUST-CD-208', '童趣星球成都文旅有限公司', '租户', '亲子娱乐', 103, 208, 5017, true)
on conflict (customer_id) do nothing;

insert into fact_tc_process (
    tc_id,
    project_id,
    shop_id,
    brand_id,
    contract_id,
    tc_status,
    planned_handover_date,
    actual_handover_date,
    design_submission_date,
    drawing_submission_date,
    entry_date,
    acceptance_date,
    planned_open_date,
    actual_open_date,
    exit_notice_date,
    actual_close_date,
    vacancy_days,
    fitout_days
) values
    (6001, 101, 1001, 203, 5001, 'operating', date '2023-08-10', date '2023-08-15', date '2023-08-05', date '2023-08-10', date '2023-08-16', date '2023-09-20', date '2023-09-30', date '2023-09-29', null, null, 0, 45),
    (6002, 101, 1002, 206, 5002, 'operating', date '2024-03-03', date '2024-03-05', date '2024-02-22', date '2024-02-28', date '2024-03-06', date '2024-03-09', date '2024-03-15', date '2024-03-10', null, null, 0, 5),
    (6003, 101, 1003, 201, 5003, 'operating', date '2023-10-15', date '2023-10-20', date '2023-10-05', date '2023-10-12', date '2023-10-21', date '2023-12-10', date '2023-12-25', date '2023-12-20', null, null, 0, 61),
    (6004, 101, 1004, 205, 5004, 'operating', date '2024-04-05', date '2024-04-06', date '2024-03-25', date '2024-03-30', date '2024-04-07', date '2024-04-22', date '2024-04-30', date '2024-04-26', null, null, 0, 20),
    (6005, 101, 1005, 204, 5005, 'operating', date '2024-06-05', date '2024-06-05', date '2024-05-20', date '2024-05-28', date '2024-06-06', date '2024-06-26', date '2024-06-30', date '2024-06-30', null, null, 0, 25),
    (6006, 101, 1006, 202, 5006, 'fitout', date '2024-10-08', date '2024-10-10', date '2024-09-22', date '2024-10-02', date '2024-10-12', null, date '2025-01-20', null, null, null, 0, 82),
    (6007, 102, 1007, 202, 5007, 'operating', date '2024-01-03', date '2024-01-05', date '2023-12-22', date '2023-12-28', date '2024-01-06', date '2024-01-25', date '2024-01-30', date '2024-01-28', null, null, 0, 23),
    (6008, 102, 1008, 207, 5008, 'operating', date '2024-03-02', date '2024-03-03', date '2024-02-21', date '2024-02-27', date '2024-03-04', date '2024-03-20', date '2024-03-28', date '2024-03-25', null, null, 0, 22),
    (6009, 102, 1009, 208, 5009, 'operating', date '2024-05-06', date '2024-05-08', date '2024-04-30', date '2024-05-03', date '2024-05-09', date '2024-05-26', date '2024-06-01', date '2024-05-30', null, null, 0, 22),
    (6010, 102, 1010, 209, 5010, 'operating', date '2024-02-03', date '2024-02-03', date '2024-01-18', date '2024-01-24', date '2024-02-04', date '2024-02-15', date '2024-02-20', date '2024-02-18', null, null, 0, 15),
    (6011, 102, 1011, 206, 5011, 'operating', date '2024-07-02', date '2024-07-03', date '2024-06-20', date '2024-06-25', date '2024-07-04', date '2024-07-10', date '2024-07-15', date '2024-07-12', null, null, 0, 9),
    (6012, 102, 1012, 210, 5012, 'exit', date '2024-02-03', date '2024-02-05', date '2024-01-15', date '2024-01-22', date '2024-02-06', date '2024-02-25', date '2024-03-05', date '2024-03-01', date '2024-07-25', date '2024-08-20', 41, 25),
    (6013, 103, 1013, 203, 5013, 'operating', date '2024-01-02', date '2024-01-03', date '2023-12-12', date '2023-12-18', date '2024-01-04', date '2024-01-18', date '2024-01-22', date '2024-01-20', null, null, 0, 17),
    (6014, 103, 1014, 210, 5014, 'operating', date '2024-02-01', date '2024-02-02', date '2024-01-20', date '2024-01-26', date '2024-02-03', date '2024-02-18', date '2024-02-25', date '2024-02-22', null, null, 0, 20),
    (6015, 103, 1015, 205, 5015, 'operating', date '2024-04-18', date '2024-04-18', date '2024-04-02', date '2024-04-09', date '2024-04-19', date '2024-04-29', date '2024-05-05', date '2024-05-01', null, null, 0, 13),
    (6016, 103, 1016, 204, 5016, 'operating', date '2024-06-03', date '2024-06-04', date '2024-05-20', date '2024-05-29', date '2024-06-05', date '2024-06-22', date '2024-06-28', date '2024-06-25', null, null, 0, 21),
    (6017, 103, 1017, 208, 5017, 'fitout', date '2024-11-18', date '2024-11-20', date '2024-11-05', date '2024-11-12', date '2024-11-22', null, date '2025-02-10', null, null, null, 0, 42)
on conflict (tc_id) do nothing;

insert into fact_shop_daily_operation (
    operation_id,
    date_key,
    project_id,
    shop_id,
    brand_id,
    business_status,
    sales_amount,
    sales_orders,
    customer_flow,
    operating_area,
    rent_income,
    management_fee_income,
    active_member_sales,
    coupon_writeoff_amount,
    coupon_writeoff_qty
)
with all_days as (
    select date_key, calendar_date
    from dim_date
    where calendar_date between date '2024-01-01' and date '2024-12-31'
),
shop_contract as (
    select
        s.shop_id,
        s.project_id,
        s.business_category,
        s.sub_business_category,
        coalesce(c.brand_id, null) as brand_id,
        c.lease_start_date,
        c.lease_end_date,
        c.handover_date,
        c.opening_date,
        c.closing_date,
        c.rent_area,
        c.fixed_rent_monthly,
        c.commission_rate
    from dim_shop s
    left join fact_leasing_contract c on c.shop_id = s.shop_id
),
base as (
    select
        (d.date_key::bigint * 10000) + sc.shop_id as operation_id,
        d.date_key,
        d.calendar_date,
        sc.project_id,
        sc.shop_id,
        sc.brand_id,
        sc.business_category,
        sc.sub_business_category,
        coalesce(sc.rent_area, 0) as rent_area,
        coalesce(sc.fixed_rent_monthly, 0) as fixed_rent_monthly,
        coalesce(sc.commission_rate, 0) as commission_rate,
        case
            when sc.lease_start_date is null then 'vacant'
            when d.calendar_date < sc.lease_start_date then 'vacant'
            when d.calendar_date > sc.lease_end_date then 'vacant'
            when sc.closing_date is not null and d.calendar_date >= sc.closing_date then 'closed'
            when sc.handover_date is not null and d.calendar_date < sc.handover_date then 'pre_open'
            when sc.opening_date is null or d.calendar_date < sc.opening_date then 'fitout'
            else 'operating'
        end as business_status,
        case sc.sub_business_category
            when '精品超市' then 52000.00
            when '饮品' then 9800.00
            when '影院' then 42000.00
            when '文化零售' then 12500.00
            when '健身' then 7600.00
            when '正餐' then 21000.00
            when '数码' then 16500.00
            when '亲子娱乐' then 24000.00
            when '生活服务' then 5600.00
            when '快餐' then 11800.00
            else 6800.00
        end as base_sales,
        case sc.sub_business_category
            when '精品超市' then 1650
            when '饮品' then 320
            when '影院' then 980
            when '文化零售' then 260
            when '健身' then 150
            when '正餐' then 540
            when '数码' then 190
            when '亲子娱乐' then 620
            when '生活服务' then 110
            when '快餐' then 360
            else 160
        end as base_flow
    from all_days d
    cross join shop_contract sc
),
calc as (
    select
        operation_id,
        date_key,
        project_id,
        shop_id,
        brand_id,
        business_status,
        case
            when business_status <> 'operating' then 0::numeric
            else round(
                base_sales
                * case project_id when 101 then 1.08 when 102 then 1.00 else 0.92 end
                * case extract(month from calendar_date)::integer
                    when 1 then 1.05
                    when 2 then 0.97
                    when 3 then 1.00
                    when 4 then 1.03
                    when 5 then 1.08
                    when 6 then 1.12
                    when 7 then 1.05
                    when 8 then 1.00
                    when 9 then 1.02
                    when 10 then 1.15
                    when 11 then 1.03
                    else 1.22
                end
                * case when extract(isodow from calendar_date) in (6, 7) then 1.22 else 0.96 end
                * (0.97 + ((extract(day from calendar_date)::integer % 7) * 0.015)),
                2
            )
        end as sales_amount,
        case
            when business_status <> 'operating' then 0
            else greatest(1, floor(
                base_flow
                * case project_id when 101 then 1.10 when 102 then 1.00 else 0.88 end
                * case when extract(isodow from calendar_date) in (6, 7) then 1.35 else 0.92 end
                * (0.95 + ((extract(day from calendar_date)::integer % 5) * 0.03))
            )::integer)
        end as customer_flow,
        case
            when business_status = 'operating' then rent_area
            when business_status = 'fitout' then rent_area
            else 0::numeric
        end as operating_area,
        case
            when business_status in ('pre_open', 'fitout', 'operating')
                then round(fixed_rent_monthly / extract(day from (date_trunc('month', calendar_date) + interval '1 month - 1 day')), 2)
            else 0::numeric
        end as rent_income
    from base
)
select
    operation_id,
    date_key,
    project_id,
    shop_id,
    brand_id,
    business_status,
    sales_amount,
    case
        when sales_amount = 0 then 0
        else greatest(1, floor(
            case
                when customer_flow < 150 then customer_flow * 0.42
                when customer_flow < 400 then customer_flow * 0.36
                else customer_flow * 0.28
            end
        )::integer)
    end as sales_orders,
    customer_flow,
    operating_area,
    rent_income,
    round(rent_income * 0.18, 2) as management_fee_income,
    round(sales_amount * (0.30 + ((coalesce(brand_id, 200) % 4) * 0.05)), 2) as active_member_sales,
    case
        when sales_amount = 0 then 0::numeric
        when (
            (project_id = 101 and date_key between 20240201 and 20240229)
            or (project_id = 101 and date_key between 20240705 and 20240728)
            or (project_id = 102 and date_key between 20240601 and 20240620)
            or (project_id = 102 and date_key between 20240925 and 20241007)
            or (project_id = 103 and date_key between 20240710 and 20240818)
            or (project_id = 103 and date_key between 20241201 and 20241231)
        ) then round(sales_amount * 0.045, 2)
        else round(sales_amount * 0.008, 2)
    end as coupon_writeoff_amount,
    case
        when sales_amount = 0 then 0
        when (
            (project_id = 101 and date_key between 20240201 and 20240229)
            or (project_id = 101 and date_key between 20240705 and 20240728)
            or (project_id = 102 and date_key between 20240601 and 20240620)
            or (project_id = 102 and date_key between 20240925 and 20241007)
            or (project_id = 103 and date_key between 20240710 and 20240818)
            or (project_id = 103 and date_key between 20241201 and 20241231)
        ) then greatest(1, floor(sales_amount / 1800)::integer)
        else greatest(0, floor(sales_amount / 9000)::integer)
    end as coupon_writeoff_qty
from calc
on conflict (date_key, shop_id) do nothing;

insert into fact_member_daily (
    member_fact_id,
    date_key,
    project_id,
    member_level_id,
    total_members,
    valid_members,
    new_members,
    upgraded_members,
    downgraded_members,
    lost_members,
    active_members,
    member_sales_amount,
    member_orders,
    retention_rate,
    active_rate
)
with params as (
    select *
    from (values
        (101, 1, 42000, 18, 0.2600, 118.00),
        (101, 2, 22000, 10, 0.2450, 168.00),
        (101, 3, 7600, 3, 0.2250, 286.00),
        (101, 4, 1800, 1, 0.2050, 520.00),
        (102, 1, 36000, 15, 0.2500, 112.00),
        (102, 2, 18000, 8, 0.2350, 162.00),
        (102, 3, 6200, 3, 0.2180, 280.00),
        (102, 4, 1500, 1, 0.1980, 505.00),
        (103, 1, 24000, 12, 0.2250, 108.00),
        (103, 2, 11000, 5, 0.2100, 156.00),
        (103, 3, 3600, 2, 0.1950, 268.00),
        (103, 4, 800, 1, 0.1800, 480.00)
    ) as t(project_id, member_level_id, base_total, daily_growth, active_ratio, spend_per_member)
),
days as (
    select
        date_key,
        calendar_date,
        row_number() over (order by calendar_date) - 1 as day_index
    from dim_date
    where calendar_date between date '2024-01-01' and date '2024-12-31'
)
select
    (d.date_key::bigint * 100000) + (p.project_id * 10) + p.member_level_id as member_fact_id,
    d.date_key,
    p.project_id,
    p.member_level_id,
    (p.base_total + d.day_index * p.daily_growth
        + case when extract(month from d.calendar_date)::integer in (6, 7, 8, 12) then 220 else 0 end
    )::integer as total_members,
    floor((p.base_total + d.day_index * p.daily_growth) * 0.935)::integer as valid_members,
    (
        p.daily_growth
        + case when extract(isodow from d.calendar_date) in (6, 7) then 4 else 1 end
        + case when extract(month from d.calendar_date)::integer in (2, 6, 10, 12) then 3 else 0 end
    )::integer as new_members,
    case when extract(day from d.calendar_date)::integer % 11 = 0 then 2 else 1 end as upgraded_members,
    case when extract(day from d.calendar_date)::integer % 17 = 0 then 1 else 0 end as downgraded_members,
    case when extract(day from d.calendar_date)::integer % 19 = 0 then 1 else 0 end as lost_members,
    floor(
        (p.base_total + d.day_index * p.daily_growth)
        * (p.active_ratio + case when extract(isodow from d.calendar_date) in (6, 7) then 0.018 else -0.005 end)
    )::integer as active_members,
    round(
        floor(
            (p.base_total + d.day_index * p.daily_growth)
            * (p.active_ratio + case when extract(isodow from d.calendar_date) in (6, 7) then 0.018 else -0.005 end)
        )::numeric
        * p.spend_per_member
        * case when extract(month from d.calendar_date)::integer in (2, 6, 10, 12) then 1.08 else 1.00 end,
        2
    ) as member_sales_amount,
    greatest(
        1,
        floor(
            floor(
                (p.base_total + d.day_index * p.daily_growth)
                * (p.active_ratio + case when extract(isodow from d.calendar_date) in (6, 7) then 0.018 else -0.005 end)
            )
            * (0.92 + p.member_level_id * 0.08)
        )::integer
    ) as member_orders,
    round(
        least(0.9800, 0.8400 + p.member_level_id * 0.0250 + extract(month from d.calendar_date)::integer * 0.0020),
        4
    ) as retention_rate,
    round(
        p.active_ratio + case when extract(isodow from d.calendar_date) in (6, 7) then 0.018 else -0.005 end,
        4
    ) as active_rate
from params p
cross join days d
on conflict (date_key, project_id, member_level_id) do nothing;

insert into fact_campaign_coupon_daily (
    campaign_fact_id,
    date_key,
    project_id,
    campaign_id,
    coupon_id,
    issue_qty,
    sold_qty,
    redeemed_qty,
    redeemed_amount,
    refunded_qty,
    refunded_amount,
    expired_qty,
    order_qty,
    order_amount,
    induced_sales_amount
)
select
    (d.date_key::bigint * 10000) + c.coupon_id as campaign_fact_id,
    d.date_key,
    cp.project_id,
    cp.campaign_id,
    c.coupon_id,
    greatest(
        20,
        floor(
            case cp.campaign_id
                when 401 then 240
                when 402 then 180
                when 403 then 210
                when 404 then 280
                when 405 then 160
                else 230
            end
            * case when extract(isodow from d.calendar_date) in (6, 7) then 1.18 else 0.92 end
            * (0.94 + ((extract(day from d.calendar_date)::integer % 6) * 0.02))
        )::integer
    ) as issue_qty,
    greatest(
        8,
        floor(
            case cp.campaign_id
                when 401 then 110
                when 402 then 90
                when 403 then 96
                when 404 then 132
                when 405 then 84
                else 118
            end
            * case when extract(isodow from d.calendar_date) in (6, 7) then 1.12 else 0.95 end
        )::integer
    ) as sold_qty,
    greatest(
        6,
        floor(
            case cp.campaign_id
                when 401 then 78
                when 402 then 65
                when 403 then 70
                when 404 then 104
                when 405 then 60
                else 92
            end
            * case when extract(isodow from d.calendar_date) in (6, 7) then 1.20 else 0.88 end
        )::integer
    ) as redeemed_qty,
    round(
        greatest(
            6,
            floor(
                case cp.campaign_id
                    when 401 then 78
                    when 402 then 65
                    when 403 then 70
                    when 404 then 104
                    when 405 then 60
                    else 92
                end
                * case when extract(isodow from d.calendar_date) in (6, 7) then 1.20 else 0.88 end
            )::integer
        ) * c.coupon_amount,
        2
    ) as redeemed_amount,
    case when extract(day from d.calendar_date)::integer % 9 = 0 then 3 else 1 end as refunded_qty,
    round((case when extract(day from d.calendar_date)::integer % 9 = 0 then 3 else 1 end) * c.coupon_amount, 2) as refunded_amount,
    case when d.calendar_date = cp.end_date then 35 else 0 end as expired_qty,
    greatest(
        10,
        floor(
            case cp.campaign_id
                when 401 then 92
                when 402 then 74
                when 403 then 81
                when 404 then 110
                when 405 then 66
                else 98
            end
            * case when extract(isodow from d.calendar_date) in (6, 7) then 1.15 else 0.93 end
        )::integer
    ) as order_qty,
    round(
        greatest(
            10,
            floor(
                case cp.campaign_id
                    when 401 then 92
                    when 402 then 74
                    when 403 then 81
                    when 404 then 110
                    when 405 then 66
                    else 98
                end
                * case when extract(isodow from d.calendar_date) in (6, 7) then 1.15 else 0.93 end
            )::integer
        ) * (c.coupon_amount * 2.8),
        2
    ) as order_amount,
    round(
        greatest(
            6,
            floor(
                case cp.campaign_id
                    when 401 then 78
                    when 402 then 65
                    when 403 then 70
                    when 404 then 104
                    when 405 then 60
                    else 92
                end
                * case when extract(isodow from d.calendar_date) in (6, 7) then 1.20 else 0.88 end
            )::integer
        ) * (c.coupon_amount * 6.2),
        2
    ) as induced_sales_amount
from dim_campaign cp
join dim_coupon c on c.campaign_id = cp.campaign_id
join dim_date d on d.calendar_date between cp.start_date and cp.end_date
on conflict (date_key, coupon_id) do nothing;

insert into fact_campaign_channel_daily (
    campaign_channel_fact_id,
    date_key,
    project_id,
    campaign_id,
    channel_id,
    exposure_count,
    click_count,
    lead_count,
    spend_amount,
    settled_amount
)
with channel_map as (
    select *
    from (values
        (401, 101, 1, 0.22, 0.055, 0.18),
        (401, 101, 4, 0.18, 0.008, 0.06),
        (401, 101, 5, 0.12, 0.015, 0.10),
        (402, 101, 2, 0.20, 0.062, 0.20),
        (402, 101, 3, 0.26, 0.041, 0.12),
        (402, 101, 6, 0.10, 0.075, 0.24),
        (403, 102, 1, 0.18, 0.058, 0.19),
        (403, 102, 2, 0.22, 0.065, 0.22),
        (403, 102, 5, 0.10, 0.020, 0.11),
        (404, 102, 3, 0.30, 0.038, 0.10),
        (404, 102, 4, 0.20, 0.009, 0.05),
        (404, 102, 6, 0.12, 0.082, 0.25),
        (405, 103, 2, 0.16, 0.060, 0.23),
        (405, 103, 5, 0.14, 0.018, 0.12),
        (405, 103, 6, 0.10, 0.085, 0.27),
        (406, 103, 1, 0.22, 0.057, 0.20),
        (406, 103, 3, 0.24, 0.039, 0.11),
        (406, 103, 5, 0.12, 0.016, 0.09)
    ) as t(campaign_id, project_id, channel_id, budget_share, click_rate, lead_rate)
),
campaign_days as (
    select
        cp.campaign_id,
        cp.project_id,
        cp.budget_amount,
        d.date_key,
        d.calendar_date,
        row_number() over (partition by cp.campaign_id order by d.calendar_date) as day_seq
    from dim_campaign cp
    join dim_date d on d.calendar_date between cp.start_date and cp.end_date
),
calc as (
    select
        cd.campaign_id,
        cd.project_id,
        cm.channel_id,
        cd.date_key,
        cd.calendar_date,
        round(cd.budget_amount * cm.budget_share / 8.5, 2) as base_spend,
        case cd.campaign_id
            when 401 then 38000
            when 402 then 32000
            when 403 then 36000
            when 404 then 41000
            when 405 then 28000
            else 34000
        end as base_exposure,
        cm.click_rate,
        cm.lead_rate
    from campaign_days cd
    join channel_map cm on cm.campaign_id = cd.campaign_id
)
select
    (date_key::bigint * 100000) + (campaign_id * 10) + channel_id as campaign_channel_fact_id,
    date_key,
    project_id,
    campaign_id,
    channel_id,
    greatest(
        100,
        floor(
            base_exposure
            * case when extract(isodow from calendar_date) in (6, 7) then 1.22 else 0.94 end
            * (0.92 + ((extract(day from calendar_date)::integer % 6) * 0.025))
        )::integer
    ) as exposure_count,
    greatest(
        10,
        floor(
            greatest(
                100,
                floor(
                    base_exposure
                    * case when extract(isodow from calendar_date) in (6, 7) then 1.22 else 0.94 end
                    * (0.92 + ((extract(day from calendar_date)::integer % 6) * 0.025))
                )::integer
            ) * click_rate
        )::integer
    ) as click_count,
    greatest(
        2,
        floor(
            greatest(
                10,
                floor(
                    greatest(
                        100,
                        floor(
                            base_exposure
                            * case when extract(isodow from calendar_date) in (6, 7) then 1.22 else 0.94 end
                            * (0.92 + ((extract(day from calendar_date)::integer % 6) * 0.025))
                        )::integer
                    ) * click_rate
                )::integer
            ) * lead_rate
        )::integer
    ) as lead_count,
    round(
        base_spend
        * case when extract(isodow from calendar_date) in (6, 7) then 1.15 else 0.95 end
        * (0.94 + ((extract(day from calendar_date)::integer % 5) * 0.02)),
        2
    ) as spend_amount,
    round(
        round(
            base_spend
            * case when extract(isodow from calendar_date) in (6, 7) then 1.15 else 0.95 end
            * (0.94 + ((extract(day from calendar_date)::integer % 5) * 0.02)),
            2
        ) * 0.86,
        2
    ) as settled_amount
from calc
on conflict (date_key, campaign_id, channel_id) do nothing;

insert into fact_campaign_daily_performance (
    campaign_performance_fact_id,
    date_key,
    project_id,
    campaign_id,
    activity_visitors,
    participating_shop_count,
    new_members,
    activated_members,
    member_sales_amount,
    onsite_orders
)
with campaign_days as (
    select
        cp.campaign_id,
        cp.project_id,
        d.date_key,
        d.calendar_date,
        cp.campaign_type
    from dim_campaign cp
    join dim_date d on d.calendar_date between cp.start_date and cp.end_date
)
select
    (date_key::bigint * 10000) + campaign_id as campaign_performance_fact_id,
    date_key,
    project_id,
    campaign_id,
    greatest(
        120,
        floor(
            case campaign_id
                when 401 then 1800
                when 402 then 1200
                when 403 then 1600
                when 404 then 2100
                when 405 then 1300
                else 1700
            end
            * case when extract(isodow from calendar_date) in (6, 7) then 1.35 else 0.88 end
            * (0.95 + ((extract(day from calendar_date)::integer % 7) * 0.02))
        )::integer
    ) as activity_visitors,
    case campaign_id
        when 401 then 48
        when 402 then 35
        when 403 then 42
        when 404 then 55
        when 405 then 30
        else 46
    end as participating_shop_count,
    greatest(
        8,
        floor(
            case campaign_type
                when '会员营销' then 72
                when '家庭营销' then 46
                when '品类营销' then 38
                else 52
            end
            * case when extract(isodow from calendar_date) in (6, 7) then 1.25 else 0.90 end
        )::integer
    ) as new_members,
    greatest(
        10,
        floor(
            case campaign_type
                when '会员营销' then 110
                when '家庭营销' then 72
                when '品类营销' then 60
                else 86
            end
            * case when extract(isodow from calendar_date) in (6, 7) then 1.18 else 0.92 end
        )::integer
    ) as activated_members,
    round(
        greatest(
            120,
            floor(
                case campaign_id
                    when 401 then 1800
                    when 402 then 1200
                    when 403 then 1600
                    when 404 then 2100
                    when 405 then 1300
                    else 1700
                end
                * case when extract(isodow from calendar_date) in (6, 7) then 1.35 else 0.88 end
                * (0.95 + ((extract(day from calendar_date)::integer % 7) * 0.02))
            )::integer
        ) * case project_id when 101 then 26.0 when 102 then 24.5 else 21.0 end,
        2
    ) as member_sales_amount,
    greatest(
        30,
        floor(
            case campaign_id
                when 401 then 220
                when 402 then 160
                when 403 then 190
                when 404 then 260
                when 405 then 150
                else 210
            end
            * case when extract(isodow from calendar_date) in (6, 7) then 1.22 else 0.90 end
        )::integer
    ) as onsite_orders
from campaign_days
on conflict (date_key, campaign_id) do nothing;

insert into fact_work_order (
    work_order_id,
    ticket_no,
    project_id,
    area_id,
    equipment_id,
    work_order_type_id,
    vendor_id,
    reported_date_key,
    assigned_date_key,
    arrived_date_key,
    closed_date_key,
    priority_level,
    work_order_status,
    source_channel,
    response_minutes,
    repair_minutes,
    close_minutes,
    first_fix_flag,
    overtime_flag,
    satisfaction_score
)
with days as (
    select date_key, calendar_date
    from dim_date
    where calendar_date between date '2024-01-01' and date '2024-12-31'
),
base as (
    select
        d.date_key,
        d.calendar_date,
        p.project_id,
        case p.project_id when 101 then 10014 when 102 then 10024 else 10034 end as area_id,
        case p.project_id when 101 then 20001 when 102 then 20005 else 20009 end as hvac_equipment_id,
        case p.project_id when 101 then 20002 when 102 then 20006 else 20010 end as elec_equipment_id,
        case p.project_id when 101 then 20003 when 102 then 20008 else 20012 end as transport_equipment_id
    from days d
    cross join dim_project p
    where extract(day from d.calendar_date)::integer in (3, 8, 12, 18, 24, 28)
)
select
    (date_key::bigint * 1000) + project_id as work_order_id,
    'WO-' || project_id || '-' || date_key as ticket_no,
    project_id,
    area_id,
    case
        when extract(day from calendar_date)::integer in (3, 18) then hvac_equipment_id
        when extract(day from calendar_date)::integer in (8, 24) then elec_equipment_id
        else transport_equipment_id
    end as equipment_id,
    case
        when extract(day from calendar_date)::integer in (3, 18) then 1
        when extract(day from calendar_date)::integer in (8, 24) then 2
        when extract(day from calendar_date)::integer in (12, 28) then 3
        else 6
    end as work_order_type_id,
    case
        when extract(day from calendar_date)::integer in (3, 18) then 1
        when extract(day from calendar_date)::integer in (8, 24) then 2
        when extract(day from calendar_date)::integer in (12, 28) then 3
        else 5
    end as vendor_id,
    date_key as reported_date_key,
    date_key as assigned_date_key,
    date_key as arrived_date_key,
    cast(to_char(least(date '2024-12-31', calendar_date + interval '1 day'), 'YYYYMMDD') as integer) as closed_date_key,
    case when extract(day from calendar_date)::integer in (12, 24) then 'high' else 'medium' end as priority_level,
    'closed' as work_order_status,
    case when extract(day from calendar_date)::integer = 28 then '客服报修' else '巡检发现' end as source_channel,
    case when extract(day from calendar_date)::integer in (12, 24) then 75 else 35 end as response_minutes,
    case when extract(day from calendar_date)::integer in (12, 24) then 210 else 95 end as repair_minutes,
    case when extract(day from calendar_date)::integer in (12, 24) then 320 else 160 end as close_minutes,
    extract(day from calendar_date)::integer not in (24, 28) as first_fix_flag,
    extract(day from calendar_date)::integer in (24, 28) as overtime_flag,
    case when extract(day from calendar_date)::integer in (24, 28) then 3 else 4 end as satisfaction_score
from base
on conflict (work_order_id) do nothing;

insert into fact_inspection_record (
    inspection_id,
    project_id,
    area_id,
    equipment_id,
    vendor_id,
    inspection_date_key,
    inspection_type,
    planned_count,
    completed_count,
    abnormal_count,
    rectified_count
)
with days as (
    select date_key, calendar_date
    from dim_date
    where calendar_date between date '2024-01-01' and date '2024-12-31'
      and extract(day from calendar_date)::integer in (1, 7, 14, 21, 28)
)
select
    (date_key::bigint * 1000) + area_id as inspection_id,
    a.project_id,
    a.area_id,
    case a.project_id when 101 then 20001 when 102 then 20005 else 20009 end as equipment_id,
    1 as vendor_id,
    d.date_key as inspection_date_key,
    'weekly' as inspection_type,
    12 as planned_count,
    case when extract(day from d.calendar_date)::integer = 28 then 11 else 12 end as completed_count,
    case when extract(day from d.calendar_date)::integer in (14, 28) then 2 else 1 end as abnormal_count,
    case when extract(day from d.calendar_date)::integer = 28 then 1 else 2 end as rectified_count
from days d
join dim_area a on a.area_type = 'plant_room'
on conflict (inspection_id) do nothing;

insert into fact_energy_daily (
    energy_fact_id,
    date_key,
    project_id,
    area_id,
    system_id,
    electricity_kwh,
    water_ton,
    gas_ton,
    cooling_ton_hour,
    energy_cost_amount,
    customer_flow,
    operating_hours
)
with days as (
    select date_key, calendar_date
    from dim_date
    where calendar_date between date '2024-01-01' and date '2024-12-31'
),
base as (
    select
        d.date_key,
        d.calendar_date,
        a.project_id,
        a.area_id,
        case a.area_type
            when 'plant_room' then 1
            when 'public_area' then 2
            when 'atrium' then 4
            else 5
        end as system_id,
        a.managed_area
    from days d
    join dim_area a on true
)
select
    (date_key::bigint * 100000) + area_id as energy_fact_id,
    date_key,
    project_id,
    area_id,
    system_id,
    round(
        managed_area
        * case project_id when 101 then 0.42 when 102 then 0.39 else 0.36 end
        * case when extract(month from calendar_date)::integer in (6, 7, 8, 9) then 1.35 else 0.92 end
        * case when extract(isodow from calendar_date) in (6, 7) then 1.08 else 0.97 end,
        2
    ) as electricity_kwh,
    round(managed_area * 0.012, 2) as water_ton,
    round(managed_area * 0.0025, 2) as gas_ton,
    round(
        managed_area
        * case when extract(month from calendar_date)::integer in (6, 7, 8, 9) then 0.28 else 0.16 end,
        2
    ) as cooling_ton_hour,
    round(
        managed_area
        * case project_id when 101 then 0.55 when 102 then 0.51 else 0.47 end
        * case when extract(month from calendar_date)::integer in (6, 7, 8, 9) then 1.22 else 0.93 end,
        2
    ) as energy_cost_amount,
    greatest(
        150,
        floor(
            managed_area
            * case project_id when 101 then 0.18 when 102 then 0.16 else 0.14 end
            * case when extract(isodow from calendar_date) in (6, 7) then 1.35 else 0.92 end
        )::integer
    ) as customer_flow,
    case when extract(isodow from calendar_date) in (6, 7) then 13.5 else 12.0 end as operating_hours
from base
on conflict (energy_fact_id) do nothing;

insert into fact_safety_issue (
    safety_issue_id,
    project_id,
    area_id,
    issue_date_key,
    rectify_due_date_key,
    closed_date_key,
    issue_category,
    risk_level,
    issue_status,
    overtime_flag
)
with issue_dates as (
    select date_key, calendar_date
    from dim_date
    where calendar_date between date '2024-01-01' and date '2024-12-31'
      and extract(day from calendar_date)::integer in (6, 15, 26)
)
select
    (date_key::bigint * 1000) + project_id as safety_issue_id,
    a.project_id,
    a.area_id,
    d.date_key as issue_date_key,
    cast(to_char(least(date '2024-12-31', d.calendar_date + interval '7 day'), 'YYYYMMDD') as integer) as rectify_due_date_key,
    cast(to_char(least(date '2024-12-31', d.calendar_date + interval '10 day'), 'YYYYMMDD') as integer) as closed_date_key,
    case
        when extract(day from d.calendar_date)::integer = 6 then 'fire'
        when extract(day from d.calendar_date)::integer = 15 then 'equipment'
        else 'security'
    end as issue_category,
    case when extract(day from d.calendar_date)::integer = 26 then 'high' else 'medium' end as risk_level,
    'closed' as issue_status,
    extract(day from d.calendar_date)::integer = 26 as overtime_flag
from issue_dates d
join dim_area a on a.area_type in ('public_area', 'atrium')
on conflict (safety_issue_id) do nothing;

insert into fact_service_complaint (
    complaint_id,
    project_id,
    area_id,
    complaint_type_id,
    reported_date_key,
    closed_date_key,
    source_channel,
    complaint_status,
    close_minutes,
    satisfaction_score,
    repeat_flag,
    overtime_flag
)
with complaint_dates as (
    select date_key, calendar_date
    from dim_date
    where calendar_date between date '2024-01-01' and date '2024-12-31'
      and extract(day from calendar_date)::integer in (5, 11, 19, 27)
)
select
    (date_key::bigint * 10000) + area_id as complaint_id,
    a.project_id,
    a.area_id,
    case
        when extract(day from d.calendar_date)::integer = 5 then 1
        when extract(day from d.calendar_date)::integer = 11 then 2
        when extract(day from d.calendar_date)::integer = 19 then 3
        else 5
    end as complaint_type_id,
    d.date_key as reported_date_key,
    cast(to_char(least(date '2024-12-31', d.calendar_date + interval '1 day'), 'YYYYMMDD') as integer) as closed_date_key,
    case when extract(day from d.calendar_date)::integer in (11, 27) then '小程序' else '客服台' end as source_channel,
    'closed' as complaint_status,
    case when extract(day from d.calendar_date)::integer = 27 then 300 else 120 end as close_minutes,
    case when extract(day from d.calendar_date)::integer = 27 then 3 else 4 end as satisfaction_score,
    extract(day from d.calendar_date)::integer = 27 as repeat_flag,
    extract(day from d.calendar_date)::integer = 27 as overtime_flag
from complaint_dates d
join dim_area a on a.area_type in ('public_area', 'atrium', 'corridor')
on conflict (complaint_id) do nothing;

insert into fact_parking_daily (
    parking_fact_id,
    date_key,
    project_id,
    parking_entries,
    parking_exits,
    avg_turnover_times,
    avg_queue_minutes,
    abnormal_event_count,
    parking_revenue_amount
)
with days as (
    select date_key, calendar_date
    from dim_date
    where calendar_date between date '2024-01-01' and date '2024-12-31'
)
select
    (date_key::bigint * 1000) + project_id as parking_fact_id,
    date_key,
    project_id,
    greatest(
        200,
        floor(
            case project_id when 101 then 2500 when 102 then 2100 else 1650 end
            * case when extract(isodow from calendar_date) in (6, 7) then 1.28 else 0.90 end
            * case when extract(month from calendar_date)::integer in (5, 6, 10, 12) then 1.10 else 0.96 end
        )::integer
    ) as parking_entries,
    greatest(
        200,
        floor(
            case project_id when 101 then 2480 when 102 then 2085 else 1630 end
            * case when extract(isodow from calendar_date) in (6, 7) then 1.26 else 0.91 end
            * case when extract(month from calendar_date)::integer in (5, 6, 10, 12) then 1.08 else 0.97 end
        )::integer
    ) as parking_exits,
    round(case project_id when 101 then 2.45 when 102 then 2.30 else 2.12 end, 2) as avg_turnover_times,
    round(
        case when extract(isodow from calendar_date) in (6, 7) then 8.5 else 4.2 end
        + case when project_id = 101 then 0.8 when project_id = 102 then 0.5 else 0.3 end,
        2
    ) as avg_queue_minutes,
    case when extract(day from calendar_date)::integer in (1, 15, 30) then 2 else 0 end as abnormal_event_count,
    round(
        greatest(
            200,
            floor(
                case project_id when 101 then 2500 when 102 then 2100 else 1650 end
                * case when extract(isodow from calendar_date) in (6, 7) then 1.28 else 0.90 end
                * case when extract(month from calendar_date)::integer in (5, 6, 10, 12) then 1.10 else 0.96 end
            )::integer
        ) * case project_id when 101 then 8.2 when 102 then 7.6 else 6.9 end,
        2
    ) as parking_revenue_amount
from days
cross join dim_project
on conflict (parking_fact_id) do nothing;

insert into fact_finance_monthly (
    finance_fact_id,
    month_key,
    project_id,
    revenue_amount,
    operating_cost_amount,
    gross_profit_amount,
    gross_margin,
    net_profit_amount,
    net_margin,
    budget_revenue_amount,
    budget_cost_amount,
    rent_revenue_amount,
    property_fee_amount,
    parking_revenue_amount,
    marketing_expense_amount,
    admin_expense_amount,
    cash_in_amount,
    cash_out_amount,
    occupancy_rate,
    opening_rate
)
with month_series as (
    select
        date_trunc('month', calendar_date)::date as month_begin
    from dim_date
    where calendar_date between date '2024-01-01' and date '2024-12-31'
    group by 1
),
project_base as (
    select *
    from (values
        (101, 6900000.00, 0.59, 0.9500, 0.9150),
        (102, 5600000.00, 0.61, 0.9250, 0.8900),
        (103, 4300000.00, 0.66, 0.8600, 0.8050)
    ) as t(project_id, base_revenue, cost_ratio, base_occupancy, base_opening)
)
select
    (cast(to_char(s.month_begin, 'YYYYMMDD') as bigint) * 1000) + s.project_id as finance_fact_id,
    cast(to_char(s.month_begin, 'YYYYMMDD') as integer) as month_key,
    s.project_id,
    revenue_amount,
    operating_cost_amount,
    gross_profit_amount,
    round(gross_profit_amount / nullif(revenue_amount, 0), 4) as gross_margin,
    net_profit_amount,
    round(net_profit_amount / nullif(revenue_amount, 0), 4) as net_margin,
    round(revenue_amount * 1.035, 2) as budget_revenue_amount,
    round(operating_cost_amount * 0.985, 2) as budget_cost_amount,
    round(revenue_amount * 0.68, 2) as rent_revenue_amount,
    round(revenue_amount * 0.14, 2) as property_fee_amount,
    round(revenue_amount * 0.08, 2) as parking_revenue_amount,
    round(revenue_amount * 0.06, 2) as marketing_expense_amount,
    round(revenue_amount * 0.07, 2) as admin_expense_amount,
    round(revenue_amount * 1.06, 2) as cash_in_amount,
    round(operating_cost_amount * 1.03, 2) as cash_out_amount,
    occupancy_rate,
    opening_rate
from (
    select
        m.month_begin,
        p.project_id,
        round(
            p.base_revenue
            * case extract(month from m.month_begin)::integer
                when 1 then 1.02
                when 2 then 0.96
                when 3 then 1.00
                when 4 then 1.01
                when 5 then 1.06
                when 6 then 1.08
                when 7 then 1.05
                when 8 then 1.00
                when 9 then 1.03
                when 10 then 1.12
                when 11 then 1.04
                else 1.18
            end
            * case p.project_id when 101 then 1.03 when 102 then 1.00 else 0.95 end,
            2
        ) as revenue_amount,
        round(
            round(
                p.base_revenue
                * case extract(month from m.month_begin)::integer
                    when 1 then 1.02
                    when 2 then 0.96
                    when 3 then 1.00
                    when 4 then 1.01
                    when 5 then 1.06
                    when 6 then 1.08
                    when 7 then 1.05
                    when 8 then 1.00
                    when 9 then 1.03
                    when 10 then 1.12
                    when 11 then 1.04
                    else 1.18
                end
                * case p.project_id when 101 then 1.03 when 102 then 1.00 else 0.95 end,
                2
            ) * p.cost_ratio,
            2
        ) as operating_cost_amount,
        round(
            round(
                p.base_revenue
                * case extract(month from m.month_begin)::integer
                    when 1 then 1.02
                    when 2 then 0.96
                    when 3 then 1.00
                    when 4 then 1.01
                    when 5 then 1.06
                    when 6 then 1.08
                    when 7 then 1.05
                    when 8 then 1.00
                    when 9 then 1.03
                    when 10 then 1.12
                    when 11 then 1.04
                    else 1.18
                end
                * case p.project_id when 101 then 1.03 when 102 then 1.00 else 0.95 end,
                2
            ) * (1 - p.cost_ratio),
            2
        ) as gross_profit_amount,
        round(
            round(
                p.base_revenue
                * case extract(month from m.month_begin)::integer
                    when 1 then 1.02
                    when 2 then 0.96
                    when 3 then 1.00
                    when 4 then 1.01
                    when 5 then 1.06
                    when 6 then 1.08
                    when 7 then 1.05
                    when 8 then 1.00
                    when 9 then 1.03
                    when 10 then 1.12
                    when 11 then 1.04
                    else 1.18
                end
                * case p.project_id when 101 then 1.03 when 102 then 1.00 else 0.95 end,
                2
            ) * (1 - p.cost_ratio) - (
                round(
                    p.base_revenue
                    * case extract(month from m.month_begin)::integer
                        when 1 then 1.02
                        when 2 then 0.96
                        when 3 then 1.00
                        when 4 then 1.01
                        when 5 then 1.06
                        when 6 then 1.08
                        when 7 then 1.05
                        when 8 then 1.00
                        when 9 then 1.03
                        when 10 then 1.12
                        when 11 then 1.04
                        else 1.18
                    end
                    * case p.project_id when 101 then 1.03 when 102 then 1.00 else 0.95 end,
                    2
                ) * 0.13
            ),
            2
        ) as net_profit_amount,
        round(
            least(0.9900, p.base_occupancy + extract(month from m.month_begin)::integer * 0.0025),
            4
        ) as occupancy_rate,
        round(
            least(0.9800, p.base_opening + extract(month from m.month_begin)::integer * 0.0030),
            4
        ) as opening_rate
    from month_series m
    cross join project_base p
) s
on conflict (month_key, project_id) do nothing;

insert into fact_rental_budget_monthly (
    rental_budget_id,
    month_key,
    project_id,
    subject_id,
    budget_amount
)
with month_series as (
    select
        calendar_date as month_begin,
        date_key as month_key
    from dim_date
    where is_month_start
      and calendar_date between date '2024-01-01' and date '2024-12-01'
),
active_contract_month as (
    select
        m.month_begin,
        m.month_key,
        c.project_id,
        c.contract_id,
        c.rent_type,
        c.fixed_rent_monthly,
        c.sales_target_monthly,
        c.commission_rate
    from month_series m
    join fact_leasing_contract c
      on c.lease_start_date <= (m.month_begin + interval '1 month - 1 day')::date
     and c.lease_end_date >= m.month_begin
),
rent_budget as (
    select
        month_key,
        project_id,
        round(sum(
            fixed_rent_monthly
            * case extract(month from month_begin)::integer
                when 1 then 1.01
                when 2 then 0.98
                when 3 then 1.00
                when 4 then 1.01
                when 5 then 1.03
                when 6 then 1.05
                when 7 then 1.03
                when 8 then 1.01
                when 9 then 1.02
                when 10 then 1.08
                when 11 then 1.04
                else 1.10
            end
            + case
                when rent_type = 'fixed_plus_commission'
                    then sales_target_monthly * commission_rate * 0.60
                else 0
            end
        ), 2) as budget_amount
    from active_contract_month
    group by month_key, project_id
)
select
    (rb.month_key::bigint * 1000) + (rb.project_id * 10) + s.subject_id as rental_budget_id,
    rb.month_key,
    rb.project_id,
    s.subject_id,
    round(
        case s.subject_id
            when 1 then rb.budget_amount
            when 2 then rb.budget_amount * 0.18
            when 3 then rb.budget_amount * 0.05
        end,
        2
    ) as budget_amount
from rent_budget rb
join dim_fee_subject s on s.subject_id in (1, 2, 3)
on conflict (month_key, project_id, subject_id) do nothing;

insert into fact_receivable_bill (
    bill_id,
    bill_no,
    bill_month_key,
    bill_date_key,
    due_date_key,
    project_id,
    customer_id,
    contract_id,
    shop_id,
    subject_id,
    fee_period_start,
    fee_period_end,
    bill_amount,
    reduction_amount,
    receivable_amount,
    bill_status
)
with month_series as (
    select
        calendar_date as month_begin,
        date_key as month_key
    from dim_date
    where is_month_start
      and calendar_date between date '2024-01-01' and date '2024-12-01'
),
active_contract_month as (
    select
        m.month_begin,
        m.month_key,
        c.project_id,
        c.contract_id,
        c.shop_id,
        t.customer_id,
        c.rent_type,
        c.fixed_rent_monthly,
        c.sales_target_monthly,
        c.commission_rate
    from month_series m
    join fact_leasing_contract c
      on c.lease_start_date <= (m.month_begin + interval '1 month - 1 day')::date
     and c.lease_end_date >= m.month_begin
    join dim_tenant_customer t on t.contract_id = c.contract_id
),
bill_source as (
    select
        acm.month_begin,
        acm.month_key,
        acm.project_id,
        acm.customer_id,
        acm.contract_id,
        acm.shop_id,
        1 as subject_id,
        round(
            acm.fixed_rent_monthly
            * case extract(month from acm.month_begin)::integer
                when 1 then 1.01
                when 2 then 0.98
                when 3 then 1.00
                when 4 then 1.01
                when 5 then 1.03
                when 6 then 1.05
                when 7 then 1.03
                when 8 then 1.01
                when 9 then 1.02
                when 10 then 1.08
                when 11 then 1.04
                else 1.10
            end
            + case
                when acm.rent_type = 'fixed_plus_commission'
                    then acm.sales_target_monthly * acm.commission_rate * 0.52
                else 0
            end,
            2
        ) as bill_amount,
        round(
            case
                when acm.project_id = 103 and extract(month from acm.month_begin)::integer in (1, 2, 3) then acm.fixed_rent_monthly * 0.05
                when acm.project_id = 101 and extract(month from acm.month_begin)::integer = 10 then acm.fixed_rent_monthly * 0.03
                else 0
            end,
            2
        ) as reduction_amount
    from active_contract_month acm

    union all

    select
        acm.month_begin,
        acm.month_key,
        acm.project_id,
        acm.customer_id,
        acm.contract_id,
        acm.shop_id,
        2 as subject_id,
        round(acm.fixed_rent_monthly * 0.18, 2) as bill_amount,
        0::numeric(16,2) as reduction_amount
    from active_contract_month acm

    union all

    select
        acm.month_begin,
        acm.month_key,
        acm.project_id,
        acm.customer_id,
        acm.contract_id,
        acm.shop_id,
        3 as subject_id,
        round(
            case
                when extract(month from acm.month_begin)::integer in (3, 6, 9, 12)
                    then greatest(acm.fixed_rent_monthly * 0.05, 6000)
                else greatest(acm.fixed_rent_monthly * 0.02, 2000)
            end,
            2
        ) as bill_amount,
        0::numeric(16,2) as reduction_amount
    from active_contract_month acm
    where acm.project_id in (101, 102, 103)
      and acm.contract_id in (5001, 5002, 5004, 5007, 5008, 5009, 5013, 5014, 5015)
)
select
    (bs.month_key::bigint * 100000) + (bs.contract_id * 10) + bs.subject_id as bill_id,
    'BILL-' || bs.project_id || '-' || bs.contract_id || '-' || bs.subject_id || '-' || to_char(bs.month_begin, 'YYYYMM') as bill_no,
    bs.month_key as bill_month_key,
    cast(to_char((bs.month_begin + interval '4 day')::date, 'YYYYMMDD') as integer) as bill_date_key,
    cast(to_char((bs.month_begin + interval '9 day')::date, 'YYYYMMDD') as integer) as due_date_key,
    bs.project_id,
    bs.customer_id,
    bs.contract_id,
    bs.shop_id,
    bs.subject_id,
    bs.month_begin as fee_period_start,
    (bs.month_begin + interval '1 month - 1 day')::date as fee_period_end,
    bs.bill_amount,
    bs.reduction_amount,
    round(bs.bill_amount - bs.reduction_amount, 2) as receivable_amount,
    'issued' as bill_status
from bill_source bs
on conflict (bill_id) do nothing;

insert into fact_cash_receipt (
    receipt_id,
    receipt_no,
    receipt_date_key,
    project_id,
    customer_id,
    bill_id,
    subject_id,
    receipt_amount,
    payment_channel,
    payment_method
)
with bill_base as (
    select
        b.bill_id,
        b.bill_no,
        b.bill_month_key,
        dbill.calendar_date as bill_month_date,
        ddue.calendar_date as due_date,
        b.project_id,
        b.customer_id,
        b.subject_id,
        b.receivable_amount,
        greatest(
            0.55,
            least(
                1.00,
                case b.project_id
                    when 101 then 0.95
                    when 102 then 0.92
                    else 0.87
                end
                + case b.subject_id
                    when 1 then 0.03
                    when 2 then -0.02
                    when 3 then -0.01
                    else 0
                end
                + case
                    when extract(month from dbill.calendar_date)::integer in (2, 6, 10, 12) then 0.02
                    else 0
                end
                + case
                    when b.customer_id in (9006, 9012, 9017) then -0.12
                    when b.customer_id in (9002, 9008, 9010) then -0.05
                    else 0
                end
            )
        ) as receipt_ratio
    from fact_receivable_bill b
    join dim_date dbill on dbill.date_key = b.bill_month_key
    join dim_date ddue on ddue.date_key = b.due_date_key
),
receipt_source as (
    select
        bill_id,
        project_id,
        customer_id,
        subject_id,
        round(receivable_amount * receipt_ratio, 2) as receipt_amount,
        least(
            date '2024-12-31',
            case
                when receipt_ratio >= 0.98 then (due_date + interval '2 day')::date
                when receipt_ratio >= 0.93 then (due_date + interval '15 day')::date
                when receipt_ratio >= 0.85 then (due_date + interval '35 day')::date
                else (due_date + interval '65 day')::date
            end
        ) as receipt_date
    from bill_base
    where round(receivable_amount * receipt_ratio, 2) > 0
)
select
    bill_id as receipt_id,
    'RCPT-' || bill_id as receipt_no,
    cast(to_char(receipt_date, 'YYYYMMDD') as integer) as receipt_date_key,
    project_id,
    customer_id,
    bill_id,
    subject_id,
    receipt_amount,
    case
        when subject_id = 1 then '资产租赁系统'
        when subject_id = 2 then '商户服务平台'
        else '人工导入'
    end as payment_channel,
    case
        when customer_id in (9006, 9012, 9017) then '银行转账'
        when subject_id = 2 then '线上缴费'
        else '托收'
    end as payment_method
from receipt_source
on conflict (receipt_id) do nothing;

insert into fact_ar_aging_snapshot (
    aging_snapshot_id,
    snapshot_date_key,
    bill_id,
    project_id,
    customer_id,
    subject_id,
    outstanding_amount,
    days_past_due,
    aging_bucket
)
with month_end as (
    select
        date_key as snapshot_date_key,
        calendar_date as snapshot_date
    from dim_date
    where is_month_end
      and calendar_date between date '2024-01-31' and date '2024-12-31'
),
bill_receipt as (
    select
        me.snapshot_date_key,
        me.snapshot_date,
        b.bill_id,
        b.project_id,
        b.customer_id,
        b.subject_id,
        ddue.calendar_date as due_date,
        b.receivable_amount,
        coalesce(sum(r.receipt_amount) filter (where dr.calendar_date <= me.snapshot_date), 0) as received_amount
    from month_end me
    join fact_receivable_bill b on true
    join dim_date ddue on ddue.date_key = b.due_date_key
    left join fact_cash_receipt r on r.bill_id = b.bill_id
    left join dim_date dr on dr.date_key = r.receipt_date_key
    where ddue.calendar_date <= me.snapshot_date
    group by
        me.snapshot_date_key,
        me.snapshot_date,
        b.bill_id,
        b.project_id,
        b.customer_id,
        b.subject_id,
        ddue.calendar_date,
        b.receivable_amount
)
select
    (snapshot_date_key::bigint * 1000000) + bill_id as aging_snapshot_id,
    snapshot_date_key,
    bill_id,
    project_id,
    customer_id,
    subject_id,
    round(receivable_amount - received_amount, 2) as outstanding_amount,
    greatest(0, (snapshot_date - due_date))::integer as days_past_due,
    case
        when greatest(0, (snapshot_date - due_date)) <= 30 then '0-30天'
        when greatest(0, (snapshot_date - due_date)) <= 60 then '31-60天'
        when greatest(0, (snapshot_date - due_date)) <= 90 then '61-90天'
        when greatest(0, (snapshot_date - due_date)) <= 180 then '91-180天'
        else '180天以上'
    end as aging_bucket
from bill_receipt
where round(receivable_amount - received_amount, 2) > 0
on conflict (snapshot_date_key, bill_id) do nothing;
