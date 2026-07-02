app BlogApp {
  database: sqlite @path("./data/blog.db")
  features: [cors, swagger]
}

enum PostStatus {
  DRAFT
  PUBLISHED
}

entity User {
  email: string @required @email @unique
  name: string @required @minLength(1) @maxLength(100)
  posts: Post[] @OneToMany(inverse: author)
}

entity Post {
  title: string @required @minLength(3) @maxLength(200)
  status: PostStatus @required @default("DRAFT")
  author: User @ManyToOne(inverse: posts) @onDelete(CASCADE)
}

dto CreatePost for Post {
  title
  status
  author
}

module Users for User {
  route GET /users -> User[]
  route POST /users -> User
}

module Posts for Post {
  route GET /posts -> Post[]
  route POST /posts -> Post
  route PATCH /posts/:id -> Post
  route DELETE /posts/:id -> void
}
