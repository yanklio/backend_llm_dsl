app UserManagement {
  database: sqlite @path("./data/users.db")
  features: [cors, swagger]
}

entity User {
  email: string @required @email @unique @minLength(5) @maxLength(255)
  name: string @required @minLength(1) @maxLength(100)
}

dto CreateUser for User {
  email
  name
}

module Users for User {
  route GET /users -> User[]
  route POST /users -> User
  route PATCH /users/:id -> User
  route DELETE /users/:id -> void
}
