from django.test import TestCase
from django.urls import reverse

from .models import Comment, Follow, Like, Post, User


class SocialFlowTests(TestCase):
    def setUp(self):
        self.alice = User.objects.create_user(
            username="alice", password="testpass123", first_name="آلیس"
        )
        self.bob = User.objects.create_user(username="bob", password="testpass123")

    def test_signup_logs_user_in(self):
        response = self.client.post(
            reverse("social:signup"),
            {
                "username": "carol",
                "password1": "Sup3rSecret!",
                "password2": "Sup3rSecret!",
            },
        )
        self.assertRedirects(response, reverse("social:feed"))
        self.assertTrue(User.objects.filter(username="carol").exists())

    def test_feed_shows_followed_users_posts_only(self):
        Post.objects.create(author=self.bob, content="پست باب")
        carol = User.objects.create_user(username="carol", password="testpass123")
        Post.objects.create(author=carol, content="پست کارول")

        self.client.force_login(self.alice)
        Follow.objects.create(follower=self.alice, following=self.bob)

        response = self.client.get(reverse("social:feed"))
        self.assertContains(response, "پست باب")
        self.assertNotContains(response, "پست کارول")
        self.assertTrue(response.context["posts"].paginator.object_list.ordered)

    def test_create_post_requires_login(self):
        response = self.client.get(reverse("social:post_create"))
        self.assertEqual(response.status_code, 302)

    def test_create_post(self):
        self.client.force_login(self.alice)
        response = self.client.post(
            reverse("social:post_create"), {"content": "سلام دنیا"}
        )
        post = Post.objects.get()
        self.assertRedirects(response, post.get_absolute_url())
        self.assertEqual(post.author, self.alice)

    def test_like_toggle(self):
        post = Post.objects.create(author=self.bob, content="سلام")
        self.client.force_login(self.alice)
        self.client.post(reverse("social:like_toggle", args=[post.pk]))
        self.assertEqual(Like.objects.filter(post=post, user=self.alice).count(), 1)
        self.client.post(reverse("social:like_toggle", args=[post.pk]))
        self.assertEqual(Like.objects.filter(post=post, user=self.alice).count(), 0)

    def test_cannot_delete_others_post(self):
        post = Post.objects.create(author=self.bob, content="سلام")
        self.client.force_login(self.alice)
        response = self.client.post(reverse("social:post_delete", args=[post.pk]))
        self.assertEqual(response.status_code, 403)
        self.assertTrue(Post.objects.filter(pk=post.pk).exists())

    def test_comment_create(self):
        post = Post.objects.create(author=self.bob, content="سلام")
        self.client.force_login(self.alice)
        self.client.post(
            reverse("social:comment_create", args=[post.pk]), {"body": "نظر من"}
        )
        comment = Comment.objects.get()
        self.assertEqual(comment.author, self.alice)
        self.assertEqual(comment.body, "نظر من")

    def test_follow_toggle_and_no_self_follow(self):
        self.client.force_login(self.alice)
        self.client.post(reverse("social:follow_toggle", args=[self.bob.username]))
        self.assertTrue(self.alice.is_following(self.bob))
        self.client.post(reverse("social:follow_toggle", args=[self.bob.username]))
        self.assertFalse(self.alice.is_following(self.bob))

        self.client.post(reverse("social:follow_toggle", args=[self.alice.username]))
        self.assertFalse(Follow.objects.filter(follower=self.alice).exists())

    def test_profile_page_renders(self):
        self.client.force_login(self.alice)
        response = self.client.get(
            reverse("social:profile", args=[self.bob.username])
        )
        self.assertContains(response, "bob")
