from django.contrib.auth.models import AbstractUser
from django.db import models
from django.urls import reverse


def avatar_upload_path(instance, filename):
    return f"avatars/user_{instance.pk}/{filename}"


def post_image_upload_path(instance, filename):
    return f"posts/user_{instance.author_id}/{filename}"


class User(AbstractUser):
    phone = models.CharField(max_length=11, blank=True, verbose_name="شماره تلفن")
    bio = models.TextField(blank=True, verbose_name="بیوگرافی")
    profile_avatar = models.ImageField(
        upload_to=avatar_upload_path, blank=True, verbose_name="عکس پروفایل"
    )
    birth_date = models.DateField(null=True, blank=True, verbose_name="تاریخ تولد")
    job = models.CharField(max_length=50, blank=True, verbose_name="شغل")

    def get_absolute_url(self):
        return reverse("social:profile", args=[self.username])

    def is_following(self, other):
        if not other or other.pk == self.pk:
            return False
        return Follow.objects.filter(follower=self, following=other).exists()

    def followers_count(self):
        return self.followers.count()

    def following_count(self):
        return self.following.count()

    def posts_count(self):
        return self.posts.count()

    def __str__(self):
        return self.get_full_name() or self.username


class Post(models.Model):
    author = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="posts", verbose_name="نویسنده"
    )
    content = models.TextField(verbose_name="متن")
    image = models.ImageField(
        upload_to=post_image_upload_path, blank=True, verbose_name="تصویر"
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="تاریخ انتشار")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="آخرین ویرایش")

    class Meta:
        ordering = ["-created_at", "id"]  # Added id for stable pagination
        verbose_name = "پست"
        verbose_name_plural = "پست‌ها"

    def get_absolute_url(self):
        return reverse("social:post_detail", args=[self.pk])

    def likes_count(self):
        return self.likes.count()

    def comments_count(self):
        return self.comments.count()

    def is_liked_by(self, user):
        if not user.is_authenticated:
            return False
        return self.likes.filter(user=user).exists()

    def __str__(self):
        return f"{self.author} – {self.content[:40]}"


class Comment(models.Model):
    post = models.ForeignKey(
        Post, on_delete=models.CASCADE, related_name="comments", verbose_name="پست"
    )
    author = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="comments", verbose_name="نویسنده"
    )
    body = models.TextField(verbose_name="متن نظر")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="تاریخ")

    class Meta:
        ordering = ["created_at"]
        verbose_name = "نظر"
        verbose_name_plural = "نظرات"

    def __str__(self):
        return f"{self.author} – {self.body[:30]}"


class Like(models.Model):
    post = models.ForeignKey(
        Post, on_delete=models.CASCADE, related_name="likes", verbose_name="پست"
    )
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="likes", verbose_name="کاربر"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["post", "user"], name="unique_post_like"),
        ]
        verbose_name = "پسند"
        verbose_name_plural = "پسندها"

    def __str__(self):
        return f"{self.user} liked post {self.post_id}"


class Follow(models.Model):
    follower = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="following",
        verbose_name="دنبال‌کننده",
    )
    following = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="followers",
        verbose_name="دنبال‌شونده",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["follower", "following"], name="unique_follow"
            ),
            models.CheckConstraint(
                condition=~models.Q(follower=models.F("following")),
                name="prevent_self_follow",
            ),
        ]
        verbose_name = "دنبال کردن"
        verbose_name_plural = "دنبال کردن‌ها"

    def __str__(self):
        return f"{self.follower} → {self.following}"


class Notification(models.Model):
    NOTIFICATION_TYPES = (
        ("like", "پسند"),
        ("comment", "نظر"),
        ("follow", "دنبال‌کردن"),
    )
    recipient = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="notifications", verbose_name="گیرنده"
    )
    sender = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="sent_notifications", verbose_name="فرستنده"
    )
    notification_type = models.CharField(max_length=20, choices=NOTIFICATION_TYPES, verbose_name="نوع")
    post = models.ForeignKey(
        Post, on_delete=models.CASCADE, null=True, blank=True, related_name="notifications", verbose_name="پست"
    )
    is_read = models.BooleanField(default=False, verbose_name="خوانده‌شده")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="تاریخ")

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "اعلان"
        verbose_name_plural = "اعلان‌ها"

    def __str__(self):
        return f"{self.sender} -> {self.recipient} ({self.notification_type})"

