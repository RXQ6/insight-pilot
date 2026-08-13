# 数据字典

## 业务表

### customers 客户表
- id：客户 ID
- name：客户名称
- region：区域，取值：华东、华南、华北、西南、华中
- city：城市
- created_at：客户创建日期

### products 商品表
- id：商品 ID
- name：商品名称
- category：品类，取值：数码、家电、服饰、食品、美妆
- price：单价

### orders 订单表
- id：订单 ID
- customer_id：客户 ID，关联 customers.id
- order_date：下单日期
- status：订单状态，取值：completed（已完成）、pending（待支付）、refunded（已退款）
- amount：订单金额

### order_items 订单明细表
- id：明细 ID
- order_id：订单 ID，关联 orders.id
- product_id：商品 ID，关联 products.id
- quantity：数量
- price：成交单价

## 统计口径
- 销售额优先使用 order_items 的 quantity * price 计算
- 订单金额可以直接使用 orders.amount
- 时间字段统一使用 order_date，过滤时注意使用半开区间 [start, end)
