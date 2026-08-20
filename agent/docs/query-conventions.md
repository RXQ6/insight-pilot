# 查询约定

## 时间与日期
- 默认日期范围：如果用户没有指定，先追问，不随意默认最近一个月
- 时间过滤使用半开区间：order_date >= 'YYYY-MM-DD' AND order_date < 'YYYY-MM-DD'
- 按月分组使用 to_char(order_date, 'YYYY-MM')
- 按周分组使用 to_char(order_date, 'IYYY-IW')
- 按季度使用 CASE WHEN order_date < '2026-04-01' THEN 'Q1' ELSE 'Q2' END

## 枚举取值
- 订单状态使用英文枚举：completed、pending、refunded
- 品类使用中文枚举：数码、家电、服饰、食品、美妆
- 区域使用中文枚举：华东、华南、华北、西南、华中

## 聚合与排序
- 聚合查询必须使用 GROUP BY
- 结果行数默认不超过 1000
- TopN 查询使用 ORDER BY ... DESC LIMIT N
- 图表数据优先返回类别维度和数值两列

## 空值与精度
- 合计类指标使用 coalesce(sum(x), 0)，避免空值导致结果为 NULL
- 平均类指标使用 round(avg(x), 2)
- 除法使用 ::numeric 保证小数精度

## 命名规范
- 输出列名使用英文小写蛇形命名：cnt、total、revenue、avg_amount
- 指标列加注释说明口径，例如 sum(oi.quantity * oi.price) AS revenue
