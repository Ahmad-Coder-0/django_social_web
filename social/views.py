from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView
from django.core.paginator import Paginator
from django.db.models import Count, Exists, OuterRef, Q, Value
from django.http import HttpResponseForbidden, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme

from .forms import PostForm, ProfileForm, SignupForm
from .models import Comment, Follow, Like, Notification, Post, User


def _safe_redirect(request, fallback):
    target = request.POST.get("next") or request.GET.get("next")
    if target and url_has_allowed_host_and_scheme(
        target, allowed_hosts={request.get_host()}, require_https=request.is_secure()
    ):
        return redirect(target)
    return redirect(fallback)


def _posts_with_meta(user):
    if user is not None and user.is_authenticated:
        liked = Like.objects.filter(post=OuterRef("pk"), user=user)
        liked_expr = Exists(liked)
    else:
        liked_expr = Value(False)
    return Post.objects.select_related("author").annotate(
        num_likes=Count("likes", distinct=True),
        num_comments=Count("comments", distinct=True),
        liked_by_me=liked_expr,
    ).order_by("-created_at", "id")


def feed(request):
    if request.user.is_authenticated:
        following_ids = Follow.objects.filter(follower=request.user).values_list(
            "following_id", flat=True
        )
        posts_qs = _posts_with_meta(request.user).filter(
            author__in=list(following_ids) + [request.user.pk]
        )
    else:
        posts_qs = _posts_with_meta(None)

    paginator = Paginator(posts_qs, 10)
    page_number = request.GET.get("page", 1)
    posts = paginator.get_page(page_number)

    if request.headers.get("HX-Request"):
        return render(request, "social/_post_list_page.html", {"posts": posts})

    return render(request, "social/feed.html", {"posts": posts})


@login_required
def post_create(request):
    if request.method == "POST":
        form = PostForm(request.POST, request.FILES)
        if form.is_valid():
            post = form.save(commit=False)
            post.author = request.user
            post.save()
            messages.success(request, "پست شما منتشر شد.")
            return redirect(post)
    else:
        form = PostForm()
    return render(request, "social/post_form.html", {"form": form})


def post_detail(request, pk):
    post = get_object_or_404(_posts_with_meta(request.user), pk=pk)
    comments = post.comments.select_related("author")
    return render(
        request,
        "social/post_detail.html",
        {
            "post": post,
            "comments": comments,
        },
    )


@login_required
def post_delete(request, pk):
    post = get_object_or_404(Post, pk=pk)
    if request.method != "POST":
        return HttpResponseForbidden("درخواست نامعتبر")
    if post.author != request.user:
        return HttpResponseForbidden("اجازهٔ حذف این پست را ندارید.")
    post.delete()
    messages.success(request, "پست حذف شد.")
    return redirect("social:feed")


@login_required
def comment_create(request, pk):
    post = get_object_or_404(Post, pk=pk)
    if request.method == "POST":
        body = request.POST.get("body", "").strip()
        if body:
            comment = Comment.objects.create(post=post, author=request.user, body=body)
            if post.author != request.user:
                Notification.objects.create(
                    recipient=post.author,
                    sender=request.user,
                    notification_type="comment",
                    post=post,
                )
            if request.headers.get("HX-Request"):
                return render(request, "social/_comment_item.html", {"comment": comment})
        else:
            if request.headers.get("HX-Request"):
                return HttpResponse("متن نظر نمی‌تواند خالی باشد.", status=400)
            messages.error(request, "متن نظر نمی‌تواند خالی باشد.")
    return redirect(post)


@login_required
def like_toggle(request, pk):
    post = get_object_or_404(_posts_with_meta(request.user), pk=pk)
    if request.method == "POST":
        like, created = Like.objects.get_or_create(post=post, user=request.user)
        if not created:
            like.delete()
        else:
            if post.author != request.user:
                Notification.objects.create(
                    recipient=post.author,
                    sender=request.user,
                    notification_type="like",
                    post=post,
                )
        post.refresh_from_db()
        # Re-evaluate annotations for template
        post = _posts_with_meta(request.user).get(pk=post.pk)

    if request.headers.get("HX-Request"):
        return render(request, "social/_like_button.html", {"post": post})

    return _safe_redirect(request, reverse("social:feed"))


@login_required
def follow_toggle(request, username):
    target = get_object_or_404(User, username=username)
    if request.method == "POST":
        if target == request.user:
            messages.error(request, "نمی‌توانید خودتان را دنبال کنید.")
        else:
            follow, created = Follow.objects.get_or_create(
                follower=request.user, following=target
            )
            if not created:
                follow.delete()
            else:
                Notification.objects.create(
                    recipient=target,
                    sender=request.user,
                    notification_type="follow",
                )
    return _safe_redirect(request, reverse("social:profile", args=[username]))


def profile(request, username):
    profile_user = get_object_or_404(User, username=username)
    posts_qs = _posts_with_meta(request.user).filter(author=profile_user)

    paginator = Paginator(posts_qs, 10)
    page_number = request.GET.get("page", 1)
    posts = paginator.get_page(page_number)

    is_following = (
        request.user.is_authenticated and request.user.is_following(profile_user)
    )

    if request.headers.get("HX-Request"):
        return render(request, "social/_post_list_page.html", {"posts": posts})

    return render(
        request,
        "social/profile.html",
        {"profile_user": profile_user, "posts": posts, "is_following": is_following},
    )


@login_required
def profile_edit(request):
    if request.method == "POST":
        form = ProfileForm(request.POST, request.FILES, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, "پروفایل به‌روزرسانی شد.")
            return redirect(request.user)
    else:
        form = ProfileForm(instance=request.user)
    return render(request, "social/profile_edit.html", {"form": form})


def search(request):
    query = request.GET.get("q", "").strip()
    users = User.objects.none()
    posts = Post.objects.none()
    comments = Comment.objects.none()

    if query:
        users = User.objects.filter(
            Q(username__icontains=query) | Q(first_name__icontains=query) | Q(last_name__icontains=query)
        ).distinct()
        posts = _posts_with_meta(request.user).filter(content__icontains=query)
        comments = Comment.objects.select_related("author", "post").filter(body__icontains=query)

    if request.headers.get("HX-Request"):
        return render(
            request,
            "social/_search_results.html",
            {"users": users, "posts": posts, "comments": comments, "query": query},
        )

    return render(
        request,
        "social/search.html",
        {"users": users, "posts": posts, "comments": comments, "query": query},
    )


@login_required
def notifications_list(request):
    notifs = request.user.notifications.select_related("sender", "post").all()
    request.user.notifications.filter(is_read=False).update(is_read=True)
    return render(request, "social/notifications.html", {"notifications": notifs})


@login_required
def notifications_unread_count(request):
    count = request.user.notifications.filter(is_read=False).count()
    return HttpResponse(f'<span id="notif-badge" class="absolute -top-1 -right-1 flex h-4 w-4 items-center justify-center rounded-full bg-rose-600 text-[10px] text-white {"" if count > 0 else "hidden"}">{count}</span>')


def signup(request):
    if request.user.is_authenticated:
        return redirect("social:feed")
    if request.method == "POST":
        form = SignupForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, "به شبکهٔ اجتماعی خوش آمدید!")
            return redirect("social:feed")
    else:
        form = SignupForm()
    return render(request, "registration/signup.html", {"form": form})


class PersianLoginView(LoginView):
    template_name = "registration/login.html"
