app UserManagement {
  database: sqlite @path("./data/users.db")
  features: [cors, swagger]
}

entity User {
  email: string @required @email @unique @minLength(5) @maxLength(255)
  name: string @required @minLength(1) @maxLength(100)
}

module Users for User
