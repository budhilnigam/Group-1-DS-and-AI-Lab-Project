"""Blueprint for blog post endpoints."""

from flask import Blueprint, render_template, request, redirect, url_for, flash
from app.models import db, Post
from app.forms import PostForm

blogBp = Blueprint("blog", __name__, url_prefix="/blog")


@blogBp.route("/")
def listPosts():
    """Return the blog index page with all published posts."""
    page = request.args.get("page", 1, type=int)
    posts = Post.query.filter_by(is_published=True).order_by(
        Post.created_at.desc()
    ).paginate(page=page, per_page=10)
    return render_template("blog/index.html", posts=posts)


@blogBp.route("/<int:postId>")
def viewPost(postId):
    """Show a single blog post by its ID."""
    post = Post.query.get_or_404(postId)
    return render_template("blog/detail.html", post=post)


@blogBp.route("/create", methods=["GET", "POST"])
def createPost():
    """Handle creation of a new blog post."""
    form = PostForm()
    if form.validate_on_submit():
        newPost = Post(
            title=form.title.data,
            body=form.body.data,
            is_published=form.publish.data,
        )
        db.session.add(newPost)
        db.session.commit()
        flash("Post created successfully.", "success")
        return redirect(url_for("blog.viewPost", postId=newPost.id))
    return render_template("blog/create.html", form=form)


@blogBp.route("/<int:postId>/edit", methods=["GET", "POST"])
def editPost(postId):
    """Edit an existing blog post."""
    post = Post.query.get_or_404(postId)
    form = PostForm(obj=post)
    if form.validate_on_submit():
        post.title = form.title.data
        post.body = form.body.data
        post.is_published = form.publish.data
        db.session.commit()
        flash("Post updated.", "info")
        return redirect(url_for("blog.viewPost", postId=post.id))
    return render_template("blog/edit.html", form=form, post=post)


@blogBp.route("/<int:postId>/delete", methods=["POST"])
def deletePost(postId):
    """Delete a blog post."""
    post = Post.query.get_or_404(postId)
    db.session.delete(post)
    db.session.commit()
    flash("Post deleted.", "warning")
    return redirect(url_for("blog.listPosts"))
