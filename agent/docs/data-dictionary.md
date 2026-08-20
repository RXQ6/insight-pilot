# 数据字典

## 业务表

### customers 客户表
- id：客户 ID，自增主键
- name：客户名称
- region：区域，取值：华东、华南、华北、西南、华中
- city：客户所在城市
- created_at：客户创建日期

### products 商品表
- id：商品 ID，自增主键
- name：商品名称
- category：品类，取值：数码、家电、服饰、食品、美妆
- price：商品单价，单位元

### orders 订单表
- id：订单 ID，自增主键
- customer_id：客户 ID，关联 customers.id
- order_date：下单日期
- status：订单状态，取值：completed（已完成）、pending（待支付）、refunded（已退款）
- amount：订单金额，单位元

### order_items 订单明细表
- id：明细 ID，自增主键
- order_id：订单 ID，关联 orders.id
- product_id：商品 ID，关联 products.id
- quantity：购买数量
- price：成交单价（可能不等于商品表 price，例如促销价）

## 关联关系
- 一张订单属于一个客户：orders.customer_id = customers.id
- 一张订单包含多条明细：order_items.order_id = orders.id
- 一条明细对应一个商品：order_items.product_id = products.id

## 统计口径
- 销售额优先使用 order_items 的 quantity * price 计算，不使用 orders.amount
- 订单金额可以直接使用 orders.amount（一张订单一条记录）
- 时间字段统一使用 order_date，过滤时注意使用半开区间 [start, end)
- 客单价 = sum(orders.amount) / count(distinct customers.id)
- 退款金额：过滤 status = 'refunded' 后求 sum(amount)

## 数据说明
- 示例业务数据从 2026-01-01 开始
- 区域枚举固定 5 个：华东、华南、华北、西南、华中
- 品类枚举固定 5 个：数码、家电、服饰、食品、美妆
