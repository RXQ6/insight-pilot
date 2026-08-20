# 订单数据排查

## 查询结果为空
1. 检查时间范围是否超出数据区间，业务数据从 2026-01-01 开始
2. 检查状态枚举是否写错，状态值必须为 completed / pending / refunded
3. 检查区域/品类枚举是否写错，区域：华东/华南/华北/西南/华中；品类：数码/家电/服饰/食品/美妆
4. 先调用 get_schema 获取真实表结构，确认表名和列名拼写
5. 确认示例数据是否已导入：psql -U insight -d insight -f agent/data/sample_data.sql

## 金额对不上
- 订单金额看 orders.amount（一张订单一条记录）
- 明细销售额看 order_items.quantity * order_items.price
- 退款金额单独过滤 status = 'refunded'
- 促销场景下 order_items.price 可能低于 products.price，以明细价格为准

## 指标口径混淆
- 订单数：count(orders.id)
- 销售额：sum(quantity * price) 或 sum(orders.amount)
- 客单价：sum(orders.amount) / count(distinct customer_id)
- 退款率：退款订单数 / 全部订单数
- 复购客户：订单数 >= 2 的客户

## 重复数据
- 订单明细与订单 join 时如果结果翻倍，检查是否漏掉 order_items.order_id = orders.id
- 统计订单数时避免 join 明细表，直接 count(orders.id)
- 需要去重时使用 count(distinct 列)
