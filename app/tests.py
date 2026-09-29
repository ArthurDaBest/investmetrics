from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.contrib.auth.tokens import default_token_generator
from django.test import TestCase
from django.urls import reverse
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode


class IJIRIEditorialPasswordSetupTests(TestCase):

    AJER_GROUP_NAME = "AJER Editorial Partner"

    def setUp(self):
        self.User = get_user_model()

        self.ajer_group = Group.objects.create(
            name=self.AJER_GROUP_NAME
        )

        self.user = self.User.objects.create_user(
            username="ajer-editor",
            email="editor.ajernet@gmail.com",
        )
        self.user.is_staff = True
        self.user.is_active = True
        self.user.set_unusable_password()
        self.user.save()

        self.user.groups.add(self.ajer_group)

    def setup_url(self, user=None, token=None):
        user = user or self.user

        uidb64 = urlsafe_base64_encode(
            force_bytes(user.pk)
        )

        token = token or default_token_generator.make_token(
            user
        )

        return reverse(
            "ijiri-editor-set-initial-password",
            kwargs={
                "uidb64": uidb64,
                "token": token,
            },
        )

    def test_ajer_user_with_unusable_password_can_open_setup_link(self):
        self.assertFalse(
            self.user.has_usable_password()
        )

        response = self.client.get(
            self.setup_url()
        )

        self.assertEqual(
            response.status_code,
            200,
        )
        self.assertFalse(
            response.context["link_invalid"]
        )
        self.assertContains(
            response,
            self.user.email,
        )

    def test_ajer_user_can_create_initial_password(self):
        url = self.setup_url()

        response = self.client.post(
            url,
            {
                "new_password1": "T9!mQ4#zP7@vL2$x",
                "new_password2": "T9!mQ4#zP7@vL2$x",
            },
        )

        self.assertRedirects(
            response,
            "/admin/",
            fetch_redirect_response=False,
        )

        self.user.refresh_from_db()

        self.assertTrue(
            self.user.has_usable_password()
        )
        self.assertTrue(
            self.user.check_password(
                "T9!mQ4#zP7@vL2$x"
            )
        )

    def test_setup_link_cannot_be_reused_after_password_creation(self):
        url = self.setup_url()

        response = self.client.post(
            url,
            {
                "new_password1": "T9!mQ4#zP7@vL2$x",
                "new_password2": "T9!mQ4#zP7@vL2$x",
            },
        )

        self.assertEqual(
            response.status_code,
            302,
        )

        second_response = self.client.get(url)

        self.assertEqual(
            second_response.status_code,
            400,
        )
        self.assertTrue(
            second_response.context["link_invalid"]
        )

    def test_invalid_token_is_rejected(self):
        response = self.client.get(
            self.setup_url(
                token="invalid-token"
            )
        )

        self.assertEqual(
            response.status_code,
            400,
        )
        self.assertTrue(
            response.context["link_invalid"]
        )

    def test_staff_user_without_ajer_group_is_rejected(self):
        other_user = self.User.objects.create_user(
            username="other-staff",
            email="other@example.com",
        )
        other_user.is_staff = True
        other_user.is_active = True
        other_user.set_unusable_password()
        other_user.save()

        response = self.client.get(
            self.setup_url(
                user=other_user
            )
        )

        self.assertEqual(
            response.status_code,
            400,
        )
        self.assertTrue(
            response.context["link_invalid"]
        )

    def test_superuser_is_rejected_even_if_in_ajer_group(self):
        superuser = self.User.objects.create_superuser(
            username="site-owner",
            email="owner@example.com",
            password="OwnerTest-9Q!m4Z#p",
        )
        superuser.groups.add(
            self.ajer_group
        )

        response = self.client.get(
            self.setup_url(
                user=superuser
            )
        )

        self.assertEqual(
            response.status_code,
            400,
        )
        self.assertTrue(
            response.context["link_invalid"]
        )

    def test_inactive_ajer_user_is_rejected(self):
        self.user.is_active = False
        self.user.save(
            update_fields=["is_active"]
        )

        response = self.client.get(
            self.setup_url()
        )

        self.assertEqual(
            response.status_code,
            400,
        )
        self.assertTrue(
            response.context["link_invalid"]
        )
