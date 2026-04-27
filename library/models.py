from datetime import timedelta

from django.conf import settings
from django.contrib.auth.models import User
from cloudinary.models import CloudinaryField
from django.db import models
from django.utils import timezone

# default book borrow duration in days
DEFAULT_BOOK_BORROW_DURATION = settings.DEFAULT_BOOK_BORROW_DURATION


# Create your models here.
class Profile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    date_of_birth = models.DateField(null=True, blank=True)
    address = models.CharField(max_length=255, blank=True)
    phone_number = models.CharField(max_length=20, blank=True)

    def __str__(self):
        return self.user.username


class Author(models.Model):
    author_name = models.CharField(max_length=120, unique=True)

    def __str__(self):
        return self.author_name


class Category(models.Model):
    category_name = models.CharField(max_length=120, unique=True)

    def __str__(self):
        return self.category_name

    class Meta:
        verbose_name_plural = "Categories"


class Book(models.Model):
    book_name = models.CharField(max_length=200)
    author = models.ForeignKey(Author, on_delete=models.PROTECT, related_name="books")
    description = models.TextField(blank=True)
    cover_img = CloudinaryField('Image', null=True, blank=True)
    isbn = models.CharField(max_length=20, unique=True)
    language = models.CharField(max_length=50, blank=True)
    shelf_details = models.CharField(max_length=120, blank=True)
    category = models.ForeignKey(Category, on_delete=models.PROTECT, related_name="books")
    is_active = models.BooleanField(default=True)
    stock = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.book_name}"


class BorrowManager(models.Manager):

    def is_borrowed_by_user(self, user, book):
        """
        Determines if a book is currently borrowed or waiting by a specific user.
        Any rejected borrows a 30 days old are excluded from the check.
        """

        return super().get_queryset().filter(
            user=user,
            book=book,
        ).exclude(
            status=self.model.Status.rejected,
            created_at__gte = timezone.now() - timedelta(days=30)
        ).exists()


class Borrow(models.Model):

    class Meta:
        permissions = [
            ("issue_borrow", "can borrow the book to a user"),
            ("return_borrow", "can return the book back to library from borrow"),
            ("renew_borrow", "can renew the book borrow"),
        ]

    class Status(models.TextChoices):
        open = "OP", "Awaiting Issuance"
        issued = "IS", "Issued"
        renewed = "RE", "Renewed"
        rejected = "RJ", "Rejected"
        returned = "RT", "Returned"
        overdue = "OD", "Overdue"

    book = models.ForeignKey(Book, on_delete=models.PROTECT, related_name="borrows")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="borrows")
    created_at = models.DateTimeField(auto_now_add=True)
    issued_from = models.DateField(default=None, null=True)
    return_date = models.DateField(default=None, null=True)
    notes = models.CharField(max_length=120, blank=True)
    issued_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="issued_by",
                                  default=None, null=True)
    status = models.CharField(max_length=2, choices=Status, default=Status.open)

    objects = BorrowManager()

    def __str__(self):
        return f"{self.user.username} -> {self.book.book_name}"
