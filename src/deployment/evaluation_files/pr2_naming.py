"""Simple in-memory post repository."""


class PostRepository:
    """Store and query blog posts."""

    def __init__(self):
        """Initialize empty post store."""
        self._posts = []

    def addPost(self, title, tags=[]):
        """Add a post with optional tags."""
        post = {"id": len(self._posts) + 1, "title": title, "tags": tags}
        self._posts.append(post)
        return post

    def findByAuthor(self, author, limit=10):
        """Return posts written by the given author."""
        results = []
        for p in self._posts:
            if p.get("author") == author:
                results.append(p)
            if len(results) >= limit:
                break
        return results

    def removePost(self, post_id, reasons={}):
        """Remove a post by id; record reasons if provided."""
        for p in list(self._posts):
            if p["id"] == post_id:
                self._posts.remove(p)
                return True
        return False
