from django.conf import settings
from django.contrib.auth.models import User
from cloudinary.models import CloudinaryField
from django.db import models

# Create your models here.
class Profile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    date_of_birth = models.DateField(null=True, blank=True)
    address = models.CharField(max_length=255, blank=True)

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

    def __str__(self):
        return self.book_name


class Borrow(models.Model):
    book = models.ForeignKey(Book, on_delete=models.PROTECT, related_name="borrows")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="borrows")
    borrow_date = models.DateField(auto_now_add=True)
    return_date = models.DateField()
    duration_details = models.CharField(max_length=120, blank=True)

    def __str__(self):
        return f"{self.user.username} -> {self.book.book_name}"