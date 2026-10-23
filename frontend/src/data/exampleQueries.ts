export interface ExampleQuery {
  id: string;
  title: string;
  description: string;
  sql: string;
}

export const EXAMPLE_QUERIES: ExampleQuery[] = [
  {
    id: 'user-first-name',
    title: 'Filter Users by First Name',
    description: 'Scans users table on an unindexed column (ideal for index recommendations and SELECT * expansion).',
    sql: "SELECT * FROM users WHERE first_name = 'Emily';",
  },
  {
    id: 'users-orders-join',
    title: 'Top Customer Orders Join',
    description: 'Multi-table join between users and orders with aggregation, grouping, and ordering.',
    sql: `SELECT u.email, count(o.id) AS total_orders, sum(o.total_amount) AS total_spent
FROM users u
JOIN orders o ON u.id = o.user_id
WHERE o.status = 'completed'
GROUP BY u.email
ORDER BY total_spent DESC
LIMIT 10;`,
  },
  {
    id: 'category-revenue',
    title: 'Category Revenue & Units Sold',
    description: 'Full 3-table join aggregation across products, order_items, and orders.',
    sql: `SELECT p.category, sum(oi.quantity) AS units_sold, sum(oi.quantity * oi.unit_price) AS revenue
FROM products p
JOIN order_items oi ON p.id = oi.product_id
JOIN orders o ON oi.order_id = o.id
WHERE o.status = 'completed'
GROUP BY p.category
ORDER BY revenue DESC;`,
  },
  {
    id: 'orders-date-status',
    title: 'Orders by Status & Date Range',
    description: 'Filters orders table using status and high-value total_amount range predicates.',
    sql: `SELECT id, user_id, order_date, status, total_amount
FROM orders
WHERE status = 'completed' AND total_amount > 500.00
ORDER BY order_date DESC
LIMIT 25;`,
  },
];
