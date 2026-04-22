from django.contrib import admin
from .models import Author, Book, Borrow, Category, Profile

# Register your models here.
admin.site.register(Profile)
admin.site.register(Author)
admin.site.register(Category)
admin.site.register(Book)
admin.site.register(Borrow)
