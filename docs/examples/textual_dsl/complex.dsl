app CommerceApp {
  database: sqlite @path("./data/commerce.db")
  features: [cors, swagger]
}

enum OrderStatus {
  PENDING
  PAID
  SHIPPED
  CANCELLED
}

type Money {
  amount: number @required @min(0)
  currency: string @required @minLength(3) @maxLength(3)
}

entity Customer {
  email: string @required @email @unique
  name: string @required @minLength(1) @maxLength(100)
  orders: Order[] @OneToMany(inverse: customer)
}

entity Product {
  name: string @required @minLength(2) @maxLength(120)
  price: Money @required
  orderItems: Orderitem[] @OneToMany(inverse: product)
}

entity Order {
  status: OrderStatus @required @default("PENDING")
  customer: Customer @ManyToOne(inverse: orders) @onDelete(CASCADE)
  items: Orderitem[] @OneToMany(inverse: order)
}

entity Orderitem {
  quantity: number @required @min(1)
  order: Order @ManyToOne(inverse: items) @onDelete(CASCADE)
  product: Product @ManyToOne(inverse: orderItems)
}

dto CreateOrder for Order {
  status
  customer
  items
}

module Customers for Customer {
  route GET /customers -> Customer[]
  route POST /customers -> Customer
}

module Products for Product {
  route GET /products -> Product[]
  route POST /products -> Product
}

module Orders for Order {
  route GET /orders -> Order[]
  route POST /orders -> Order
  route PATCH /orders/:id -> Order
  route DELETE /orders/:id -> void
}
