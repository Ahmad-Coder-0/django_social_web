from django import forms
from django.contrib.auth.forms import UserCreationForm

from .models import Post, User


class SignupForm(UserCreationForm):
    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("username", "first_name", "last_name", "email")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.setdefault("class", "form-input")
        self.fields["username"].label = "نام کاربری"
        self.fields["username"].help_text = "فقط حروف، اعداد و @/./+/-/_. حداکثر ۱۵۰ کاراکتر."
        self.fields["first_name"].label = "نام"
        self.fields["last_name"].label = "نام خانوادگی"
        self.fields["email"].label = "ایمیل"
        self.fields["password1"].label = "گذرواژه"
        self.fields["password2"].label = "تکرار گذرواژه"


class ProfileForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ("first_name", "last_name", "email", "phone", "job", "bio",
                  "birth_date", "profile_avatar")
        widgets = {
            "birth_date": forms.DateInput(attrs={"type": "date"}),
            "bio": forms.Textarea(attrs={"rows": 4}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.setdefault("class", "form-input")


class PostForm(forms.ModelForm):
    class Meta:
        model = Post
        fields = ("content", "image")
        widgets = {
            "content": forms.Textarea(
                attrs={"rows": 3, "placeholder": "چه خبر؟", "class": "form-input"}
            ),
            "image": forms.FileInput(attrs={"class": "form-input"}),
        }
        labels = {"content": "متن پست", "image": "تصویر (اختیاری)"}

    def clean(self):
        cleaned = super().clean()
        if not cleaned.get("content") and not cleaned.get("image"):
            raise forms.ValidationError("پست باید متن یا تصویر داشته باشد.")
        return cleaned
