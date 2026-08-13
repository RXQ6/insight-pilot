# 订单数据排查

## 查询结果为空
1. 检查时间范围是否超出数据区间，业务数据从 2026-01-01 开始
2. 检查状态枚举是否写错，状态值必须为 completed / pending / refunded
3. 先调用 get_schema 获取真实表结构

## 金额对不上
- 订单金额看 orders.amount
- 明细销售额看 order_items.quantity * order_items.price
- 退款金额单独过滤 status = 'refunded'

## 指标口径混淆
- 订单数：count(orders.id)
- 销售额：sum(quantity * price) 或 sum(orders.amount)
- 客单价：sum(orders.amount) / count(distinct customer_id)
