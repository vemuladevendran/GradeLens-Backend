from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models

class UserRole(models.TextChoices):
    PROFESSOR = "PROFESSOR", "Professor"
    STUDENT   = "STUDENT", "Student"

class UserManager(BaseUserManager):
    use_in_migrations = True
    def _create_user(self, email, password, **extra_fields):
        if not email:
            raise ValueError("Email must be set")
        email = self.normalize_email(email)
        user = self.model(email=email, username=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user
    def create_user(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        if not extra_fields.get("role"):
            extra_fields["role"] = UserRole.STUDENT
        return self._create_user(email, password, **extra_fields)
    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("role", UserRole.PROFESSOR)
        return self._create_user(email, password, **extra_fields)

class User(AbstractUser):
    # use email as the primary credential
    email = models.EmailField(unique=True)
    role = models.CharField(max_length=16, choices=UserRole.choices, default=UserRole.STUDENT)

    username = models.CharField(max_length=150, unique=True)  # still required by AbstractUser
    first_name = models.CharField(max_length=150, blank=True)
    last_name  = models.CharField(max_length=150, blank=True)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS: list[str] = []

    objects = UserManager()

    def __str__(self) -> str:
        return f"{self.email} ({self.role})"
